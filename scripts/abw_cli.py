#!/usr/bin/env python
import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from abw.overview import build_overview
from abw.save import save_candidate
from abw.doctor import build_doctor_report, render_doctor_report
from abw.migrate import build_migration_report, render_migration_report
from abw.upgrade import build_upgrade_report, render_upgrade_report
from abw.version import build_version_report, render_version_report
from abw.workspace import ensure_workspace

import abw_help

USER_LEVELS = ("beginner", "intermediate", "expert")

DEPRECATED_ALIASES = {
    "health": "doctor",
    "update": "upgrade",
    "query": "ask",
    "query-deep": "ask",
    "query_deep": "ask",
}

PUBLIC_HELP = {
    "help": "Show product help.",
    "ask": "Route a normal task.",
    "ingest": "Create a draft from a raw source.",
    "review": "Review pending drafts.",
    "overview": "Show a workspace overview.",
    "version": "Show package and workspace version info.",
    "migrate": "Normalize an older workspace safely.",
    "save": "Save a candidate note.",
    "doctor": "Check system health.",
    "upgrade": "Show upgrade guidance.",
    "rollback": "Restore the last runtime backup.",
    "repair": "Repair runtime drift.",
    "research": "Reserved placeholder.",
    "init": "Create or normalize workspace structure.",
    "menu": "Show the simple menu.",
}


def run_entry(task: str, debug: bool = False, level: str = None, *, advanced_help: bool = False) -> int:
    return run_entry_command("/abw-ask", task=task, debug=debug, level=level, advanced_help=advanced_help)


def run_entry_command(
    command: str,
    task: str = "",
    debug: bool = False,
    level: str = None,
    *,
    advanced_help: bool = False,
) -> int:
    env = os.environ.copy()
    env["ABW_ENTRY_CALLER"] = "abw_cli"
    if advanced_help:
        env["ABW_HELP_ADVANCED"] = "1"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "abw_entry.py"),
        command,
    ]

    if task:
        cmd.extend(["--task", task])

    cmd.extend(["--workspace", "."])

    if debug:
        cmd.append("--debug")
    if level:
        cmd.extend(["--level", level])

    completed = subprocess.run(cmd, env=env)
    return completed.returncode


def add_common(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--debug", action="store_true", default=argparse.SUPPRESS)
    parser.add_argument("--level", choices=USER_LEVELS, default=argparse.SUPPRESS)
    return parser


def add_hidden_parser(subparsers, name):
    parser = add_common(subparsers.add_parser(name, help=argparse.SUPPRESS))
    subparsers._choices_actions = [action for action in subparsers._choices_actions if action.dest != name]
    return parser


def add_public_parser(subparsers, name):
    return add_common(subparsers.add_parser(name, help=PUBLIC_HELP.get(name)))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="abw")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--level", choices=USER_LEVELS)

    sub = parser.add_subparsers(dest="command", metavar="command")

    help_parser = add_public_parser(sub, "help")
    help_parser.add_argument("--advanced", action="store_true")

    ask = add_public_parser(sub, "ask")
    ask.add_argument("text")

    ingest = add_public_parser(sub, "ingest")
    ingest.add_argument("path")

    add_public_parser(sub, "review")
    add_hidden_parser(sub, "overview")
    add_public_parser(sub, "version")
    add_public_parser(sub, "migrate")
    save = add_hidden_parser(sub, "save")
    save.add_argument("text", nargs="?")
    save.add_argument("--stdin", action="store_true")
    add_public_parser(sub, "doctor")
    add_hidden_parser(sub, "upgrade")
    add_hidden_parser(sub, "rollback")
    add_hidden_parser(sub, "repair")
    add_hidden_parser(sub, "research")
    add_public_parser(sub, "init")
    sub.add_parser("menu", help=argparse.SUPPRESS)
    sub._choices_actions = [action for action in sub._choices_actions if action.dest != "menu"]

    approve = add_hidden_parser(sub, "approve")
    approve.add_argument("path")
    add_hidden_parser(sub, "dashboard")
    add_hidden_parser(sub, "coverage")
    add_hidden_parser(sub, "wizard")
    add_hidden_parser(sub, "health")
    add_hidden_parser(sub, "update")

    query = add_hidden_parser(sub, "query")
    query.add_argument("text")
    query_deep = add_hidden_parser(sub, "query-deep")
    query_deep.add_argument("text")
    query_deep_alt = add_hidden_parser(sub, "query_deep")
    query_deep_alt.add_argument("text")

    return parser.parse_args(argv)


