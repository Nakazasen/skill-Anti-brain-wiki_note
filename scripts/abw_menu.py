import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def configure_stdout():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def clear_screen(enabled=True):
    if enabled:
        os.system("cls" if os.name == "nt" else "clear")


def run_cli(args):
    cmd = [sys.executable, str(ROOT / "scripts" / "abw_cli.py"), *args]
    completed = subprocess.run(cmd)
    return completed.returncode


def print_header(output_func=print):
    output_func("ABW")
    output_func("---")


def menu_main(input_func=input, output_func=print, clear=False):
    configure_stdout()
    while True:
        clear_screen(clear)
        print_header(output_func)
        output_func("")
        output_func("What do you want to do?")
        output_func("")
        output_func("[1] View system (dashboard)")
        output_func("[2] Ask something")
        output_func("[3] Add file")
        output_func("[4] Review drafts")
        output_func("[0] Exit")
        output_func("")

        choice = input_func("Choose: ").strip()

        if choice == "1":
            run_cli(["ask", "dashboard"])
        elif choice == "2":
            query_flow(input_func=input_func, output_func=output_func)
        elif choice == "3":
            ingest_flow(input_func=input_func, output_func=output_func)
        elif choice == "4":
            review_flow()
        elif choice == "0":
            return 0
        else:
            output_func("Invalid choice.")


def query_flow(input_func=input, output_func=print):
    query = input_func("Ask: ").strip()
    if not query:
        output_func("Question is empty.")
        return 1
    return run_cli(["ask", query])


def ingest_flow(input_func=input, output_func=print):
    path = input_func("File path (example: raw/file.pdf): ").strip()
    if not path:
        output_func("File path is empty.")
        return 1
    return run_cli(["ingest", path])


def review_flow():
    return run_cli(["review"])


def system_flow(input_func=input, output_func=print):
    output_func("")
    output_func("[1] Coverage")
    output_func("[2] Dashboard")
    output_func("[3] Health")
    choice = input_func("Choose: ").strip()

    if choice == "1":
        return run_cli(["coverage"])
    if choice == "2":
        return run_cli(["dashboard"])
    if choice == "3":
        return run_cli(["health"])

    output_func("Invalid choice.")
    return 1


if __name__ == "__main__":
    raise SystemExit(menu_main())
