from __future__ import annotations

from .legacy import load


_legacy_help = load("abw_help")


def build_help_report(workspace=".", *, advanced: bool | None = None) -> dict:
    return _legacy_help.run(workspace, advanced=advanced)


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
