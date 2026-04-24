import argparse
import json
import os
import re
import sys
from pathlib import Path


REJECTED_OUTPUT = {
    "binding_status": "rejected",
    "current_state": "blocked",
    "reason": "output not produced by runner",
}
ALLOWED_BINDING_STATUS = {
    "runner_enforced",
    "runner_checked",
    "prompt_only",
    "rejected",
}
ALLOWED_BINDING_SOURCES = {"cli", "mcp"}
RUNTIME_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
NONCE_PATTERN = re.compile(r"^[0-9a-f]{32}$")
USER_LEVELS = {"beginner", "intermediate", "expert"}


def strict_schema_validation(result):
    if not isinstance(result, dict):
        return "output not produced by runner"

    binding_status = str(result.get("binding_status") or "").strip()
    if binding_status not in ALLOWED_BINDING_STATUS:
        return "invalid binding_status"

    runtime_id = str(result.get("runtime_id") or "").strip()
    if not runtime_id or not RUNTIME_ID_PATTERN.fullmatch(runtime_id):
        return "invalid runtime_id"

    validation_proof = str(result.get("validation_proof") or "").strip()
    if not SHA256_PATTERN.fullmatch(validation_proof):
        return "invalid validation_proof"

    binding_source = str(result.get("binding_source") or "").strip().lower()
    if binding_source not in ALLOWED_BINDING_SOURCES:
        return "invalid binding_source"

    nonce = str(result.get("nonce") or "").strip().lower()
    if not NONCE_PATTERN.fullmatch(nonce):
        return "invalid nonce"

    answer = str(result.get("answer") or "").strip()
    if not answer:
        return "empty answer"

    finalization_block = str(result.get("finalization_block") or "").strip()
    if not finalization_block:
        return "missing finalization_block"

    return None


def enforce_runner_output(result):
    reason = strict_schema_validation(result)
    if reason:
        rejected = dict(REJECTED_OUTPUT)
        rejected["reason"] = reason
        return rejected
    return result


def trust_label(result):
    binding_status = str(result.get("binding_status") or "").strip()
    if binding_status == "runner_enforced":
        return "enforced"
    if binding_status == "runner_checked":
        return "checked"
    if binding_status == "prompt_only":
        return "prompt"
    if binding_status == "rejected":
        return "rejected"
    return "unknown"


def result_intent(result):
    route = result.get("route") if isinstance(result.get("route"), dict) else {}
    return str(
        route.get("lane")
        or route.get("intent")
        or result.get("lane")
        or result.get("intent")
        or ""
    ).strip().lower()


def clean_answer(result):
    answer = str(
        result.get("message")
        or result.get("answer")
        or result.get("summary")
        or result.get("reason")
        or ""
    ).strip()
    finalization_block = str(result.get("finalization_block") or "").strip()
    if finalization_block and answer.endswith(finalization_block):
        answer = answer[: -len(finalization_block)].rstrip()
    if "## Finalization" in answer:
        answer = answer.split("## Finalization", 1)[0].rstrip()
    return answer


def clean_summary(result):
    summary = result.get("summary")
    if isinstance(summary, (dict, list)):
        return json.dumps(summary, ensure_ascii=False, sort_keys=True)
    if summary:
        return str(summary).strip()

    knowledge = result.get("knowledge") if isinstance(result.get("knowledge"), dict) else {}
    if knowledge.get("source_summary"):
        return str(knowledge["source_summary"]).strip()

    if result.get("current_state"):
        return f"state: {result['current_state']}"
    return ""


def normalize_actions(actions):
    normalized = []
    for action in actions or []:
        if isinstance(action, dict):
            label = str(action.get("label") or "").strip()
            command = str(action.get("command") or "").strip()
            if label and command:
                normalized.append(f"{label}: {command}")
            elif command:
                normalized.append(command)
            elif label:
                normalized.append(label)
        else:
            text = str(action or "").strip()
            if text:
                normalized.append(text)
    return normalized


def normalize_agent_actions(actions):
    normalized = []
    for action in actions or []:
        if isinstance(action, dict):
            text = str(action.get("command") or action.get("label") or "").strip()
        else:
            text = str(action or "").strip()
        if text:
            normalized.append(text)
    return normalized


def normalize_user_level(level):
    normalized = str(level or "").strip().lower()
    return normalized if normalized in USER_LEVELS else None


def detect_ui_mode(result=None, debug=False):
    if debug:
        return "debug"
    if os.environ.get("ABW_AGENT_MODE") == "1":
        return "agent"
    if os.environ.get("ABW_CLI_MODE") == "1":
        return "cli"
    if os.environ.get("ABW_ENTRY_CALLER") == "abw_cli":
        return "cli"

    if isinstance(result, dict):
        binding_source = str(result.get("binding_source") or "").strip().lower()
        if binding_source == "mcp":
            return "agent"

    if not sys.stdout.isatty():
        return "agent"
    return "cli"


