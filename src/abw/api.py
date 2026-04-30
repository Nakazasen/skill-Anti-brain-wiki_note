from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

try:  # pragma: no cover - exercised only when installed FastAPI/Starlette are compatible.
    from fastapi import FastAPI
    from fastapi.exceptions import RequestValidationError
except Exception:  # pragma: no cover
    FastAPI = None
    RequestValidationError = None

from . import __version__
from .apply import ACTIONS as APPLY_ACTIONS, run_apply, run_rollback
from .entry import ask as run_ask
from .gaps import build_gap_report
from .improve import build_improvement_plan
from .inspect import build_inspect_report
from .recovery import build_recovery_report
from .recovery_verify import build_verify_report
from .trend import build_trend_report
from .workspace_intel import (
    build_workspace_intel_report, 
    detect_workspace_purpose, 
    run_workspace_fix,
    compute_semantic_similarity,
    normalize_text,
    NOVEL_KEYWORDS,
    INDUSTRIAL_KEYWORDS,
    DOMAIN_SPECIFIC_INDUSTRIAL,
    DOMAIN_SPECIFIC_NOVEL,
    GENERIC_ROUTING_TERMS
)
from .workspace_registry import (
    load_workspaces, 
    register_workspace as register_ws, 
    disable_workspace as disable_ws, 
    list_enabled_workspaces
)

# Promotion logic is currently in scripts/abw_knowledge.py
try:
    from scripts.abw_knowledge import run_promote_drafts
except ImportError:
    # Fallback if scripts not in path (e.g. production install without scripts)
    run_promote_drafts = None

CONFIDENCE_MAP = {
    "high": 85,
    "medium": 60,
    "low": 30,
    "insufficient": 10,
    "insufficient_evidence": 10,
}


def _configure_api_logging() -> logging.Logger:
    log_dir = Path(os.environ.get("ABW_LOG_DIR", "logs")).expanduser().resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("abw.api")
    logger.setLevel(logging.INFO)
    logger.propagate = True
    log_path = log_dir / "api.log"
    if not any(isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == log_path for handler in logger.handlers):
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
    return logger


LOGGER = _configure_api_logging()


class WorkspaceRequest(BaseModel):
    workspace: str | None = None


class ApplyRequest(WorkspaceRequest):
    action: str = "cleanup-drafts"
    yes: bool = False
    rollback_id: str | None = None


class AskRequest(WorkspaceRequest):
    query: str | None = None


class WorkspaceFixRequest(WorkspaceRequest):
    issue_type: str | None = None
    dry_run: bool = True


class PromoteRequest(WorkspaceRequest):
    limit: int = 20
    dry_run: bool = False


class RouteRequest(BaseModel):
    query: str
    workspaces: list[str] | None = None


class RegisterRequest(BaseModel):
    path: str
    name: str | None = None


class DisableRequest(BaseModel):
    path: str


def _build_fastapi_app():
    if FastAPI is None:
        return None
    try:
        fastapi_app = FastAPI(title="ABW Local API", version=__version__)
    except TypeError:
        return None

    if RequestValidationError is not None:
        fastapi_app.exception_handler(RequestValidationError)(validation_exception_handler)

    fastapi_app.get("/health")(health)
    fastapi_app.post("/inspect")(inspect)
    fastapi_app.post("/gaps")(gaps)
    fastapi_app.post("/recover-plan")(recover_plan)
    fastapi_app.post("/recover-verify")(recover_verify)
    fastapi_app.post("/trend")(trend)
    fastapi_app.post("/improve")(improve)
    fastapi_app.post("/apply")(apply_action)
    fastapi_app.post("/ask")(ask)
    fastapi_app.post("/workspace-intel")(workspace_intel)
    fastapi_app.post("/workspace-fix")(workspace_fix)
    fastapi_app.post("/promote-drafts")(promote_drafts_fastapi)
    fastapi_app.post("/route-query")(route_query)
    fastapi_app.get("/list-workspaces")(list_workspaces_api)
    fastapi_app.post("/register-workspace")(register_workspace_api)
    fastapi_app.post("/disable-workspace")(disable_workspace_api)
    return fastapi_app


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "ok": False,
            "command": "unknown",
            "version": __version__,
            "error": "bad request",
            "details": exc.errors() if hasattr(exc, "errors") else str(exc),
        },
    )


def _workspace_path(payload: WorkspaceRequest) -> Path:
    workspace = str(payload.workspace or "").strip()
    if not workspace:
        raise HTTPException(status_code=400, detail="workspace is required")
    return Path(workspace).expanduser().resolve()


