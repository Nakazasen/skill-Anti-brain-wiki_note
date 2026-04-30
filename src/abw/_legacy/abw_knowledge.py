import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


KNOWLEDGE_TIER_RANK = {
    "E0_unknown": 0,
    "E1_fallback": 1,
    "E2_wiki": 2,
    "E3_grounded": 3,
}
KNOWLEDGE_STOPWORDS = {
    "a",
    "an",
    "ai",
    "and",
    "are",
    "cho",
    "cua",
    "duoc",
    "explain",
    "for",
    "giai",
    "is",
    "la",
    "ly",
    "tai",
    "the",
    "thich",
    "this",
    "ve",
    "what",
    "who",
    "why",
    "summarize",
    "summary",
    "summarise",
    "overview",
}
WIKI_SEARCH_DIRS = ("concepts", "entities", "timelines", "sources", "auto_promoted", "manual")
WEAK_WIKI_CONFIDENCE_THRESHOLD = 0.45
BOUNDED_SUMMARY_SOURCE_LIMIT = 5
SEARCH_TEXT_EXTENSIONS = {".md", ".txt", ".json", ".jsonl", ".csv", ".html", ".htm"}
RETRIEVAL_SEARCH_ROOTS = ("wiki", "raw", "drafts")
TRUSTED_WIKI_STATUSES = {"grounded", "compiled", "trusted"}
ABBREVIATION_ALIASES = {
    "agv": ["automated", "guided", "vehicle"],
    "mom": ["manufacturing", "operations", "management"],
    "wms": ["warehouse", "management", "system"],
    "qlsx": ["quan", "ly", "san", "xuat", "production", "order"],
    "qllsx": ["quan", "ly", "lenh", "san", "xuat", "production", "order"],
    "qllssx": ["quan", "ly", "lenh", "san", "xuat", "production", "order"],
    "mp": ["master", "plan", "budget", "simulation"],
}
KEYWORD_ALIASES = {
    "communication": ["comms", "interface", "protocol", "ket", "noi", "giao", "tiep"],
    "communications": ["communication", "comms", "interface", "protocol", "ket", "noi", "giao", "tiep"],
    "workflow": ["flow", "process", "procedure", "quy", "trinh"],
    "constraints": ["constraint", "rule", "limit", "restriction", "rang", "buoc"],
    "source": ["document", "file", "tai", "lieu"],
    "sources": ["document", "documents", "file", "files", "tai", "lieu"],
    "spreadsheet": ["csv", "xlsx", "xls", "excel"],
    "budgeting": ["budget", "simulation", "forecast"],
}
GENERIC_SOURCE_TERMS = {
    "available",
    "document",
    "documents",
    "file",
    "files",
    "mention",
    "mentions",
    "source",
    "sources",
    "system",
}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_runtime_id():
    return str(int(datetime.now(timezone.utc).timestamp() * 1000))


def _normalize_text(text):
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    without_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    lowered = without_marks.lower()
    return re.sub(r"[^0-9a-z]+", " ", lowered, flags=re.IGNORECASE)


def _split_compound_token(token):
    raw = str(token or "").strip()
    if not raw:
        return []
    parts = re.sub(r"([a-z])([A-Z])", r"\1 \2", raw)
    parts = re.sub(r"([A-Za-z])([0-9])", r"\1 \2", parts)
    parts = re.sub(r"([0-9])([A-Za-z])", r"\1 \2", parts)
    return _normalize_text(parts).split()


def _task_terms(task):
    tokens = []
    seen = set()
    raw_tokens = re.findall(r"[A-Za-z0-9À-ỹ_./\\-]+", str(task or ""))
    expanded_tokens = []
    for raw in raw_tokens:
        normalized_raw = _normalize_text(raw).replace(" ", "")
        if len(normalized_raw) >= 3:
            expanded_tokens.append(normalized_raw)
        expanded_tokens.extend(_split_compound_token(raw))
    if not expanded_tokens:
        expanded_tokens = _normalize_text(task).split()

    for token in expanded_tokens:
        if len(token) < 3 or token in KNOWLEDGE_STOPWORDS:
            continue
        if token not in seen:
            seen.add(token)
            tokens.append(token)
        for alias in ABBREVIATION_ALIASES.get(token, []) + KEYWORD_ALIASES.get(token, []):
            if len(alias) >= 3 and alias not in KNOWLEDGE_STOPWORDS and alias not in seen:
                seen.add(alias)
                tokens.append(alias)
    return tokens


