import json
import os
from pathlib import Path

import abw_alias
import abw_i18n
import abw_suggestions


PUBLIC_COMMANDS = [
    ("abw init", "Create or normalize the current workspace structure."),
    ('abw ask "..."', "Ask ABW to route a normal task."),
    ("abw ingest raw/<file>", "Create a draft from a raw source."),
    ("abw review", "Review pending drafts."),
    ("abw doctor", "Check system health."),
    ("abw version", "Show package and workspace version info."),
    ("abw migrate", "Normalize an older workspace safely."),
    ("abw help", "Show this help."),
]

POWER_USER_COMMANDS = [
    ("abw upgrade", "Upgrade the local ABW runtime."),
    ("abw rollback", "Restore the last runtime backup."),
    ("abw repair", "Repair runtime drift and encoding issues."),
    ("abw research", "Reserved command. Not implemented yet."),
    ("abw help --advanced", "Show maintainer commands."),
]

PUBLIC_NEXT_ACTIONS = {
    'ask "..."',
    "doctor",
    "help",
    "ingest raw/<file>",
    "migrate",
    "review drafts",
    "version",
}


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
        "Run `abw init` once in a new project.",
        "Add documents with `abw ingest raw/<file>`.",
        "Promote draft knowledge through `abw review`.",
        "Run `abw doctor` when the system looks wrong.",
        "Use `abw version` to inspect the installed engine and workspace schema.",
        "Use `abw migrate` before working in older ABW project layouts.",
        "Workspace isolation: the current working directory is the default workspace unless ABW_WORKSPACE is set.",
    ]


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


def product_next_actions(actions):
    filtered = []
    for action in actions or []:
        command = str(action.get("command") if isinstance(action, dict) else action or "").strip()
        if command in PUBLIC_NEXT_ACTIONS:
            filtered.append(action)
    return filtered


def build_legacy_sections(snapshot, next_actions, workspace="."):
    guidance = situational_guidance(snapshot, next_actions, workspace=workspace)
    return [
        {
            "title": abw_i18n.t("help.overview", workspace),
            "items": [
                f"Raw files: {snapshot['raw_files']}",
                f"Draft files: {snapshot['draft_files']}",
                f"Wiki files: {snapshot['wiki_files']}",
                f"Pending drafts: {snapshot['pending_drafts']}",
                f"Coverage ratio: {format_coverage(snapshot['coverage_ratio'])}",
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


def run(workspace=".", advanced=None, mode="product"):
    workspace = str(workspace or ".")
    snapshot = build_state_snapshot(workspace)
    next_actions = abw_suggestions.suggest_next_actions(workspace)
    if mode == "legacy_runtime":
        sections = build_legacy_sections(snapshot, next_actions, workspace=workspace)
        return {
            "message": abw_i18n.t("help.message", workspace),
            "state_snapshot": snapshot,
            "sections": sections,
            "next_actions": next_actions,
        }
    next_actions = product_next_actions(next_actions)
    advanced = advanced_mode_enabled(advanced)
    sections = build_sections(snapshot, next_actions, advanced=advanced)
    message = "ABW v0.2.1 keeps the public surface small: init, ask, ingest, review, doctor, version, migrate, help."
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
