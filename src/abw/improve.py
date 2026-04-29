from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .doctor import build_doctor_report
from .gaps import build_gap_report
from .inspect import build_inspect_report
from .recovery_verify import build_verify_report
from .trend import build_trend_report


def build_improvement_plan(workspace: str | Path = ".") -> dict[str, Any]:
    root = Path(workspace).resolve()
    
    # Collect all inputs
    doctor = build_doctor_report(root)
    inspect = build_inspect_report(root)
    gaps = build_gap_report(root)
    verify = build_verify_report(root)
    trend = build_trend_report(root)
    
    actions = []
    
    # 1. Check for Format Blocks (Critical)
    if doctor.get("corpus", {}).get("unsupported_ratio", 0) > 0.3:
        unsupported_types = ", ".join(doctor["corpus"].get("unsupported_source_counts", {}).keys()).upper() or "unknown types"
        actions.append({
            "priority": "CRITICAL",
            "type": "format_block",
            "title": "Convert Unsupported Formats",
            "reason": f"{round(doctor['corpus']['unsupported_ratio']*100)}% of your corpus is unsupported ({unsupported_types}).",
            "command": "abw ingest raw/*.pdf",
            "est_gain": "+4.0 Grounding Score",
            "weight": 100
        })
        
    # 2. Check for Missing Wiki Anchors (High)
    if inspect["wiki_stats"]["total"] == 0 and inspect["raw_stats"]["total"] > 0:
        actions.append({
            "priority": "HIGH",
            "type": "missing_wiki",
            "title": "Establish Wiki Anchors",
            "reason": "Raw sources exist but no wiki notes are anchoring them.",
            "command": 'abw save --wiki "Project Overview and Source Map"',
            "est_gain": "+2.5 Grounding Score",
            "weight": 90
        })
        
    # 3. Check for Draft Noise (High)
    if inspect["draft_stats"]["total"] > 50:
        actions.append({
            "priority": "HIGH",
            "type": "draft_noise",
            "title": "Reduce Draft Noise",
            "reason": f"High draft volume ({inspect['draft_stats']['total']}) creates retrieval pollution.",
            "command": "abw review",
            "est_gain": "+1.0 Retrieval Precision",
            "weight": 85
        })

    # 4. Check Trend (Medium/High)
    if trend.get("status") == "degrading":
        actions.append({
            "priority": "HIGH",
            "type": "degrading_trend",
            "title": "Reverse Degrading Trend",
            "reason": "Grounding scores are dropping over time.",
            "command": "abw eval",
            "est_gain": "Stability Restoration",
            "weight": 95
        })
    elif trend.get("status") == "unstable":
        actions.append({
            "priority": "MEDIUM",
            "type": "unstable_trend",
            "title": "Stabilize Retrieval",
            "reason": "Grounding scores show high variance across runs.",
            "command": "abw eval",
            "est_gain": "Consistent Grounding",
            "weight": 70
        })
        
    # 5. Gap Specific Actions (Medium)
    for gap in gaps.get("gaps", [])[:2]:
        gap_type = gap["type"]
        if any(a["type"] == gap_type for a in actions):
            continue
            
        actions.append({
            "priority": "MEDIUM",
            "type": gap_type,
            "title": f"Resolve {gap_type.replace('_', ' ').title()}",
            "reason": gap.get("suspected_cause", "Detected retrieval gap."),
            "command": "abw recover-plan",
            "est_gain": "+1.5 Quality",
            "weight": 60
        })

    # Sort and take top 3
    actions.sort(key=lambda x: x["weight"], reverse=True)
    top_actions = actions[:3]

    return {
        "workspace": str(root),
        "health_summary": {
            "doctor": doctor.get("overall"),
            "trend": trend.get("status"),
            "verdict": verify.get("verdict")
        },
        "priorities": top_actions,
        "verification_sequence": ["abw eval", "abw recover-verify"]
    }


def render_improvement_plan(report: dict[str, Any]) -> str:
    lines = [
        "ABW Improvement Plan",
        "--------------------",
        f"Workspace: {report['workspace']}",
        f"Status:    {report['health_summary']['doctor']} | Trend: {report['health_summary']['trend'].upper()}",
        "",
        "Top Action Items:",
        ""
    ]
    
    if not report["priorities"]:
        lines.append("No immediate improvements needed. System is healthy.")
    else:
        for i, action in enumerate(report["priorities"], 1):
            lines.append(f"{i}. [{action['priority']}] {action['title']}")
            lines.append(f"   - Reason:   {action['reason']}")
            lines.append(f"   - Command:  {action['command']}")
            lines.append(f"   - Est Gain: {action['est_gain']}")
            lines.append("")

    lines.append("Verification Sequence:")
    for i, cmd in enumerate(report["verification_sequence"], 1):
        lines.append(f"{i}. {cmd}")
        
    return "\n".join(lines)
