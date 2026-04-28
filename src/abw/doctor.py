from __future__ import annotations

import json
import shutil
from pathlib import Path

from .ocr import tesseract_status
from .version import build_version_report
from .workspace import CONFIG_FILENAME, REQUIRED_DIRS, read_workspace_config, resolve_workspace

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
    "xlsx",
    "pdf",
    "pptx",
}
VISIBLE_EXTENSIONS = ("docx", "xlsx", "csv", "pdf", "html", "htm", "txt")


def _status(level: str, message: str) -> dict:
    return {"level": level, "message": message}


def _load_open_knowledge_gaps(root: Path) -> list[dict]:
    path = root / ".brain" / "knowledge_gaps.json"
    if not path.exists():
        return []
    try:
        import json

        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return []
    gaps = payload.get("gaps", [])
    if not isinstance(gaps, list):
        return []
    return [gap for gap in gaps if isinstance(gap, dict) and gap.get("status") == "open"]


def _short_text(value: object, limit: int = 80) -> str:
    text = " ".join(str(value or "unknown").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _load_ingest_state(root: Path) -> dict:
    path = root / ".brain" / "ingest_state.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _supported_source_counts(root: Path) -> dict:
    counts: dict[str, int] = {}
    raw = root / "raw"
    if not raw.exists():
        return counts
    for path in raw.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower().lstrip(".") or "unknown"
        if suffix in SUPPORTED_SOURCE_EXTENSIONS:
            counts[suffix] = counts.get(suffix, 0) + 1
    return counts


def _file_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def _raw_extension_counts(root: Path) -> dict:
    raw = root / "raw"
    counts: dict[str, int] = {}
    if not raw.exists():
        return counts
    for path in raw.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower().lstrip(".") or "unknown"
        counts[suffix] = counts.get(suffix, 0) + 1
    return dict(sorted(counts.items()))


def _workspace_config_version(root: Path) -> str:
    config, status = read_workspace_config(root)
    if status != "ok" or not isinstance(config, dict):
        return "unknown"
    return str(config.get("abw_version") or "unknown")


def _is_old_abw_state(version_value: str) -> bool:
    if version_value in {"", "unknown"}:
        return False
    try:
        parts = tuple(int(part) for part in version_value.split(".")[:2])
    except ValueError:
        return False
    return parts < (0, 4)


def _corpus_readiness(root: Path) -> dict:
    raw_count = _file_count(root / "raw")
    wiki_count = _file_count(root / "wiki")
    draft_count = _file_count(root / "drafts")
    processed_count = _file_count(root / "processed")
    extension_counts = _raw_extension_counts(root)
    supported_counts = {ext: count for ext, count in extension_counts.items() if ext in SUPPORTED_SOURCE_EXTENSIONS}
    unsupported_counts = {ext: count for ext, count in extension_counts.items() if ext not in SUPPORTED_SOURCE_EXTENSIONS}
    supported_total = sum(supported_counts.values())
    unsupported_total = sum(unsupported_counts.values())
    total_raw = supported_total + unsupported_total
    if raw_count == 0 and wiki_count == 0 and draft_count == 0:
        classification = "empty_corpus"
    elif raw_count > 0 and supported_total == 0:
        classification = "unsupported_corpus"
    elif raw_count > 0 and unsupported_total > 0:
        classification = "partial_supported_corpus"
    else:
        classification = "healthy_supported_corpus"
    config_version = _workspace_config_version(root)
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
        "extension_counts": extension_counts,
        "visible_extension_counts": visible_counts,
        "supported_source_counts": supported_counts,
        "unsupported_source_counts": unsupported_counts,
        "supported_total": supported_total,
        "unsupported_total": unsupported_total,
        "unsupported_ratio": round((unsupported_total / total_raw), 4) if total_raw else 0.0,
        "workspace_abw_version": config_version,
    }


def _ingest_operational_summary(root: Path) -> dict:
    state = _load_ingest_state(root)
    last_run = state.get("last_run") if isinstance(state.get("last_run"), dict) else {}
    counts = last_run.get("supported_source_counts") if isinstance(last_run.get("supported_source_counts"), dict) else {}
    if not counts:
        counts = _supported_source_counts(root)
    return {
        "last_ingest_time": str(last_run.get("timestamp") or "unknown"),
        "last_ingest_duration": last_run.get("duration_seconds", "unknown"),
        "skipped_files_count": int(last_run.get("skipped_count") or 0),
        "skipped_unchanged_count": int(last_run.get("skipped_unchanged_count") or 0),
        "supported_source_counts": counts,
    }


