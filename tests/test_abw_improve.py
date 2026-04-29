import pytest
from pathlib import Path
from abw.improve import build_improvement_plan, render_improvement_plan

def test_improve_plan_structure(tmp_path):
    # Setup some structure to avoid total failure in sub-reports
    (tmp_path / ".brain" / "eval").mkdir(parents=True)
    
    report = build_improvement_plan(tmp_path)
    assert "workspace" in report
    assert "health_summary" in report
    assert "priorities" in report
    assert isinstance(report["priorities"], list)

def test_render_improvement_plan_empty():
    report = {
        "workspace": "/tmp/test",
        "health_summary": {"doctor": "OK", "trend": "stagnant", "verdict": "unchanged"},
        "priorities": [],
        "verification_sequence": ["abw eval"]
    }
    output = render_improvement_plan(report)
    assert "No immediate improvements needed" in output

def test_render_improvement_plan_with_data():
    report = {
        "workspace": "/tmp/test",
        "health_summary": {"doctor": "WARN", "trend": "degrading", "verdict": "worse"},
        "priorities": [
            {
                "priority": "CRITICAL",
                "title": "Fix Everything",
                "reason": "It is broken",
                "command": "abw restore",
                "est_gain": "+100"
            }
        ],
        "verification_sequence": ["abw eval"]
    }
    output = render_improvement_plan(report)
    assert "ABW Improvement Plan" in output
    assert "[CRITICAL] Fix Everything" in output
    assert "abw restore" in output
