from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


STOPWORDS = {
    "about",
    "after",
    "before",
    "candidate",
    "captured",
    "content",
    "draft",
    "file",
    "files",
    "from",
    "have",
    "into",
    "manual",
    "note",
    "notes",
    "only",
    "overview",
    "pending",
    "project",
    "raw",
    "review",
    "source",
    "status",
    "that",
    "their",
    "there",
    "these",
    "this",
    "trusted",
    "wiki",
    "with",
}


def _count_files(root: Path, *, pattern: str | None = None, exclude: set[str] | None = None) -> int:
    if not root.exists():
        return 0
    exclude = exclude or set()
    iterator = root.rglob(pattern) if pattern else root.rglob("*")
    total = 0
    for path in iterator:
        if not path.is_file():
            continue
        relpath = str(path.relative_to(root.parent)).replace("\\", "/")
        if relpath in exclude:
            continue
        total += 1
    return total


def _load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _pending_review_count(workspace: Path) -> int:
    payload = _load_json(workspace / ".brain" / "ingest_queue.json", {"items": []}) or {"items": []}
    items = payload.get("items", [])
    if not isinstance(items, list):
        return 0
    return sum(1 for item in items if isinstance(item, dict) and item.get("status") == "review_needed")


def _topic_terms(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", str(text or "").lower())
    return [token for token in tokens if token not in STOPWORDS]


def _top_topics(workspace: Path) -> list[str]:
    counts: Counter[str] = Counter()
    wiki_root = workspace / "wiki"
    for path in wiki_root.rglob("*.md"):
        if not path.is_file() or path.name == "overview.md":
            continue
        counts.update(_topic_terms(path.stem.replace("-", " ")))
        counts.update(_topic_terms(path.read_text(encoding="utf-8-sig", errors="ignore"))[:12])
    if not counts:
        return []
    return [term for term, _count in counts.most_common(3)]


def _recent_updates(workspace: Path) -> list[str]:
    candidates = []
    for folder in ("wiki", "raw", "drafts"):
        root = workspace / folder
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relpath = str(path.relative_to(workspace)).replace("\\", "/")
            if relpath == "wiki/overview.md":
                continue
            candidates.append((path.stat().st_mtime, relpath))
    candidates.sort(reverse=True)
    return [relpath for _mtime, relpath in candidates[:3]]


def _top_gaps(workspace: Path) -> list[str]:
    gap_path = workspace / ".brain" / "knowledge_gaps.json"
    payload = _load_json(gap_path, [])
    results: list[str] = []
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                text = str(item.get("question") or item.get("gap") or item.get("topic") or "").strip()
            else:
                text = str(item or "").strip()
            if text:
                results.append(text)
    elif isinstance(payload, dict):
        for key in ("gaps", "items", "questions"):
            values = payload.get(key)
            if not isinstance(values, list):
                continue
            for item in values:
                if isinstance(item, dict):
                    text = str(item.get("question") or item.get("gap") or item.get("topic") or "").strip()
                else:
                    text = str(item or "").strip()
                if text:
                    results.append(text)
    if results:
        return results[:3]

    if _count_files(workspace / "raw") == 0 and _count_files(workspace / "wiki", pattern="*.md", exclude={"wiki/overview.md"}) == 0:
        return ["No grounded knowledge yet. Add a file under raw/."]
    if _count_files(workspace / "wiki", pattern="*.md", exclude={"wiki/overview.md"}) == 0:
        return ["Raw sources exist but trusted wiki is still empty."]
    return []


def _suggested_actions(raw_files: int, pending_reviews: int, wiki_files: int) -> list[str]:
    if raw_files == 0 and wiki_files == 0:
        return ['abw save "project goals and constraints"', "abw ingest raw/<file>", 'abw ask "overview"']
    if pending_reviews > 0:
        return ["abw review", 'abw ask "summarize pending drafts"', 'abw save "follow-up questions"']
    if raw_files > 0 and wiki_files == 0:
        return ["abw ingest raw/<file>", "abw review", 'abw ask "what is still missing?"']
    return ['abw ask "overview"', 'abw ask "top gaps"', 'abw save "new findings"']


def build_overview(workspace: str | Path = ".") -> dict:
    root = Path(workspace).resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "wiki").mkdir(parents=True, exist_ok=True)

    project_name = root.name
    config_path = root / "abw_config.json"
    if config_path.exists():
        config = _load_json(config_path, {}) or {}
        configured_name = str(config.get("project_name") or "").strip()
        if configured_name:
            project_name = configured_name

    trusted_wiki_files = _count_files(root / "wiki", pattern="*.md", exclude={"wiki/overview.md"})
    raw_files = _count_files(root / "raw")
    draft_files = _count_files(root / "drafts", pattern="*.md")
    pending_reviews = _pending_review_count(root)
    topics = _top_topics(root)
    updates = _recent_updates(root)
    gaps = _top_gaps(root)
    actions = _suggested_actions(raw_files, pending_reviews, trusted_wiki_files)

    lines = [
        "# ABW Overview",
        "",
        f"- Project name: {project_name}",
        f"- Workspace path: {root}",
        f"- Trusted wiki file count: {trusted_wiki_files}",
        f"- Raw file count: {raw_files}",
        f"- Draft count: {draft_files}",
        f"- Pending review count: {pending_reviews}",
        "",
        "## Top known topics",
    ]
    if topics:
        lines.extend(f"- {topic}" for topic in topics)
    else:
        lines.append("- No stable topics yet.")
    lines.extend(["", "## Recent updates"])
    if updates:
        lines.extend(f"- {item}" for item in updates)
    else:
        lines.append("- No recent source changes detected.")
    lines.extend(["", "## Top gaps / missing areas"])
    if gaps:
        lines.extend(f"- {gap}" for gap in gaps)
    else:
        lines.append("- No major gaps logged yet.")
    lines.extend(["", "## Suggested next actions"])
    lines.extend(f"- {action}" for action in actions[:3])

    content = "\n".join(lines).strip() + "\n"
    overview_path = root / "wiki" / "overview.md"
    overview_path.write_text(content, encoding="utf-8")
    return {
        "path": overview_path,
        "relative_path": "wiki/overview.md",
        "content": content,
        "project_name": project_name,
        "trusted_wiki_files": trusted_wiki_files,
        "raw_files": raw_files,
        "draft_files": draft_files,
        "pending_reviews": pending_reviews,
    }
