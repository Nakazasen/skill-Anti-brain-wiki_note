import json
from pathlib import Path

import abw_alias
import abw_i18n
import abw_suggestions


def load_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def count_files(path):
    path = Path(path)
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def ingest_queue(workspace):
    payload = load_json(Path(workspace) / ".brain" / "ingest_queue.json", {"items": []}) or {"items": []}
    items = payload.get("items", [])
    return items if isinstance(items, list) else []


def coverage_ratio(workspace):
    payload = load_json(Path(workspace) / ".brain" / "coverage_report.json", {}) or {}
    try:
        return float(payload.get("coverage_ratio"))
    except (TypeError, ValueError):
        return None


def build_state_snapshot(workspace):
    workspace = Path(workspace or ".")
    queue_items = ingest_queue(workspace)
    pending_drafts = [item for item in queue_items if item.get("status") == "review_needed"]
    approved_drafts = [item for item in queue_items if item.get("status") == "approved"]
    return {
        "raw_files": count_files(workspace / "raw"),
        "draft_files": count_files(workspace / "drafts"),
        "wiki_files": count_files(workspace / "wiki"),
        "queue_total": len(queue_items),
        "pending_drafts": len(pending_drafts),
        "approved_drafts": len(approved_drafts),
        "coverage_ratio": coverage_ratio(workspace),
    }


def format_coverage(value):
    if value is None:
        return "unknown"
    return f"{value:.2f}"


def situational_guidance(snapshot, next_actions, workspace="."):
    guidance = []
    if snapshot["raw_files"] == 0 and snapshot["wiki_files"] == 0 and snapshot["draft_files"] == 0:
        guidance.append(abw_i18n.t("help.guidance.no_data", workspace))
    if snapshot["pending_drafts"] > 0:
        guidance.append(abw_i18n.t("help.guidance.pending_drafts", workspace))
    if snapshot["coverage_ratio"] is not None and snapshot["coverage_ratio"] < 0.6:
        guidance.append(abw_i18n.t("help.guidance.low_coverage", workspace))
    if snapshot["raw_files"] > 0 and snapshot["pending_drafts"] == 0 and snapshot["wiki_files"] == 0:
        guidance.append(abw_i18n.t("help.guidance.raw_without_wiki", workspace))
    if not guidance and next_actions:
        guidance.append(abw_i18n.t("help.guidance.ready", workspace))
    return guidance


def minimal_commands(snapshot, workspace="."):
    commands = []
    if snapshot["raw_files"] > 0:
        commands.append("ingest raw/<file>")
    else:
        commands.append(abw_i18n.t("help.command.add_raw_and_ingest", workspace))
    if snapshot["pending_drafts"] > 0:
        commands.extend(["review drafts", "approve draft drafts/<file>"])
    if snapshot["wiki_files"] > 0:
        commands.append(abw_i18n.t("help.command.ask_direct", workspace))
    commands.extend(["coverage", "audit system"])

    deduped = []
    seen = set()
    for command in commands:
        if command in seen:
            continue
        seen.add(command)
        deduped.append(command)
    return deduped


def alias_command_items():
    labels = {
        "approve_draft": "Approve draft",
        "coverage": "Coverage",
        "dashboard": "Dashboard",
        "explain_draft": "Explain draft",
        "help": "Help",
        "ingest": "Ingest",
        "list_drafts": "Drafts",
        "query": "Query",
        "query_deep": "Deep query",
        "resume": "Resume",
        "review_drafts": "Review drafts",
        "set_language": "Language",
        "system_trend": "System trend",
        "wizard": "Wizard",
    }
    return [
        f"{labels.get(item['intent'], item['intent'])}: natural: \"{item['natural']}\"; command: {item['command']}"
        for item in abw_alias.help_pairs()
    ]


def build_sections(snapshot, next_actions, workspace="."):
    guidance = situational_guidance(snapshot, next_actions, workspace=workspace)
    return [
        {
            "title": abw_i18n.t("help.overview", workspace),
            "items": [
                f"raw_files: {snapshot['raw_files']}",
                f"draft_files: {snapshot['draft_files']}",
                f"wiki_files: {snapshot['wiki_files']}",
                f"pending_drafts: {snapshot['pending_drafts']}",
                f"coverage_ratio: {format_coverage(snapshot['coverage_ratio'])}",
            ],
        },
        {
            "title": abw_i18n.t("help.next_actions", workspace),
            "items": list(next_actions),
        },
        {
            "title": abw_i18n.t("help.situational_guidance", workspace),
            "items": guidance,
        },
        {
            "title": abw_i18n.t("help.minimal_commands", workspace),
            "items": minimal_commands(snapshot, workspace=workspace),
        },
        {
            "title": "Explicit commands",
            "items": alias_command_items(),
        },
    ]


def run(workspace="."):
    workspace = str(workspace or ".")
    snapshot = build_state_snapshot(workspace)
    next_actions = abw_suggestions.suggest_next_actions(workspace)
    sections = build_sections(snapshot, next_actions, workspace=workspace)
    return {
        "message": abw_i18n.t("help.message", workspace),
        "state_snapshot": snapshot,
        "sections": sections,
        "next_actions": next_actions,
    }