def print_deprecation(command: str) -> None:
    replacement = DEPRECATED_ALIASES.get(command)
    if replacement:
        print(f"Deprecated command. Use: abw {replacement}")


def render_help_report(report: dict) -> str:
    lines = ["ABW Help", report.get("message", "")]
    for section in report.get("sections", []):
        title = str(section.get("title") or "").strip()
        if title:
            lines.append("")
            lines.append(title)
        for item in section.get("items", []):
            lines.append(f"- {item}")
    return "\n".join(line for line in lines if line is not None)


def main(argv=None) -> int:
    args = parse_args(argv)
    level = getattr(args, "level", None)

    if args.command is None:
        completed = subprocess.run([sys.executable, str(ROOT / "scripts" / "abw_menu.py")])
        return completed.returncode

    if args.command == "init":
        report = ensure_workspace(".")
        print(f"ABW workspace initialized: {report['root']}")
        if report["config_status"] == "invalid":
            print("Preserved invalid abw_config.json. Run: abw doctor")
            return 2
        created_dirs = ", ".join(f"{name}/" for name in report["created_dirs"]) or "no new folders"
        print(f"Workspace state: {created_dirs}")
        print(f"Workspace schema: {report['config'].get('workspace_schema', 'unknown')}")
        return 0

    if args.command == "help":
        print(render_help_report(abw_help.run(".", advanced=getattr(args, "advanced", False))))
        return 0

    if args.command == "ask":
        if str(args.text).strip().lower() == "overview":
            print(build_overview(".")["content"], end="")
            return 0
        return run_entry(args.text, args.debug, level=level)

    if args.command == "ingest":
        return run_entry(f"ingest {args.path}", args.debug, level=level)

    if args.command == "review":
        return run_entry("review drafts", args.debug, level=level)

    if args.command == "overview":
        print(build_overview(".")["content"], end="")
        return 0

    if args.command == "version":
        print(render_version_report(build_version_report(".")))
        return 0

    if args.command == "migrate":
        print(render_migration_report(build_migration_report(".")))
        return 0

    if args.command == "save":
        text = args.text
        if getattr(args, "stdin", False):
            text = sys.stdin.read()
        try:
            saved = save_candidate(text, ".")
        except ValueError as exc:
            print(str(exc))
            return 2
        print(f"Saved candidate note: {saved['relative_path']}")
        print(f"Suggested next step: {saved['next_step']}")
        return 0

    if args.command == "doctor":
        print(render_doctor_report(build_doctor_report(".")))
        return 0

    if args.command == "upgrade":
        print(render_upgrade_report(build_upgrade_report(".")))
        return 0

    if args.command == "rollback":
        return run_entry_command("/abw-rollback", debug=args.debug, level=level)

    if args.command == "repair":
        return run_entry_command("/abw-repair", debug=args.debug, level=level)

    if args.command == "research":
        print("Research mode is not a separate public runtime command yet. Use: abw ask \"...\"")
        return 2

    if args.command == "menu":
        completed = subprocess.run([sys.executable, str(ROOT / "scripts" / "abw_menu.py")])
        return completed.returncode

    if args.command == "approve":
        return run_entry(f"approve draft {args.path}", args.debug, level=level)

    if args.command == "dashboard":
        return run_entry("dashboard", args.debug, level=level)

    if args.command == "coverage":
        return run_entry("coverage", args.debug, level=level)

    if args.command == "wizard":
        return run_entry("wizard", args.debug, level=level)

    if args.command == "health":
        print_deprecation("health")
        print(render_doctor_report(build_doctor_report(".")))
        return 0

    if args.command == "update":
        print_deprecation("update")
        print(render_upgrade_report(build_upgrade_report(".")))
        return 0

    if args.command == "query":
        print_deprecation("query")
        return run_entry(args.text, args.debug, level=level)

    if args.command in {"query-deep", "query_deep"}:
        print_deprecation("query-deep")
        return run_entry(args.text, args.debug, level=level)

    print("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
