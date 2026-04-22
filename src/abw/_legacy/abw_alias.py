import ast
import inspect

ALIAS_MAP = {
    "abw-dashboard": "dashboard",
    "abw-wizard": "wizard",
    "abw-resume": "resume",
    "abw-trend": "system_trend",
    "abw-language": "set_language",
    "abw-query": "query",
    "abw-deep": "query_deep",
    "abw-ingest": "ingest",
    "abw-review": "review_drafts",
    "abw-drafts": "list_drafts",
    "abw-explain": "explain_draft",
    "abw-approve": "approve_draft",
    "abw-coverage": "coverage",
    "abw-help": "help",
}


INTENT_COMMANDS = {
    "approve_draft": "approve draft",
    "coverage": "coverage",
    "dashboard": "show dashboard",
    "explain_draft": "explain draft",
    "help": "help",
    "ingest": "ingest",
    "list_drafts": "list drafts",
    "query": "ask",
    "query_deep": "deep query",
    "resume": "resume",
    "review_drafts": "review drafts",
    "set_language": "set language",
    "system_trend": "system trend",
    "wizard": "wizard",
}


def _runner_handler_lanes():
    import abw_runner

    source = inspect.getsource(abw_runner.execute_lane)
    tree = ast.parse(source)
    lanes = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name) or target.id != "handlers":
                continue
            if isinstance(node.value, ast.Dict):
                lanes.update(
                    key.value
                    for key in node.value.keys
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                )
    return lanes


def discover_lanes():
    import abw_router

    lanes = set(abw_router.SUPPORTED_LANES)
    lanes.update(_runner_handler_lanes())
    lanes.add("set_language")
    lanes.discard("legacy_execution")
    return sorted(lanes)


def unknown_aliases():
    lanes = set(discover_lanes())
    return {alias: lane for alias, lane in ALIAS_MAP.items() if lane not in lanes}


def normalize_alias_token(token):
    normalized = str(token or "").strip()
    if normalized.startswith("/"):
        normalized = normalized[1:]
    return normalized.lower()


def is_alias_command(token):
    return normalize_alias_token(token) in ALIAS_MAP


def rewrite_task(task):
    raw = str(task or "").strip()
    if not raw.startswith("/abw-"):
        return raw

    alias, _, arguments = raw.partition(" ")
    intent = ALIAS_MAP.get(normalize_alias_token(alias))
    if not intent:
        return raw

    prefix = INTENT_COMMANDS[intent]
    arguments = arguments.strip()
    return f"{prefix} {arguments}".strip()


def rewrite_entry_command(command, task=""):
    command_text = str(command or "").strip()
    task_text = str(task or "").strip()
    if not is_alias_command(command_text):
        return command_text, rewrite_task(task_text)

    combined = f"{command_text} {task_text}".strip()
    return "/abw-ask", rewrite_task(combined)


def help_pairs():
    reverse_aliases = {intent: alias for alias, intent in ALIAS_MAP.items()}
    pairs = []
    for intent, natural in INTENT_COMMANDS.items():
        alias = reverse_aliases.get(intent)
        if alias:
            pairs.append(
                {
                    "intent": intent,
                    "natural": natural,
                    "command": f"/{alias}",
                }
            )
    return pairs
