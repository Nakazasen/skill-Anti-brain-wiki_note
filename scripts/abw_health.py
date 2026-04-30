import argparse
import hashlib
import json
import math
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import abw_proof


TEXT_GLOBS = ("scripts/*.py", "workflows/*.md", "*.md", "*.json")
DRIFT_GLOBS = {
    "scripts/*.py": "scripts",
    "workflows/*.md": "global_workflows",
}
EPS = 1e-9
MOJIBAKE_CHARS = ("Ã", "Ä", "å", "æ", "â")
MOJIBAKE_THRESHOLD = 0.02
SUPPORTED_SOURCE_EXTENSIONS = {
    "md",
    "markdown",
    "txt",
    "rst",
    "adoc",
    "csv",
    "html",
    "htm",
    "png",
    "jpg",
    "jpeg",
    "bmp",
    "gif",
    "webp",
    "tif",
    "tiff",
    "docx",
    "xlsx",
    "pdf",
    "pptx",
}
VISIBLE_EXTENSIONS = ("docx", "xlsx", "csv", "pdf", "html", "htm", "txt")


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_runtime_id():
    return str(int(datetime.now(timezone.utc).timestamp() * 1000))


def health_log_path(workspace="."):
    return Path(workspace) / ".brain" / "cache" / "health_log.jsonl"


