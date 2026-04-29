import pytest
from pathlib import Path
from abw.inspect import build_inspect_report

def test_inspect_empty_workspace(tmp_path):
    # Setup empty workspace
    report = build_inspect_report(tmp_path)
    assert report["raw_stats"]["total"] == 0
    assert report["wiki_stats"]["total"] == 0
    assert len(report["suggestions"]) == 0

def test_inspect_mom_workspace(tmp_path):
    # Setup MOM-like workspace
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "agv_comm.pdf").write_text("dummy")
    (raw / "wms_workflow.txt").write_text("dummy")
    
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "index.md").write_text("dummy")
    
    report = build_inspect_report(tmp_path)
    assert report["raw_stats"]["total"] == 2
    assert report["raw_stats"]["supported"] == 2
    assert report["wiki_stats"]["total"] == 1
    assert "add wiki notes" not in report["suggestions"]

def test_inspect_docx_heavy_workspace(tmp_path):
    # Setup DOCX-heavy workspace
    raw = tmp_path / "raw"
    raw.mkdir()
    for i in range(5):
        (raw / f"doc_{i}.docx").write_text("dummy")
    
    report = build_inspect_report(tmp_path)
    assert report["raw_stats"]["total"] == 5
    assert report["raw_stats"]["unsupported"] == 5
    assert ".docx" in report["raw_stats"]["by_ext"]
    assert any("convert 5 docx" in s for s in report["suggestions"])

def test_inspect_mixed_stale_workspace(tmp_path):
    # Setup mixed workspace with many drafts
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "test.md").write_text("dummy")
    
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    for i in range(15):
        (drafts / f"draft_{i}.md").write_text("dummy")
        
    report = build_inspect_report(tmp_path)
    assert report["draft_stats"]["total"] == 15
    assert any("too many stale drafts" in s for s in report["suggestions"])
