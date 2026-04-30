from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from .doctor import build_doctor_report
from .inspect import build_inspect_report

READABLE_EXTENSIONS = {".md", ".txt", ".json", ".jsonl", ".csv", ".html", ".htm"}
UNSUPPORTED_FORMAT_ACTIONS = {
    ".xls": "convert xls to xlsx/csv or add a text index",
}
STALE_DRAFT_THRESHOLD = 10


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def latest_eval_report_path(workspace: str | Path) -> Path | None:
    eval_dir = Path(workspace) / ".brain" / "eval"
    if not eval_dir.exists():
        return None
    reports = [path for path in eval_dir.glob("eval_report_*.json") if path.is_file()]
    if not reports:
        return None
    return max(reports, key=lambda path: path.stat().st_mtime)


def _normalize_text(text: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    without_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^0-9a-z]+", " ", without_marks.lower(), flags=re.IGNORECASE)


def _compact(text: Any) -> str:
    return _normalize_text(text).replace(" ", "")


def _identity_terms(question: str) -> list[str]:
    terms = []
    seen = set()
    for raw in re.findall(r"[A-Za-z]+20\d{2}", str(question or "")):
        term = raw.lower()
        if term not in seen:
            seen.add(term)
            terms.append(term)
    return terms


def _identity_variants(term: str) -> set[str]:
    variants = {term.lower()}
    match = re.fullmatch(r"([a-z]+)(20\d{2})", term.lower())
    if not match:
        return variants
    prefix, year = match.groups()
    variants.add(f"{prefix}fy{year}")
    variants.add(f"{prefix}fiscalyear{year}")
    variants.add(f"fy{year}")
    return variants


def _corpus_text_index(workspace: Path) -> dict[str, str]:
    roots = ("raw", "wiki", "drafts", "processed")
    path_parts: list[str] = []
    content_parts: list[str] = []
    for root_name in roots:
        root = workspace / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            try:
                relative = str(path.relative_to(workspace))
            except ValueError:
                relative = str(path)
            path_parts.append(relative)
            if path.suffix.lower() in READABLE_EXTENSIONS:
                try:
                    content_parts.append(path.read_text(encoding="utf-8-sig", errors="ignore")[:20000])
                except OSError:
                    pass
    return {"paths": _compact("\n".join(path_parts)), "content": _compact("\n".join(content_parts))}


def _sample_files_by_ext(workspace: Path, ext: str, limit: int = 3) -> list[str]:
    raw = workspace / "raw"
    if not raw.exists():
        return []
    samples = []
    for path in sorted(raw.rglob(f"*{ext}")):
        if path.is_file():
            try:
                samples.append(str(path.relative_to(workspace)))
            except ValueError:
                samples.append(str(path))
        if len(samples) >= limit:
            break
    return samples


def _question_failed(detail: dict[str, Any]) -> bool:
    return not bool(detail.get("passed"))


def _question_label(detail: dict[str, Any]) -> str:
    return str(detail.get("id") or detail.get("question") or "unknown")


def _eval_warning_count(eval_report: dict[str, Any], details: list[dict[str, Any]]) -> int:
    summary = eval_report.get("summary") if isinstance(eval_report.get("summary"), dict) else {}
    try:
        return int(summary.get("warnings", 0) or 0)
    except (TypeError, ValueError):
        pass
    return sum(len(detail.get("warnings") or []) for detail in details)


