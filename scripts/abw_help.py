import json
import os
from pathlib import Path

import abw_suggestions


PUBLIC_COMMANDS = [
    ('abw ask "..."', "Ask ABW to route a normal task."),
    ("abw ingest raw/<file>", "Create a draft from a raw source."),
    ("abw review", "Review pending drafts."),
    ("abw overview", "Generate a short workspace overview."),
    ('abw save "..."', "Save a candidate note under raw/captured_notes."),
    ("abw doctor", "Check system health."),
    ("abw help", "Show this help."),
]

POWER_USER_COMMANDS = [
    ("abw upgrade", "Upgrade the local ABW runtime."),
    ("abw rollback", "Restore the last runtime backup."),
    ("abw repair", "Repair runtime drift and encoding issues."),
    ("abw research", "Reserved command. Not implemented yet."),
    ("abw help --advanced", "Show maintainer commands."),
]


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
    return {
        "raw_files": count_files(workspace / "raw"),
        "draft_files": count_files(workspace / "drafts"),
        "wiki_files": count_files(workspace / "wiki"),
        "pending_drafts": len(pending_drafts),
        "coverage_ratio": coverage_ratio(workspace),
    }


def advanced_mode_enabled(explicit=None):
    if explicit is not None:
        return bool(explicit)
    return os.environ.get("ABW_HELP_ADVANCED") == "1"


def quick_start_items():
    return [
        'Use `abw ask "..."` for most tasks.',
        "Add documents with `abw ingest raw/<file>`.",
        "Promote draft knowledge through `abw review`.",
        "Generate a workspace summary with `abw overview`.",
        'Capture a candidate note with `abw save "..."`.',
        "Run `abw doctor` when the system looks wrong.",
    ]


def command_items(pairs):
    return [f"{command} - {description}" for command, description in pairs]


def workspace_items(snapshot):
    coverage = snapshot["coverage_ratio"]
    coverage_text = "unknown" if coverage is None else f"{coverage:.2f}"
    return [
        f"Raw files: {snapshot['raw_files']}",
        f"Draft files: {snapshot['draft_files']}",
        f"Wiki files: {snapshot['wiki_files']}",
        f"Pending drafts: {snapshot['pending_drafts']}",
        f"Coverage: {coverage_text}",
    ]


def build_sections(snapshot, next_actions, advanced=False):
    sections = [
        {
            "title": "Quick start",
            "items": quick_start_items(),
        },
        {
            "title": "Commands",
            "items": command_items(PUBLIC_COMMANDS),
        },
        {
            "title": "Workspace",
            "items": workspace_items(snapshot),
        },
    ]
    if advanced:
        sections.append(
            {
                "title": "Advanced commands",
                "items": command_items(POWER_USER_COMMANDS),
            }
        )
        sections.append(
            {
                "title": "Advanced notes",
                "items": ["Ingest flags possible contradictions automatically and writes review reports under drafts/conflicts/."],
            }
        )
    if next_actions:
        sections.append(
            {
                "title": "Suggested next steps",
                "items": [action["command"] for action in next_actions],
            }
        )
    return sections


def run(workspace=".", advanced=None):
    workspace = str(workspace or ".")
    snapshot = build_state_snapshot(workspace)
    next_actions = abw_suggestions.suggest_next_actions(workspace)
    advanced = advanced_mode_enabled(advanced)
    sections = build_sections(snapshot, next_actions, advanced=advanced)
    message = "ABW v2 keeps the public surface small: ask, ingest, review, overview, save, doctor, help."
    if advanced:
        message += " Advanced mode adds maintainer commands and notes that ingest flags possible contradictions automatically."
    return {
        "message": message,
        "state_snapshot": snapshot,
        "sections": sections,
        "next_actions": next_actions,
        "advanced": advanced,
        "public_commands": [command for command, _description in PUBLIC_COMMANDS],
        "advanced_commands": [command for command, _description in POWER_USER_COMMANDS] if advanced else [],
    }
