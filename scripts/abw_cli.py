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

USER_LEVELS = ("beginner", "intermediate", "expert")

DEPRECATED_ALIASES = {
    "health": "doctor",
    "update": "upgrade",
    "query": "ask",
    "query-deep": "ask",
    "query_deep": "ask",
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
    return add_common(subparsers.add_parser(name, help=argparse.SUPPRESS))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="abw")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--level", choices=USER_LEVELS)

    sub = parser.add_subparsers(dest="command")

    help_parser = add_common(sub.add_parser("help"))
    help_parser.add_argument("--advanced", action="store_true")

    ask = add_common(sub.add_parser("ask"))
    ask.add_argument("text")

    ingest = add_common(sub.add_parser("ingest"))
    ingest.add_argument("path")

    add_common(sub.add_parser("review"))
    add_common(sub.add_parser("overview"))
    save = add_common(sub.add_parser("save"))
    save.add_argument("text", nargs="?")
    save.add_argument("--stdin", action="store_true")
    add_common(sub.add_parser("doctor"))
    add_common(sub.add_parser("upgrade"))
    add_common(sub.add_parser("rollback"))
    add_common(sub.add_parser("repair"))
    add_common(sub.add_parser("research"))
    sub.add_parser("menu")

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


def main(argv=None) -> int:
    args = parse_args(argv)
    level = getattr(args, "level", None)

    if args.command is None:
        completed = subprocess.run([sys.executable, str(ROOT / "scripts" / "abw_menu.py")])
        return completed.returncode

    if args.command == "help":
        return run_entry("help", args.debug, level=level, advanced_help=getattr(args, "advanced", False))

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
        return run_entry_command("/abw-health", debug=args.debug, level=level)

    if args.command == "upgrade":
        return run_entry_command("/abw-update", debug=args.debug, level=level)

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
        return run_entry_command("/abw-health", debug=args.debug, level=level)

    if args.command == "update":
        print_deprecation("update")
        return run_entry_command("/abw-update", debug=args.debug, level=level)

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
