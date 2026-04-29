import pytest
from pathlib import Path
from abw.trend import build_trend_report, render_trend_report

def test_trend_report_structure(tmp_path):
    report = build_trend_report(tmp_path)
    assert "workspace" in report
    assert "status" in report
    if report["status"] != "not_run":
        assert "metrics" in report
        assert "trends" in report

def test_render_trend_report_empty():
    report = {
        "status": "not_run",
        "message": "No reports found."
    }
    output = render_trend_report(report)
    assert "No reports found" in output

def test_render_trend_report_with_data():
    report = {
        "workspace": "/tmp/test",
        "status": "improving",
        "report_count": 2,
        "metrics": {
            "best_score": 3.0,
            "worst_score": 1.0,
            "current_score": 3.0,
            "avg_grounding_latest_5": 2.0,
            "recovery_success_rate": 50.0,
            "total_warnings": 2,
            "total_failures": 0
        },
        "trends": {
            "grounding": [1.0, 3.0],
            "warnings": [5, 2],
            "failures": [1, 0]
        },
        "timestamps": ["2026-04-29T10:00:00", "2026-04-29T11:00:00"]
    }
    output = render_trend_report(report)
    assert "ABW Trend Report" in output
    assert "Status:    IMPROVING" in output
    assert "3.00 |    2 |    0 | 2026-04-29 11:00" in output
