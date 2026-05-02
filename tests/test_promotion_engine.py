import json
from pathlib import Path
import sys
import tempfile
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
    config = {
        "project_name": "test",
        "workspace_schema": 1,
        "abw_version": "1.1.0",
        "domain_profile": "generic",
        "providers": {"promotion_mode": "auto"},
    }
    (workspace_root / "abw_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
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
    config = {
        "project_name": "test",
        "workspace_schema": 1,
        "abw_version": "1.1.0",
        "domain_profile": "generic",
        "providers": {"promotion_mode": "auto"},
    }
    (workspace_root / "abw_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    client = TestClient(app)
    response = client.post("/promote-drafts", json={"workspace": str(workspace_root), "limit": 10})
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "data" in data
    assert "promoted_count" in data["data"]

def test_promote_drafts_dry_run(workspace_root):
    config = {
        "project_name": "test",
        "workspace_schema": 1,
        "abw_version": "1.1.0",
        "domain_profile": "generic",
        "providers": {"promotion_mode": "auto"},
    }
    (workspace_root / "abw_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
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
    config = {
        "project_name": "test",
        "workspace_schema": 1,
        "abw_version": "1.1.0",
        "domain_profile": "generic",
        "providers": {"promotion_mode": "auto"},
    }
    (tmp_path / "abw_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
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


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import abw_ingest  # noqa: E402


class TestPromotionSafety:
    def test_review_decision_never_returns_candidate_promoted(self):
        result, reason = abw_ingest._review_decision("pdf", 0.95, [])
        assert result == "review_needed"
        assert reason != "high_confidence"

        result, reason = abw_ingest._review_decision("pdf", 0.99, [])
        assert result == "review_needed"

        result, reason = abw_ingest._review_decision("md", 0.95, [])
        assert result == "review_needed"

        result, reason = abw_ingest._review_decision("pptx", 0.65, [])
        assert result == "review_needed"
        assert reason == "medium_confidence_enterprise_parse"

    def test_review_decision_low_confidence_returns_review_needed(self):
        result, reason = abw_ingest._review_decision("txt", 0.2, [])
        assert result == "review_needed"
        assert reason == "low_confidence"

    def test_review_decision_conflict_always_review_needed(self):
        result, reason = abw_ingest._review_decision("pdf", 0.95, ["conflict-report.md"])
        assert result == "review_needed"
        assert reason == "conflict_detected"

    def test_auto_promote_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "drafts").mkdir()
            draft = workspace / "drafts" / "quality-draft.md"
            draft.write_text(
                "# High Quality Draft\n\n## Important Section\n"
                "This is a very informative draft.\n"
                "Fact: Promotion safety must be tested.\n"
                + ("text\n" * 300),
                encoding="utf-8",
            )

            result = run_promote_drafts(workspace, dry_run=False)

            assert result["promoted_count"] == 0
            assert "disabled by default" in result["message"]
            assert not (workspace / "wiki" / "auto_promoted").exists()

    def test_auto_promote_enabled_with_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "drafts").mkdir()
            config = {
                "project_name": "test",
                "workspace_schema": 1,
                "abw_version": "1.1.0",
                "domain_profile": "generic",
                "providers": {"promotion_mode": "auto"},
            }
            (workspace / "abw_config.json").write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            draft = workspace / "drafts" / "long-draft.md"
            draft.write_text(
                "# Auto-Ready Draft\n\n## Important\n"
                "Fact: Long enough for promotion.\n"
                + ("body\n" * 300),
                encoding="utf-8",
            )

            result = run_promote_drafts(workspace, dry_run=False)

            assert result["promoted_count"] == 1
            assert (workspace / "wiki" / "auto_promoted" / "long-draft.md").exists()

    def test_ingest_high_confidence_does_not_auto_promote(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "ops.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text(
                "# Operations Rule\nMOM station routing rule v2 approved by team.\n"
                "Process: AGV handoff before WMS confirmation.\n"
                "Approval: Required for capacity changes.\n",
                encoding="utf-8",
            )

            result = abw_ingest.run("ingest raw/ops.md", str(workspace))

            assert result["queue_status"] == "review_needed"
            assert result["promotion_status"] == "review_needed"
            assert not (workspace / "wiki" / "auto_promoted").exists()
            assert result["review_reason"] != "high_confidence"
            queue = json.loads((workspace / ".brain" / "ingest_queue.json").read_text(encoding="utf-8"))
            assert queue["items"][0]["status"] == "review_needed"

    def test_ingest_creates_queue_not_wiki(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "network.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text(
                "Network retry strategy with exponential backoff.\n", encoding="utf-8"
            )

            result = abw_ingest.run("ingest raw/network.md", str(workspace))

            assert not (workspace / "wiki").exists() or not list((workspace / "wiki").rglob("*.md"))
            queue_path = workspace / ".brain" / "ingest_queue.json"
            assert queue_path.exists()
            queue = json.loads(queue_path.read_text(encoding="utf-8"))
            assert len(queue["items"]) == 1
            assert queue["items"][0]["status"] == "review_needed"
            assert (workspace / result["draft_file"]).exists()

    def test_explicit_approval_path_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw_file = workspace / "raw" / "printer.md"
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            raw_file.write_text("# Printer Notes\nDrum unit handles image transfer.\n", encoding="utf-8")

            result = abw_ingest.run("ingest raw/printer.md", str(workspace))

            assert result["status"] == "draft_created"
            assert result["queue_status"] == "review_needed"
            queue = json.loads((workspace / ".brain" / "ingest_queue.json").read_text(encoding="utf-8"))
            assert queue["items"][0]["status"] == "review_needed"