def detect_user_level(result, level=None):
    override = normalize_user_level(level) or normalize_user_level(os.environ.get("ABW_USER_LEVEL"))
    if override:
        return override

    actions = result.get("next_actions", []) if isinstance(result, dict) else []
    action_count = len(actions) if isinstance(actions, list) else 0
    if action_count <= 1:
        return "beginner"
    if action_count <= 3:
        return "intermediate"
    return "expert"


def agent_mode_enabled():
    return detect_ui_mode() == "agent"


def agent_title(result):
    intent = result_intent(result)
    if intent == "help":
        return "ABW Help"
    if intent in {"query", "query_deep", "knowledge", "knowledge_deep"}:
        return "ABW Query"
    if intent in {"review", "review_drafts", "list_drafts", "explain_draft", "approve_draft"}:
        return "ABW Review"
    if intent == "coverage":
        return "ABW Coverage"
    if intent in {"dashboard", "system_trend"}:
        return "ABW Dashboard"
    return "ABW"


def _agent_answer_lines(result):
    intent = result_intent(result)
    if intent == "help":
        lines = []
        for section in result.get("sections") or []:
            title = str(section.get("title") or "").strip().lower()
            if title in {"quick start", "commands", "advanced commands"}:
                lines.extend(str(item).strip() for item in section.get("items") or [] if str(item).strip())
        return lines[:6] or ["Use `abw ask \"...\"` for most tasks."]

    if intent == "coverage":
        report = result.get("coverage_report") if isinstance(result.get("coverage_report"), dict) else {}
        lines = [
            f"Coverage ratio: {report.get('coverage_ratio', 'unknown')}",
            f"Questions: {report.get('total_questions', 'unknown')}",
            f"Pass/Weak/Fail: {report.get('success', 0)}/{report.get('weak', 0)}/{report.get('fail', 0)}",
        ]
        gaps = report.get("top_gaps") or []
        if gaps:
            lines.extend(f"Gap: {gap}" for gap in gaps[:3])
        return lines

    if intent in {"dashboard", "system_trend"}:
        knowledge = result.get("knowledge") if isinstance(result.get("knowledge"), dict) else {}
        return [
            f"Raw files: {knowledge.get('raw_files', 'unknown')}",
            f"Draft files: {knowledge.get('draft_files', 'unknown')}",
            f"Wiki files: {knowledge.get('wiki_files', 'unknown')}",
            f"Pending drafts: {knowledge.get('pending_drafts', 'unknown')}",
            f"Coverage: {knowledge.get('coverage_ratio', 'unknown')}",
        ]

    answer_lines = compact_text(clean_answer(result), max_lines=6)
    return answer_lines or ["No answer text was returned."]


def _agent_status_lines(result, include_coverage=False):
    lines = [
        f"Raw files: {_state_value(result, 'raw_files')}",
        f"Draft files: {_state_value(result, 'draft_files')}",
        f"Wiki files: {_state_value(result, 'wiki_files')}",
        f"Pending drafts: {_state_value(result, 'pending_drafts')}",
    ]
    if include_coverage:
        coverage = _state_value(result, "coverage_ratio", fallback=None)
        if coverage is None:
            knowledge = result.get("knowledge") if isinstance(result.get("knowledge"), dict) else {}
            coverage = knowledge.get("coverage_ratio", "unknown")
        lines.append(f"Coverage: {coverage}")
    return lines


def render_beginner(result):
    actions = normalize_agent_actions(result.get("next_actions") or [])[:2]
    if not actions:
        actions = ["ingest raw/<file>", 'ask "..."']

    summary = clean_summary(result) or "You can continue with one of these simple next steps."
    lines = [
        f"### {agent_title(result)}",
        "",
        "### Summary",
        f"- {summary}",
    ]
    if result_intent(result) in {"help", "dashboard", "system_trend"}:
        answer_lines = _agent_answer_lines(result)
    else:
        answer_lines = compact_text(clean_answer(result), max_lines=2)
    if answer_lines:
        lines.extend(["", "### Answer"])
        lines.extend(f"- {line}" for line in answer_lines)

    lines.extend(["", "### Next Actions"])
    lines.extend(f"- {action}" for action in actions)
    return "\n".join(lines).strip()


