from __future__ import annotations

import hashlib
import json
import re
import unicodedata
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

NOISE_TOKENS = {
    "binary",
    "confidence",
    "detected",
    "draft",
    "evidence",
    "extracted",
    "local",
    "metadata",
    "method",
    "ocr",
    "page",
    "perception",
    "pipeline",
    "provider",
    "recovered",
    "region",
    "status",
    "text",
    "unknown",
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
    return {token for token in tokens if token not in STOPWORDS and token not in NOISE_TOKENS}


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


def _declared_confidence(text: str) -> float | None:
    matches = re.findall(r"\bconfidence\s*[:=]\s*([01](?:\.\d+)?)", str(text or ""), flags=re.IGNORECASE)
    if not matches:
        return None
    try:
        return min(float(value) for value in matches)
    except ValueError:
        return None


def _is_low_confidence_ocr(text: str) -> bool:
    norm = _normalize_text(text)
    if "ocr" not in norm:
        return False
    if any(marker in norm for marker in ("none recovered", "metadata_only=true", "binary_text_probe=metadata_only")):
        return True
    confidence = _declared_confidence(text)
    return confidence is not None and confidence < 0.35


def _tokenize_context(text: str, profile: ConflictProfile = GENERIC_PROFILE) -> list[str]:
    return re.findall(r"[^\W_][\w-]*|\d{4}-\d{2}-\d{2}|\d+(?:\.\d+)*", _normalize_text(text, profile))


def _semantic_context(tokens: list[str], index: int, profile: ConflictProfile, *, radius: int = _CONTEXT_RADIUS) -> set[str]:
    opposites = {term for pair in OPPOSITE_PAIRS for term in pair}
    context: set[str] = set()
    for token in tokens[max(0, index - radius) : min(len(tokens), index + radius + 1)]:
        if token in STOPWORDS or token in NOISE_TOKENS or token in opposites:
            continue
        if token in profile.comparable_numeric_keys or token in profile.ignore_numeric_contexts:
            continue
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}|\d+(?:\.\d+)*", token):
            continue
        context.add(token)
    return context


def _extract_keyed_numbers(text: str, profile: ConflictProfile = GENERIC_PROFILE) -> dict[str, list[str]]:
    """Extract comparable numeric/date values keyed by nearby semantic field."""
    tokens = _tokenize_context(text, profile)
    keyed: dict[str, list[str]] = {}

    for i, token in enumerate(tokens):
        if token not in profile.comparable_numeric_keys:
            continue
        context = sorted(_semantic_context(tokens, i, profile, radius=4))
        comparable_key = f"{token}|{' '.join(context[:3])}" if context else token
        for j in range(i + 1, min(i + _CONTEXT_RADIUS + 1, len(tokens))):
            candidate = tokens[j]
            if candidate in profile.ignore_numeric_contexts:
                break
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}|\d+(?:\.\d+)*", candidate):
                keyed.setdefault(comparable_key, []).append(candidate)
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

    if parts and parts[0] == "raw":
        return "source", "generic"

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

    if parts and parts[0] == "wiki":
        return "source", "generic"

    return "unknown", ""


def _is_generated_candidate(path: Path, workspace_root: Path) -> bool:
    rel = str(path.relative_to(workspace_root)).replace("\\", "/").lower()
    parts = [part for part in rel.split("/") if part]
    name = path.name.lower()
    stem = path.stem.lower()
    if rel == "wiki/index.md":
        return True
    if name == "repair_report.md":
        return True
    if "status" in parts or "health" in parts:
        return True
    if stem in {"health", "health_summary", "status", "status_summary"}:
        return True
    if stem.endswith("_health") or stem.endswith("_status") or stem.endswith("_summary"):
        return True
    return False


