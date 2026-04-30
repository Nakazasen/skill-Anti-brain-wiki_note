from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Any, Set

SUPPORTED_EXTENSIONS = {
    ".pdf", ".txt", ".md", ".py", ".js", ".json", ".csv", ".docx", ".xlsx", ".html", ".htm", ".ts"
}

def build_inspect_report(workspace: str) -> Dict[str, Any]:
    ws_path = Path(workspace)
    raw_dir = ws_path / "raw"
    wiki_dir = ws_path / "wiki"
    drafts_dir = ws_path / "drafts"
    processed_dir = ws_path / "processed"

    report = {
        "workspace": str(workspace),
        "raw_stats": {"total": 0, "supported": 0, "unsupported": 0, "by_ext": {}},
        "wiki_stats": {"total": 0},
        "draft_stats": {"total": 0, "orphans": 0},
        "processed_stats": {"total": 0, "stale": 0},
        "weak_areas": [],
        "suggestions": []
    }

    # 1. Raw file analysis
    if raw_dir.exists():
        for root, _, files in os.walk(raw_dir):
            for f in files:
                ext = Path(f).suffix.lower()
                report["raw_stats"]["total"] += 1
                report["raw_stats"]["by_ext"][ext] = report["raw_stats"]["by_ext"].get(ext, 0) + 1
                if ext in SUPPORTED_EXTENSIONS:
                    report["raw_stats"]["supported"] += 1
                else:
                    report["raw_stats"]["unsupported"] += 1

    # 2. Wiki analysis
    if wiki_dir.exists():
        for root, _, files in os.walk(wiki_dir):
            for f in files:
                if f.endswith(".md"):
                    report["wiki_stats"]["total"] += 1

    # 3. Drafts analysis (Simple check for now)
    if drafts_dir.exists():
        draft_files = list(drafts_dir.glob("**/*.md"))
        report["draft_stats"]["total"] = len(draft_files)
        # Orphan detection: If a draft doesn't have a corresponding file in raw/ (not perfect but a start)
        # Actually, let's just keep it simple for M1.

    # 4. Processed analysis
    if processed_dir.exists():
        proc_files = list(processed_dir.glob("**/*"))
        report["processed_stats"]["total"] = len([f for f in proc_files if f.is_file()])

    # 5. Suggestions logic
    if report["raw_stats"]["total"] > 0 and report["wiki_stats"]["total"] == 0:
        report["suggestions"].append("add wiki notes for key topics")
        report["weak_areas"].append("zero wiki coverage")

    if report["draft_stats"]["total"] > 10:
        report["suggestions"].append("too many stale drafts")
        report["weak_areas"].append(f"high draft count: {report['draft_stats']['total']} files")

    if report["raw_stats"]["total"] > 0 and report["processed_stats"]["total"] == 0:
        report["suggestions"].append("run ingest raw to populate processed state")

    return report

def render_inspect_report(report: Dict[str, Any]) -> str:
    lines = []
    lines.append("ABW Corpus Intelligence")
    lines.append("-" * 23)
    lines.append(f"Workspace: {report['workspace']}")
    lines.append("")
    
    raw = report["raw_stats"]
    lines.append(f"Raw Files: {raw['total']}")
    lines.append(f"  - Supported:   {raw['supported']}")
    lines.append(f"  - Unsupported: {raw['unsupported']}")
    if raw["by_ext"]:
        ext_line = ", ".join(f"{ext or 'no-ext'}: {count}" for ext, count in raw["by_ext"].items())
        lines.append(f"  - Types: {ext_line}")
    
    lines.append(f"Wiki Coverage: {report['wiki_stats']['total']} notes")
    lines.append(f"Drafts: {report['draft_stats']['total']} pending")
    lines.append(f"Processed: {report['processed_stats']['total']} items")
    lines.append("")

    if report["weak_areas"]:
        lines.append("Weak Areas:")
        for area in report["weak_areas"]:
            lines.append(f"  [!] {area}")
        lines.append("")

    if report["suggestions"]:
        lines.append("Suggested Next Actions:")
        for sugg in report["suggestions"]:
            lines.append(f"  -> {sugg}")
    else:
        lines.append("Suggested Next Actions: None (Corpus looks healthy)")

    return "\n".join(lines)
