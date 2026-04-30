
import pytest
from pathlib import Path
from abw.api import route_query, RouteRequest, list_enabled_workspaces
from abw.workspace_registry import save_workspaces, load_workspaces

@pytest.fixture
def mock_workspaces(tmp_path, monkeypatch):
    # Setup mock workspaces
    mom_path = tmp_path / "MOM_WMS"
    mom_path.mkdir()
    (mom_path / "raw").mkdir()
    (mom_path / "README.md").write_text("Industrial MOM WMS AGV system documentation", encoding="utf-8")
    
    novel_path = tmp_path / "WebNovel"
    novel_path.mkdir()
    (novel_path / "raw").mkdir()
    (novel_path / "README.md").write_text("Web Novel truyện Chương 7 nhân vật", encoding="utf-8")
    
    workspaces = [
        {"path": str(mom_path), "name": "MOM_WMS", "enabled": True},
        {"path": str(novel_path), "name": "Web Novel", "enabled": True}
    ]
    
    # Mock load_workspaces and list_enabled_workspaces
    monkeypatch.setattr("abw.api.list_enabled_workspaces", lambda: [str(mom_path), str(novel_path)])
    monkeypatch.setattr("abw.workspace_registry.load_workspaces", lambda: workspaces)
    
    return {"mom": str(mom_path), "novel": str(novel_path)}

def test_cross_domain_ambiguity(mock_workspaces):
    # A. "AGV trong truyện có gì?" => ambiguous
    req = RouteRequest(query="AGV trong truyện có gì?")
    res = route_query(req)
    assert res["data"]["decision"] == "ambiguous"

def test_industrial_routing(mock_workspaces):
    # B. "AGV là gì?" => MOM_WMS
    req = RouteRequest(query="AGV là gì?")
    res = route_query(req)
    assert res["data"]["decision"] == "route"
    assert res["data"]["best_workspace"] == mock_workspaces["mom"]

def test_novel_routing(mock_workspaces):
    # C. "Chương 7 nói gì?" => Web Novel
    req = RouteRequest(query="Chương 7 nói gì?")
    res = route_query(req)
    assert res["data"]["decision"] == "route"
    assert res["data"]["best_workspace"] == mock_workspaces["novel"]

def test_momo_novel_routing(mock_workspaces):
    # D. "Momo là gì trong truyện?" => Web Novel (contains 'truyện', no industrial keywords)
    req = RouteRequest(query="Momo là gì trong truyện?")
    res = route_query(req)
    # Even if similarity is low, it should not route to MOM
    assert res["data"]["decision"] == "route"
    assert res["data"]["best_workspace"] == mock_workspaces["novel"]