def _response(command: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "command": command, "version": __version__, "data": data}


def _extract_text(result: dict[str, Any]) -> str:
    for key in ("answer", "content", "rendered", "message"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    final = result.get("final")
    if isinstance(final, dict):
        for key in ("answer", "content", "rendered", "message"):
            value = final.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _confidence_value(value: Any, default: int = 60) -> int:
    if isinstance(value, (int, float)):
        val = float(value)
        if val <= 1.0 and val > 0:
            val = val * 100
        return max(0, min(100, int(val)))
    text = str(value or "").strip().lower()
    return CONFIDENCE_MAP.get(text, default)


def _source_title(path: str) -> str:
    name = Path(path.replace("\\", "/")).name
    return Path(name).stem.replace("-", " ").replace("_", " ").strip() or path


def _source_object(path: str, *, title: str | None = None, snippet: str | None = None, confidence: Any = None) -> dict[str, Any]:
    clean_path = str(path or "").strip()
    normalized = clean_path.replace("\\", "/").lower()
    default_confidence = 15
    if normalized.startswith("wiki/"):
        default_confidence = 65
    elif normalized.startswith("raw/"):
        default_confidence = 30
    elif normalized.startswith("processed/"):
        default_confidence = 25
    elif normalized.startswith("drafts/"):
        default_confidence = 15
    return {
        "path": clean_path,
        "title": str(title or _source_title(clean_path)).strip(),
        "snippet": str(snippet or "").strip(),
        "confidence": _confidence_value(confidence, default=default_confidence),
    }


def _is_allowed_source_path(path: str) -> bool:
    normalized = str(path or "").strip().replace("\\", "/").lower()
    if not normalized.startswith(("wiki/", "drafts/", "raw/", "processed/")):
        return False
    if any(part in normalized for part in ("/quarantine/", "/.brain/", "/meta/", "/metadata/")):
        return False
    if normalized.endswith(("/readme.md", "/readme.txt")):
        return False
    return True


def _source_exists_in_workspace(path: str, workspace_root: Path | None) -> bool:
    if workspace_root is None:
        return True
    candidate = (workspace_root / Path(path)).resolve()
    try:
        candidate.relative_to(workspace_root)
    except ValueError:
        return False
    return candidate.exists() and candidate.is_file()


def _extract_sources(value: Any, workspace_root: Path | None = None) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []

    def collect(item: Any) -> None:
        if isinstance(item, dict):
            path_value = item.get("path") or item.get("file") or item.get("source")
            if (
                isinstance(path_value, str)
                and _is_allowed_source_path(path_value)
                and _source_exists_in_workspace(path_value, workspace_root)
            ):
                sources.append(
                    _source_object(
                        path_value,
                        title=item.get("title"),
                        snippet=item.get("snippet") or item.get("content") or item.get("text"),
                        confidence=item.get("confidence") or item.get("score"),
                    )
                )
            for key, child in item.items():
                lowered = str(key).lower()
                if lowered in {"source", "sources", "path", "paths", "file", "files", "evidence", "citations", "artifact_paths"}:
                    collect(child)
                elif isinstance(child, (dict, list)):
                    collect(child)
        elif isinstance(item, list):
            for child in item:
                collect(child)
        elif isinstance(item, str):
            text = item.strip()
            if _is_allowed_source_path(text) and _source_exists_in_workspace(text, workspace_root):
                sources.append(_source_object(text))

    collect(value)
    deduped: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for source in sources:
        path = str(source.get("path") or "")
        if path and path not in seen_paths:
            seen_paths.add(path)
            deduped.append(source)
    return deduped


def _trust_score(result: dict[str, Any], sources: list[dict[str, Any]]) -> int:
    base = _confidence_value(result.get("confidence") or result.get("status"), default=50)
    if sources:
        source_score = max(source["confidence"] for source in sources)
        return max(0, min(100, int((base + source_score) / 2)))
    return min(base, 35)


def _normalize_ask_result(result: Any, workspace_root: Path | None = None) -> dict[str, Any]:
    if not isinstance(result, dict):
        answer = str(result or "")
        return {
            "answer": f"Low confidence: no supporting sources were returned.\n\n{answer}".strip(),
            "sources": [],
            "trust_score": 20,
            "warnings": ["No supporting sources were returned."],
            "logs": [],
            "retrieval_status": "no_match",
            "meta": {"raw_result_type": type(result).__name__},
        }

    logs = []
    warnings = []
    for key in ("logs", "fail_reasons"):
        value = result.get(key)
        if isinstance(value, list):
            logs.extend(value)
        elif isinstance(value, str) and value.strip():
            logs.append(value.strip())
    raw_warnings = result.get("warnings")
    if isinstance(raw_warnings, list):
        warnings.extend(str(item) for item in raw_warnings if str(item).strip())
    elif isinstance(raw_warnings, str) and raw_warnings.strip():
        warnings.append(raw_warnings.strip())
    logs.extend(warnings)

    sources = _extract_sources(result, workspace_root=workspace_root)
    trust_score = _trust_score(result, sources)
    answer = _extract_text(result)
    knowledge_output = (
        result.get("knowledge_output") 
        if isinstance(result.get("knowledge_output"), dict) 
        else (result.get("knowledge") if isinstance(result.get("knowledge"), dict) else {})
    )
    retrieval_status = str(
        result.get("retrieval_status")
        or knowledge_output.get("retrieval_status")
        or ("fuzzy_match" if sources else "no_match")
    )
    if not sources:
        retrieval_status = "no_match"
    if retrieval_status == "no_match":
        answer = "Không tìm thấy thông tin đáng tin cậy."
        trust_score = 0
    if not sources:
        warnings.append("No supporting sources were returned.")
        if retrieval_status != "no_match":
            prefix = "Low confidence: no supporting sources were returned."
            answer = f"{prefix}\n\n{answer}".strip() if answer else prefix
    elif trust_score < 50:
        warnings.append("Weak evidence: trust score is below 50.")

    meta = {
        "route": result.get("route"),
        "confidence": result.get("confidence"),
        "status": result.get("status"),
        "workspace": result.get("workspace"),
    }
    return {
        "answer": answer,
        "sources": sources,
        "trust_score": trust_score,
        "warnings": warnings,
        "logs": logs,
        "retrieval_status": retrieval_status,
        "meta": {key: value for key, value in meta.items() if value is not None},
    }


def _error_response(command: str, exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc
    return HTTPException(status_code=500, detail=str(exc) or exc.__class__.__name__)


def _run_report(command: str, payload: WorkspaceRequest, builder) -> dict[str, Any]:
    try:
        return _response(command, builder(_workspace_path(payload)))
    except Exception as exc:
        raise _error_response(command, exc) from exc


def health() -> dict[str, Any]:
    LOGGER.info("health check")
    return _response("health", {"status": "ok"})


def inspect(payload: WorkspaceRequest) -> dict[str, Any]:
    return _run_report("inspect", payload, build_inspect_report)


def gaps(payload: WorkspaceRequest) -> dict[str, Any]:
    return _run_report("gaps", payload, build_gap_report)


def recover_plan(payload: WorkspaceRequest) -> dict[str, Any]:
    return _run_report("recover-plan", payload, build_recovery_report)


def recover_verify(payload: WorkspaceRequest) -> dict[str, Any]:
    return _run_report("recover-verify", payload, build_verify_report)


def trend(payload: WorkspaceRequest) -> dict[str, Any]:
    return _run_report("trend", payload, build_trend_report)


def improve(payload: WorkspaceRequest) -> dict[str, Any]:
    return _run_report("improve", payload, build_improvement_plan)


def workspace_intel(payload: WorkspaceRequest) -> dict[str, Any]:
    return _run_report("workspace-intel", payload, build_workspace_intel_report)


def workspace_fix(payload: WorkspaceFixRequest) -> dict[str, Any]:
    try:
        workspace = _workspace_path(payload)
        issue_type = str(payload.issue_type or "").strip()
        if not issue_type:
            raise HTTPException(status_code=400, detail="issue_type is required")
        return _response("workspace-fix", run_workspace_fix(workspace, issue_type, dry_run=payload.dry_run))
    except Exception as exc:
        raise _error_response("workspace-fix", exc) from exc


def ask(payload: AskRequest) -> dict[str, Any]:
    try:
        query = str(payload.query or "").strip()
        if not query:
            raise HTTPException(status_code=400, detail="query is required")

        workspace_input = str(payload.workspace or "").strip().lower()
        is_auto = not workspace_input or workspace_input == "auto"
        selected_workspace = None
        routed = False
        similarity = 0.0

        if is_auto:
            # Automatic routing using registry
            enabled_workspaces = list_enabled_workspaces()
            route_payload = RouteRequest(query=query, workspaces=enabled_workspaces)
            route_result = route_query(route_payload)
            if route_result["data"]["decision"] == "route":
                selected_workspace = Path(route_result["data"]["best_workspace"])
                routed = True
                # Find the score for the selected workspace
                for s in route_result["data"]["scores"]:
                    if s["workspace"] == str(selected_workspace):
                        similarity = s["similarity"]
                        break
            else:
                return _response("ask", {
                    "retrieval_status": "no_confident_workspace",
                    "trust_score": 0,
                    "sources": [],
                    "answer": "Không tìm thấy workspace nào phù hợp với câu hỏi của bạn.",
                    "warnings": ["Auto-routing failed to find a confident workspace."],
                    "meta": {"routed": True, "decision": route_result["data"]["decision"]}
                })
        else:
            selected_workspace = _workspace_path(payload)

        # Workspace Purpose Guard (Semantic + Keyword Fallback)
        intel = detect_workspace_purpose(selected_workspace, query=query)
        if not routed:
            similarity = intel.get("similarity_score", 1.0)
        
        if intel["workspace_purpose"] == "web_novel_platform":
            pattern = "|".join([rf"\b{term}\b" for term in INDUSTRIAL_KEYWORDS])
            keyword_match = re.search(pattern, query, re.IGNORECASE)
            
            # Semantic Guard: Block if similarity is very low and it looks industrial
            if similarity < 0.2:
                # Only block if it's actually a novel workspace and similarity is low
                if keyword_match or similarity < 0.1: # Allow low similarity if no industrial keywords unless extremely low
                    return _response("ask", {
                        "retrieval_status": "wrong_workspace",
                        "trust_score": 0,
                        "sources": [],
                        "answer": f"Workspace này không chứa tài liệu công nghiệp đáng tin cậy. (Similarity: {similarity:.2f}). Hãy dùng workspace D:\\Sandbox\\MOM_WMS_QLLSSX hoặc nạp tài liệu kỹ thuật đúng.",
                        "warnings": [f"Query similarity {similarity:.2f} is below threshold 0.20 in a creative fiction workspace."],
                        "meta": {
                            "workspace_purpose": "web_novel_platform",
                            "similarity_score": round(similarity, 3),
                            "routed": routed
                        }
                    })

        result = _normalize_ask_result(run_ask(query, workspace=str(selected_workspace)), workspace_root=selected_workspace)
        if "meta" not in result:
            result["meta"] = {}
        result["meta"]["similarity_score"] = round(similarity, 3)
        result["meta"]["workspace_purpose"] = intel["workspace_purpose"]
        result["meta"]["routed"] = routed
        result["meta"]["selected_workspace"] = str(selected_workspace)
        return _response("ask", result)
    except Exception as exc:
        raise _error_response("ask", exc) from exc


def promote_drafts(payload: PromoteRequest) -> dict[str, Any]:
    try:
        workspace = _workspace_path(payload)
        if run_promote_drafts is None:
            raise HTTPException(status_code=500, detail="Promotion engine (scripts/abw_knowledge.py) not found in path")
        return _response("promote-drafts", run_promote_drafts(workspace, limit=payload.limit, dry_run=payload.dry_run))
    except Exception as exc:
        raise _error_response("promote-drafts", exc) from exc


def route_query(payload: RouteRequest) -> dict[str, Any]:
    try:
        query = str(payload.query or "").strip()
        if not query:
            raise HTTPException(status_code=400, detail="query is required")

        workspaces = payload.workspaces
        if workspaces is None:
            workspaces = list_enabled_workspaces()

        scores = []
        for ws_path in workspaces:
            ws = Path(ws_path).expanduser().resolve()
            if not ws.exists():
                continue
            intel = detect_workspace_purpose(ws, query=query)
            scores.append({
                "workspace": str(ws),
                "similarity": intel.get("similarity_score", 0.0),
                "purpose": intel.get("workspace_purpose", "unknown")
            })

        scores.sort(key=lambda x: x["similarity"], reverse=True)

        decision = "no_confident_workspace"
        best_workspace = None

        if scores:
            top = scores[0]
            if top["similarity"] >= 0.2:
                decision = "route"
                best_workspace = top["workspace"]

                # Check for ambiguity
                if len(scores) > 1:
                    second = scores[1]
                    if (top["similarity"] - second["similarity"]) < 0.1:
                        decision = "ambiguous"

                # Guard against generic terms (e.g. "Hệ thống XYZ là gì?")
                query_tokens = set(normalize_text(query))
                has_industrial_spec = any(t in query_tokens for t in DOMAIN_SPECIFIC_INDUSTRIAL)
                has_novel_spec = any(t in query_tokens for t in DOMAIN_SPECIFIC_NOVEL)
                
                if not has_industrial_spec and not has_novel_spec:
                    # Downgrade decision if similarity is decent but not overwhelming and no specific terms matched
                    if top["similarity"] < 0.6:
                        decision = "no_confident_workspace"
                        best_workspace = None

        # Cross-domain keyword guard
        query_lower = query.lower()
        has_novel = any(re.search(rf"\b{k}\b", query_lower, re.IGNORECASE) for k in NOVEL_KEYWORDS)
        has_industrial = any(re.search(rf"\b{k}\b", query_lower, re.IGNORECASE) for k in INDUSTRIAL_KEYWORDS)
        
        if has_novel and has_industrial:
            decision = "ambiguous"
            # best_workspace stays as the top one but user will see ambiguity warning

        return _response("route-query", {
            "query": query,
            "best_workspace": best_workspace,
            "scores": scores,
            "decision": decision
        })
    except Exception as exc:
        raise _error_response("route-query", exc) from exc


def list_workspaces_api() -> dict[str, Any]:
    return _response("list-workspaces", {"workspaces": load_workspaces()})


def register_workspace_api(payload: RegisterRequest) -> dict[str, Any]:
    try:
        ws = register_ws(payload.path, payload.name)
        return _response("register-workspace", {"workspace": ws})
    except Exception as exc:
        raise _error_response("register-workspace", exc) from exc


def disable_workspace_api(payload: DisableRequest) -> dict[str, Any]:
    try:
        found = disable_ws(payload.path)
        return _response("disable-workspace", {"path": payload.path, "found": found})
    except Exception as exc:
        raise _error_response("disable-workspace", exc) from exc


def promote_drafts_fastapi(payload: PromoteRequest):
    return promote_drafts(payload)


def apply_action(payload: ApplyRequest) -> dict[str, Any]:
    try:
        workspace = _workspace_path(payload)
        if payload.action == "rollback":
            if not payload.rollback_id:
                raise HTTPException(status_code=400, detail="rollback_id is required for rollback")
            data = run_rollback(workspace, payload.rollback_id, yes=payload.yes)
        else:
            if payload.action not in APPLY_ACTIONS:
                raise HTTPException(status_code=400, detail=f"unknown apply action: {payload.action}")
            data = run_apply(workspace, payload.action, yes=payload.yes)
        return _response("apply", data)
    except Exception as exc:
        raise _error_response("apply", exc) from exc


async def _json_payload(request: Request, model) -> BaseModel:
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="request body must be a JSON object")
    return model(**body)


async def _starlette_health(request: Request) -> JSONResponse:
    return JSONResponse(health())


async def _starlette_report(request: Request, command_func, model=WorkspaceRequest) -> JSONResponse:
    try:
        payload = await _json_payload(request, model)
        return JSONResponse(command_func(payload))
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc) or exc.__class__.__name__) from exc