def render_intermediate(result):
    lines = [f"### {agent_title(result)}"]
    summary = clean_summary(result)
    if summary:
        lines.extend(["", "### Summary", f"- {summary}"])

    answer_lines = _agent_answer_lines(result)
    if answer_lines:
        lines.extend(["", "### Answer"])
        lines.extend(f"- {line}" for line in answer_lines)

    actions = normalize_agent_actions(result.get("next_actions") or [])
    if actions:
        lines.extend(["", "### Next Actions"])
        lines.extend(f"- {action}" for action in actions[:4])

    return "\n".join(lines).strip()


def render_expert(result):
    lines = [f"### {agent_title(result)}"]
    summary = clean_summary(result)
    if summary:
        lines.extend(["", "### Summary", f"- {summary}"])

    lines.extend(["", "### Answer"])
    lines.extend(f"- {line}" for line in _agent_answer_lines(result))

    details = ["Level: expert"]
    if result.get("current_state"):
        state = str(result.get("current_state")).replace("_", " ")
        details.append(f"Mode: {state}")
    if details:
        lines.extend(["", "### Details"])
        lines.extend(f"- {detail}" for detail in details)

    actions = normalize_agent_actions(result.get("next_actions") or [])
    if actions:
        lines.extend(["", "### Next Actions"])
        lines.extend(f"- {action}" for action in actions)

    return "\n".join(lines).strip()


def render_agent(result, level=None):
    user_level = detect_user_level(result, level=level)
    if user_level == "beginner":
        return render_beginner(result)
    if user_level == "intermediate":
        return render_intermediate(result)
    return render_expert(result)


def box_header(title):
    text = f" {str(title or 'ABW').strip()} "
    rule = "=" * len(text)
    return [rule, text.strip(), rule]


def divider():
    return "-" * 16


def append_section(lines, title, items, limit=None):
    cleaned = [str(item).strip() for item in items or [] if str(item).strip()]
    if limit is not None:
        cleaned = cleaned[:limit]
    if not cleaned:
        return
    if lines and str(lines[-1]).strip():
        lines.append(divider())
    lines.append(str(title).strip())
    lines.extend(f"- {item}" for item in cleaned)