def _grounded_warning_details(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grounded = []
    for detail in details:
        warnings = detail.get("warnings") or []
        if not warnings:
            continue
        retrieval_status = str(detail.get("retrieval_quality_status") or "").lower()
        try:
            grounding_score = int(detail.get("grounding_score", 0) or 0)
        except (TypeError, ValueError):
            grounding_score = 0
        try:
            citations_count = int(detail.get("citations_count", 0) or 0)
        except (TypeError, ValueError):
            citations_count = 0
        if detail.get("passed") or retrieval_status == "pass" or grounding_score >= 3 or citations_count > 0:
            grounded.append(detail)
    return grounded


def _make_gap(
    gap_type: str,
    *,
    affected_questions: list[str],
    suspected_cause: str,
    evidence: dict[str, Any],
    suggested_next_actions: list[str],
    severity: str = "warn",
) -> dict[str, Any]:
    return {
        "type": gap_type,
        "severity": severity,
        "affected_questions": affected_questions,
        "suspected_cause": suspected_cause,
        "evidence": evidence,
        "suggested_next_actions": suggested_next_actions,
    }


def _has_failed_unsupported_format_question(failed_details: list[dict[str, Any]]) -> bool:
    for detail in failed_details:
        text = f"{detail.get('id', '')} {detail.get('question', '')} {detail.get('reason', '')}".lower()
        if any(ext.lstrip(".") in text for ext in UNSUPPORTED_FORMAT_ACTIONS):
            return True
    return False


def _classify_identity_gaps(
    workspace: Path,
    failed_details: list[dict[str, Any]],
    corpus_index: dict[str, str],
) -> list[dict[str, Any]]:
    gaps = []
    for detail in failed_details:
        question = str(detail.get("question") or "")
        missing = []
        near_matches = []
        for term in _identity_terms(question):
            variants = _identity_variants(term) - {term}
            exact_in_content = term in corpus_index["content"]
            exact_in_paths = term in corpus_index["paths"]
            variant_hits = sorted(variant for variant in variants if variant in corpus_index["paths"] or variant in corpus_index["content"])
            if variant_hits and not exact_in_content:
                missing.append(term)
                near_matches.extend(variant_hits)
            elif not exact_in_content and not exact_in_paths:
                missing.append(term)
        if missing and near_matches:
            gaps.append(
                _make_gap(
                    "identity_gap",
                    affected_questions=[_question_label(detail)],
                    suspected_cause="Question identity terms do not match corpus naming conventions.",
                    evidence={
                        "missing_identity_terms": sorted(set(missing)),
                        "near_match_terms": sorted(set(near_matches)),
                        "sample_files": _sample_files_by_ext(workspace, ".csv") + _sample_files_by_ext(workspace, ".xlsx"),
                    },
                    suggested_next_actions=[
                        "add a small wiki/source index that maps project identity aliases",
                        "keep raw files unchanged; prefer an explicit text index over parser expansion",
                    ],
                    severity="fail",
                )
            )
    return gaps


def build_gap_report(workspace: str | Path = ".") -> dict[str, Any]:
    root = Path(workspace).resolve()
    inspect_report = build_inspect_report(root)
    doctor_report = build_doctor_report(root)
    eval_path = latest_eval_report_path(root)
    eval_report = _load_json(eval_path) if eval_path else {}
    details = eval_report.get("details") if isinstance(eval_report.get("details"), list) else []
    failed_details = [detail for detail in details if isinstance(detail, dict) and _question_failed(detail)]
    warning_count = _eval_warning_count(eval_report, details)
    raw_stats = inspect_report["raw_stats"]
    wiki_stats = inspect_report["wiki_stats"]
    draft_stats = inspect_report["draft_stats"]
    processed_stats = inspect_report["processed_stats"]
    by_ext = raw_stats.get("by_ext", {})
    corpus_index = _corpus_text_index(root)

    gaps: list[dict[str, Any]] = []

    gaps.extend(_classify_identity_gaps(root, failed_details, corpus_index))

    unsupported_count = int(raw_stats.get("unsupported", 0) or 0)
    xls_count = int(by_ext.get(".xls", 0) or 0)
    if xls_count and (failed_details or raw_stats.get("total", 0)):
        affected = [_question_label(detail) for detail in failed_details if "xls" in str(detail.get("question", "")).lower()]
        if affected or xls_count >= max(1, int(raw_stats.get("total", 0) or 0) // 2):
            gaps.append(
                _make_gap(
                    "format_block",
                    affected_questions=affected,
                    suspected_cause=f"Unsupported XLS files dominate or block retrievable local evidence.",
                    evidence={
                        "xls_count": xls_count,
                        "unsupported_count": unsupported_count,
                        "raw_total": raw_stats.get("total", 0),
                        "sample_files": _sample_files_by_ext(root, ".xls"),
                    },
                    suggested_next_actions=["convert xls to xlsx/csv or add a text index", "run eval again after supported sources exist"],
                    severity="fail" if affected else "warn",
                )
            )

    if unsupported_count and _has_failed_unsupported_format_question(failed_details):
        gaps.append(
            _make_gap(
                "unsupported_source_gap",
                affected_questions=[
                    _question_label(detail)
                    for detail in failed_details
                    if any(ext.lstrip(".") in str(detail.get("question", "")).lower() for ext in UNSUPPORTED_FORMAT_ACTIONS)
                ],
                suspected_cause="The failed question asks about source formats ABW does not parse as grounded text.",
                evidence={"unsupported_count": unsupported_count, "by_ext": by_ext},
                suggested_next_actions=["convert unsupported source files to supported text, PDF, CSV, XLSX, or HTML"],
                severity="fail",
            )
        )

    if failed_details and raw_stats.get("total", 0) == 0 and wiki_stats.get("total", 0) == 0:
        gaps.append(
            _make_gap(
                "corpus_gap",
                affected_questions=[_question_label(detail) for detail in failed_details],
                suspected_cause="Eval failed with no raw or wiki corpus available.",
                evidence={"raw_total": raw_stats.get("total", 0), "wiki_total": wiki_stats.get("total", 0)},
                suggested_next_actions=["add raw sources", "add grounded wiki notes before rerunning eval"],
                severity="fail",
            )
        )

    if raw_stats.get("total", 0) > 0 and wiki_stats.get("total", 0) == 0:
        gaps.append(
            _make_gap(
                "missing_wiki_coverage",
                affected_questions=[_question_label(detail) for detail in failed_details],
                suspected_cause="Raw evidence exists but there are no wiki notes to anchor retrieval.",
                evidence={"raw_total": raw_stats.get("total", 0), "wiki_total": 0, "raw_by_ext": by_ext},
                suggested_next_actions=["abw save --wiki for key source summaries", "ingest or compile raw evidence into wiki notes"],
                severity="warn",
            )
        )

    if draft_stats.get("total", 0) > STALE_DRAFT_THRESHOLD:
        gaps.append(
            _make_gap(
                "stale_draft_noise",
                affected_questions=[_question_label(detail) for detail in failed_details],
                suspected_cause="High draft volume may pollute retrieval ranking or hide reviewed evidence.",
                evidence={"draft_total": draft_stats.get("total", 0), "threshold": STALE_DRAFT_THRESHOLD},
                suggested_next_actions=["review, archive, or repair stale drafts manually; do not auto-promote"],
                severity="warn",
            )
        )

    classified_questions = {
        question
        for gap in gaps
        for question in gap.get("affected_questions", [])
    }
    weak_questions = [
        detail
        for detail in failed_details
        if _question_label(detail) not in classified_questions
        and (int(detail.get("grounding_score", 0) or 0) < 3 or int(detail.get("citations_count", 0) or 0) == 0)
    ]
    if weak_questions:
        gaps.append(
            _make_gap(
                "weak_retrieval_signal",
                affected_questions=[_question_label(detail) for detail in weak_questions],
                suspected_cause="Corpus exists, but failed questions lack enough ranked citations or grounding score.",
                evidence={
                    "raw_total": raw_stats.get("total", 0),
                    "wiki_total": wiki_stats.get("total", 0),
                    "processed_total": processed_stats.get("total", 0),
                    "failed_count": len(weak_questions),
                },
                suggested_next_actions=["add targeted wiki notes", "inspect matched source names and rerun eval"],
                severity="fail",
            )
        )

    grounded_warning_details = _grounded_warning_details([detail for detail in details if isinstance(detail, dict)])
    if (
        warning_count > 0
        and grounded_warning_details
        and wiki_stats.get("total", 0) == 0
        and (raw_stats.get("total", 0) > 0 or draft_stats.get("total", 0) > 0)
    ):
        gaps.append(
            _make_gap(
                "weak_retrieval_signal",
                affected_questions=[_question_label(detail) for detail in grounded_warning_details],
                suspected_cause="Eval passed with warnings while grounded answers depend on raw or draft evidence without wiki coverage.",
                evidence={
                    "warnings": warning_count,
                    "raw_total": raw_stats.get("total", 0),
                    "wiki_total": wiki_stats.get("total", 0),
                    "draft_total": draft_stats.get("total", 0),
                },
                suggested_next_actions=["add targeted wiki notes for warned answers", "rerun eval after wiki coverage exists"],
                severity="warn",
            )
        )

    gap_counts: dict[str, int] = {}
    for gap in gaps:
        gap_counts[gap["type"]] = gap_counts.get(gap["type"], 0) + 1

    return {
        "workspace": str(root),
        "latest_eval_report": str(eval_path) if eval_path else None,
        "doctor_state": (
            doctor_report.get("state")
            or doctor_report.get("overall")
            or doctor_report.get("classification", {}).get("state")
            or "unknown"
        ),
        "eval_summary": eval_report.get("summary") or {"total": 0, "passed": 0, "failed": 0, "warnings": 0},
        "corpus_counts": {
            "raw": raw_stats,
            "wiki": wiki_stats,
            "drafts": draft_stats,
            "processed": processed_stats,
        },
        "gap_summary": {"total": len(gaps), "by_type": gap_counts},
        "gaps": gaps,
    }


def render_gap_report(report: dict[str, Any]) -> str:
    lines = [
        "ABW Retrieval Gaps",
        "-" * 18,
        f"Workspace: {report['workspace']}",
        f"Latest eval: {report.get('latest_eval_report') or 'none'}",
        f"Doctor state: {report.get('doctor_state', 'unknown')}",
    ]
    summary = report.get("eval_summary") or {}
    lines.append(
        f"Eval: total={summary.get('total', 0)} passed={summary.get('passed', 0)} "
        f"failed={summary.get('failed', 0)} warnings={summary.get('warnings', 0)}"
    )
    counts = report.get("corpus_counts") or {}
    raw = counts.get("raw", {})
    wiki = counts.get("wiki", {})
    drafts = counts.get("drafts", {})
    processed = counts.get("processed", {})
    lines.append(
        f"Corpus: raw={raw.get('total', 0)} wiki={wiki.get('total', 0)} "
        f"drafts={drafts.get('total', 0)} processed={processed.get('total', 0)}"
    )
    lines.append("")
    gaps = report.get("gaps") or []
    if not gaps:
        lines.append("Gap Summary: none detected")
        return "\n".join(lines)

    by_type = report.get("gap_summary", {}).get("by_type", {})
    type_summary = ", ".join(f"{gap_type}={count}" for gap_type, count in sorted(by_type.items()))
    lines.append(f"Gap Summary: total={len(gaps)} {type_summary}")
    for index, gap in enumerate(gaps, start=1):
        lines.append("")
        lines.append(f"{index}. {gap['type']} ({gap.get('severity', 'warn')})")
        affected = gap.get("affected_questions") or []
        lines.append(f"- affected_questions: {', '.join(affected) if affected else 'corpus-wide'}")
        lines.append(f"- suspected_cause: {gap.get('suspected_cause', 'unknown')}")
        evidence = gap.get("evidence") or {}
        if evidence:
            evidence_parts = []
            for key, value in evidence.items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                evidence_parts.append(f"{key}={value}")
            lines.append(f"- evidence: {'; '.join(evidence_parts)}")
        actions = gap.get("suggested_next_actions") or []
        lines.append(f"- suggested_next_actions: {'; '.join(actions) if actions else 'none'}")
    return "\n".join(lines)
