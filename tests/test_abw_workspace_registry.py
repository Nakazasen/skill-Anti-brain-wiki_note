import sys
import json
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import abw.workspace_registry as registry

@pytest.fixture
def temp_brain(tmp_path, monkeypatch):
    monkeypatch.setenv("ABW_ROOT", str(tmp_path))
    (tmp_path / ".brain").mkdir()
    return tmp_path

def test_register_workspace(temp_brain):
    ws_path = temp_brain / "WS1"
    ws_path.mkdir()
    (ws_path / "wiki").mkdir()
    
    ws = registry.register_workspace(str(ws_path), "My Workspace")
    assert ws["name"] == "My Workspace"
    assert ws["enabled"] is True
    assert Path(ws["path"]) == ws_path.resolve()
    
    workspaces = registry.load_workspaces()
    assert len(workspaces) == 1
    assert workspaces[0]["name"] == "My Workspace"

def test_disable_workspace(temp_brain):
    ws_path = temp_brain / "WS1"
    ws_path.mkdir()
    (ws_path / "wiki").mkdir()
    registry.register_workspace(str(ws_path))
    
    success = registry.disable_workspace(str(ws_path))
    assert success is True
    
    enabled = registry.list_enabled_workspaces()
    assert len(enabled) == 0
    
    all_ws = registry.load_workspaces()
    assert all_ws[0]["enabled"] is False

def test_list_enabled_workspaces(temp_brain):
    ws1 = temp_brain / "WS1"
    ws1.mkdir()
    (ws1 / "wiki").mkdir()
    ws2 = temp_brain / "WS2"
    ws2.mkdir()
    (ws2 / "wiki").mkdir()
    
    registry.register_workspace(str(ws1))
    registry.register_workspace(str(ws2))
    registry.disable_workspace(str(ws2))
    
    enabled = registry.list_enabled_workspaces()
    assert len(enabled) == 1
    assert Path(enabled[0]) == ws1.resolve()

@patch("abw.api.detect_workspace_purpose")
def test_api_registry_routing(mock_detect, temp_brain):
    from abw.api import route_query, RouteRequest
    
    ws1 = temp_brain / "WS1"
    ws1.mkdir()
    (ws1 / "wiki").mkdir()
    registry.register_workspace(str(ws1))
    
    mock_detect.return_value = {"workspace_purpose": "test", "similarity_score": 0.8}
    
    # Route with None workspaces (should use registry)
    req = RouteRequest(query="test", workspaces=None)
    response = route_query(req)
    
    assert response["ok"] is True
    assert len(response["data"]["scores"]) == 1
    assert response["data"]["best_workspace"] == str(ws1.resolve())

def test_register_re_enables(temp_brain):
    ws1 = temp_brain / "WS1"
    ws1.mkdir()
    (ws1 / "wiki").mkdir()
    registry.register_workspace(str(ws1))
    registry.disable_workspace(str(ws1))
    
    # Register again should re-enable
    registry.register_workspace(str(ws1))
    enabled = registry.list_enabled_workspaces()
    assert len(enabled) == 1

def test_register_workspace_rejects_nonexistent_path(temp_brain):
    missing = temp_brain / "missing-workspace"

    with pytest.raises(ValueError, match="does not exist"):
        registry.register_workspace(str(missing))
