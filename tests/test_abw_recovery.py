import pytest
from pathlib import Path
from abw.recovery import build_recovery_report, render_recovery_report

def test_recovery_report_structure(tmp_path):
    # Mock a workspace structure if needed, or just run on empty
    report = build_recovery_report(tmp_path)
    assert "workspace" in report
    assert "doctor_state" in report
    assert "steps" in report
    assert isinstance(report["steps"], list)
    assert "retest_sequence" in report

def test_render_recovery_report():
    report = {
        "workspace": "/tmp/test",
        "doctor_state": "WARN",
        "corpus_summary": "raw=10 wiki=0 drafts=5",
        "steps": [
            {
                "type": "missing_wiki_coverage",
                "severity": "FAIL",
                "action": "Create wiki notes",
                "command": "abw save --wiki",
                "gain": "+2.5",
                "impact": "No anchors"
            }
        ],
        "retest_sequence": ["abw eval"]
    }
    output = render_recovery_report(report)
    assert "ABW Recovery Plan" in output
    assert "missing_wiki_coverage" not in output # should be titleized
    assert "Missing Wiki Coverage" in output
    assert "abw save --wiki" in output