def _original_query_terms(task):
    terms = []
    seen = set()
    for raw in re.findall(r"[A-Za-z0-9À-ỹ_./\\-]+", str(task or "")):
        normalized_raw = _normalize_text(raw).replace(" ", "")
        candidates = [normalized_raw] + _split_compound_token(raw)
        for token in candidates:
            if len(token) < 3 or token in KNOWLEDGE_STOPWORDS or token in seen:
                continue
            seen.add(token)
            terms.append(token)
    return terms


def _required_entity_terms(task):
    return [
        term
        for term in _original_query_terms(task)
        if re.search(r"[a-z]", term) and re.search(r"\d", term)
    ]


def _required_named_entity_phrases(task):
    text = str(task or "").strip()
    patterns = [
        r"^\s*(?P<entity>.+?)\s+(?:là|la)\s+ai\s*\??\s*$",
        r"^\s*who\s+is\s+(?P<entity>.+?)\s*\??\s*$",
    ]
    phrases = []
    seen = set()
    for pattern in patterns:
        match = re.match(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        entity = re.sub(r"[?!.。]+$", "", match.group("entity").strip())
        normalized_terms = [term for term in _normalize_text(entity).split() if len(term) >= 2 and term not in KNOWLEDGE_STOPWORDS]
        if len(normalized_terms) < 2:
            continue
        normalized = " ".join(normalized_terms)
        compact = normalized.replace(" ", "")
        if compact in seen:
            continue
        seen.add(compact)
        phrases.append({"text": entity, "normalized": normalized, "compact": compact})
    return phrases


def _entity_term_variants(term):
    variants = {str(term or "").lower()}
    match = re.fullmatch(r"([a-z]+)(20\d{2})", str(term or "").lower())
    if match and match.group(1) == "mp":
        year = match.group(2)
        variants.add(f"mpfy{year}")
        variants.add(f"mpfiscalyear{year}")
    return variants


def _required_fact_terms(task):
    terms = set(_original_query_terms(task))
    required = []
    if "cutover" in terms:
        required.append("cutover")
    return required


def _strict_chapter_number(task):
    match = re.search(r"\bch(?:uong|ương)\s+(\d+)\b", str(task or ""), flags=re.IGNORECASE)
    return match.group(1) if match else None


def _required_domain_terms(task):
    normalized_terms = set(_original_query_terms(task))
    required = []
    for term in ("agv", "mom", "wms"):
        if term in normalized_terms:
            required.append(term)
    return required


def _high_specificity_query_terms(task):
    generic_terms = GENERIC_SOURCE_TERMS.union({"agv", "mom", "wms"})
    return [term for term in _original_query_terms(task) if len(term) >= 4 and term not in generic_terms]


def _summarize_document(text, limit=420):
    content = str(text or "")
    if not content.strip():
        return ""

    lines = []
    in_frontmatter = False
    frontmatter_markers = 0
    for raw in content.splitlines():
        stripped = raw.strip()
        if stripped == "---" and frontmatter_markers < 2:
            in_frontmatter = not in_frontmatter
            frontmatter_markers += 1
            continue
        if in_frontmatter or not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)

    summary = " ".join(lines).strip()
    if len(summary) <= limit:
        return summary
    return summary[: limit - 3].rstrip() + "..."


