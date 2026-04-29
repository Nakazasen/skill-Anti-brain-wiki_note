from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .doctor import build_doctor_report
from .gaps import build_gap_report
from .inspect import build_inspect_report


GAP_WEIGHTS = {
    "format_block": 1.0,
    "corpus_gap": 0.9,
    "missing_wiki_coverage": 0.8,
    "identity_gap": 0.7,
    "weak_retrieval_signal": 0.5,
    "stale_draft_noise": 0.4,
}

ACTION_TEMPLATES = {
    "format_block": {
        "action": "Convert unsupported formats to supported PDF or TXT",
        "command": "abw ingest raw/*.pdf",
        "gain": "+4.0 Grounding Score",
    },
    "corpus_gap": {
        "action": "Add initial raw sources or wiki notes",
        "command": "abw init",
        "gain": "+5.0 System Readiness",
    },
    "missing_wiki_coverage": {
        "action": "Create wiki notes to anchor raw evidence",
        "command": 'abw save --wiki "Summary of key sources"',
        "gain": "+2.5 Grounding Score",
    },
    "identity_gap": {
        "action": "Add a wiki index mapping project aliases",
        "command": 'abw save --wiki "Identity Mapping Index"',
        "gain": "+2.0 Retrieval Accuracy",
    },
    "weak_retrieval_signal": {
        "action": "Add targeted wiki notes for warned questions",
        "command": "abw eval",
        "gain": "+1.5 Grounding Score",
    },
    "stale_draft_noise": {
        "action": "Review and archive stale drafts",
        "command": "abw review",
        "gain": "+1.0 Retrieval Precision",
    },
}


def build_recovery_report(workspace: str | Path = ".") -> dict[str, Any]:
    root = Path(workspace).resolve()
    doctor = build_doctor_report(root)
    inspect = build_inspect_report(root)
    gaps_report = build_gap_report(root)

    gaps = gaps_report.get("gaps", [])
    
    # Rank gaps by weight
    ranked_gaps = sorted(
        gaps,
        key=lambda g: GAP_WEIGHTS.get(g["type"], 0.1),
        reverse=True
    )

    recovery_steps = []
    for gap in ranked_gaps[:3]:
        gap_type = gap["type"]
        template = ACTION_TEMPLATES.get(gap_type, {
            "action": f"Resolve {gap_type} manually",
            "command": "abw help",
            "gain": "+0.5 Quality",
        })
        
        step = {
            "type": gap_type,
            "severity": gap.get("severity", "warn").upper(),
            "action": template["action"],
            "command": template["command"],
            "gain": template["gain"],
            "impact": gap.get("suspected_cause", "unknown impact"),
        }
        recovery_steps.append(step)

    return {
        "workspace": str(root),
        "doctor_state": doctor.get("overall", "unknown"),
        "corpus_summary": (
            f"raw={inspect['raw_stats']['total']} "
            f"wiki={inspect['wiki_stats']['total']} "
            f"drafts={inspect['draft_stats']['total']}"
        ),
        "steps": recovery_steps,
        "retest_sequence": ["abw eval", "abw gaps"]
    }


def render_recovery_report(report: dict[str, Any]) -> str:
    lines = [
        "ABW Recovery Plan",
        "-----------------",
        f"Workspace: {report['workspace']}",
        f"Health State: {report['doctor_state']}",
        f"Corpus Health: {report['corpus_summary']}",
        "",
        "Top Recovery Steps:",
        ""
    ]
    
    if not report["steps"]:
        lines.append("No critical gaps detected. System is healthy.")
    else:
        for i, step in enumerate(report["steps"], 1):
            lines.append(f"{i}. [{step['severity']}] {step['type'].replace('_', ' ').title()}")
            lines.append(f"   - Action: {step['action']}")
            lines.append(f"   - Command: {step['command']}")
            lines.append(f"   - Est. Gain: {step['gain']}")
            lines.append(f"   - Impact: {step['impact']}")
            lines.append("")

    lines.append("Verification Sequence:")
    for i, cmd in enumerate(report["retest_sequence"], 1):
        lines.append(f"{i}. {cmd}")
        
    return "\n".join(lines)