def health_log_enabled(persist_log=None):
    if persist_log is not None:
        return bool(persist_log)
    raw = str(os.environ.get("ABW_HEALTH_PERSIST_LOG", "0")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_text_files(workspace):
    root = Path(workspace)
    seen = set()
    for pattern in TEXT_GLOBS:
        for path in root.glob(pattern):
            if path.is_file() and path not in seen:
                seen.add(path)
                yield path


def iter_drift_pairs(workspace, runtime_root):
    workspace_root = Path(workspace)
    runtime = Path(runtime_root)
    for pattern, runtime_dir in DRIFT_GLOBS.items():
        for source in workspace_root.glob(pattern):
            if not source.is_file():
                continue
            target = _resolve_runtime_target(runtime, runtime_dir, source.name)
            if target is None:
                continue
            yield source, target


def _resolve_runtime_target(runtime_root, runtime_dir, filename):
    runtime_root = Path(runtime_root)
    if runtime_dir == "scripts":
        nested_scripts = runtime_root / "scripts"
        if nested_scripts.exists():
            return nested_scripts / filename
        if (runtime_root / "abw_runner.py").exists():
            return runtime_root / filename
        return None
    if runtime_dir == "global_workflows":
        global_workflows = runtime_root / "global_workflows"
        local_workflows = runtime_root / "workflows"
        global_target = global_workflows / filename
        local_target = local_workflows / filename
        if global_target.exists():
            return global_target
        if local_target.exists():
            return local_target
        if global_workflows.exists():
            return global_target
        if local_workflows.exists():
            return local_target
        return None
    return runtime_root / runtime_dir / filename


def check_drift(workspace=".", runtime_root=None):
    runtime_root = Path(runtime_root or (Path.home() / ".gemini" / "antigravity"))
    mismatches = []
    for source, target in iter_drift_pairs(workspace, runtime_root):
        item = {
            "workspace_file": str(source),
            "runtime_file": str(target),
        }
        if not target.exists():
            item["status"] = "MISSING"
            mismatches.append(item)
            continue

        source_hash = sha256_file(source)
        target_hash = sha256_file(target)
        item["workspace_sha256"] = source_hash
        item["runtime_sha256"] = target_hash
        if source_hash != target_hash:
            item["status"] = "DRIFT"
            mismatches.append(item)
    return mismatches


def fix_drift(workspace=".", runtime_root=None):
    runtime_root = Path(runtime_root or (Path.home() / ".gemini" / "antigravity"))
    fixes = []
    for source, target in iter_drift_pairs(workspace, runtime_root):
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        fixes.append(
            {
                "workspace_file": str(source),
                "runtime_file": str(target),
                "workspace_sha256": sha256_file(source),
                "runtime_sha256": sha256_file(target),
                "status": "MATCH" if sha256_file(source) == sha256_file(target) else "DRIFT",
            }
        )
    return fixes


def check_encoding(workspace="."):
    issues = []
    for path in iter_text_files(workspace):
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            issues.append(
                {
                    "file": str(path),
                    "problem": f"invalid UTF-8: {exc}",
                    "status": "INVALID_UTF8",
                }
            )
            continue

        if "\ufffd" in text:
            issues.append(
                {
                    "file": str(path),
                    "problem": "contains replacement character",
                    "status": "REPLACEMENT_CHAR",
                }
            )
    return issues


def detect_mojibake(text):
    content = str(text or "")
    if not content:
        return False
    suspicious_count = sum(content.count(char) for char in MOJIBAKE_CHARS)
    return suspicious_count > len(content) * MOJIBAKE_THRESHOLD


def check_mojibake(workspace="."):
    issues = []
    for path in iter_text_files(workspace):
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue

        if detect_mojibake(text):
            suspicious_count = sum(text.count(char) for char in MOJIBAKE_CHARS)
            issues.append(
                {
                    "file": str(path),
                    "problem": f"suspicious mojibake pattern count={suspicious_count}",
                    "status": "MOJIBAKE",
                }
            )
    return issues


def _file_count(path):
    path = Path(path)
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def _raw_extension_counts(workspace="."):
    raw = Path(workspace) / "raw"
    counts = {}
    if not raw.exists():
        return counts
    for path in raw.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower().lstrip(".") or "unknown"
        counts[suffix] = counts.get(suffix, 0) + 1
    return dict(sorted(counts.items()))


def _workspace_abw_version(workspace="."):
    path = Path(workspace) / "abw_config.json"
    if not path.exists():
        return "unknown"
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return "unknown"
    if not isinstance(payload, dict):
        return "unknown"
    return str(payload.get("abw_version") or "unknown")


def _is_old_abw_state(version_value):
    if version_value in {"", "unknown"}:
        return False
    try:
        parts = tuple(int(part) for part in str(version_value).split(".")[:2])
    except ValueError:
        return False
    return parts < (0, 4)


def analyze_corpus_readiness(workspace="."):
    root = Path(workspace)
    raw_count = _file_count(root / "raw")
    wiki_count = _file_count(root / "wiki")
    draft_count = _file_count(root / "drafts")
    processed_count = _file_count(root / "processed")
    corpus_dirs_present = any((root / name).exists() for name in ("raw", "wiki", "drafts"))
    extension_counts = _raw_extension_counts(root)
    supported_counts = {ext: count for ext, count in extension_counts.items() if ext in SUPPORTED_SOURCE_EXTENSIONS}
    unsupported_counts = {ext: count for ext, count in extension_counts.items() if ext not in SUPPORTED_SOURCE_EXTENSIONS}
    supported_total = sum(supported_counts.values())
    unsupported_total = sum(unsupported_counts.values())
    total_raw = supported_total + unsupported_total
    if corpus_dirs_present and raw_count == 0 and wiki_count == 0 and draft_count == 0:
        classification = "empty_corpus"
    elif raw_count > 0 and supported_total == 0:
        classification = "unsupported_corpus"
    elif raw_count > 0 and unsupported_total > 0:
        classification = "partial_supported_corpus"
    else:
        classification = "healthy_supported_corpus"
    config_version = _workspace_abw_version(root)
    flags = []
    if _is_old_abw_state(config_version):
        flags.append("old_abw_state")
    visible_counts = {ext: extension_counts.get(ext, 0) for ext in VISIBLE_EXTENSIONS if extension_counts.get(ext, 0)}
    return {
        "classification": classification,
        "flags": flags,
        "raw_files": raw_count,
        "wiki_files": wiki_count,
        "draft_files": draft_count,
        "processed_files": processed_count,
        "corpus_dirs_present": corpus_dirs_present,
        "extension_counts": extension_counts,
        "visible_extension_counts": visible_counts,
        "supported_source_counts": supported_counts,
        "unsupported_source_counts": unsupported_counts,
        "supported_total": supported_total,
        "unsupported_total": unsupported_total,
        "unsupported_ratio": round((unsupported_total / total_raw), 4) if total_raw else 0.0,
        "workspace_abw_version": config_version,
    }


def workspace_metadata_status(workspace="."):
    path = Path(workspace) / "abw_config.json"
    if not path.exists():
        return {"status": "missing", "path": str(path), "hard_block": False, "reason": "abw_config.json missing"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001
        return {"status": "invalid", "path": str(path), "hard_block": True, "reason": f"abw_config.json unreadable: {exc}"}
    if not isinstance(payload, dict):
        return {"status": "invalid", "path": str(path), "hard_block": True, "reason": "abw_config.json is not a JSON object"}
    return {"status": "ok", "path": str(path), "hard_block": False, "reason": "ok"}


def recovery_suggestions(corpus, summary):
    suggestions = []
    if "old_abw_state" in corpus.get("flags", []):
        suggestions.append("backup .brain, then run repair dry-run before changing workspace state")
    if summary.get("drift_remaining", 0):
        suggestions.append("run abw repair --dry-run")
    if corpus.get("classification") == "partial_supported_corpus":
        suggestions.extend(["rebuild processed state", "reindex corpus", "continue ingest"])
    if corpus.get("classification") == "empty_corpus":
        suggestions.append("add raw files or trusted wiki notes before retrieval benchmarking")
    if corpus.get("classification") == "unsupported_corpus":
        suggestions.append("unsupported corpus: convert unsupported sources to supported formats before ingest")
    return suggestions or ["none"]


def classify_health_state(summary, corpus, metadata, health_dashboard):
    hard_reasons = []
    if metadata.get("hard_block"):
        hard_reasons.append(metadata.get("reason") or "workspace metadata is unreadable")
    if health_dashboard.get("invariant_violation"):
        hard_reasons.append("health trend invariant violation")
    if hard_reasons:
        return "blocked", hard_reasons
    sparse_old_state = bool("old_abw_state" in corpus.get("flags", []) and not corpus.get("wiki_files") and not corpus.get("draft_files"))
    soft = bool(
        summary.get("drift_remaining", 0)
        or summary.get("encoding_remaining", 0)
        or corpus.get("classification") in {"empty_corpus", "unsupported_corpus"}
        or sparse_old_state
    )
    if soft:
        return "recoverable", []
    return "verified", []


def fix_encoding(workspace="."):
    fixes = []
    for issue in check_encoding(workspace):
        path = Path(issue["file"])
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace").replace("\ufffd", "")
        path.write_text(text, encoding="utf-8", newline="")
        fixes.append(
            {
                "file": str(path),
                "status": "FIXED",
                "replacement_chars_remaining": path.read_text(encoding="utf-8").count("\ufffd"),
            }
        )
    return fixes


def append_health_log(workspace, entry):
    log_path = health_log_path(workspace)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    return log_path


def compute_health_trend(log_path):
    path = Path(log_path)
    rows = []
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    return _compute_health_trend_from_rows(rows, total_runs=len(rows))


def _compute_health_trend_from_rows(rows, *, total_runs=None):
    rows = list(rows or [])
    if total_runs is None:
        total_runs = len(rows)
    recent_runs = rows[-10:]
    sample_size = len(recent_runs)
    if sample_size == 0:
        return {
            "total_runs": total_runs,
            "recent_runs": [],
            "drift_rate": 0.0,
            "encoding_rate": 0.0,
            "mojibake_rate": 0.0,
            "clean_pass_rate": 1.0,
            "remediation_rate": 0.0,
            "validation_rate": 0.0,
            "validation_rate_fallback": 0.0,
            "validation_rate_policy": 0.0,
            "execution_rate": 1.0,
            "validation_count": 0,
            "fallback_count": 0,
            "policy_count": 0,
            "stability_score": 100,
            "invariant_violation": False,
            "invariant_severity": "none",
        }

    drift_rate = sum(1 for row in recent_runs if int(row.get("drift_detected", 0)) > 0) / sample_size
    encoding_rate = sum(1 for row in recent_runs if int(row.get("encoding_detected", 0)) > 0) / sample_size
    mojibake_rate = sum(1 for row in recent_runs if int(row.get("mojibake_detected", 0)) > 0) / sample_size
    clean_pass_rate = sum(int(row.get("clean_pass", 1)) for row in recent_runs) / sample_size
    remediation_rate = 1 - clean_pass_rate
    validation_count = sum(int(row.get("used_validation", 0)) for row in recent_runs)
    fallback_count = sum(
        1 for row in recent_runs if (row.get("validation_source") or "none") == "fallback"
    )
    policy_count = sum(
        1 for row in recent_runs if (row.get("validation_source") or "none") == "policy"
    )
    validation_rate = validation_count / sample_size
    validation_rate_fallback = fallback_count / sample_size
    validation_rate_policy = policy_count / sample_size
    execution_rate = 1 - validation_rate
    rate_delta = abs(validation_rate - (validation_rate_fallback + validation_rate_policy))
    invariant_violation = (
        validation_count != (fallback_count + policy_count)
        or not math.isclose(
            validation_rate,
            validation_rate_fallback + validation_rate_policy,
            rel_tol=0,
            abs_tol=EPS,
        )
    )
    if rate_delta < 1e-9 and validation_count == (fallback_count + policy_count):
        invariant_severity = "none"
    elif rate_delta < 1e-6 and validation_count == (fallback_count + policy_count):
        invariant_severity = "minor"
    else:
        invariant_severity = "major"
    stability_score = max(0, min(100, int(round(100 - (drift_rate * 50) - (encoding_rate * 50)))))
    return {
        "total_runs": total_runs,
        "recent_runs": recent_runs,
        "drift_rate": drift_rate,
        "encoding_rate": encoding_rate,
        "mojibake_rate": mojibake_rate,
        "clean_pass_rate": clean_pass_rate,
        "remediation_rate": remediation_rate,
        "validation_rate": validation_rate,
        "validation_rate_fallback": validation_rate_fallback,
        "validation_rate_policy": validation_rate_policy,
        "execution_rate": execution_rate,
        "validation_count": validation_count,
        "fallback_count": fallback_count,
        "policy_count": policy_count,
        "stability_score": stability_score,
        "invariant_violation": invariant_violation,
        "invariant_severity": invariant_severity,
    }


def render_stability_graph(recent_runs):
    markers = []
    for row in list(recent_runs)[-10:]:
        drift_hit = int(row.get("drift_detected", 0)) > 0
        encoding_hit = int(row.get("encoding_detected", 0)) > 0
        score = max(0, min(100, int(round(100 - (50 if drift_hit else 0) - (50 if encoding_hit else 0)))))
        if score >= 80:
            markers.append("#")
        elif score >= 50:
            markers.append("*")
        else:
            markers.append("-")
    return "trend: " + "".join(markers)


def detect_anomaly(recent_runs):
    if len(recent_runs) < 3:
        return "STABLE"

    scores = []
    for row in list(recent_runs)[-3:]:
        drift_hit = int(row.get("drift_detected", 0)) > 0
        encoding_hit = int(row.get("encoding_detected", 0)) > 0
        score = max(0, min(100, int(round(100 - (50 if drift_hit else 0) - (50 if encoding_hit else 0)))))
        scores.append(score)

    if scores[0] > scores[1] > scores[2]:
        return "DEGRADING"
    if scores[0] < scores[1] < scores[2]:
        return "RECOVERING"
    if scores[-1] < scores[0] and scores[-1] < 80:
        return "WEAK_DEGRADING"
    return "STABLE"


def _finalization_block(current_state, evidence, gaps, next_steps):
    return "\n".join(
        [
            "## Finalization",
            f"- current_state: {current_state}",
            f"- evidence: {evidence}",
            f"- gaps_or_limitations: {gaps}",
            f"- next_steps: {next_steps}",
        ]
    )


def normalize_mode(mode):
    normalized = str(mode or "audit").strip().lower()
    if normalized in {"audit", "repair"}:
        return normalized
    return "audit"


def run_health(
    workspace=".",
    runtime_root=None,
    binding_status="runner_enforced",
    binding_source="cli",
    validation_source=None,
    mode="audit",
    persist_log=None,
    dry_run=False,
):
    mode = normalize_mode(mode)
    initial_drift = check_drift(workspace=workspace, runtime_root=runtime_root)
    drift_fixes = []
    if mode == "repair" and initial_drift and not dry_run:
        drift_fixes = fix_drift(workspace=workspace, runtime_root=runtime_root)

    initial_encoding = check_encoding(workspace=workspace)
    initial_mojibake = check_mojibake(workspace=workspace)
    encoding_fixes = []
    if mode == "repair" and initial_encoding and not dry_run:
        encoding_fixes = fix_encoding(workspace=workspace)

    final_drift = check_drift(workspace=workspace, runtime_root=runtime_root)
    final_encoding = check_encoding(workspace=workspace)
    final_mojibake = check_mojibake(workspace=workspace)
    corpus = analyze_corpus_readiness(workspace)
    metadata = workspace_metadata_status(workspace)

    summary = {
        "drift_detected": len(initial_drift),
        "drift_fixed": len([item for item in drift_fixes if item["status"] == "MATCH"]),
        "encoding_detected": len(initial_encoding),
        "encoding_fixed": len([item for item in encoding_fixes if item["status"] == "FIXED"]),
        "mojibake_detected": 1 if initial_mojibake else 0,
        "drift_remaining": len(final_drift),
        "encoding_remaining": len(final_encoding),
        "mojibake_remaining": 1 if final_mojibake else 0,
    }
    provisional_log_state = "verified" if not final_drift and not final_encoding else "recoverable"
    clean_pass = 1 if (provisional_log_state == "verified" and summary["drift_detected"] == 0 and summary["encoding_detected"] == 0) else 0
    used_validation = 1 if binding_status == "runner_checked" else 0
    if used_validation:
        normalized_validation_source = validation_source if validation_source in {"fallback", "policy"} else "fallback"
    else:
        normalized_validation_source = "none"
    log_entry = {
        "timestamp": now_iso(),
        "drift_detected": summary["drift_detected"],
        "drift_remaining": summary["drift_remaining"],
        "encoding_detected": summary["encoding_detected"],
        "encoding_remaining": summary["encoding_remaining"],
        "mojibake_detected": summary["mojibake_detected"],
        "clean_pass": clean_pass,
        "used_validation": used_validation,
        "validation_source": normalized_validation_source,
        "status": provisional_log_state,
    }
    log_path = health_log_path(workspace)
    if health_log_enabled(persist_log=persist_log):
        log_path = append_health_log(workspace, log_entry)
        health_dashboard = compute_health_trend(log_path)
    else:
        health_dashboard = _compute_health_trend_from_rows([log_entry], total_runs=1)
    health_dashboard["trend"] = render_stability_graph(health_dashboard["recent_runs"])
    health_dashboard["anomaly"] = detect_anomaly(health_dashboard["recent_runs"])
    if health_dashboard.get("invariant_violation"):
        health_dashboard["anomaly_override_reason"] = "invariant_violation"
    current_state, hard_reasons = classify_health_state(summary, corpus, metadata, health_dashboard)
    evidence = json.dumps(summary, ensure_ascii=False, sort_keys=True)
    suggestions = recovery_suggestions(corpus, summary)
    if hard_reasons:
        next_steps_text = "; ".join(hard_reasons)
    elif current_state == "verified":
        next_steps_text = "none"
    elif mode == "audit":
        next_steps_text = "; ".join(suggestions)
    else:
        next_steps_text = "dry-run only; no files changed" if dry_run else "; ".join(suggestions)
    finalization_block = _finalization_block(
        current_state=current_state,
        evidence=evidence,
        gaps=(
            "read-only audit; soft findings are recoverable onboarding state"
            if mode == "audit"
            else ("dry-run only; no repair was attempted" if dry_run else "repair covers runtime drift and UTF-8/replacement-char cleanup only")
        ),
        next_steps=next_steps_text,
    )
    answer = "\n\n".join(
        [
            f"ABW health {mode} completed.",
            "## Recovery Classification\n"
            f"* state: {current_state}\n"
            f"* hard_block_reasons: {json.dumps(hard_reasons, ensure_ascii=False)}\n"
            f"* repair_suggestions: {json.dumps(suggestions, ensure_ascii=False)}\n"
            f"* dry_run: {bool(dry_run)}",
            "## Runtime/Package State\n"
            f"* runtime_drift_detected: {summary['drift_detected']}\n"
            f"* runtime_drift_remaining: {summary['drift_remaining']}",
            "## Corpus Readiness\n"
            f"* classification: {corpus['classification']}\n"
            f"* flags: {', '.join(corpus['flags']) or 'none'}\n"
            f"* raw_files: {corpus['raw_files']}\n"
            f"* wiki_files: {corpus['wiki_files']}\n"
            f"* draft_files: {corpus['draft_files']}\n"
            f"* processed_files: {corpus['processed_files']}\n"
            f"* supported_source_counts: {json.dumps(corpus['supported_source_counts'], ensure_ascii=False, sort_keys=True)}\n"
            f"* unsupported_source_counts: {json.dumps(corpus['unsupported_source_counts'], ensure_ascii=False, sort_keys=True)}\n"
            f"* visible_extension_counts: {json.dumps(corpus['visible_extension_counts'], ensure_ascii=False, sort_keys=True)}\n"
            f"* unsupported_ratio: {corpus['unsupported_ratio']}",
            "## Encoding/Data Quality\n"
            f"* encoding_detected: {summary['encoding_detected']}\n"
            f"* mojibake_detected: {summary['mojibake_detected']}",
            "## Health Dashboard\n"
            f"* stability_score: {health_dashboard['stability_score']}/100\n"
            f"* drift_rate: {health_dashboard['drift_rate'] * 100:.0f}%\n"
            f"* encoding_rate: {health_dashboard['encoding_rate'] * 100:.0f}%\n"
            f"* mojibake_rate: {health_dashboard['mojibake_rate'] * 100:.0f}%\n"
            f"* clean_pass_rate: {health_dashboard['clean_pass_rate'] * 100:.0f}%\n"
            f"* remediation_rate: {health_dashboard['remediation_rate'] * 100:.0f}%\n"
            f"* validation_rate: {health_dashboard['validation_rate'] * 100:.0f}%\n"
            f"* validation_rate_fallback: {health_dashboard['validation_rate_fallback'] * 100:.0f}%\n"
            f"* validation_rate_policy: {health_dashboard['validation_rate_policy'] * 100:.0f}%\n"
            f"* execution_rate: {health_dashboard['execution_rate'] * 100:.0f}%\n"
            f"* validation_count: {health_dashboard['validation_count']}\n"
            f"* fallback_count: {health_dashboard['fallback_count']}\n"
            f"* policy_count: {health_dashboard['policy_count']}\n"
            f"* invariant_violation: {health_dashboard['invariant_violation']}\n"
            f"* invariant_severity: {health_dashboard['invariant_severity']}\n"
            f"* total_runs: {health_dashboard['total_runs']}\n"
            f"* {health_dashboard['trend']}\n"
            f"* anomaly: {health_dashboard['anomaly']}",
            finalization_block,
        ]
    )
    runtime_id = new_runtime_id()
    nonce = abw_proof.new_nonce()
    return {
        "task": "/abw-health" if mode == "audit" else "/abw-repair",
        "answer": answer,
        "binding_status": binding_status,
        "binding_source": binding_source,
        "current_state": current_state,
        "runner_status": "blocked" if current_state == "blocked" else "completed",
        "mode": mode,
        "dry_run": bool(dry_run),
        "nonce": nonce,
        "runtime_id": runtime_id,
        "health": {
            "drift_before": initial_drift,
            "drift_fix": drift_fixes,
            "drift_after": final_drift,
            "encoding_before": initial_encoding,
            "encoding_fix": encoding_fixes,
            "encoding_after": final_encoding,
            "mojibake_before": initial_mojibake,
            "mojibake_after": final_mojibake,
        },
        "health_dashboard": health_dashboard,
        "corpus_readiness": corpus,
        "workspace_metadata": metadata,
        "hard_block_reasons": hard_reasons,
        "repair_suggestions": suggestions,
        "finalization_block": finalization_block,
        "validation_proof": abw_proof.generate_proof(
            answer,
            finalization_block,
            runtime_id,
            nonce,
            binding_source,
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="ABW health audit and repair utility.")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--runtime-root")
    parser.add_argument("--binding-status", default="runner_enforced")
    parser.add_argument("--validation-source")
    parser.add_argument("--mode", default="audit", help="audit or repair")
    parser.add_argument("--persist-log", action="store_true", help="Persist health trend log to .brain/cache/health_log.jsonl")
    parser.add_argument("--dry-run", action="store_true", help="Report planned repair actions without modifying files")
    args = parser.parse_args(argv)

    result = run_health(
        workspace=args.workspace,
        runtime_root=args.runtime_root,
        binding_status=args.binding_status,
        binding_source="cli",
        validation_source=args.validation_source,
        mode=args.mode,
        persist_log=args.persist_log,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 3 if result.get("current_state") == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