def _build_starlette_app() -> Starlette:
    def report_endpoint(command_func, model=WorkspaceRequest):
        async def endpoint(request: Request) -> JSONResponse:
            return await _starlette_report(request, command_func, model)

        return endpoint

    return Starlette(
        routes=[
            Route("/health", _starlette_health, methods=["GET"]),
            Route("/inspect", report_endpoint(inspect), methods=["POST"]),
            Route("/gaps", report_endpoint(gaps), methods=["POST"]),
            Route("/recover-plan", report_endpoint(recover_plan), methods=["POST"]),
            Route("/recover-verify", report_endpoint(recover_verify), methods=["POST"]),
            Route("/trend", report_endpoint(trend), methods=["POST"]),
            Route("/improve", report_endpoint(improve), methods=["POST"]),
            Route("/apply", report_endpoint(apply_action, ApplyRequest), methods=["POST"]),
            Route("/ask", report_endpoint(ask, AskRequest), methods=["POST"]),
            Route("/workspace-intel", report_endpoint(workspace_intel), methods=["POST"]),
            Route("/workspace-fix", report_endpoint(workspace_fix, WorkspaceFixRequest), methods=["POST"]),
            Route("/promote-drafts", report_endpoint(promote_drafts, PromoteRequest), methods=["POST"]),
            Route("/route-query", report_endpoint(route_query, RouteRequest), methods=["POST"]),
            Route("/list-workspaces", lambda r: JSONResponse(list_workspaces_api()), methods=["GET"]),
            Route("/register-workspace", report_endpoint(register_workspace_api, RegisterRequest), methods=["POST"]),
            Route("/disable-workspace", report_endpoint(disable_workspace_api, DisableRequest), methods=["POST"]),
        ]
    )


app = _build_fastapi_app() or _build_starlette_app()
