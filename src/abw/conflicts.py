from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


STOPWORDS = {
    "about",
    "after",
    "before",
    "being",
    "could",
    "from",
    "have",
    "into",
    "manual",
    "note",
    "only",
    "review",
    "should",
    "source",
    "status",
    "that",
    "their",
    "there",
    "these",
    "this",
    "trust",
    "with",
}

OPPOSITE_PAIRS = [
    ("enabled", "disabled"),
    ("true", "false"),
    ("yes", "no"),
    ("increase", "decrease"),
    ("supported", "unsupported"),
    ("support", "not support"),
    ("allow", "deny"),
]


def _normalize_text(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def _terms(text: str) -> set[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", _normalize_text(text))
    return {token for token in tokens if token not in STOPWORDS}


def _numbers(text: str) -> list[str]:
    return re.findall(r"\b\d+(?:\.\d+)*\b", str(text or ""))


def _excerpt(text: str, shared_terms: set[str], limit: int = 220) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", str(text or "").strip())
    lowered_terms = {term.lower() for term in shared_terms}
    for sentence in sentences:
        lowered = sentence.lower()
        if any(term in lowered for term in lowered_terms):
            return sentence[:limit].strip()
    compact = " ".join(str(text or "").split())
    return compact[:limit].strip()


def _reasons(incoming_text: str, existing_text: str) -> list[str]:
    reasons = []
    incoming_norm = _normalize_text(incoming_text)
    existing_norm = _normalize_text(existing_text)

    for left, right in OPPOSITE_PAIRS:
        incoming_has_left = left in incoming_norm
        incoming_has_right = right in incoming_norm
        existing_has_left = left in existing_norm
        existing_has_right = right in existing_norm
        if (incoming_has_left and existing_has_right) or (incoming_has_right and existing_has_left):
            reasons.append(f"opposite terms detected: {left} vs {right}")

    incoming_numbers = _numbers(incoming_text)
    existing_numbers = _numbers(existing_text)
    if incoming_numbers and existing_numbers and set(incoming_numbers) != set(existing_numbers):
        reasons.append(
            "different numeric values detected: "
            + f"incoming={', '.join(incoming_numbers[:3])}; existing={', '.join(existing_numbers[:3])}"
        )

    return reasons


def detect_conflicts(incoming_source: str, incoming_text: str, workspace: str) -> list[dict]:
    workspace_root = Path(workspace).resolve()
    wiki_root = workspace_root / "wiki"
    if not wiki_root.exists():
        return []

    incoming_terms = _terms(incoming_text)
    if not incoming_terms:
        return []

    matches = []
    for path in wiki_root.rglob("*.md"):
        if not path.is_file() or path.name == "overview.md":
            continue
        existing_text = path.read_text(encoding="utf-8-sig", errors="ignore")
        existing_terms = _terms(existing_text)
        shared_terms = incoming_terms & existing_terms
        if len(shared_terms) < 2:
            continue

        reasons = _reasons(incoming_text, existing_text)
        if not reasons:
            continue

        matches.append(
            {
                "incoming_source": incoming_source,
                "conflicting_file": str(path.relative_to(workspace_root)).replace("\\", "/"),
                "shared_terms": sorted(shared_terms)[:5],
                "reasons": reasons,
                "incoming_excerpt": _excerpt(incoming_text, shared_terms),
                "existing_excerpt": _excerpt(existing_text, shared_terms),
            }
        )
    return matches[:5]


def write_conflict_reports(conflicts: list[dict], workspace: str) -> list[str]:
    workspace_root = Path(workspace).resolve()
    conflict_root = workspace_root / "drafts" / "conflicts"
    conflict_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    report_paths = []

    for index, conflict in enumerate(conflicts, start=1):
        relpath = f"drafts/conflicts/conflict_{timestamp}_{index}.md"
        path = workspace_root / relpath
        content = "\n".join(
            [
                "# Potential Contradiction",
                "",
                f"Incoming source: {conflict['incoming_source']}",
                f"Possible conflicting file: {conflict['conflicting_file']}",
                f"Why flagged: {'; '.join(conflict['reasons'])}",
                "",
                "Incoming excerpt:",
                conflict["incoming_excerpt"] or "(none)",
                "",
                "Existing excerpt:",
                conflict["existing_excerpt"] or "(none)",
                "",
                "Status:",
                "review_required",
                "",
            ]
        )
        path.write_text(content, encoding="utf-8")
        report_paths.append(relpath)
    return report_paths
