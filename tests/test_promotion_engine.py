import json
from pathlib import Path
import pytest
from src.abw.api import app
from starlette.testclient import TestClient
from scripts.abw_knowledge import run_promote_drafts, _search_wiki_contexts

@pytest.fixture
def workspace_root(tmp_path):
    # Setup a mock workspace
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    
    # Create some drafts
    d1 = drafts / "draft-1.md"
    d1.write_text("# High Quality Draft\n\n## Important Section\nThis is a very informative draft with lots of facts.\n\nFact: ABW is powerful.\nFact: Promoted drafts are better than raw ones.\n\nKeywords: abw, promotion, engine")
    
    d2 = drafts / "d2.md"
    d2.write_text("tiny")
    
    d3 = drafts / "draft-3.md"
    d3.write_text("# Already Promoted\n\nstatus: promoted\nThis one should be skipped.")
    
    return tmp_path

def test_promote_drafts_logic(workspace_root):
    # Test the promotion logic directly
    result = run_promote_drafts(workspace_root, limit=5, dry_run=False)
    
    assert result["ok"] is True
    assert result["promoted_count"] == 1
    
    auto_promoted_dir = workspace_root / "wiki" / "auto_promoted"
    assert auto_promoted_dir.exists()
    
    promoted_files = list(auto_promoted_dir.glob("*.md"))
    assert len(promoted_files) == 1
    
    # Check content of promoted file
    content = promoted_files[0].read_text()
    assert "High Quality Draft" in content
    assert "auto-promoted" in content
    
    # Check if original draft was marked as promoted
    d1_content = (workspace_root / "drafts" / "draft-1.md").read_text()
    assert "status: promoted" in d1_content

def test_promote_drafts_api(workspace_root):
    client = TestClient(app)
    response = client.post("/promote-drafts", json={"workspace": str(workspace_root), "limit": 10})
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "data" in data
    assert "promoted_count" in data["data"]

def test_promote_drafts_dry_run(workspace_root):
    # Dry run should not create files
    result = run_promote_drafts(workspace_root, limit=5, dry_run=True)
    
    assert result["ok"] is True
    assert result["promoted_count"] == 1
    
    auto_promoted_dir = workspace_root / "wiki" / "auto_promoted"
    assert not auto_promoted_dir.exists()
    
    # Original draft should NOT be marked
    d1_content = (workspace_root / "drafts" / "draft-1.md").read_text()
    assert "status: promoted" not in d1_content

def test_agv_glossary_is_not_exact_match(tmp_path):
    (tmp_path / "wiki" / "manual").mkdir(parents=True)
    (tmp_path / "wiki" / "manual" / "agv-glossary.md").write_text(
        "# AGV Glossary\n\nAGV basics and terminology only.",
        encoding="utf-8",
    )

    matches = _search_wiki_contexts("AGV communication issue", workspace=tmp_path, limit=3)

    assert len(matches) == 1
    assert matches[0]["retrieval_status"] == "fuzzy_match"

def test_root_human_wiki_collision_blocks_auto_promotion(tmp_path):
    (tmp_path / "wiki").mkdir()
    (tmp_path / "drafts").mkdir()
    (tmp_path / "wiki" / "draft-1.md").write_text(
        "# Human Note\nstatus: grounded\n\nHuman canonical content.",
        encoding="utf-8",
    )
    (tmp_path / "drafts" / "draft-1.md").write_text(
        "# Auto Draft\n\n## Important\nThis is a long draft with enough substance to promote.\n"
        "Fact: Draft fact one.\nFact: Draft fact two.\nKeywords: draft, auto, shadow\n"
        + ("body\n" * 300),
        encoding="utf-8",
    )

    result = run_promote_drafts(tmp_path, dry_run=False)

    assert result["promoted_count"] == 0
    assert not (tmp_path / "wiki" / "auto_promoted" / "draft-1.md").exists()
