from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def get_all_eval_reports(workspace: str | Path) -> list[dict[str, Any]]:
    eval_dir = Path(workspace) / ".brain" / "eval"
    if not eval_dir.exists():
        return []
    
    paths = sorted(
        [path for path in eval_dir.glob("eval_report_*.json") if path.is_file()],
        key=lambda path: path.stat().st_mtime
    )
    
    reports = []
    for path in paths:
        data = _load_json(path)
        if data:
            reports.append(data)
    return reports


def build_trend_report(workspace: str | Path = ".") -> dict[str, Any]:
    root = Path(workspace).resolve()
    reports = get_all_eval_reports(root)
    
    if not reports:
        return {
            "workspace": str(root),
            "status": "not_run",
            "message": "No historical evaluation reports found."
        }

    grounding_scores = [r.get("scores", {}).get("average_grounding", 0.0) for r in reports]
    warnings = [r.get("summary", {}).get("warnings", 0) for r in reports]
    failures = [r.get("summary", {}).get("failed", 0) for r in reports]
    
    # Trend Analysis
    latest_5 = grounding_scores[-5:]
    avg_latest_5 = sum(latest_5) / len(latest_5) if latest_5 else 0.0
    
    improvement_count = 0
    for i in range(1, len(grounding_scores)):
        if grounding_scores[i] > grounding_scores[i-1]:
            improvement_count += 1
            
    success_rate = (improvement_count / (len(grounding_scores) - 1)) * 100 if len(grounding_scores) > 1 else 0.0
    
    # State detection
    status = "stagnant"
    if len(grounding_scores) >= 3:
        last_3 = grounding_scores[-3:]
        if all(last_3[i] > last_3[i-1] for i in range(1, 3)):
            status = "improving"
        elif all(last_3[i] < last_3[i-1] for i in range(1, 3)):
            status = "degrading"
        elif max(last_3) - min(last_3) > 1.0:
            status = "unstable"
            
    return {
        "workspace": str(root),
        "report_count": len(reports),
        "metrics": {
            "best_score": max(grounding_scores),
            "worst_score": min(grounding_scores),
            "current_score": grounding_scores[-1],
            "avg_grounding_latest_5": round(avg_latest_5, 2),
            "recovery_success_rate": round(success_rate, 1),
            "total_warnings": warnings[-1],
            "total_failures": failures[-1]
        },
        "trends": {
            "grounding": grounding_scores,
            "warnings": warnings,
            "failures": failures
        },
        "status": status,
        "timestamps": [r.get("timestamp") for r in reports]
    }


def render_trend_report(report: dict[str, Any]) -> str:
    if report.get("status") == "not_run":
        return f"ABW Trend Report\n----------------\n{report['message']}"

    lines = [
        "ABW Trend Report",
        "----------------",
        f"Workspace: {report['workspace']}",
        f"Status:    {report['status'].upper()}",
        f"Reports:   {report['report_count']}",
        "",
        "Key Metrics:",
        f"- Current Grounding: {report['metrics']['current_score']}",
        f"- Best Recent Score: {report['metrics']['best_score']}",
        f"- Worst Recent Score: {report['metrics']['worst_score']}",
        f"- Avg (Latest 5):    {report['metrics']['avg_grounding_latest_5']}",
        f"- Recovery Success:  {report['metrics']['recovery_success_rate']}%",
        "",
        "Health History (Last 10 or all):",
        "  Score | Warn | Fail | Timestamp",
        "  ------|------|------|----------"
    ]
    
    # Show last 10 entries
    for i in range(max(0, report["report_count"] - 10), report["report_count"]):
        score = report["trends"]["grounding"][i]
        warn = report["trends"]["warnings"][i]
        fail = report["trends"]["failures"][i]
        ts = report["timestamps"][i][:16].replace("T", " ") if report["timestamps"][i] else "unknown"
        lines.append(f"  {score:5.2f} | {warn:4} | {fail:4} | {ts}")
        
    lines.append("")
    lines.append(f"Verdict: System is {report['status']}.")
    return "\n".join(lines)
