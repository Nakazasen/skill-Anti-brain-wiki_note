from __future__ import annotations


PUBLIC_COMMANDS = (
    ("init", "Create or normalize workspace structure."),
    ("ask", "Route a normal task."),
    ("ingest", "Create a draft from a raw source."),
    ("review", "Review pending drafts."),
    ("provider", "Manage multi-provider routing and health."),
    ("doctor", "Check system health."),
    ("inspect", "Report corpus intelligence diagnostics."),
    ("gaps", "Explain retrieval eval failures using corpus diagnostics."),
    ("recover-plan", "Generate a structured recovery roadmap for corpus gaps."),
    ("recover-verify", "Measure improvement between the last two evaluation runs."),
    ("trend", "Analyze historical health and retrieval quality trends."),
    ("improve", "Turn diagnostics into prioritized action items."),
    ("apply", "Safely execute or dry-run remediation actions."),
    ("version", "Show package and workspace version info."),
    ("migrate", "Normalize an older workspace safely."),
    ("help", "Show product help."),
)

ADVANCED_COMMANDS = (
    ("upgrade", "Upgrade ABW package safely with backup and health checks."),
    ("rollback", "Restore the last runtime backup."),
    ("repair", "Repair runtime drift."),
    ("eval", "Run retrieval evaluation harness."),
    ("research", "Reserved command. Not implemented yet."),
    ("help --advanced", "Show maintainer commands."),
)

DEPRECATED_ALIASES = {
    "health": "doctor",
    "update": "upgrade",
    "query": "ask",
    "query-deep": "ask",
    "query_deep": "ask",
}

PUBLIC_HELP = dict(PUBLIC_COMMANDS)
ADVANCED_HELP = dict(ADVANCED_COMMANDS)

PUBLIC_USAGE = {
    "ask": 'ask "..."',
    "ingest": "ingest raw/<file>",
}


def command_items(commands=PUBLIC_COMMANDS, *, prefix: str = "abw") -> list[tuple[str, str]]:
    return [(f"{prefix} {PUBLIC_USAGE.get(command, command)}", description) for command, description in commands]
