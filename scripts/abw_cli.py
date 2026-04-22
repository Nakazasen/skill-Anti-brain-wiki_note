#!/usr/bin/env python
import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


USER_LEVELS = ("beginner", "intermediate", "expert")


def run_entry(task: str, debug: bool = False, level: str = None) -> int:
    return run_entry_command("/abw-ask", task=task, debug=debug, level=level)


def run_entry_command(command: str, task: str = "", debug: bool = False, level: str = None) -> int:
    env = os.environ.copy()
    env["ABW_ENTRY_CALLER"] = "abw_cli"
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


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="abw")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--level", choices=USER_LEVELS)

    sub = parser.add_subparsers(dest="command")

    add_common(sub.add_parser("help"))

    ask = add_common(sub.add_parser("ask"))
    ask.add_argument("text")

    ingest = add_common(sub.add_parser("ingest"))
    ingest.add_argument("path")

    add_common(sub.add_parser("review"))

    approve = add_common(sub.add_parser("approve"))
    approve.add_argument("path")

    add_common(sub.add_parser("coverage"))
    add_common(sub.add_parser("dashboard"))
    add_common(sub.add_parser("health"))
    add_common(sub.add_parser("wizard"))
    sub.add_parser("menu")

    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    level = getattr(args, "level", None)

    if args.command is None:
        completed = subprocess.run([sys.executable, str(ROOT / "scripts" / "abw_menu.py")])
        return completed.returncode

    if args.command == "help":
        return run_entry("help", args.debug, level=level)

    if args.command == "ask":
        return run_entry(args.text, args.debug, level=level)

    if args.command == "ingest":
        return run_entry(f"ingest {args.path}", args.debug, level=level)

    if args.command == "review":
        return run_entry("review drafts", args.debug, level=level)

    if args.command == "approve":
        return run_entry(f"approve draft {args.path}", args.debug, level=level)

    if args.command == "coverage":
        return run_entry("coverage", args.debug, level=level)

    if args.command == "dashboard":
        return run_entry("dashboard", args.debug, level=level)

    if args.command == "health":
        return run_entry_command("/abw-health", debug=args.debug, level=level)

    if args.command == "wizard":
        return run_entry("wizard", args.debug, level=level)

    if args.command == "menu":
        completed = subprocess.run([sys.executable, str(ROOT / "scripts" / "abw_menu.py")])
        return completed.returncode

    print("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
