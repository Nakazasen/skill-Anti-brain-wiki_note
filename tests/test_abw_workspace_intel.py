from __future__ import annotations

import os
import time
from pathlib import Path

from abw.workspace_intel import build_workspace_intel_report, render_workspace_intel_report


def test_workspace_intel_detects_quality_issues(tmp_path):
    raw = tmp_path / "raw"
    wiki = tmp_path / "wiki"
    drafts = tmp_path / "drafts"
    raw.mkdir()
    wiki.mkdir()
    drafts.mkdir()

    (raw / "spec.md").write_text("raw", encoding="utf-8")
    (wiki / "spec.md").write_text("wiki", encoding="utf-8")
    (raw / "legacy.bin").write_text("unsupported", encoding="utf-8")
    old_draft = drafts / "old.md"
    old_draft.write_text("draft", encoding="utf-8")
    old_time = time.time() - (30 * 24 * 60 * 60)
    os.utime(old_draft, (old_time, old_time))

    report = build_workspace_intel_report(tmp_path)
    types = {issue["type"] for issue in report["issues"]}

    assert "stale_drafts" in types
    assert "duplicate_docs" in types
    assert "unsupported_raw_formats" in types
    assert report["summary"]["issue_count"] >= 3
    assert report["top_actions"]
    stale = next(issue for issue in report["issues"] if issue["type"] == "stale_drafts")
    assert stale["can_auto_fix"] is True
    assert stale["recommended_action"]
    assert stale["risk_level"] == "low"


def test_workspace_intel_detects_low_wiki_coverage(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    for index in range(5):
        (raw / f"source-{index}.md").write_text("raw", encoding="utf-8")

    report = build_workspace_intel_report(tmp_path)
    issue = next(item for item in report["issues"] if item["type"] == "low_wiki_coverage")

    assert issue["severity"] == "high"
    assert issue["supported_raw"] == 5
    assert issue["wiki_notes"] == 0
    assert "Create concise wiki notes" in issue["recommendation"]


def test_workspace_intel_render_is_human_readable(tmp_path):
    report = {
        "summary": {
            "workspace": str(Path(tmp_path)),
            "raw_files": 1,
            "wiki_topics": 0,
            "drafts": 0,
            "processed_files": 0,
            "issue_count": 1,
            "highest_severity": "high",
        },
        "issues": [
            {
                "type": "low_wiki_coverage",
                "severity": "high",
                "count": 1,
                "recommendation": "Add wiki notes.",
            }
        ],
        "top_actions": ["Add wiki notes."],
    }

    rendered = render_workspace_intel_report(report)

    assert "Workspace Intel" in rendered
    assert "low_wiki_coverage [high]" in rendered


def test_workspace_fix_uses_existing_apply_engine(tmp_path):
    draft = tmp_path / "drafts" / "old.md"
    draft.parent.mkdir()
    draft.write_text("draft", encoding="utf-8")

    from abw.workspace_intel import run_workspace_fix

    preview = run_workspace_fix(tmp_path, "stale_drafts", dry_run=True)

    assert preview["apply_action"] == "cleanup-drafts"
    assert preview["dry_run"] is True
    assert preview["backup_or_archive_first"] is True
    assert draft.exists()
    applied = run_workspace_fix(tmp_path, "stale_drafts", dry_run=False)
    assert applied["dry_run"] is False
    assert not draft.exists()
    assert applied["apply_report"]["changes_applied_count"] == 1


def test_workspace_fix_rejects_manual_issue(tmp_path):
    from abw.workspace_intel import run_workspace_fix

    try:
        run_workspace_fix(tmp_path, "duplicate_docs", dry_run=True)
    except ValueError as exc:
        assert "not auto-fixable" in str(exc)
    else:
        raise AssertionError("duplicate_docs should require manual remediation")