def build_doctor_report(workspace: str | Path = ".") -> dict:
    root = resolve_workspace(workspace)
    workspace_checks = []
    engine_checks = []
    next_steps = []

    for name in REQUIRED_DIRS:
        path = root / name
        if path.exists() and path.is_dir():
            workspace_checks.append(_status("OK", f"{name}/ present"))
        else:
            workspace_checks.append(_status("WARN", f"missing {name}/"))
            next_steps.append("run `abw init`")

    config, config_status = read_workspace_config(root)
    if config_status == "ok":
        workspace_checks.append(_status("OK", f"{CONFIG_FILENAME} present"))
    elif config_status == "missing":
        workspace_checks.append(_status("WARN", f"missing {CONFIG_FILENAME}"))
        next_steps.append("run `abw init`")
    else:
        workspace_checks.append(_status("WARN", f"{CONFIG_FILENAME} is invalid JSON"))
        next_steps.append("run `abw migrate`")

    try:
        import abw  # noqa: F401

        engine_checks.append(_status("OK", "package import works"))
    except Exception as exc:  # noqa: BLE001
        engine_checks.append(_status("WARN", f"package import failed: {exc}"))
        next_steps.append("reinstall the package")

    cli_path = shutil.which("abw")
    if cli_path:
        engine_checks.append(_status("OK", f"CLI found at {cli_path}"))
    else:
        engine_checks.append(_status("WARN", "global `abw` command not found on PATH"))
        next_steps.append("reinstall or expose the console script")

    version = build_version_report(root)
    engine_checks.append(_status("OK", f"package version {version['package_version']}"))
    engine_checks.append(
        _status(
            "OK" if version.get("runtime_source") != "unknown" else "WARN",
            f"runtime source {version.get('runtime_source', 'unknown')} ({version.get('runtime_source_path', 'unknown')})",
        )
    )

    legacy_folder = root / "abw"
    if legacy_folder.exists() and legacy_folder.is_dir():
        workspace_checks.append(_status("WARN", "local legacy ABW engine detected at ./abw"))
        next_steps.append("run `abw migrate`")

    if version["install_mode"] == "unknown":
        engine_checks.append(_status("WARN", "install mode could not be determined"))
        next_steps.append("run `abw version` and verify the package source")
    release_match = version.get("release_match_state", "unknown")
    release_verification = version.get("release_verification_status", release_match)
    if release_match == "matched":
        engine_checks.append(_status("OK", "package version matches current git tag"))
    elif release_match == "mismatched":
        engine_checks.append(_status("WARN", "package version does not match current git tag"))
        next_steps.append("run `abw version` and verify the package source")
    elif release_verification == "unverified_wheel_release":
        engine_checks.append(_status("OK", "release verification unverified_wheel_release; package version is wheel truth"))
    else:
        engine_checks.append(_status("WARN", "release match could not be verified from git tag"))
        next_steps.append("run `abw version` and verify the package source")
    mirror_status = version.get("mirror_status", "not_checked")
    if mirror_status == "matched":
        engine_checks.append(_status("OK", "runtime mirror status matched"))
    elif mirror_status == "mismatch":
        mismatch_list = ", ".join(version.get("mirror_mismatches", [])) or "unknown files"
        engine_checks.append(_status("WARN", "runtime mirror status mismatch"))
        engine_checks.append(_status("WARN", f"runtime mirror mismatch: {mismatch_list}"))
        next_steps.append("sync scripts/* and src/abw/_legacy/* critical runtime modules")
    else:
        engine_checks.append(_status("WARN", "runtime mirror status not checked"))
        next_steps.append("run ABW from repository source to verify runtime mirror status")
    if version.get("stale_install_suspected"):
        engine_checks.append(_status("WARN", "stale install may be active"))
        next_steps.append("run `abw self-check`")
        next_steps.append("run `py -m pip install -U .` or `py -m pip install -U git+<repo-url>`")
    provider_mode = str(version.get("provider_ask_mode") or "local")
    provider_default = str(version.get("provider_default") or "unknown")
    provider_healthy_count = int(version.get("provider_healthy_count") or 0)
    engine_checks.append(
        _status(
            "OK" if provider_healthy_count > 0 or provider_mode == "local" else "WARN",
            f"provider state mode={provider_mode} default={provider_default} healthy={provider_healthy_count}",
        )
    )
    if provider_mode in {"ai", "hybrid"} and provider_healthy_count == 0:
        next_steps.append("run `abw provider test`")
        next_steps.append("run `abw provider set-default mock`")
    tess = tesseract_status()
    if tess.get("status") == "available":
        engine_checks.append(_status("OK", f"local OCR tesseract available at {tess.get('path')} ({tess.get('version')})"))
    else:
        engine_checks.append(_status("WARN", f"local OCR tesseract unavailable: {tess.get('reason', 'unknown')}"))
        next_steps.append("install Tesseract OCR or set ABW_TESSERACT_CMD")
    open_gaps = _load_open_knowledge_gaps(root)
    if open_gaps:
        high_priority = sum(1 for gap in open_gaps if str(gap.get("priority") or "").lower() == "high")
        recent_gap = open_gaps[-1]
        recent_label = recent_gap.get("query") or recent_gap.get("reason") or recent_gap.get("id") or "unknown"
        engine_checks.append(
            _status(
                "WARN",
                f"coverage gaps open={len(open_gaps)} high_priority={high_priority} latest={_short_text(recent_label)}",
            )
        )
        next_steps.append("ingest raw sources or add wiki notes for open knowledge gaps")
    else:
        engine_checks.append(_status("OK", "coverage gaps open=0"))

    ingest_summary = _ingest_operational_summary(root)
    corpus = _corpus_readiness(root)
    corpus_level = "OK" if corpus["classification"] == "healthy_supported_corpus" else "WARN"
    workspace_checks.append(_status(corpus_level, f"corpus readiness {corpus['classification']}"))
    if corpus["flags"]:
        workspace_checks.append(_status("WARN", f"workspace flags: {', '.join(corpus['flags'])}"))
    if corpus["classification"] == "empty_corpus":
        next_steps.append("add raw files or trusted wiki notes before expecting grounded answers")
    elif corpus["classification"] == "unsupported_corpus":
        next_steps.append("add supported raw files or trusted wiki notes; unsupported formats are not ingested")
    elif corpus["classification"] == "partial_supported_corpus":
        next_steps.append("review supported vs unsupported raw source counts before benchmarking retrieval")
    engine_checks.append(
        _status(
            "OK" if ingest_summary["last_ingest_time"] != "unknown" else "WARN",
            (
                "ingest last_run="
                f"{ingest_summary['last_ingest_time']} duration={ingest_summary['last_ingest_duration']}s "
                f"skipped={ingest_summary['skipped_files_count']} "
                f"skipped_unchanged={ingest_summary['skipped_unchanged_count']}"
            ),
        )
    )
    engine_checks.append(
        _status(
            "OK",
            "supported sources by type: "
            + (json.dumps(ingest_summary["supported_source_counts"], ensure_ascii=False, sort_keys=True) or "{}"),
        )
    )
    engine_checks.append(
        _status(
            "OK",
            "unsupported sources by type: "
            + (json.dumps(corpus["unsupported_source_counts"], ensure_ascii=False, sort_keys=True) or "{}"),
        )
    )

    overall = "OK"
    checks = workspace_checks + engine_checks
    if any(item["level"] == "WARN" for item in checks):
        overall = "WARN"

    workspace_health = "WARN" if any(item["level"] == "WARN" for item in workspace_checks) else "OK"
    engine_health = "WARN" if any(item["level"] == "WARN" for item in engine_checks) else "OK"
    top_warnings = [item["message"] for item in checks if item["level"] == "WARN"][:5]

    deduped_steps = []
    seen = set()
    for step in next_steps or ["run `abw ask \"dashboard\"`"]:
        if step in seen:
            continue
        seen.add(step)
        deduped_steps.append(step)

    return {
        "workspace": str(root),
        "overall": overall,
        "workspace_health": workspace_health,
        "engine_health": engine_health,
        "workspace_checks": workspace_checks,
        "engine_checks": engine_checks,
        "checks": checks,
        "next_steps": deduped_steps,
        "version": version,
        "ingest": ingest_summary,
        "corpus": corpus,
        "top_warnings": top_warnings,
    }


