import json
import re
from pathlib import Path


STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "into",
    "that",
    "this",
    "what",
    "how",
    "why",
    "does",
    "work",
    "query",
    "deep",
    "compare",
    "about",
    "task",
    "wiki",
    "abw",
}


def load_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def count_wiki_topics(workspace="."):
    wiki_root = Path(workspace) / "wiki"
    if not wiki_root.exists():
        return {"file_count": 0, "topic_count": 0}

    note_files = [
        path
        for path in wiki_root.rglob("*.md")
        if path.is_file() and path.name != "index.md" and "_schemas" not in path.parts
    ]
    return {
        "file_count": len(note_files),
        "topic_count": len(note_files),
    }


def read_query_logs(workspace="."):
    path = Path(workspace) / ".brain" / "query_deep_runs.jsonl"
    rows = load_jsonl(path)
    extracted = []
    for row in rows:
        result = row.get("result", {})
        extracted.append(
            {
                "task": row.get("task", ""),
                "confidence": str(result.get("confidence") or row.get("confidence") or "").lower(),
                "status": str(result.get("status") or row.get("status") or "").lower(),
            }
        )
    return extracted


def classify_results(rows):
    success = 0
    weak = 0
    fail = 0
    for row in rows:
        confidence = row.get("confidence")
        status = row.get("status")
        if status == "insufficient_evidence":
            fail += 1
        elif confidence in {"high", "medium"}:
            success += 1
        elif confidence == "low":
            weak += 1
        else:
            fail += 1
    return {"success": success, "weak": weak, "fail": fail}


def extract_keywords(task):
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", str(task or "").lower())
    keywords = []
    for token in tokens:
        if token in STOPWORDS:
            continue
        keywords.append(token)
    return keywords


def detect_top_gaps(rows, topn=5):
    counts = {}
    for row in rows:
        if row.get("status") != "insufficient_evidence":
            continue
        keywords = extract_keywords(row.get("task", ""))
        if not keywords:
            topic = "unknown"
            counts[topic] = counts.get(topic, 0) + 1
            continue
        topic = " ".join(sorted(set(keywords[:3])))
        counts[topic] = counts.get(topic, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [{"topic": topic, "count": count} for topic, count in ranked[:topn]]


def save_report(workspace, report):
    path = Path(workspace) / ".brain" / "coverage_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def run_coverage(workspace: str) -> dict:
    workspace = str(workspace or ".")
    wiki_stats = count_wiki_topics(workspace)
    rows = read_query_logs(workspace)
    classified = classify_results(rows)
    total_questions = len(rows)
    coverage_ratio = 0.0
    if total_questions > 0:
        coverage_ratio = round(classified["success"] / total_questions, 4)

    report = {
        "total_questions": total_questions,
        "success": classified["success"],
        "weak": classified["weak"],
        "fail": classified["fail"],
        "coverage_ratio": coverage_ratio,
        "top_gaps": detect_top_gaps(rows, topn=5),
        "wiki_file_count": wiki_stats["file_count"],
        "wiki_topic_count": wiki_stats["topic_count"],
    }
    save_report(workspace, report)
    return report
