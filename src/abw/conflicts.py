from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path

from .profiles import GENERIC_PROFILE, get_profile
from .profiles.base import ConflictProfile
from .workspace import read_workspace_config


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

_CONTEXT_RADIUS = 5
_MOJIBAKE_PATTERN = re.compile(
    r"(?:\ufffd|Ã.|Â.|â€|â€“|â€”|â€™|â€œ|â€\x9d|ðŸ|æ.|å.|ç.)"
)


def _workspace_profile(workspace_root: Path) -> ConflictProfile:
    config, status = read_workspace_config(workspace_root)
    if status != "ok" or not isinstance(config, dict):
        return GENERIC_PROFILE
    return get_profile(config.get("domain_profile"))


def _normalize_text(text: str, profile: ConflictProfile = GENERIC_PROFILE) -> str:
    """Lower-case, substitute profile synonyms, collapse whitespace."""
    norm = unicodedata.normalize("NFKC", str(text or "")).lower()
    for key in sorted(profile.synonyms, key=len, reverse=True):
        canon = profile.synonyms[key]
        if re.search(r"[a-z]", key):
            norm = re.sub(rf"\b{re.escape(key)}\b", canon, norm)
        else:
            norm = norm.replace(key, canon)
    return " ".join(norm.split())


def _terms(text: str, profile: ConflictProfile = GENERIC_PROFILE) -> set[str]:
    """Extract normalized word tokens, excluding stopwords."""
    tokens = re.findall(r"[^\W\d_][\w-]{1,}", _normalize_text(text, profile))
    return {token for token in tokens if token not in STOPWORDS}


def _corruption_score(text: str) -> float:
    """Heuristic score for mojibake / broken decoding artifacts."""
    if not text:
        return 0.0
    norm = unicodedata.normalize("NFKC", str(text))
    suspicious = len(_MOJIBAKE_PATTERN.findall(norm))
    replacement = norm.count("\ufffd")
    controls = sum(1 for ch in norm if ord(ch) < 32 and ch not in "\n\r\t")
    length = max(1, len(norm))
    return (suspicious + (replacement * 2) + (controls * 2)) / length


def _is_high_corruption(text: str) -> bool:
    """Gate contradiction checks when text quality is too corrupted."""
    score = _corruption_score(text)
    if score >= 0.05:
        return True
    norm = unicodedata.normalize("NFKC", str(text or ""))
    suspicious = len(_MOJIBAKE_PATTERN.findall(norm))
    return suspicious >= 8


def _extract_keyed_numbers(text: str, profile: ConflictProfile = GENERIC_PROFILE) -> dict[str, list[str]]:
    """Extract comparable numeric/date values keyed by nearby semantic field."""
    norm = _normalize_text(text, profile)
    tokens = re.findall(r"[^\W\d_][\w-]*|\d{4}-\d{2}-\d{2}|\d+(?:\.\d+)*", norm)
    keyed: dict[str, list[str]] = {}

    for i, token in enumerate(tokens):
        if token not in profile.comparable_numeric_keys:
            continue
        for j in range(i + 1, min(i + _CONTEXT_RADIUS + 1, len(tokens))):
            candidate = tokens[j]
            if candidate in profile.ignore_numeric_contexts:
                break
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}|\d+(?:\.\d+)*", candidate):
                keyed.setdefault(token, []).append(candidate)
                break
            if candidate in profile.comparable_numeric_keys:
                break

    return keyed


def _numbers(text: str, profile: ConflictProfile = GENERIC_PROFILE) -> list[str]:
    """Backward-compatible numeric helper used by tests."""
    values: list[str] = []
    for keyed_values in _extract_keyed_numbers(text, profile).values():
        values.extend(keyed_values)
    return values


def _doc_kind(path_like: str) -> tuple[str, str]:
    """
    Return (kind, source_type).
    kind in: source|concept|entity|unknown
    source_type only matters for kind=source.
    """
    normalized = str(path_like or "").replace("\\", "/").lower()
    parts = [part for part in normalized.split("/") if part]

    if "concepts" in parts:
        return "concept", ""
    if "entities" in parts:
        return "entity", ""

    source_type = "generic"
    if "sources" in parts:
        idx = parts.index("sources")
        if idx + 1 < len(parts) - 1:
            source_type = re.sub(r"[^a-z0-9_]+", "_", parts[idx + 1]).strip("_") or "generic"
        return "source", source_type

    if parts and parts[0] in {"raw", "wiki"}:
        return "source", "generic"

    return "unknown", ""


def _is_compatible_doc_pair(incoming_source: str, existing_path: Path, workspace_root: Path) -> bool:
    incoming_kind, incoming_type = _doc_kind(incoming_source)
    existing_kind, existing_type = _doc_kind(str(existing_path.relative_to(workspace_root)))
    if incoming_kind != existing_kind:
        return False
    if incoming_kind == "source":
        return incoming_type == existing_type
    return incoming_kind in {"concept", "entity"}


def _excerpt(text: str, shared_terms: set[str], limit: int = 220) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", str(text or "").strip())
    lowered_terms = {token.lower() for token in shared_terms}
    for sentence in sentences:
        if any(token in sentence.lower() for token in lowered_terms):
            return sentence[:limit].strip()
    return " ".join(str(text or "").split())[:limit].strip()


def _reasons(incoming_text: str, existing_text: str, profile: ConflictProfile = GENERIC_PROFILE) -> list[str]:
    reasons: list[str] = []
    incoming_norm = _normalize_text(incoming_text, profile)
    existing_norm = _normalize_text(existing_text, profile)

    for left, right in OPPOSITE_PAIRS:
        inc_l = left in incoming_norm
        inc_r = right in incoming_norm
        ex_l = left in existing_norm
        ex_r = right in existing_norm
        if (inc_l and ex_r) or (inc_r and ex_l):
            reasons.append(f"opposite terms detected: {left} vs {right}")

    incoming_keyed = _extract_keyed_numbers(incoming_text, profile)
    existing_keyed = _extract_keyed_numbers(existing_text, profile)
    shared_keys = sorted(set(incoming_keyed) & set(existing_keyed))
    for key in shared_keys:
        incoming_values = sorted(set(incoming_keyed[key]))
        existing_values = sorted(set(existing_keyed[key]))
        if incoming_values != existing_values:
            reasons.append(
                "different numeric values detected: "
                + f"key={key}; incoming={', '.join(incoming_values[:3])}; "
                + f"existing={', '.join(existing_values[:3])}"
            )

    return reasons


def detect_conflicts(incoming_source: str, incoming_text: str, workspace: str) -> list[dict]:
    workspace_root = Path(workspace).resolve()
    wiki_root = workspace_root / "wiki"
    if not wiki_root.exists():
        return []

    if _is_high_corruption(incoming_text):
        return []

    profile = _workspace_profile(workspace_root)
    incoming_terms = _terms(incoming_text, profile)
    if not incoming_terms:
        return []

    matches: list[dict] = []
    for path in wiki_root.rglob("*.md"):
        if not path.is_file() or path.name == "overview.md":
            continue
        if not _is_compatible_doc_pair(incoming_source, path, workspace_root):
            continue
        existing_text = path.read_text(encoding="utf-8-sig", errors="ignore")
        if _is_high_corruption(existing_text):
            continue
        existing_terms = _terms(existing_text, profile)
        shared_terms = incoming_terms & existing_terms
        if len(shared_terms) < 2:
            continue

        reasons = _reasons(incoming_text, existing_text, profile)
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
    report_paths: list[str] = []

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
