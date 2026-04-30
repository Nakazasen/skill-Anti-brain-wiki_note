import importlib
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from abw.workspace_intel import compute_semantic_similarity, detect_workspace_purpose


def _api():
    return importlib.import_module("abw.api")


def test_detect_workspace_purpose_novel(tmp_path):
    workspace = tmp_path / "mat-the-website"
    workspace.mkdir()
    (workspace / "raw").mkdir()
    (workspace / "raw" / "Chương 1.docx").write_text("dummy", encoding="utf-8")
    (workspace / "raw" / "Chương 2.docx").write_text("dummy", encoding="utf-8")
    for i in range(3, 15):
        (workspace / "raw" / f"Chương {i}.docx").write_text("dummy", encoding="utf-8")

    (workspace / "SPECS mô tướng.md").write_text("Đây là dự án đọc truyện online.", encoding="utf-8")

    intel = detect_workspace_purpose(workspace)
    assert intel["workspace_purpose"] == "web_novel_platform"
    assert intel["confidence"] in ["medium", "high"]
    assert any("novel" in e or "truyện" in e or "Chương" in e for e in intel["evidence"])


def test_detect_workspace_purpose_industrial(tmp_path):
    workspace = tmp_path / "MOM_WMS_QLLSSX"
    workspace.mkdir()
    (workspace / "raw").mkdir()
    (workspace / "raw" / "manual_agv.pdf").write_text("dummy", encoding="utf-8")
    (workspace / "README.md").write_text("Industrial MOM and WMS system documentation.", encoding="utf-8")

    intel = detect_workspace_purpose(workspace)
    assert intel["workspace_purpose"] == "industrial_documentation"
    assert any("industrial" in e or "mom" in e or "agv" in e for e in intel["evidence"])


def test_compute_semantic_similarity():
    profile = {"chương": 10, "truyện": 5, "phong": 3, "trần": 3}

    score_high = compute_semantic_similarity("Chương 7 nói gì về Trần Phong?", profile)
    assert score_high > 0.4

    score_low = compute_semantic_similarity("AGV communication protocol WMS", profile)
    assert score_low == 0.0

    score_partial = compute_semantic_similarity("Chương này có AGV không?", profile)
    assert 0.1 < score_partial < 0.4


@patch("abw.api.detect_workspace_purpose")
@patch("abw.api.run_ask")
@patch("abw.api._workspace_path")
def test_ask_guard_blocks_industrial_in_novel(mock_path, mock_run_ask, mock_detect, tmp_path):
    api = _api()
    mock_path.return_value = tmp_path
    mock_detect.return_value = {
        "workspace_purpose": "web_novel_platform",
        "confidence": "high",
        "evidence": ["Detected novel chapters"],
        "similarity_score": 0.05,
    }

    req = api.AskRequest(workspace=str(tmp_path), query="AGV là gì?")
    response = api.ask(req)

    assert response["ok"] is True
    assert response["data"]["retrieval_status"] == "wrong_workspace"
    assert "tài liệu công nghiệp" in response["data"]["answer"]
    mock_run_ask.assert_not_called()


@patch("abw.api.detect_workspace_purpose")
@patch("abw.api.run_ask")
@patch("abw.api._workspace_path")
def test_ask_guard_allows_story_in_novel(mock_path, mock_run_ask, mock_detect, tmp_path):
    api = _api()
    mock_path.return_value = tmp_path
    mock_detect.return_value = {
        "workspace_purpose": "web_novel_platform",
        "confidence": "high",
        "evidence": ["Detected novel chapters"],
        "similarity_score": 0.6,
    }
    (tmp_path / "raw").mkdir(exist_ok=True)
    (tmp_path / "raw" / "Chương 7.docx").write_text("dummy", encoding="utf-8")
    mock_run_ask.return_value = {"answer": "Chương 7 nói về...", "sources": [{"path": "raw/Chương 7.docx"}]}

    req = api.AskRequest(workspace=str(tmp_path), query="Chương 7 nói gì?")
    response = api.ask(req)

    assert response["ok"] is True
    assert "Chương 7" in response["data"]["answer"]
    mock_run_ask.assert_called_once()


@patch("abw.api.detect_workspace_purpose")
@patch("abw.api.run_ask")
@patch("abw.api._workspace_path")
def test_ask_guard_allows_industrial_in_mom(mock_path, mock_run_ask, mock_detect, tmp_path):
    api = _api()
    mock_path.return_value = tmp_path
    mock_detect.return_value = {
        "workspace_purpose": "industrial_documentation",
        "confidence": "high",
        "evidence": ["Detected MOM docs"],
        "similarity_score": 0.8,
    }
    (tmp_path / "wiki").mkdir(exist_ok=True)
    (tmp_path / "wiki" / "agv.md").write_text("AGV communicates via UDP...", encoding="utf-8")
    mock_run_ask.return_value = {"answer": "AGV communicates via UDP...", "sources": [{"path": "wiki/agv.md"}]}

    req = api.AskRequest(workspace=str(tmp_path), query="AGV là gì?")
    response = api.ask(req)

    assert response["ok"] is True
    assert "AGV communicates" in response["data"]["answer"]
    mock_run_ask.assert_called_once()


@patch("abw.api.detect_workspace_purpose")
@patch("abw.api.run_ask")
@patch("abw.api._workspace_path")
def test_ask_guard_ignores_false_positives_in_novel(mock_path, mock_run_ask, mock_detect, tmp_path):
    api = _api()
    mock_path.return_value = tmp_path
    mock_detect.return_value = {
        "workspace_purpose": "web_novel_platform",
        "confidence": "high",
        "evidence": ["Detected novel chapters"],
        "similarity_score": 0.25,
    }
    (tmp_path / "raw").mkdir(exist_ok=True)
    (tmp_path / "raw" / "Chương 10.docx").write_text("dummy", encoding="utf-8")
    mock_run_ask.return_value = {"answer": "Momo là ví điện tử...", "sources": [{"path": "raw/Chương 10.docx"}]}

    req = api.AskRequest(workspace=str(tmp_path), query="Momo là gì trong truyện?")
    response = api.ask(req)

    assert response["ok"] is True
    assert response["data"]["retrieval_status"] != "wrong_workspace"
    assert "Momo là ví điện tử" in response["data"]["answer"]
    mock_run_ask.assert_called_once()


@patch("abw.api.detect_workspace_purpose")
@patch("abw.api.run_ask")
@patch("abw.api._workspace_path")
def test_ask_guard_does_not_block_unknown_workspace(mock_path, mock_run_ask, mock_detect, tmp_path):
    api = _api()
    mock_path.return_value = tmp_path
    mock_detect.return_value = {
        "workspace_purpose": "unknown",
        "confidence": "low",
        "evidence": [],
    }
    (tmp_path / "raw").mkdir(exist_ok=True)
    (tmp_path / "raw" / "generic.txt").write_text("Some generic info about AGV", encoding="utf-8")
    mock_run_ask.return_value = {"answer": "Some generic info about AGV", "sources": [{"path": "raw/generic.txt"}]}

    req = api.AskRequest(workspace=str(tmp_path), query="AGV là gì?")
    response = api.ask(req)

    assert response["ok"] is True
    assert response["data"]["retrieval_status"] != "wrong_workspace"
    assert "Some generic info" in response["data"]["answer"]
    mock_run_ask.assert_called_once()
