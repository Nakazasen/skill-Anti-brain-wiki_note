import json
import os
from pathlib import Path

import abw_audit
import abw_help
import abw_i18n
import abw_suggestions
import abw_version


def load_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def coverage_report(workspace):
    return load_json(Path(workspace) / ".brain" / "coverage_report.json", {}) or {}


def health_from_audit(audit_result):
    system_map = audit_result.get("system_map", {})
    analysis = audit_result.get("analysis", {})
    data_layers = system_map.get("data_layers", [])
    return {
        "modules": len(system_map.get("modules", [])),
        "lanes": len(system_map.get("lanes", [])),
        "data_layers": sum(1 for layer in data_layers if layer.get("exists")),
        "bottleneck_count": len(analysis.get("bottlenecks", [])),
        "unused_lanes": len(analysis.get("unused_lanes", [])),
    }


def knowledge_from_help(help_result, coverage):
    snapshot = help_result.get("state_snapshot", {})
    return {
        "raw_files": int(snapshot.get("raw_files", 0)),
        "draft_files": int(snapshot.get("draft_files", 0)),
        "wiki_files": int(snapshot.get("wiki_files", 0)),
        "pending_drafts": int(snapshot.get("pending_drafts", 0)),
        "coverage_ratio": coverage.get("coverage_ratio", snapshot.get("coverage_ratio")),
        "total_questions": int(coverage.get("total_questions", 0) or 0),
        "success": int(coverage.get("success", 0) or 0),
        "weak": int(coverage.get("weak", 0) or 0),
        "fail": int(coverage.get("fail", 0) or 0),
    }


def top_gaps_from_coverage(coverage):
    gaps = coverage.get("top_gaps", [])
    return gaps if isinstance(gaps, list) else []


def build_header(health, knowledge, version, workspace="."):
    return {
        "title": abw_i18n.t("dashboard.title", workspace),
        "summary": (
            f"{health['lanes']} lanes, {health['modules']} modules, "
            f"{knowledge['wiki_files']} wiki files, {knowledge['pending_drafts']} pending drafts, "
            f"deploy={version['deploy_status']}"
        ),
    }


def render_dashboard(dashboard, workspace="."):
    lines = [
        dashboard["header"]["title"],
        dashboard["header"]["summary"],
        "",
        f"{abw_i18n.t('dashboard.version', workspace)}:",
        f"- commit: {dashboard['version']['commit']}",
        f"- git_commit: {dashboard['version']['git_commit']}",
        f"- status: {dashboard['version']['status']}",
        f"- deploy_status: {dashboard['version']['deploy_status']}",
        f"- source: {dashboard['version']['source']}",
        "",
        f"{abw_i18n.t('dashboard.health', workspace)}:",
        f"- modules: {dashboard['health']['modules']}",
        f"- lanes: {dashboard['health']['lanes']}",
        f"- data_layers: {dashboard['health']['data_layers']}",
        f"- bottlenecks: {dashboard['health']['bottleneck_count']}",
        "",
        f"{abw_i18n.t('dashboard.knowledge', workspace)}:",
        f"- raw_files: {dashboard['knowledge']['raw_files']}",
        f"- draft_files: {dashboard['knowledge']['draft_files']}",
        f"- wiki_files: {dashboard['knowledge']['wiki_files']}",
        f"- pending_drafts: {dashboard['knowledge']['pending_drafts']}",
        f"- coverage_ratio: {dashboard['knowledge']['coverage_ratio']}",
        "",
        f"{abw_i18n.t('dashboard.bottlenecks', workspace)}:",
    ]
    bottlenecks = dashboard.get("bottleneck", [])
    if bottlenecks:
        for item in bottlenecks:
            lines.append(f"- {item.get('type')}: {item.get('detail')}")
    else:
        lines.append(f"- {abw_i18n.t('dashboard.none_detected', workspace)}")

    lines.append("")
    lines.append(f"{abw_i18n.t('dashboard.top_gaps', workspace)}:")
    top_gaps = dashboard.get("top_gaps", [])
    if top_gaps:
        for item in top_gaps:
            lines.append(f"- {item}")
    else:
        lines.append(f"- {abw_i18n.t('dashboard.none', workspace)}")

    lines.append("")
    lines.append(f"{abw_i18n.t('dashboard.next_actions', workspace)}:")
    lines.append("- Guided wizard: wizard")
    for action in dashboard.get("next_actions", []):
        lines.append(f"- {action['label']}: {action['command']}")
    return "\n".join(lines)


def render_agent(dashboard, workspace="."):
    knowledge = dashboard["knowledge"]
    actions = ["wizard"]
    actions.extend(action["command"] for action in dashboard.get("next_actions", []))

    lines = [
        f"### {dashboard['header']['title']}",
        "",
        "### Summary",
        f"- Wiki files: {knowledge['wiki_files']}",
        f"- Pending drafts: {knowledge['pending_drafts']}",
        f"- Coverage: {knowledge['coverage_ratio']}",
        "",
        "### Answer",
        f"- Raw files: {knowledge['raw_files']}",
        f"- Draft files: {knowledge['draft_files']}",
        f"- Wiki files: {knowledge['wiki_files']}",
        f"- Pending drafts: {knowledge['pending_drafts']}",
        f"- Coverage: {knowledge['coverage_ratio']}",
        "",
        "### Next Actions",
    ]
    lines.extend(f"- {action}" for action in actions)
    return "\n".join(lines)


def run_dashboard(workspace="."):
    workspace = str(workspace or ".")
    audit_result = abw_audit.run_audit(workspace)
    help_result = abw_help.run(workspace)
    coverage = coverage_report(workspace)
    next_actions = abw_suggestions.suggest_next_actions(workspace)
    version = abw_version.resolve_version(workspace)
    health = health_from_audit(audit_result)
    knowledge = knowledge_from_help(help_result, coverage)
    dashboard = {
        "header": build_header(health, knowledge, version, workspace=workspace),
        "version": version,
        "deploy": {
            "status": version["deploy_status"],
            "state": version["deploy_state"],
            "source": version["source"],
        },
        "health": health,
        "knowledge": knowledge,
        "bottleneck": audit_result.get("analysis", {}).get("bottlenecks", []),
        "top_gaps": top_gaps_from_coverage(coverage),
        "wizard": {"command": "wizard", "label": "Guided wizard"},
        "next_actions": next_actions,
        "audit": audit_result,
        "help": help_result,
    }
    if os.environ.get("ABW_AGENT_MODE") == "1":
        dashboard["rendered"] = render_agent(dashboard, workspace=workspace)
    else:
        dashboard["rendered"] = render_dashboard(dashboard, workspace=workspace)
    return dashboard
