import json
import re
from pathlib import Path


VALID_STEPS = {
    "choose_action",
    "ingest_input",
    "ingest_result",
    "explain_draft",
    "approve_draft",
    "review_list",
    "review_item_loop",
    "query_input",
    "query_result",
    "gap_action",
}
DEFAULT_STATE = {"step": "choose_action", "selected_draft": None, "flow": None}


def state_path(workspace="."):
    return Path(workspace or ".") / ".brain" / "wizard_state.json"


def load_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return default


def save_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize_state(state):
    state = dict(state or {})
    step = str(state.get("step") or "choose_action").strip()
    if step not in VALID_STEPS:
        step = "choose_action"
    return {
        "step": step,
        "selected_draft": state.get("selected_draft"),
        "flow": state.get("flow"),
    }


def load_state(workspace="."):
    return normalize_state(load_json(state_path(workspace), DEFAULT_STATE))


def save_state(workspace, state):
    state = normalize_state(state)
    save_json(state_path(workspace), state)
    return state


def reset_state(workspace="."):
    return save_state(workspace, DEFAULT_STATE)


def ingest_queue(workspace="."):
    payload = load_json(Path(workspace) / ".brain" / "ingest_queue.json", {"items": []}) or {"items": []}
    items = payload.get("items", [])
    return items if isinstance(items, list) else []


def pending_drafts(workspace="."):
    return [
        item.get("draft")
        for item in ingest_queue(workspace)
        if item.get("status") == "review_needed" and item.get("draft")
    ]


def extract_selection(task):
    normalized = str(task or "").strip().lower()
    match = re.search(r"(?:wizard|choose|select)\s+(\d+)\b", normalized)
    if match:
        return int(match.group(1))
    if normalized.isdigit():
        return int(normalized)
    return None


def option(label, command, next_step, *, selected_draft=None, flow=None):
    return {
        "label": label,
        "command": command,
        "next_step": next_step,
        "selected_draft": selected_draft,
        "flow": flow,
    }


def choose_action_options():
    return [
        option("Flow 1: ingest -> review -> approve", "ingest raw/<file>", "ingest_input", flow="ingest_review_approve"),
        option("Flow 2: batch review", "list drafts", "review_list", flow="batch_review"),
        option("Flow 3: query -> gap -> ingest", "What is <topic>?", "query_input", flow="query_gap_ingest"),
    ]


def draft_options(drafts, next_step):
    if not drafts:
        return [
            option("No pending drafts. Ingest a raw file first.", "ingest raw/<file>", "ingest_input", flow="ingest_review_approve"),
            option("Back to the three flows.", "wizard reset", "choose_action"),
        ]
    return [
        option(f"Explain {draft}", f"explain draft {draft}", next_step, selected_draft=draft)
        for draft in drafts
    ] + [option("Back to the three flows.", "wizard reset", "choose_action")]


def options_for_step(workspace, state):
    step = state["step"]
    drafts = pending_drafts(workspace)
    selected = state.get("selected_draft")
    flow = state.get("flow")

    if step == "ingest_input":
        return [
            option("Run ingest with an explicit raw path.", "ingest raw/<file>", "ingest_result", flow=flow),
            option("Back to the three flows.", "wizard reset", "choose_action"),
        ]

    if step == "ingest_result":
        return [
            option("List drafts created by ingest.", "list drafts", "explain_draft", flow=flow),
            option("Back to the three flows.", "wizard reset", "choose_action"),
        ]

    if step == "explain_draft":
        if selected:
            return [
                option(f"Explain {selected}", f"explain draft {selected}", "approve_draft", selected_draft=selected, flow=flow),
                option("Choose another draft.", "list drafts", "explain_draft", selected_draft=None, flow=flow),
                option("Back to the three flows.", "wizard reset", "choose_action"),
            ]
        return draft_options(drafts, "approve_draft")

    if step == "approve_draft" and selected:
        return [
            option(f"Approve {selected}", f"approve draft {selected}", "choose_action", selected_draft=None, flow=None),
            option(f"Explain {selected} again", f"explain draft {selected}", "approve_draft", selected_draft=selected, flow=flow),
            option("Choose another draft.", "list drafts", "explain_draft", selected_draft=None, flow=flow),
        ]

    if step == "review_list":
        return [
            option("List pending drafts.", "list drafts", "review_item_loop", flow=flow),
            option("Back to the three flows.", "wizard reset", "choose_action"),
        ]

    if step == "review_item_loop":
        return draft_options(drafts, "approve_draft")

    if step == "query_input":
        return [
            option("Ask a concrete question.", "What is <topic>?", "query_result", flow=flow),
            option("Back to the three flows.", "wizard reset", "choose_action"),
        ]

    if step == "query_result":
        return [
            option("If a gap was logged, choose an ingest action.", "ingest raw/<file>", "gap_action", flow=flow),
            option("Ask another concrete question.", "What is <topic>?", "query_result", flow=flow),
            option("Back to the three flows.", "wizard reset", "choose_action"),
        ]

    if step == "gap_action":
        return [
            option("Ingest a raw source for the gap.", "ingest raw/<file>", "ingest_result", flow="ingest_review_approve"),
            option("Back to the three flows.", "wizard reset", "choose_action"),
        ]

    return choose_action_options()


def indexed_options(options):
    return [{**item, "index": index} for index, item in enumerate(options, start=1)]


def render_menu(step, options):
    lines = [
        "ABW Wizard",
        f"Step: {step}",
        "",
        "Choose one option. The wizard returns an existing command and never runs it automatically.",
    ]
    for item in indexed_options(options):
        lines.append(f"{item['index']}. {item['label']} ({item['command']})")
    lines.append("")
    lines.append("Reply with: wizard <number>")
    return "\n".join(lines)


def apply_selection(workspace, state, selection):
    options = indexed_options(options_for_step(workspace, state))
    selected = next((item for item in options if item["index"] == selection), None)
    if selected is None:
        return {
            "status": "blocked",
            "reason": f"Invalid wizard selection: {selection}",
            "state": state,
            "options": options,
            "rendered": render_menu(state["step"], options),
        }

    next_state = save_state(
        workspace,
        {
            "step": selected["next_step"],
            "selected_draft": selected.get("selected_draft"),
            "flow": selected.get("flow") if selected.get("flow") is not None else state.get("flow"),
        },
    )
    next_options = indexed_options(options_for_step(workspace, next_state))
    return {
        "status": "selection_mapped",
        "state": next_state,
        "selected": selected,
        "selected_command": selected["command"],
        "should_execute": False,
        "options": next_options,
        "rendered": "\n".join(
            [
                "ABW Wizard",
                f"Selected: {selected['label']}",
                f"Command: {selected['command']}",
                "",
                "Safety: command was not executed. Send this command via /abw-ask when ready.",
            ]
        ),
    }


def run(task="", workspace="."):
    workspace = str(workspace or ".")
    normalized = str(task or "").strip().lower()
    if "reset" in normalized:
        state = reset_state(workspace)
    else:
        state = load_state(workspace)

    selection = extract_selection(task)
    if selection is not None:
        return apply_selection(workspace, state, selection)

    options = indexed_options(options_for_step(workspace, state))
    save_state(workspace, state)
    return {
        "status": "menu",
        "state": state,
        "selected_command": None,
        "should_execute": False,
        "options": options,
        "rendered": render_menu(state["step"], options),
    }
