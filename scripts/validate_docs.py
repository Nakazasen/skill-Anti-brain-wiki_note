import os
import re
import sys

# Commands that are intentional or aliases and do not have a direct 1:1 file match.
COMMAND_ALLOWLIST = {
    "help",        # Back-reference to help.md itself
    "save-brain",  # Alias for save_brain.md
}

# Suspicious tokens commonly seen when UTF-8 text is decoded with the wrong codec.
SUSPICIOUS_TOKENS = [
    "\u00c3",
    "\u00c2",
    "\u7ab6",
    "\uff83",
    "\u862f",
    "\u76fb",
    "\u7aca",
    "\u7b0f",
    "\ufffd",
]


def check_content(filepath):
    """Check if a file is valid UTF-8 and contains no likely mojibake."""
    errors = []
    content = ""

    try:
        with open(filepath, "rb") as handle:
            raw_data = handle.read()
        content = raw_data.decode("utf-8")
    except UnicodeDecodeError as exc:
        errors.append(f"UnicodeDecodeError: {exc}")
        return errors, ""

    for token in SUSPICIOUS_TOKENS:
        if token in content:
            errors.append(f"Suspicious token found (likely mojibake): {token}")
            break

    return errors, content if not errors else ""


def extract_commands(content):
    """Extract slash commands like /abw-init from markdown content.

    Uses negative lookbehind to avoid matching paths (for example `.brain/lessons`)
    or combined terms such as `UI/UX`.
    """

    matches = re.findall(r"(?<![a-zA-Z0-9.])/(?P<cmd>[a-zA-Z0-9_-]+)", content)
    return set(matches)


def main():
    workflows_dir = "workflows"
    help_file = os.path.join(workflows_dir, "help.md")
    readme_file = os.path.join(workflows_dir, "README.md")

    overall_success = True

    files_to_check = [help_file, readme_file, "README.md", "README.en.md"]
    for filepath in files_to_check:
        if not os.path.exists(filepath):
            print(f"Warning: {filepath} not found.")
            continue

        errors, _ = check_content(filepath)
        if errors:
            print(f"ERROR: {filepath} failed checks:")
            for error in errors:
                print(f"  - {error}")
            overall_success = False
        else:
            print(f"OK: {filepath} passed encoding and mojibake checks.")

    expected_from_files = set()
    for filename in os.listdir(workflows_dir):
        if filename.endswith(".md") and filename != "README.md":
            cmd_name = filename.replace(".md", "").replace("_", "-")
            expected_from_files.add(cmd_name)

    errors, help_content = check_content(help_file)
    if not errors:
        documented_cmds = extract_commands(help_content)

        missing = expected_from_files - (documented_cmds | COMMAND_ALLOWLIST)
        if missing:
            print(f"ERROR: Commands in workflows/ but missing in help.md: {missing}")
            overall_success = False

        non_command_patterns = {
            "localhost",
            "orders",
            "api",
            "path",
            "workspace",
            "step-id",
            "command",
            "next_cmd",
            "package_id",
        }
        raw_extra = documented_cmds - (expected_from_files | COMMAND_ALLOWLIST)
        extra = {cmd for cmd in raw_extra if cmd not in non_command_patterns}
        if extra:
            print(f"ERROR: Stale or extra commands in help.md (not found in workflows/): {extra}")
            overall_success = False

        if not missing and not extra:
            print("OK: help.md is perfectly synchronized with workflows/.")
    else:
        overall_success = False

    errors, readme_content = check_content(readme_file)
    if not errors:
        documented_cmds = extract_commands(readme_content)
        missing = expected_from_files - (documented_cmds | COMMAND_ALLOWLIST)
        extra = documented_cmds - (expected_from_files | COMMAND_ALLOWLIST)

        if missing:
            print(f"ERROR: Commands in workflows/ but missing in workflows/README.md: {missing}")
            overall_success = False
        if extra:
            print(f"ERROR: Stale or extra commands in workflows/README.md: {extra}")
            overall_success = False

        if not missing and not extra:
            print("OK: workflows/README.md is perfectly synchronized with workflows/.")
    else:
        overall_success = False

    print(f"\nTotal command files found: {len(expected_from_files)}")

    if overall_success:
        print("\nVERDICT: PASS")
        sys.exit(0)

    print("\nVERDICT: FAIL")
    sys.exit(1)


if __name__ == "__main__":
    main()
