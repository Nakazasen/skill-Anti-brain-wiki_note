import importlib
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))


def _api():
    return importlib.import_module("abw.api")


@patch("abw.api.detect_workspace_purpose")
def test_route_query_to_best_workspace(mock_detect, tmp_path):
    api = _api()
    ws1 = tmp_path / "MOM"
    ws1.mkdir()
    ws2 = tmp_path / "NOVEL"
    ws2.mkdir()

    def mock_side_effect(ws, query=None):
        if "MOM" in str(ws):
            return {"workspace_purpose": "industrial_documentation", "similarity_score": 0.8 if "AGV" in str(query) else 0.0}
        if "NOVEL" in str(ws):
            return {"workspace_purpose": "web_novel_platform", "similarity_score": 0.8 if "Chương" in str(query) else 0.0}
        return {"workspace_purpose": "unknown", "similarity_score": 0.0}

    mock_detect.side_effect = mock_side_effect

    req = api.RouteRequest(query="AGV là gì?", workspaces=[str(ws1), str(ws2)])
    response = api.route_query(req)
    assert response["ok"] is True
    assert response["data"]["best_workspace"] == str(ws1.resolve())
    assert response["data"]["decision"] == "route"

    req = api.RouteRequest(query="Chương 7 nói gì?", workspaces=[str(ws1), str(ws2)])
    response = api.route_query(req)
    assert response["ok"] is True
    assert response["data"]["best_workspace"] == str(ws2.resolve())
    assert response["data"]["decision"] == "route"


@patch("abw.api.detect_workspace_purpose")
def test_route_query_ambiguous(mock_detect, tmp_path):
    api = _api()
    ws1 = tmp_path / "WS1"
    ws1.mkdir()
    ws2 = tmp_path / "WS2"
    ws2.mkdir()

    mock_detect.side_effect = lambda ws, query=None: {"workspace_purpose": "unknown", "similarity_score": 0.5}

    req = api.RouteRequest(query="AGV trong truyện có gì?", workspaces=[str(ws1), str(ws2)])
    response = api.route_query(req)
    assert response["data"]["decision"] == "ambiguous"


@patch("abw.api.detect_workspace_purpose")
def test_route_query_no_confident(mock_detect, tmp_path):
    api = _api()
    ws = tmp_path / "WS"
    ws.mkdir()

    mock_detect.return_value = {"workspace_purpose": "unknown", "similarity_score": 0.1}

    req = api.RouteRequest(query="Alien language", workspaces=[str(ws)])
    response = api.route_query(req)
    assert response["data"]["decision"] == "no_confident_workspace"
