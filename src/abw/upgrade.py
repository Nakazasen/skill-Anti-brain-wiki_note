from __future__ import annotations

from pathlib import Path

from .version import REPO_URL, build_version_report, install_mode_details, package_version


def build_upgrade_report(workspace: str | Path = ".") -> dict:
    version = build_version_report(workspace)
    install = install_mode_details()
    mode = install["install_mode"]

    if mode == "pip package":
        commands = ["py -m pip install -U abw-skill", "abw doctor"]
        summary = "Use pip to update the installed ABW package."
    elif mode == "git+pip":
        commands = [f"py -m pip install -U git+{REPO_URL}", "abw doctor"]
        summary = "Reinstall from the Git source URL to update this ABW install."
    elif mode == "editable/dev":
        source_path = install.get("source_path") or "."
        commands = [f'git -C "{source_path}" pull', f'py -m pip install -e "{source_path}"', "abw doctor"]
        summary = "Update the local editable source tree, then refresh the editable install."
    else:
        commands = ["py -m pip install -U abw-skill", "abw doctor"]
        summary = "Install mode is unknown, so only generic upgrade guidance is safe."

    return {
        "workspace": version["workspace"],
        "package_version": package_version(),
        "install_mode": mode,
        "commands": commands,
        "summary": summary,
        "note": "Upgrade guidance only. ABW did not perform an automatic engine update in this command.",
    }


def render_upgrade_report(report: dict) -> str:
    lines = [
        "ABW Upgrade",
        f"- workspace: {report['workspace']}",
        f"- package_version: {report['package_version']}",
        f"- install_mode: {report['install_mode']}",
        f"- summary: {report['summary']}",
    ]
    for command in report["commands"]:
        lines.append(f"- RUN: {command}")
    lines.append(f"- note: {report['note']}")
    return "\n".join(lines)