def compact_text(text, max_lines=4):
    compacted = []
    for line in str(text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("## Finalization"):
            break
        if stripped.startswith(("- current_state:", "- evidence:", "- gaps_or_limitations:", "- next_steps:")):
            continue
        compacted.append(stripped)
        if len(compacted) >= max_lines:
            break
    return compacted


def limit_lines(lines, max_lines=15):
    cleaned = []
    previous_blank = False
    for line in lines:
        is_blank = not str(line).strip()
        if is_blank and previous_blank:
            continue
        cleaned.append(line)
        previous_blank = is_blank
    return "\n".join(cleaned[:max_lines]).strip()


def _lookup_section_item(sections, label):
    expected = str(label or "").strip().lower()
    for section in sections or []:
        if not isinstance(section, dict):
            continue
        for item in section.get("items") or []:
            text = str(item or "").strip()
            key, sep, value = text.partition(":")
            if sep and key.strip().lower() == expected:
                return value.strip()
    return None


def _state_value(result, key, fallback="unknown"):
    snapshot = result.get("state_snapshot") if isinstance(result.get("state_snapshot"), dict) else {}
    value = snapshot.get(key)
    if value is None:
        value = _lookup_section_item(result.get("sections") or [], key)
    if value is None or value == "":
        return fallback
    return value


def _action_command(action):
    if isinstance(action, dict):
        return str(action.get("command") or action.get("label") or "").strip()
    return str(action or "").strip()


def render_help(result):
    lines = box_header("ABW Help")
    for section in result.get("sections") or []:
        title = str(section.get("title") or "").strip()
        items = []
        for item in section.get("items") or []:
            if isinstance(item, dict) and item.get("label") and item.get("command"):
                text = f"{item['label']}: {item['command']}"
            else:
                text = str(item).strip()
            if text:
                items.append(text)
        append_section(lines, title, items, limit=7 if title == "Commands" else None)
    return limit_lines(lines, max_lines=24)


def render_query(result):
    lines = box_header("ABW Query")
    summary = clean_summary(result)
    if summary:
        append_section(lines, "Source", [summary], limit=1)
    append_section(lines, "Result", compact_text(clean_answer(result), max_lines=4), limit=4)
    append_section(lines, "Actions", normalize_actions(result.get("next_actions") or []), limit=3)
    return limit_lines(lines)


def render_review(result):
    lines = box_header("ABW Review")
    summary = clean_summary(result)
    if summary:
        append_section(lines, "Summary", [summary], limit=1)
    append_section(lines, "Result", compact_text(clean_answer(result), max_lines=5), limit=5)
    append_section(lines, "Actions", normalize_actions(result.get("next_actions") or []), limit=3)
    return limit_lines(lines)


def render_coverage(result):
    report = result.get("coverage_report") if isinstance(result.get("coverage_report"), dict) else {}
    lines = box_header("ABW Coverage")
    append_section(
        lines,
        "Status",
        [
            f"Coverage ratio: {report.get('coverage_ratio', 'unknown')}",
            f"Questions: {report.get('total_questions', 'unknown')}",
            f"Pass/Weak/Fail: {report.get('success', 0)}/{report.get('weak', 0)}/{report.get('fail', 0)}",
            f"Wiki topics: {report.get('wiki_topic_count', 'unknown')}",
        ],
    )
    gaps = report.get("top_gaps") or []
    append_section(lines, "Gaps", gaps if gaps else ["No top gaps"], limit=3)
    append_section(lines, "Actions", normalize_actions(result.get("next_actions") or []), limit=2)
    return limit_lines(lines)


def render_dashboard(result):
    knowledge = result.get("knowledge") if isinstance(result.get("knowledge"), dict) else {}
    lines = box_header("ABW Dashboard")
    append_section(
        lines,
        "Workspace",
        [
            f"Raw files: {knowledge.get('raw_files', 'unknown')}",
            f"Draft files: {knowledge.get('draft_files', 'unknown')}",
            f"Wiki files: {knowledge.get('wiki_files', 'unknown')}",
            f"Pending drafts: {knowledge.get('pending_drafts', 'unknown')}",
            f"Coverage: {knowledge.get('coverage_ratio', 'unknown')}",
        ],
    )
    append_section(lines, "Actions", normalize_actions(result.get("next_actions") or []), limit=3)
    return limit_lines(lines)


def render_generic(result):
    lines = box_header("ABW")
    summary = clean_summary(result)
    if summary:
        append_section(lines, "Status", [summary], limit=1)
    append_section(lines, "Result", compact_text(clean_answer(result), max_lines=5), limit=5)
    append_section(lines, "Actions", normalize_actions(result.get("next_actions") or []), limit=3)
    return limit_lines(lines)


def render_cli(result, debug=False):
    intent = result_intent(result)
    if intent == "help":
        return render_help(result)
    if intent in {"query", "query_deep", "knowledge", "knowledge_deep"}:
        return render_query(result)
    if intent in {"review", "review_drafts", "list_drafts", "explain_draft", "approve_draft"}:
        return render_review(result)
    if intent == "coverage":
        return render_coverage(result)
    if intent in {"dashboard", "system_trend"}:
        return render_dashboard(result)
    return render_generic(result)


def render(result, debug=False, level=None):
    mode = detect_ui_mode(result, debug=debug)
    if mode == "debug":
        return json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if mode == "agent":
        return render_agent(result, level=level)
    return render_cli(result)


def render_user_view(result):
    message = str(result.get("message") or result.get("answer") or result.get("reason") or "").strip()
    trust = trust_label(result)
    if trust:
        message = f"trust: {trust}\n\n{message}".strip()

    return {
        "message": message,
        "next_actions": result.get("next_actions") or [],
        "sections": result.get("sections") or [],
    }


def debug_requested(args, result, raw_payload=None):
    return bool(args.debug)


def read_text_tolerant(path):
    data = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def normalize_newlines(text):
    return str(text).replace("\r\n", "\n").replace("\r", "\n")


def configure_stdout():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main(argv=None):
    configure_stdout()
    parser = argparse.ArgumentParser(description="Outer binding shim for ABW runner outputs.")
    parser.add_argument("--file", help="Path to a JSON payload to validate.")
    parser.add_argument("--debug", action="store_true", help="Expose the full trusted runner payload.")
    parser.add_argument("--level", choices=sorted(USER_LEVELS), help="Override adaptive agent output level.")
    args = parser.parse_args(argv)

    raw_payload = None
    input_text = None
    try:
        if args.file:
            input_text = read_text_tolerant(args.file)
        else:
            input_text = sys.stdin.read()
        raw_payload = json.loads(input_text) if input_text.strip() else None
        result = enforce_runner_output(raw_payload)
    except json.JSONDecodeError:
        if input_text and input_text.strip():
            print(normalize_newlines(input_text).rstrip())
            return 0
        result = dict(REJECTED_OUTPUT)
    except Exception:
        result = dict(REJECTED_OUTPUT)

    print(render(result, debug=debug_requested(args, result, raw_payload), level=args.level))
    return 0 if result.get("binding_status") != "rejected" else 3


if __name__ == "__main__":
    if os.environ.get("ABW_DEV_OUTPUT") != "1":
        print("Do not run abw_output directly. Use 'abw' CLI. Set ABW_DEV_OUTPUT=1 for dev mode.", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main())
