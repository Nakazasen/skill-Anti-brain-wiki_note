import json
import os
import re
import sys
from pathlib import Path


INGEST_FLOW = [
    "/abw-ingest",
    "/abw-drafts",
    "/abw-explain",
    "USER_APPROVE",
]

QUERY_FLOW = [
    "/abw-query",
    "AUTO_IF_FAIL:/abw-deep",
]

HEALTH_FLOW = [
    "/abw-dashboard",
    "/abw-coverage",
    "/abw-trend",
]

FLOW_CHOICES = {
    1: {
        "name": "Learn knowledge",
        "description": "ingest -> drafts -> explain -> optional approval",
        "flow": INGEST_FLOW,
    },
    2: {
        "name": "Ask question",
        "description": "query -> deep query only if needed",
        "flow": QUERY_FLOW,
    },
    3: {
        "name": "System check",
        "description": "dashboard -> coverage -> trend",
        "flow": HEALTH_FLOW,
    },
}

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
        option("Learn knowledge", "/abw-wizard 1", "ingest_input", flow="ingest_review_approve"),
        option("Ask question", "/abw-wizard 2", "query_input", flow="query_gap_ingest"),
        option("System check", "/abw-wizard 3", "choose_action", flow="system_check"),
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
        "Choose a guided flow. Every action goes through the ABW entrypoint.",
    ]
    for item in indexed_options(options):
        lines.append(f"{item['index']}. {item['label']} ({item['command']})")
    lines.append("")
    lines.append("Reply with: /abw-wizard <number>")
    return "\n".join(lines)


def render_flow_menu():
    lines = [
        "ABW Wizard",
        "",
        "Choose a guided workflow:",
    ]
    for index, item in FLOW_CHOICES.items():
        lines.append(f"{index}. {item['name']} - {item['description']}")
    lines.append("")
    lines.append("Reply with: /abw-wizard <number>")
    return "\n".join(lines)


def command_without_placeholder(command, prompt, input_func):
    command = str(command or "").strip()
    if command == "/abw-ingest":
        value = input_func("Raw file path for ingest, or blank to skip: ").strip()
        return f"/abw-ingest {value}" if value else None
    if command == "/abw-query":
        value = input_func("Question: ").strip()
        return f"/abw-query {value}" if value else None
    if command == "/abw-deep":
        value = prompt.get("last_query") or input_func("Deep question: ").strip()
        return f"/abw-deep {value}" if value else None
    if command == "/abw-explain":
        draft = first_draft_from_history(prompt.get("history", []))
        if not draft:
            draft = input_func("Draft path to explain, or blank to skip: ").strip()
        return f"/abw-explain {draft}" if draft else None
    return command


def result_failed(result):
    if not isinstance(result, dict):
        return True
    if result.get("gap_logged") is True:
        return True
    if result.get("binding_status") == "rejected":
        return True
    if result.get("runner_status") == "blocked":
        return True
    current_state = str(result.get("current_state") or "").strip().lower()
    if current_state in {"blocked", "knowledge_gap_logged"}:
        return True
    knowledge = result.get("knowledge") if isinstance(result.get("knowledge"), dict) else {}
    return bool(knowledge.get("gap_logged"))


def first_draft_from_result(result):
    if not isinstance(result, dict):
        return None
    for key in ("requested_draft",):
        value = str(result.get(key) or "").strip()
        if value.startswith("drafts/"):
            return value
    pending = result.get("pending_drafts") or []
    for item in pending:
        if isinstance(item, dict) and str(item.get("draft") or "").startswith("drafts/"):
            return item["draft"]
    ingest = result.get("ingest_draft") or {}
    if isinstance(ingest, dict) and str(ingest.get("draft") or "").startswith("drafts/"):
        return ingest["draft"]
    explanation = result.get("draft_explanation") or {}
    if isinstance(explanation, dict) and str(explanation.get("draft") or "").startswith("drafts/"):
        return explanation["draft"]
    batch = result.get("draft_batch_review") or {}
    for item in batch.get("items", []) if isinstance(batch, dict) else []:
        if isinstance(item, dict) and str(item.get("draft") or "").startswith("drafts/"):
            return item["draft"]
    return None


def first_draft_from_history(history):
    for item in reversed(history or []):
        draft = first_draft_from_result(item.get("result") if isinstance(item, dict) else None)
        if draft:
            return draft
    return None


def normalize_command_for_match(command):
    command = str(command or "").strip()
    if not command:
        return ""
    if command.startswith("/"):
        try:
            import abw_alias

            return abw_alias.rewrite_task(command)
        except Exception:  # noqa: BLE001 - matching must not block flow execution.
            return command
    return command