def render_doctor_report(report: dict) -> str:
    lines = [
        "ABW Doctor",
        f"- workspace: {report['workspace']}",
        f"- status: {report['overall']}",
        f"- workspace_health: {report['workspace_health']}",
        f"- engine_health: {report['engine_health']}",
        f"- last_ingest_time: {report.get('ingest', {}).get('last_ingest_time', 'unknown')}",
        f"- last_ingest_duration: {report.get('ingest', {}).get('last_ingest_duration', 'unknown')}",
        f"- skipped_files_count: {report.get('ingest', {}).get('skipped_files_count', 0)}",
        f"- corpus_readiness: {report.get('corpus', {}).get('classification', 'unknown')}",
        f"- corpus_flags: {', '.join(report.get('corpus', {}).get('flags') or []) or 'none'}",
        f"- raw_files: {report.get('corpus', {}).get('raw_files', 'unknown')}",
        f"- wiki_files: {report.get('corpus', {}).get('wiki_files', 'unknown')}",
        f"- draft_files: {report.get('corpus', {}).get('draft_files', 'unknown')}",
        f"- supported_source_counts: {json.dumps(report.get('ingest', {}).get('supported_source_counts', {}), ensure_ascii=False, sort_keys=True)}",
        f"- unsupported_source_counts: {json.dumps(report.get('corpus', {}).get('unsupported_source_counts', {}), ensure_ascii=False, sort_keys=True)}",
        f"- visible_extension_counts: {json.dumps(report.get('corpus', {}).get('visible_extension_counts', {}), ensure_ascii=False, sort_keys=True)}",
        f"- top_warnings: {', '.join(report.get('top_warnings') or []) or 'none'}",
        "Workspace checks:",
    ]
    for item in report["workspace_checks"]:
        lines.append(f"- {item['level']}: {item['message']}")
    lines.append("Engine checks:")
    for item in report["engine_checks"]:
        lines.append(f"- {item['level']}: {item['message']}")
    for step in report["next_steps"]:
        lines.append(f"- NEXT: {step}")
    lines.append("- Workspace isolation: current working directory is the default workspace unless ABW_WORKSPACE is set.")
    return "\n".join(lines)