def _extract_title(text, path):
    for raw in str(text or "").splitlines()[:30]:
        stripped = raw.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        match = re.match(r'^title:\s*"?(.*?)"?$', stripped, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return Path(path).stem.replace("-", " ").replace("_", " ")


def _extract_headings(text):
    headings = []
    for raw in str(text or "").splitlines():
        stripped = raw.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                headings.append(heading)
    return headings


def _extract_status(text):
    match = re.search(r"^\s*status:\s*['\"]?([A-Za-z0-9_-]+)", str(text or ""), flags=re.IGNORECASE | re.MULTILINE)
    return match.group(1).lower() if match else ""


def _read_searchable_text(path):
    if path.suffix.lower() not in SEARCH_TEXT_EXTENSIONS:
        return ""
    try:
        return path.read_text(encoding="utf-8-sig", errors="ignore")
    except OSError:
        return ""


def _source_kind(path, workspace_root):
    try:
        relative = path.relative_to(workspace_root)
    except ValueError:
        return "local"
    root = relative.parts[0] if relative.parts else ""
    if root == "wiki":
        return "wiki"
    if root == "raw":
        return "raw"
    if root == "processed":
        return "processed"
    if root == "drafts":
        return "draft_metadata"
    return "local"


def _candidate_score(path, text, terms, task, workspace_root):
    relative = str(path.relative_to(workspace_root))
    title = _extract_title(text, path)
    headings = _extract_headings(text)
    filename = _normalize_text(path.stem)
    title_norm = _normalize_text(title)
    headings_norm = _normalize_text(" ".join(headings))
    body_norm = _normalize_text(text)
    relative_norm = _normalize_text(relative)
    exact_entity_terms = [term for term in _task_terms(task) if re.search(rf"\b{re.escape(term)}\b", filename)]

    score = 0.0
    matched_terms = []
    repeated_hits = 0
    for term in terms:
        term_re = re.compile(rf"\b{re.escape(term)}\b")
        file_hits = len(term_re.findall(filename))
        title_hits = len(term_re.findall(title_norm))
        heading_hits = len(term_re.findall(headings_norm))
        body_hits = len(term_re.findall(body_norm))
        path_hits = len(term_re.findall(relative_norm))
        if file_hits or title_hits or heading_hits or body_hits or path_hits:
            matched_terms.append(term)
        score += file_hits * 8
        score += title_hits * 7
        score += heading_hits * 5
        score += min(body_hits, 6) * 2
        score += path_hits * 2
        repeated_hits += max(0, body_hits - 1)

    if len(matched_terms) > 1:
        score += len(matched_terms) * 3
    if exact_entity_terms:
        score += 8
    score += min(repeated_hits, 8)

    source_kind = _source_kind(path, workspace_root)
    status = _extract_status(text)
    if source_kind == "wiki":
        score += 4
        if status in TRUSTED_WIKI_STATUSES:
            score += 60
    elif source_kind == "processed":
        score += 3
    elif source_kind == "raw":
        score += 1
    elif source_kind == "draft_metadata":
        score -= 20

    # Prefer recently processed trusted wiki notes without letting age dominate relevance.
    if source_kind == "wiki" and status in TRUSTED_WIKI_STATUSES:
        try:
            days_old = max(0, (datetime.now(timezone.utc).timestamp() - path.stat().st_mtime) / 86400)
            score += max(0, 3 - min(days_old, 3))
        except OSError:
            pass

    return score, matched_terms, title


def _strict_exact_match(task, relative, title, matched_terms, filename_norm, title_norm, normalized_candidate, compact_candidate):
    required_named_entities = _required_named_entity_phrases(task)
    if required_named_entities and all(
        entity["normalized"] in normalized_candidate or entity["compact"] in compact_candidate
        for entity in required_named_entities
    ):
        return True

    strict_chapter_number = _strict_chapter_number(task)
    if strict_chapter_number:
        chapter_re = re.compile(rf"\b{re.escape(strict_chapter_number)}\b")
        if chapter_re.search(filename_norm) or chapter_re.search(title_norm):
            return True

    normalized_query = _normalize_text(task).strip()
    relative_norm = _normalize_text(relative)
    if normalized_query and (normalized_query in title_norm or normalized_query in relative_norm):
        return True

    specific_terms = _high_specificity_query_terms(task)
    if len(specific_terms) >= 2 and all(term in matched_terms for term in specific_terms):
        return True

    return False


def _is_search_excluded(path, text):
    """
    Checks if a file should be excluded from knowledge retrieval.
    Excludes:
    - Paths containing 'quarantine'
    - Filenames containing 'README'
    - Files with frontmatter type: 'meta'
    """
    path_str = str(path).lower().replace("\\", "/")
    if "quarantine" in path_str:
        return True
    if "readme" in path.name.lower():
        return True

    if re.search(r"^\s*type:\s*['\"]?meta['\"]?\s*$", str(text or ""), flags=re.IGNORECASE | re.MULTILINE):
        return True

    return False


def _iter_retrieval_candidates(workspace_root):
    seen: set[Path] = set()
    for root_name in RETRIEVAL_SEARCH_ROOTS:
        root = workspace_root / root_name
        if not root.exists():
            continue
        if root_name == "wiki":
            roots = [root]
            roots.extend(root / name for name in WIKI_SEARCH_DIRS if (root / name).exists())
        else:
            roots = [root]
        for search_root in roots:
            for path in search_root.rglob("*"):
                if not path.is_file() or path.name.startswith("."):
                    continue
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                yield path


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _candidate_source_tokens(task):
    pattern = r"[A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+(?:#line-\d+)?"
    return [token.strip("`'\"()[]{}<>.,;:") for token in re.findall(pattern, str(task or ""))]


def _read_explicit_local_source(task, workspace="."):
    workspace_root = Path(workspace).resolve()
    for candidate in _candidate_source_tokens(task):
        line_no = None
        path_token = candidate
        if "#line-" in candidate:
            path_token, _, raw_line = candidate.partition("#line-")
            if raw_line.isdigit():
                line_no = int(raw_line)

        path = Path(path_token)
        if not path.is_absolute():
            path = workspace_root / path
        if not path.exists() or not path.is_file():
            continue

        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue

        if line_no is not None:
            lines = text.splitlines()
            if 1 <= line_no <= len(lines):
                text = lines[line_no - 1]

        summary = _summarize_document(text)
        if not summary:
            continue

        try:
            relative = str(path.relative_to(workspace_root))
        except ValueError:
            relative = str(path)

        return {
            "source": "local",
            "content": summary,
            "confidence": 0.95,
            "path": relative,
        }

    return None


def _search_wiki_context(task, workspace="."):
    matches = _search_wiki_contexts(task, workspace=workspace, limit=1)
    return matches[0] if matches else None


def _search_wiki_contexts(task, workspace=".", limit=BOUNDED_SUMMARY_SOURCE_LIMIT):
    workspace_root = Path(workspace).resolve()
    terms = _task_terms(task)
    if not terms:
        return []
    required_entities = _required_entity_terms(task)
    required_named_entities = _required_named_entity_phrases(task)
    required_fact_terms = _required_fact_terms(task)
    strict_chapter_number = _strict_chapter_number(task)
    required_domain_terms = _required_domain_terms(task)

    candidates = []
    for path in _iter_retrieval_candidates(workspace_root):
        source_kind = _source_kind(path, workspace_root)
        text = _read_searchable_text(path)

        if _is_search_excluded(path, text):
            continue

        text_for_scoring = text

        try:
            relative = str(path.relative_to(workspace_root))
        except ValueError:
            relative = str(path)

        score, matched_terms, title = _candidate_score(path, text_for_scoring, terms, task, workspace_root)
        if not matched_terms:
            continue
        headings = _extract_headings(text_for_scoring)
        title_norm = _normalize_text(title)
        headings_norm = _normalize_text(" ".join(headings))
        body_norm = _normalize_text(text_for_scoring)
        filename_norm = _normalize_text(path.stem)
        normalized_candidate = _normalize_text(f"{relative} {title} {' '.join(headings)} {text_for_scoring}")
        compact_candidate = normalized_candidate.replace(" ", "")
        if strict_chapter_number:
            chapter_re = re.compile(rf"\b{re.escape(strict_chapter_number)}\b")
            if not (
                chapter_re.search(filename_norm)
                or chapter_re.search(title_norm)
                or chapter_re.search(headings_norm)
            ):
                continue
        if required_domain_terms:
            title_and_body = f"{title_norm} {headings_norm} {body_norm}"
            if not all(re.search(rf"\b{re.escape(term)}\b", title_and_body) for term in required_domain_terms):
                continue
        matched_named_entities = []
        for entity in required_named_entities:
            if entity["normalized"] in normalized_candidate or entity["compact"] in compact_candidate:
                matched_named_entities.append(entity["compact"])
        if required_named_entities and len(matched_named_entities) != len(required_named_entities):
            continue
        matched_entity_terms = []
        for entity in required_entities:
            if any(variant in compact_candidate for variant in _entity_term_variants(entity)):
                matched_entity_terms.append(entity)
        if required_entities and len(matched_entity_terms) != len(required_entities):
            continue
        if required_fact_terms and not all(term in matched_terms for term in required_fact_terms):
            continue
        for entity in matched_entity_terms:
            if entity not in matched_terms:
                matched_terms.append(entity)
                score += 2

        summary = _summarize_document(text)
        if not summary and source_kind in {"raw", "processed"} and path.suffix.lower() in {".csv", ".xlsx", ".xls"}:
            summary = f"Source metadata matched: {relative}"
        elif not summary and source_kind == "draft_metadata":
            summary = f"Draft metadata matched: {relative}"
        elif not summary:
            continue

        confidence = min(0.95, 0.30 + (0.07 * min(score, 8)) + (0.05 * min(len(set(matched_terms)), 4)))
        if source_kind == "draft_metadata":
            confidence = min(confidence, 0.42)
        elif source_kind == "raw" and path.suffix.lower() not in SEARCH_TEXT_EXTENSIONS:
            confidence = min(confidence, 0.48)

        candidate = {
            "source": source_kind,
            "content": summary,
            "confidence": round(confidence, 2),
            "path": relative,
            "title": title,
            "matched_terms": sorted(set(matched_terms)),
            "retrieval_status": (
                "grounded"
                if source_kind == "wiki" and _extract_status(text) == "grounded"
                else (
                    "exact_match"
                    if _strict_exact_match(
                        task,
                        relative,
                        title,
                        set(matched_terms),
                        filename_norm,
                        title_norm,
                        normalized_candidate,
                        compact_candidate,
                    )
                    else "fuzzy_match"
                )
            ),
            "_score": score,
        }
        candidates.append(candidate)

    candidates.sort(key=lambda item: (-item["_score"], item["path"]))
    selected = candidates[: max(1, int(limit or 1))]
    for candidate in selected:
        candidate.pop("_score", None)
    return selected


def is_broad_summary_query(task):
    normalized = _normalize_text(task)
    tokens = normalized.split()
    if not tokens:
        return False
    return tokens[0] in {"summarize", "summary", "summarise", "overview"} and not _candidate_source_tokens(task)


def _bounded_summary_context(task, workspace="."):
    sources = _search_wiki_contexts(task, workspace=workspace, limit=BOUNDED_SUMMARY_SOURCE_LIMIT)
    if not sources:
        return {
            "source": "none",
            "content": "",
            "confidence": 0.0,
            "path": None,
            "summary_status": "insufficient_sources",
            "scope_limit": f"Bounded to the top {BOUNDED_SUMMARY_SOURCE_LIMIT} relevant trusted wiki chunks.",
            "sources": [],
            "unknowns": ["No trusted wiki chunks matched this broad summary request."],
            "next_questions": [
                "Which workflow constraint should ABW inspect first?",
                "Which MOM WMS source should be ingested or reviewed next?",
            ],
        }

    terms = _task_terms(task)
    combined = " ".join(source["content"].lower() for source in sources)
    missing_terms = [term for term in terms if term not in combined]
    source_lines = [f"- {source['path']}: {source['content']}" for source in sources]
    focus = " ".join(terms[:4]) or "this topic"
    return {
        "source": "wiki_summary",
        "content": "\n".join(source_lines),
        "confidence": min(0.85, max(float(source["confidence"]) for source in sources)),
        "path": sources[0]["path"],
        "summary_status": "bounded_partial",
        "scope_limit": f"Bounded to {len(sources)} trusted wiki chunk(s), maximum {BOUNDED_SUMMARY_SOURCE_LIMIT}.",
        "sources": [{"path": source["path"], "confidence": source["confidence"]} for source in sources],
        "unknowns": missing_terms or ["Coverage outside the cited chunks was not inspected."],
        "next_questions": [
            f"What are the highest-risk constraints for {focus}?",
            f"Which source defines exceptions or approvals for {focus}?",
            f"What operational steps are covered by each cited {focus} source?",
        ],
    }


def _knowledge_gap_path(workspace="."):
    return Path(workspace) / ".brain" / "knowledge_gaps.json"


def log_knowledge_gap(task, workspace=".", searched_locations=None, reason="No local knowledge source matched the task."):
    path = _knowledge_gap_path(workspace)
    payload = {
        "_schema": "hybrid-abw/knowledge-gaps/1.0",
        "_description": "Log of knowledge gaps. See templates/knowledge_gaps.example.json for entry format.",
        "updated_at": now_iso(),
        "stats": {"total": 0, "open": 0, "investigating": 0, "resolved": 0},
        "gaps": [],
    }
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            pass

    gaps = payload.setdefault("gaps", [])
    for gap in gaps:
        if gap.get("query") == task and gap.get("status") == "open":
            payload["updated_at"] = now_iso()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return gap.get("id") or gap.get("gap_id")

    gap_id = f"gap-{new_runtime_id()}"
    gaps.append(
        {
            "id": gap_id,
            "query": task,
            "context": "ABW runner knowledge retrieval",
            "searched_locations": searched_locations or ["wiki/"],
            "notebooklm_checked": False,
            "notebooklm_notebook_id": None,
            "reason": reason,
            "priority": "medium",
            "status": "open",
            "created_at": now_iso(),
            "resolved_at": None,
            "resolution_path": None,
            "suggested_sources": [],
        }
    )
    stats = payload.setdefault("stats", {})
    stats["total"] = len(gaps)
    stats["open"] = sum(1 for gap in gaps if gap.get("status") == "open")
    stats["investigating"] = sum(1 for gap in gaps if gap.get("status") == "investigating")
    stats["resolved"] = sum(1 for gap in gaps if gap.get("status") == "resolved")
    payload["updated_at"] = now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return gap_id


def detect_knowledge_gap(query, context, workspace="."):
    context = context or {}
    source = context.get("source")
    confidence = _safe_float(context.get("confidence"))
    path = context.get("path")
    content = str(context.get("content") or "").strip()

    result = {
        "gap_detected": False,
        "gap_type": "none",
        "reason": "",
        "suggested_sources": [],
        "confidence": confidence,
    }

    if source in (None, "none"):
        named_entities = context.get("required_named_entities") or _required_named_entity_phrases(query)
        result.update(
            {
                "gap_detected": True,
                "gap_type": "missing_evidence",
                "reason": (
                    f"No source contained the required named entity: {named_entities[0]['text']}."
                    if named_entities
                    else "No local wiki or explicit source matched the question."
                ),
                "suggested_sources": ["wiki/", "raw/"],
            }
        )
        return result

    if source in {"wiki", "raw", "processed", "draft_metadata"} and (not content or not path):
        result.update(
            {
                "gap_detected": True,
                "gap_type": "weak_answer",
                "reason": "Local evidence matched, but the answer lacks usable content or source path.",
                "suggested_sources": ["add a targeted wiki note", "ingest a raw source for this question"],
            }
        )
        return result

    if source in {"wiki", "raw", "processed", "draft_metadata"} and confidence < WEAK_WIKI_CONFIDENCE_THRESHOLD:
        result.update(
            {
                "gap_detected": True,
                "gap_type": "weak_answer",
                "reason": (
                    "Local evidence matched, but confidence is below the weak-answer threshold "
                    f"({confidence:.2f} < {WEAK_WIKI_CONFIDENCE_THRESHOLD:.2f})."
                ),
                "suggested_sources": ["add a targeted wiki note", "ingest a raw source for this question"],
            }
        )
        return result

    return result


def _no_match_context(task):
    named_entities = _required_named_entity_phrases(task)
    context = {
        "source": "none",
        "content": "",
        "confidence": 0.0,
        "path": None,
        "retrieval_status": "no_match",
    }
    if named_entities:
        context["required_named_entities"] = named_entities
    return context


def _get_knowledge_context(task, workspace="."):
    explicit = _read_explicit_local_source(task, workspace=workspace)
    if explicit:
        return explicit

    if is_broad_summary_query(task):
        return _bounded_summary_context(task, workspace=workspace)

    wiki_context = _search_wiki_context(task, workspace=workspace)
    if wiki_context:
        return wiki_context

    return _no_match_context(task)


def get_knowledge_context(task: str) -> dict:
    return _get_knowledge_context(task, workspace=".")


def compute_knowledge_score(result):
    context = result.get("knowledge_context") or {}
    source = context.get("source")
    confidence = float(context.get("confidence") or 0.0)
    if source in {"wiki", "wiki_summary", "raw", "processed"}:
        return max(1, min(3, int(round(confidence * 3))))
    if source == "local":
        return max(2, min(3, int(round(confidence * 3))))
    return 0


def compute_knowledge_tier(result):
    context = result.get("knowledge_context") or {}
    source = context.get("source")
    if source == "local":
        return "E3_grounded"
    if source in {"raw", "processed"}:
        return "E3_grounded"
    if source in {"wiki", "wiki_summary"}:
        return "E2_wiki"
    return "E0_unknown"


def build_source_summary(result):
    context = result.get("knowledge_context") or {}
    source = context.get("source")
    if source in {"wiki", "wiki_summary"}:
        return "local_wiki"
    if source == "raw":
        return "raw_source"
    if source == "processed":
        return "processed_source"
    if source == "draft_metadata":
        return "draft_metadata"
    if source == "local":
        return "explicit_local"
    return "unknown"


def enrich_knowledge_result(task, workspace="."):
    context = _get_knowledge_context(task, workspace=workspace)
    gap = detect_knowledge_gap(task, context, workspace=workspace)
    result = {
        "task": task,
        "knowledge_context": context,
        "knowledge_gap": gap,
        "refinement_history": [],
        "strategy_trace": {},
        "semantic_fix_applied": False,
    }
    if context.get("source") == "wiki_summary":
        result["evidence"] = f"bounded summary used {len(context.get('sources') or [])} trusted wiki source(s)"
        result["gap_logged"] = context.get("summary_status") == "insufficient_sources"
        result["summary_status"] = context.get("summary_status")
    elif context.get("source") in {"wiki", "raw", "processed", "draft_metadata"}:
        result["evidence"] = f"local retrieval matched {context.get('path')}"
        result["gap_logged"] = bool(gap.get("gap_detected"))
    elif context.get("source") == "local":
        result["evidence"] = f"explicit local retrieval matched {context.get('path')}"
        result["gap_logged"] = False
    else:
        result["evidence"] = "no usable knowledge source found"
        result["gap_logged"] = True
    return result


def attach_knowledge_output(result, answer_text=None):
    context = result.get("knowledge_context") or {}
    result["knowledge_output"] = {
        "answer": answer_text if answer_text is not None else result.get("answer") or result.get("execution_result"),
        "tier": result.get("knowledge_evidence_tier"),
        "score": result.get("knowledge_source_score"),
        "gap_logged": result.get("gap_logged", False),
        "source_summary": build_source_summary(result),
        "source": context.get("source"),
        "content": context.get("content"),
        "confidence": context.get("confidence"),
        "path": context.get("path"),
        "title": context.get("title"),
        "matched_terms": context.get("matched_terms") or [],
        "retrieval_status": context.get("retrieval_status") or ("no_match" if context.get("source") in {None, "none"} else "fuzzy_match"),
        "required_named_entities": context.get("required_named_entities") or [],
        "summary_status": context.get("summary_status"),
        "scope_limit": context.get("scope_limit"),
        "sources": context.get("sources") or [],
        "unknowns": context.get("unknowns") or [],
        "next_questions": context.get("next_questions") or [],
    }
    return result
