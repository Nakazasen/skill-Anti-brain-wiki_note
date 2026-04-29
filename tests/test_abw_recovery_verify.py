import pytest
from pathlib import Path
from abw.recovery_verify import build_verify_report, render_verify_report

def test_verify_report_structure(tmp_path):
    report = build_verify_report(tmp_path)
    assert "workspace" in report
    assert "verdict" in report
    assert "current_metrics" in report
    assert "comparison" in report or report["reports_found"] < 2

def test_render_verify_report_baseline():
    report = {
        "workspace": "/tmp/test",
        "reports_found": 1,
        "current_metrics": {
            "grounding_score": 2.5,
            "warning_count": 5,
            "gap_count": 3,
            "wiki_coverage": 10,
            "supported_ratio": 0.1,
            "draft_noise": 5
        },
        "comparison": None,
        "verdict": "unchanged",
        "next_action": "Run recover-plan"
    }
    output = render_verify_report(report)
    assert "ABW Recovery Verification" in output
    assert "Baseline established" in output
    assert "Grounding Score: 2.5" in output
