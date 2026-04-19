import argparse
import hashlib
import json
import math
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


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_runtime_id():
    return str(int(datetime.now(timezone.utc).timestamp() * 1000))


def health_log_path(workspace="."):
    return Path(workspace) / ".brain" / "health_log.jsonl"


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
            yield source, runtime / runtime_dir / source.name


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
    if not path.exists():
        return {
            "total_runs": 0,
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

    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    recent_runs = rows[-10:]
    total_runs = len(rows)
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
):
    mode = normalize_mode(mode)
    initial_drift = check_drift(workspace=workspace, runtime_root=runtime_root)
    drift_fixes = []
    if mode == "repair" and initial_drift:
        drift_fixes = fix_drift(workspace=workspace, runtime_root=runtime_root)

    initial_encoding = check_encoding(workspace=workspace)
    initial_mojibake = check_mojibake(workspace=workspace)
    encoding_fixes = []
    if mode == "repair" and initial_encoding:
        encoding_fixes = fix_encoding(workspace=workspace)

    final_drift = check_drift(workspace=workspace, runtime_root=runtime_root)
    final_encoding = check_encoding(workspace=workspace)
    final_mojibake = check_mojibake(workspace=workspace)
    healthy = not final_drift and not final_encoding

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
    current_state = "verified" if healthy else "blocked"
    clean_pass = 1 if (current_state == "verified" and summary["drift_detected"] == 0 and summary["encoding_detected"] == 0) else 0
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
        "status": current_state,
    }
    log_path = append_health_log(workspace, log_entry)
    health_dashboard = compute_health_trend(log_path)
    health_dashboard["trend"] = render_stability_graph(health_dashboard["recent_runs"])
    health_dashboard["anomaly"] = detect_anomaly(health_dashboard["recent_runs"])
    if health_dashboard.get("invariant_violation"):
        health_dashboard["anomaly_override_reason"] = "invariant_violation"
    evidence = json.dumps(summary, ensure_ascii=False, sort_keys=True)
    finalization_block = _finalization_block(
        current_state=current_state,
        evidence=evidence,
        gaps=(
            "read-only audit; no drift or encoding repair was attempted"
            if mode == "audit"
            else "repair covers runtime drift and UTF-8/replacement-char cleanup only"
        ),
        next_steps=(
            "none"
            if healthy
            else ("run /abw-repair" if mode == "audit" else "inspect remaining health findings")
        ),
    )
    answer = "\n\n".join(
        [
            f"ABW health {mode} completed.",
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
        "runner_status": "completed" if healthy else "blocked",
        "mode": mode,
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
    args = parser.parse_args(argv)

    result = run_health(
        workspace=args.workspace,
        runtime_root=args.runtime_root,
        binding_status=args.binding_status,
        binding_source="cli",
        validation_source=args.validation_source,
        mode=args.mode,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("current_state") == "verified" else 3


if __name__ == "__main__":
    raise SystemExit(main())