def _is_compatible_doc_pair(incoming_source: str, existing_path: Path, workspace_root: Path) -> bool:
    incoming_kind, incoming_type = _doc_kind(incoming_source)
    existing_kind, existing_type = _doc_kind(str(existing_path.relative_to(workspace_root)))
    if incoming_kind != "source" or existing_kind != "source":
        return False
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
    incoming_tokens = _tokenize_context(incoming_text, profile)
    existing_tokens = _tokenize_context(existing_text, profile)

    for left, right in OPPOSITE_PAIRS:
        for incoming_term, existing_term in ((left, right), (right, left)):
            inc_indexes = [i for i, token in enumerate(incoming_tokens) if token == incoming_term]
            ex_indexes = [i for i, token in enumerate(existing_tokens) if token == existing_term]
            for inc_i in inc_indexes:
                inc_context = _semantic_context(incoming_tokens, inc_i, profile)
                for ex_i in ex_indexes:
                    ex_context = _semantic_context(existing_tokens, ex_i, profile)
                    shared_context = sorted(inc_context & ex_context)
                    if len(shared_context) >= 2:
                        reasons.append(
                            f"opposite terms detected: {left} vs {right}; context={', '.join(shared_context[:4])}"
                        )
                        break
                if reasons and reasons[-1].startswith(f"opposite terms detected: {left} vs {right}"):
                    break

    incoming_keyed = _extract_keyed_numbers(incoming_text, profile)
    existing_keyed = _extract_keyed_numbers(existing_text, profile)
    shared_keys = sorted(set(incoming_keyed) & set(existing_keyed))
    for key in shared_keys:
        incoming_values = sorted(set(incoming_keyed[key]))
        existing_values = sorted(set(existing_keyed[key]))
        if incoming_values != existing_values:
            field, _, context = key.partition("|")
            reasons.append(
                "different numeric values detected: "
                + f"key={field}; context={context}; incoming={', '.join(incoming_values[:3])}; "
                + f"existing={', '.join(existing_values[:3])}"
            )

    return reasons


def _confidence_score(reasons: list[str], shared_terms: set[str], incoming_text: str, existing_text: str) -> float:
    if not reasons:
        return 0.0
    score = 0.55
    score += min(0.2, len(shared_terms) * 0.03)
    if any("context=" in reason for reason in reasons):
        score += 0.15
    if _declared_confidence(incoming_text) is not None:
        score = min(score, max(0.0, float(_declared_confidence(incoming_text) or 0.0) + 0.15))
    score -= min(0.2, (_corruption_score(incoming_text) + _corruption_score(existing_text)) * 2)
    return round(max(0.0, min(0.95, score)), 2)


def detect_conflicts(incoming_source: str, incoming_text: str, workspace: str) -> list[dict]:
    workspace_root = Path(workspace).resolve()
    wiki_root = workspace_root / "wiki"
    if not wiki_root.exists():
        return []

    if _is_high_corruption(incoming_text) or _is_low_confidence_ocr(incoming_text):
        return []

    profile = _workspace_profile(workspace_root)
    incoming_terms = _terms(incoming_text, profile)
    if not incoming_terms:
        return []

    matches: list[dict] = []
    for path in wiki_root.rglob("*.md"):
        if not path.is_file() or path.name == "overview.md":
            continue
        if _is_generated_candidate(path, workspace_root):
            continue
        if not _is_compatible_doc_pair(incoming_source, path, workspace_root):
            continue
        existing_text = path.read_text(encoding="utf-8-sig", errors="ignore")
        if _is_high_corruption(existing_text) or _is_low_confidence_ocr(existing_text):
            continue
        existing_terms = _terms(existing_text, profile)
        shared_terms = incoming_terms & existing_terms
        if len(shared_terms) < 2:
            continue

        reasons = _reasons(incoming_text, existing_text, profile)
        if not reasons:
            continue
        confidence = _confidence_score(reasons, shared_terms, incoming_text, existing_text)
        if confidence < 0.65:
            continue

        matches.append(
            {
                "incoming_source": incoming_source,
                "conflicting_file": str(path.relative_to(workspace_root)).replace("\\", "/"),
                "shared_terms": sorted(shared_terms)[:5],
                "reasons": reasons,
                "confidence": confidence,
                "incoming_excerpt": _excerpt(incoming_text, shared_terms),
                "existing_excerpt": _excerpt(existing_text, shared_terms),
            }
        )
    return matches[:5]


def write_conflict_reports(conflicts: list[dict], workspace: str) -> list[str]:
    workspace_root = Path(workspace).resolve()
    conflict_root = workspace_root / "drafts" / "conflicts"
    conflict_root.mkdir(parents=True, exist_ok=True)
    report_paths: list[str] = []

    for index, conflict in enumerate(conflicts, start=1):
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "incoming_source": conflict.get("incoming_source"),
                    "conflicting_file": conflict.get("conflicting_file"),
                    "reasons": conflict.get("reasons") or [],
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8", errors="ignore")
        ).hexdigest()[:16]
        relpath = f"drafts/conflicts/conflict_{fingerprint}.md"
        path = workspace_root / relpath
        content = "\n".join(
            [
                "# Potential Contradiction",
                "",
                f"Incoming source: {conflict['incoming_source']}",
                f"Possible conflicting file: {conflict['conflicting_file']}",
                f"Confidence: {float(conflict.get('confidence', 0.0)):.2f}",
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
        if not path.exists():
            path.write_text(content, encoding="utf-8")
        report_paths.append(relpath)
    return report_paths
