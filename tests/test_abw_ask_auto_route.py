import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import abw.api as api

@patch("abw.api.route_query")
@patch("abw.api.detect_workspace_purpose")
@patch("abw.api.run_ask")
@patch("abw.api._workspace_path")
def test_ask_auto_route_to_mom(mock_path, mock_run_ask, mock_detect, mock_route, tmp_path):
    # patch decorators are bottom-up, arguments are top-to-bottom.
    # mock_route = route_query
    # mock_detect = detect_workspace_purpose
    # mock_run_ask = run_ask
    # mock_path = _workspace_path
    
    ws_mom = tmp_path / "MOM"
    ws_mom.mkdir()
    
    mock_route.return_value = {
        "data": {
            "decision": "route",
            "best_workspace": str(ws_mom),
            "scores": [{"workspace": str(ws_mom), "similarity": 0.8}]
        }
    }
    mock_detect.return_value = {"workspace_purpose": "industrial_documentation", "similarity_score": 0.8}
    mock_run_ask.return_value = {"answer": "AGV info", "sources": [{"path": "wiki/agv.md"}]}
    (ws_mom / "wiki").mkdir()
    (ws_mom / "wiki" / "agv.md").write_text("AGV info", encoding="utf-8")
    
    # Ask with 'auto' (None workspace)
    req = api.AskRequest(workspace=None, query="AGV là gì?")
    response = api.ask(req)
    
    assert response["ok"] is True
    assert response["data"]["meta"]["routed"] is True
    assert response["data"]["meta"]["selected_workspace"] == str(ws_mom)
    assert "AGV info" in response["data"]["answer"]

@patch("abw.api.route_query")
def test_ask_auto_route_no_confident(mock_route):
    mock_route.return_value = {
        "data": {
            "decision": "no_confident_workspace",
            "scores": []
        }
    }
    
    req = api.AskRequest(workspace="auto", query="Random query")
    response = api.ask(req)
    
    assert response["ok"] is True
    assert response["data"]["retrieval_status"] == "no_confident_workspace"
    assert response["data"]["meta"]["routed"] is True

@patch("abw.api._workspace_path")
@patch("abw.api.run_ask")
@patch("abw.api.detect_workspace_purpose")
def test_ask_manual_override(mock_detect, mock_run_ask, mock_path, tmp_path):
    # mock_detect = detect_workspace_purpose
    # mock_run_ask = run_ask
    # mock_path = _workspace_path
    
    ws_manual = tmp_path / "MANUAL"
    ws_manual.mkdir()
    mock_path.return_value = ws_manual
    mock_detect.return_value = {"workspace_purpose": "unknown", "similarity_score": 0.5}
    mock_run_ask.return_value = {"answer": "Manual info", "sources": []}
    
    # Ask with explicit workspace
    req = api.AskRequest(workspace=str(ws_manual), query="Chương 7")
    response = api.ask(req)
    
    assert response["ok"] is True
    assert response["data"]["meta"]["routed"] is False
    assert response["data"]["meta"]["selected_workspace"] == str(ws_manual)
