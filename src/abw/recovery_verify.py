from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .doctor import build_doctor_report
from .gaps import build_gap_report, latest_eval_report_path
from .inspect import build_inspect_report


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def get_two_latest_eval_reports(workspace: str | Path) -> list[Path]:
    eval_dir = Path(workspace) / ".brain" / "eval"
    if not eval_dir.exists():
        return []
    reports = sorted(
        [path for path in eval_dir.glob("eval_report_*.json") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )
    return reports[:2]


def build_verify_report(workspace: str | Path = ".") -> dict[str, Any]:
    root = Path(workspace).resolve()
    reports = get_two_latest_eval_reports(root)
    
    inspect = build_inspect_report(root)
    doctor = build_doctor_report(root)
    gaps = build_gap_report(root)
    
    current_metrics = {
        "grounding_score": 0.0,
        "warning_count": 0,
        "failed_count": 0,
        "gap_count": gaps.get("gap_summary", {}).get("total", 0),
        "wiki_coverage": inspect["wiki_stats"]["total"],
        "supported_ratio": doctor["corpus"]["unsupported_ratio"],
        "draft_noise": inspect["draft_stats"]["total"],
    }
    
    comparison = None
    if len(reports) >= 2:
        after_report = _load_json(reports[0])
        before_report = _load_json(reports[1])
        
        after_summary = after_report.get("summary", {})
        before_summary = before_report.get("summary", {})
        after_scores = after_report.get("scores", {})
        before_scores = before_report.get("scores", {})
        
        current_metrics["grounding_score"] = after_scores.get("average_grounding", 0.0)
        current_metrics["warning_count"] = after_summary.get("warnings", 0)
        current_metrics["failed_count"] = after_summary.get("failed", 0)
        
        comparison = {
            "grounding_delta": round(after_scores.get("average_grounding", 0.0) - before_scores.get("average_grounding", 0.0), 2),
            "warning_delta": after_summary.get("warnings", 0) - before_summary.get("warnings", 0),
            "failed_delta": after_summary.get("failed", 0) - before_summary.get("failed", 0),
            "before_timestamp": before_report.get("timestamp"),
            "after_timestamp": after_report.get("timestamp"),
        }
    elif len(reports) == 1:
        after_report = _load_json(reports[0])
        after_summary = after_report.get("summary", {})
        after_scores = after_report.get("scores", {})
        current_metrics["grounding_score"] = after_scores.get("average_grounding", 0.0)
        current_metrics["warning_count"] = after_summary.get("warnings", 0)
        current_metrics["failed_count"] = after_summary.get("failed", 0)

    # Verdict logic
    verdict = "unchanged"
    if comparison:
        if comparison["grounding_delta"] > 0 or comparison["warning_delta"] < 0 or comparison["failed_delta"] < 0:
            verdict = "improved"
        elif comparison["grounding_delta"] < 0 or comparison["warning_delta"] > 0 or comparison["failed_delta"] > 0:
            verdict = "worse"
    
    # Next action
    next_action = "Run abw recover-plan to see recommended fixes."
    if gaps.get("gap_summary", {}).get("total", 0) > 0:
        top_gap = gaps["gaps"][0]["type"]
        next_action = f"Focus on resolving {top_gap.replace('_', ' ')}. Run abw recover-plan for details."

    return {
        "workspace": str(root),
        "reports_found": len(reports),
        "current_metrics": current_metrics,
        "comparison": comparison,
        "verdict": verdict,
        "next_action": next_action
    }


def render_verify_report(report: dict[str, Any]) -> str:
    lines = [
        "ABW Recovery Verification",
        "-------------------------",
        f"Workspace: {report['workspace']}",
        f"Verdict: {report['verdict'].upper()}",
        "",
        "Current Metrics:",
        f"- Grounding Score: {report['current_metrics']['grounding_score']}",
        f"- Warning Count:   {report['current_metrics']['warning_count']}",
        f"- Gap Count:       {report['current_metrics']['gap_count']}",
        f"- Wiki Coverage:   {report['current_metrics']['wiki_coverage']} notes",
        f"- Draft Noise:     {report['current_metrics']['draft_noise']} pending",
        f"- Supported Ratio: {round((1.0 - report['current_metrics']['supported_ratio']) * 100, 1)}%",
        ""
    ]
    
    if report["comparison"]:
        comp = report["comparison"]
        lines.append("Comparison (Before -> After):")
        lines.append(f"- Grounding Delta: {comp['grounding_delta'] :+}")
        lines.append(f"- Warning Delta:   {comp['warning_delta'] :+}")
        lines.append(f"- Failed Delta:    {comp['failed_delta'] :+}")
        lines.append(f"- Window: {comp['before_timestamp']} -> {comp['after_timestamp']}")
        lines.append("")
    elif report["reports_found"] == 1:
        lines.append("Note: Only one eval report found. Baseline established.")
        lines.append("")
    else:
        lines.append("Warning: No eval reports found. Run abw eval first.")
        lines.append("")
        
    lines.append(f"Next Action: {report['next_action']}")
    return "\n".join(lines)