def next_action_matches(result, next_step):
    if not isinstance(result, dict) or not next_step:
        return False
    if str(next_step).startswith("AUTO_IF_FAIL:") or next_step == "USER_APPROVE":
        return False
    expected = normalize_command_for_match(next_step).split(" ", 1)[0]
    if not expected:
        return False
    for action in result.get("next_actions") or []:
        if not isinstance(action, dict):
            continue
        command = normalize_command_for_match(action.get("command"))
        if command == expected or command.startswith(expected + " "):
            return True
    return False


def execute_step(command, *, workspace=".", context=None):
    import abw_entry

    return abw_entry.handle_input(command, workspace=workspace)


def prompt_user_approval(context, workspace=".", input_func=input):
    draft = first_draft_from_history(context.get("history", []))
    if not draft:
        return {
            "status": "skipped",
            "reason": "No draft was available for approval.",
            "critical": True,
        }
    answer = input_func(f"Approve {draft}? Type yes to approve: ").strip().lower()
    if answer != "yes":
        return {
            "status": "skipped",
            "reason": "User did not approve the draft.",
            "draft": draft,
            "critical": True,
        }
    return execute_step(f"/abw-approve {draft}", workspace=workspace, context=context)


def run_flow(flow, *, workspace=".", input_func=input, output_func=print):
    context = {"history": [], "last_query": None}
    rendered = []
    previous = None
    index = 0
    total = len(flow)

    while index < total:
        step = flow[index]
        label = step.split(":", 1)[-1] if str(step).startswith("AUTO_IF_FAIL:") else step
        progress = f"Step {index + 1}/{total}: {label}"
        output_func(progress)
        rendered.append(progress)

        if step == "USER_APPROVE":
            result = prompt_user_approval(context, workspace=workspace, input_func=input_func)
        elif str(step).startswith("AUTO_IF_FAIL:"):
            command = step.split(":", 1)[1]
            if not result_failed(previous):
                result = {
                    "status": "skipped",
                    "reason": "Previous result did not require fallback.",
                    "command": command,
                }
            else:
                command = command_without_placeholder(command, context, input_func)
                result = execute_step(command, workspace=workspace, context=context) if command else {
                    "status": "skipped",
                    "reason": "No command input provided.",
                }
        else:
            command = command_without_placeholder(step, context, input_func)
            if command and command.startswith("/abw-query "):
                context["last_query"] = command.split(" ", 1)[1]
            result = execute_step(command, workspace=workspace, context=context) if command else {
                "status": "skipped",
                "reason": "No command input provided.",
            }

        previous = result
        context["history"].append({"step": step, "result": result})

        next_step = flow[index + 1] if index + 1 < total else None
        if next_action_matches(result, next_step):
            rendered.append(f"Next action matched: {next_step}")
        index += 1

    return {
        "status": "flow_completed",
        "state": {"step": "choose_action", "selected_draft": None, "flow": "auto"},
        "selected_command": None,
        "should_execute": False,
        "flow": list(flow),
        "history": context["history"],
        "rendered": render_flow_result(context["history"], rendered),
    }


def render_flow_result(history, progress_lines):
    lines = ["ABW Wizard Auto-Flow", ""]
    lines.extend(progress_lines)
    lines.append("")
    lines.append("Results:")
    for index, item in enumerate(history, start=1):
        result = item.get("result") or {}
        state = result.get("current_state") or result.get("status") or "unknown"
        command = item.get("step")
        lines.append(f"{index}. {command}: {state}")
        reason = result.get("reason")
        if reason:
            lines.append(f"   reason: {reason}")
    return "\n".join(lines)


def flow_for_selection(selection):
    item = FLOW_CHOICES.get(selection)
    return item["flow"] if item else None


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
        flow = flow_for_selection(selection)
        if flow and state.get("step") == "choose_action":
            allow_interactive = os.environ.get("ABW_WIZARD_INTERACTIVE") == "1" and sys.stdin.isatty()
            input_func = input if allow_interactive else (lambda _prompt: "")
            return run_flow(flow, workspace=workspace, input_func=input_func, output_func=lambda _text: None)
        return apply_selection(workspace, state, selection)

    options = indexed_options(choose_action_options())
    save_state(workspace, state)
    return {
        "status": "menu",
        "state": state,
        "selected_command": None,
        "should_execute": False,
        "options": options,
        "rendered": render_flow_menu(),
    }
