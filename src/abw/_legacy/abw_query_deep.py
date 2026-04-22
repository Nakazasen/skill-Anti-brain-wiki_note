import json
import re
from datetime import datetime, timezone
from pathlib import Path

import abw_knowledge


MAX_SUBQUESTIONS = 5
MAX_LOOPS = 2
NEGATION_TOKENS = (" not ", " no ", " never ", " without ", " instead ")
SPLIT_TOKENS = (" and ", " vs ", " versus ", " tradeoff ", " trade-off ", " compare ", "?")


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def log_path(workspace="."):
    return Path(workspace) / ".brain" / "query_deep_runs.jsonl"


def append_log(workspace, payload):
    path = log_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def normalize_text(text):
    lowered = str(text or "").lower()
    return re.sub(r"[^0-9a-z]+", " ", lowered, flags=re.IGNORECASE).strip()


def decompose_task(task):
    raw = str(task or "").strip()
    if not raw:
        return []

    working = raw
    for token in SPLIT_TOKENS:
        working = working.replace(token, "|")

    parts = []
    seen = set()
    for piece in working.split("|"):
        candidate = piece.strip(" -:;,.")
        if len(candidate) < 6:
            continue
        normalized = candidate.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        parts.append(candidate)
        if len(parts) >= MAX_SUBQUESTIONS:
            break

    if raw.lower() not in seen and len(parts) < MAX_SUBQUESTIONS:
        parts.insert(0, raw)

    return parts[:MAX_SUBQUESTIONS]


def search_wiki_candidates(query, workspace=".", limit=3):
    workspace_root = Path(workspace).resolve()
    wiki_root = workspace_root / "wiki"
    if not wiki_root.exists():
        return []

    terms = abw_knowledge._task_terms(query)
    if not terms:
        return []

    candidates = []
    for directory in abw_knowledge.WIKI_SEARCH_DIRS:
        search_dir = wiki_root / directory
        if not search_dir.exists():
            continue
        for path in search_dir.glob("*.md"):
            if path.name.startswith("."):
                continue
            try:
                text = path.read_text(encoding="utf-8-sig", errors="ignore")
            except OSError:
                continue

            haystack = f"{path.stem} {text}".lower()
            matches = sum(1 for term in terms if term in haystack)
            if matches == 0:
                continue

            score = matches
            score += sum(2 for term in terms if term in path.stem.lower())
            title_match = re.search(r'^title:\s*"?(.*?)"?$', text, flags=re.IGNORECASE | re.MULTILINE)
            if title_match:
                title = title_match.group(1).lower()
                score += sum(2 for term in terms if term in title)

            summary = abw_knowledge._summarize_document(text)
            if not summary:
                continue

            candidates.append(
                {
                    "query": query,
                    "path": str(path.relative_to(workspace_root)),
                    "content": summary,
                    "matches": matches,
                    "score": score,
                }
            )

    candidates.sort(key=lambda item: (item["score"], item["matches"], len(item["content"])), reverse=True)
    deduped = []
    seen_paths = set()
    for item in candidates:
        if item["path"] in seen_paths:
            continue
        seen_paths.add(item["path"])
        deduped.append(item)
        if len(deduped) >= limit:
            break
    return deduped


def detect_contradictions(evidence):
    contradictions = []
    by_path = {}
    for item in evidence:
        by_path.setdefault(item["path"], []).append(item)

    for path, rows in by_path.items():
        if len(rows) < 2:
            continue
        polarities = set()
        for row in rows:
            content = f" {row.get('content', '').lower()} "
            has_negation = any(token in content for token in NEGATION_TOKENS)
            polarities.add(has_negation)
        if len(polarities) > 1:
            contradictions.append(
                {
                    "path": path,
                    "type": "polarity_mismatch",
                    "queries": [row.get("query") for row in rows],
                }
            )
    return contradictions


def confidence_for(evidence, contradictions):
    unique_sources = {item["path"] for item in evidence}
    if len(unique_sources) >= 2 and not contradictions:
        return "high"
    if unique_sources:
        return "medium"
    return "low"


def compose_answer(task, evidence, contradictions, confidence):
    if not evidence:
        return (
            f"Insufficient wiki evidence for deep query '{task}'. "
            "The current wiki retrieval did not produce enough grounded material to answer safely."
        )

    lines = [f"Deep query answer for '{task}' based only on local wiki evidence."]
    lines.append("")
    lines.append("Evidence summary:")
    for item in evidence:
        lines.append(f"- {item['query']} -> {item['path']}: {item['content']}")
    if contradictions:
        lines.append("")
        lines.append("Contradictions detected:")
        for contradiction in contradictions:
            lines.append(
                f"- {contradiction['path']} shows polarity mismatch across sub-questions: "
                + ", ".join(str(query) for query in contradiction["queries"])
            )
    lines.append("")
    lines.append("Sources:")
    for path in sorted({item["path"] for item in evidence}):
        lines.append(f"- {path}")
    lines.append(f"Confidence: {confidence}")
    return "\n".join(lines)


def run(task: str, workspace: str) -> dict:
    workspace = str(workspace or ".")
    reasoning_steps = []
    subquestions = decompose_task(task)
    evidence = []
    seen_pairs = set()

    for loop_no in range(1, MAX_LOOPS + 1):
        reasoning_steps.append(
            {
                "step": "decompose" if loop_no == 1 else "refine",
                "loop": loop_no,
                "subquestions": subquestions,
            }
        )
        evidence_delta = 0
        for subquestion in subquestions:
            candidates = search_wiki_candidates(subquestion, workspace=workspace, limit=2 if loop_no == 1 else 3)
            reasoning_steps.append(
                {
                    "step": "collect_evidence",
                    "loop": loop_no,
                    "subquestion": subquestion,
                    "candidate_count": len(candidates),
                    "sources": [item["path"] for item in candidates],
                }
            )
            for candidate in candidates:
                key = (candidate["query"], candidate["path"])
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                evidence.append(candidate)
                evidence_delta += 1
        if evidence_delta == 0:
            reasoning_steps.append(
                {
                    "step": "stop",
                    "loop": loop_no,
                    "reason": "no new evidence delta",
                }
            )
            break

    contradictions = detect_contradictions(evidence)
    reasoning_steps.append(
        {
            "step": "contradiction_check",
            "contradiction_count": len(contradictions),
        }
    )
    confidence = confidence_for(evidence, contradictions)
    status = "ok" if evidence else "insufficient_evidence"
    answer = compose_answer(task, evidence, contradictions, confidence)
    sources = sorted({item["path"] for item in evidence})

    result = {
        "answer": answer,
        "sources": sources,
        "evidence": evidence,
        "confidence": confidence,
        "reasoning_steps": reasoning_steps,
        "status": status,
    }
    append_log(
        workspace,
        {
            "timestamp": now_iso(),
            "task": task,
            "status": status,
            "confidence": confidence,
            "source_count": len(sources),
            "evidence_count": len(evidence),
            "result": result,
        },
    )
    return result
