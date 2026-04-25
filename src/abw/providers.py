from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import time
import json

from .workspace import default_config, read_workspace_config, resolve_workspace, write_workspace_config


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    kind: str
    supports_sensitive: bool
    estimated_cost_tier: int  # 1=lowest, 5=highest
    env_key: str | None = None


PROVIDER_REGISTRY: tuple[ProviderSpec, ...] = (
    ProviderSpec("claude", "cloud", supports_sensitive=False, estimated_cost_tier=4, env_key="ANTHROPIC_API_KEY"),
    ProviderSpec("openai", "cloud", supports_sensitive=False, estimated_cost_tier=3, env_key="OPENAI_API_KEY"),
    ProviderSpec("gemini", "cloud", supports_sensitive=False, estimated_cost_tier=2, env_key="GEMINI_API_KEY"),
    ProviderSpec("ollama", "local", supports_sensitive=True, estimated_cost_tier=1, env_key="OLLAMA_HOST"),
    ProviderSpec("vllm", "local", supports_sensitive=True, estimated_cost_tier=1, env_key="VLLM_BASE_URL"),
    ProviderSpec("mock", "internal", supports_sensitive=True, estimated_cost_tier=1, env_key=None),
)

_REGISTRY_BY_NAME = {item.name: item for item in PROVIDER_REGISTRY}
_ALL_PROVIDER_NAMES = [item.name for item in PROVIDER_REGISTRY]

_DEFAULT_ROUTING = {
    "ask_mode": "local",
    "cost_mode": "balanced",
    "default": "mock",
    "fallback_chain": _ALL_PROVIDER_NAMES,
    "task_routes": {
        "general": ["openai", "claude", "gemini", "vllm", "ollama", "mock"],
        "coding": ["openai", "claude", "vllm", "ollama", "gemini", "mock"],
        "analysis": ["claude", "openai", "gemini", "vllm", "ollama", "mock"],
        "summarization": ["gemini", "openai", "claude", "vllm", "ollama", "mock"],
    },
    "sensitivity_routes": {
        "normal": _ALL_PROVIDER_NAMES,
        "high": ["vllm", "ollama", "mock"],
    },
    "cost_routes": {
        "balanced": _ALL_PROVIDER_NAMES,
        "low": ["mock", "ollama", "vllm", "gemini", "openai", "claude"],
        "quality": ["claude", "openai", "gemini", "vllm", "ollama", "mock"],
    },
}


def _valid_provider(name: str) -> bool:
    return str(name or "").strip().lower() in _REGISTRY_BY_NAME


def _sanitize_chain(chain: list[str] | tuple[str, ...] | None, *, fallback: list[str]) -> list[str]:
    ordered: list[str] = []
    for item in list(chain or []):
        name = str(item or "").strip().lower()
        if name in _REGISTRY_BY_NAME and name not in ordered:
            ordered.append(name)
    if not ordered:
        ordered = list(fallback)
    return ordered


def _workspace_settings(workspace: str | Path) -> tuple[Path, dict]:
    root = resolve_workspace(workspace)
    config, status = read_workspace_config(root)
    payload = dict(config) if status == "ok" and isinstance(config, dict) else {}
    providers = payload.get("providers")
    if not isinstance(providers, dict):
        providers = {}
    return root, providers


def _effective_settings(workspace: str | Path) -> dict:
    _root, providers = _workspace_settings(workspace)
    task_routes = dict(_DEFAULT_ROUTING["task_routes"])
    task_routes.update(providers.get("task_routes") or {})
    sensitivity_routes = dict(_DEFAULT_ROUTING["sensitivity_routes"])
    sensitivity_routes.update(providers.get("sensitivity_routes") or {})
    cost_routes = dict(_DEFAULT_ROUTING["cost_routes"])
    cost_routes.update(providers.get("cost_routes") or {})
    default_name = str(providers.get("default") or _DEFAULT_ROUTING["default"]).strip().lower()
    if default_name not in _REGISTRY_BY_NAME:
        default_name = _DEFAULT_ROUTING["default"]
    fallback_chain = _sanitize_chain(
        providers.get("fallback_chain"),
        fallback=list(_DEFAULT_ROUTING["fallback_chain"]),
    )
    ask_mode = str(providers.get("ask_mode") or _DEFAULT_ROUTING["ask_mode"]).strip().lower()
    if ask_mode not in {"local", "ai", "hybrid"}:
        ask_mode = _DEFAULT_ROUTING["ask_mode"]
    cost_mode = str(providers.get("cost_mode") or _DEFAULT_ROUTING["cost_mode"]).strip().lower()
    if cost_mode not in settings_cost_modes():
        cost_mode = _DEFAULT_ROUTING["cost_mode"]
    return {
        "ask_mode": ask_mode,
        "cost_mode": cost_mode,
        "default": default_name,
        "fallback_chain": fallback_chain,
        "task_routes": task_routes,
        "sensitivity_routes": sensitivity_routes,
        "cost_routes": cost_routes,
    }


def _health_status(spec: ProviderSpec) -> dict:
    if spec.name == "mock":
        return {"status": "healthy", "reason": "mock provider available"}

    if spec.kind == "cloud":
        if spec.env_key and os.environ.get(spec.env_key):
            return {"status": "healthy", "reason": f"credentials found via {spec.env_key}"}
        return {"status": "degraded", "reason": f"missing credentials ({spec.env_key})"}

    # local providers
    if spec.name == "ollama":
        host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
        return {"status": "healthy", "reason": f"configured local endpoint {host}"}
    if spec.name == "vllm":
        endpoint = os.environ.get("VLLM_BASE_URL", "http://127.0.0.1:8000")
        return {"status": "healthy", "reason": f"configured local endpoint {endpoint}"}
    return {"status": "unknown", "reason": "health probe unavailable"}


def list_providers(workspace: str | Path) -> dict:
    settings = _effective_settings(workspace)
    rows = []
    for spec in PROVIDER_REGISTRY:
        health = _health_status(spec)
        rows.append(
            {
                "name": spec.name,
                "kind": spec.kind,
                "supports_sensitive": spec.supports_sensitive,
                "estimated_cost_tier": spec.estimated_cost_tier,
                "health": health["status"],
                "is_default": spec.name == settings["default"],
            }
        )
    return {"default": settings["default"], "ask_mode": settings["ask_mode"], "providers": rows}


def run_provider_health_checks(workspace: str | Path) -> dict:
    settings = _effective_settings(workspace)
    rows = []
    healthy_names: list[str] = []
    for spec in PROVIDER_REGISTRY:
        health = _health_status(spec)
        if health["status"] == "healthy":
            healthy_names.append(spec.name)
        rows.append({"name": spec.name, **health})
    return {"default": settings["default"], "ask_mode": settings["ask_mode"], "healthy": healthy_names, "results": rows}


def set_default_provider(workspace: str | Path, provider_name: str) -> dict:
    candidate = str(provider_name or "").strip().lower()
    if not _valid_provider(candidate):
        raise ValueError(f"Unknown provider: {provider_name}")

    root = resolve_workspace(workspace)
    config, status = read_workspace_config(root)
    payload = dict(config) if status == "ok" and isinstance(config, dict) else default_config(root)
    providers = payload.get("providers")
    if not isinstance(providers, dict):
        providers = {}
    providers["default"] = candidate
    existing_chain = _sanitize_chain(providers.get("fallback_chain"), fallback=list(_DEFAULT_ROUTING["fallback_chain"]))
    if candidate in existing_chain:
        existing_chain = [candidate] + [name for name in existing_chain if name != candidate]
    else:
        existing_chain = [candidate] + existing_chain
    providers["fallback_chain"] = existing_chain
    payload["providers"] = providers
    write_workspace_config(root, payload)
    return {"default": candidate, "fallback_chain": existing_chain}


def set_ask_mode(workspace: str | Path, mode: str) -> dict:
    normalized = str(mode or "").strip().lower()
    if normalized not in {"local", "ai", "hybrid"}:
        raise ValueError("Unsupported ask mode. Use: local | ai | hybrid")
    root = resolve_workspace(workspace)
    config, status = read_workspace_config(root)
    payload = dict(config) if status == "ok" and isinstance(config, dict) else default_config(root)
    providers = payload.get("providers")
    if not isinstance(providers, dict):
        providers = {}
    providers["ask_mode"] = normalized
    payload["providers"] = providers
    write_workspace_config(root, payload)
    return {"ask_mode": normalized}


def explain_route(
    workspace: str | Path,
    *,
    task: str = "general",
    sensitivity: str = "normal",
    cost_mode: str = "balanced",
) -> dict:
    settings = _effective_settings(workspace)
    task_key = str(task or "general").strip().lower()
    if task_key not in settings["task_routes"]:
        task_key = "general"
    sensitivity_key = str(sensitivity or "normal").strip().lower()
    if sensitivity_key not in settings["sensitivity_routes"]:
        sensitivity_key = "normal"
    cost_key = str(cost_mode or "balanced").strip().lower()
    if cost_key not in settings["cost_routes"]:
        cost_key = "balanced"

    by_task = _sanitize_chain(settings["task_routes"].get(task_key), fallback=_ALL_PROVIDER_NAMES)
    by_sensitivity = set(_sanitize_chain(settings["sensitivity_routes"].get(sensitivity_key), fallback=_ALL_PROVIDER_NAMES))
    by_cost = _sanitize_chain(settings["cost_routes"].get(cost_key), fallback=_ALL_PROVIDER_NAMES)
    by_fallback = _sanitize_chain(settings["fallback_chain"], fallback=list(_DEFAULT_ROUTING["fallback_chain"]))

    candidates = [name for name in by_task if name in by_sensitivity]
    if cost_key != "balanced":
        rank = {name: idx for idx, name in enumerate(by_cost)}
        candidates = sorted(candidates, key=lambda name: rank.get(name, 999))

    # apply fallback chain as final tie-breaker / governance order
    fallback_rank = {name: idx for idx, name in enumerate(by_fallback)}
    candidates = sorted(candidates, key=lambda name: fallback_rank.get(name, 999))

    tested = run_provider_health_checks(workspace)
    health_by_name = {row["name"]: row["status"] for row in tested["results"]}
    selected = ""
    selected_reason = "no healthy provider in candidate set"
    for candidate in candidates:
        if health_by_name.get(candidate) == "healthy":
            selected = candidate
            selected_reason = "first healthy provider after task/sensitivity/cost/fallback filtering"
            break
    if not selected:
        default_name = settings["default"]
        selected = default_name
        selected_reason = "fallback to configured default provider"

    return {
        "task": task_key,
        "sensitivity": sensitivity_key,
        "cost_mode": cost_key,
        "default": settings["default"],
        "candidates": candidates,
        "selected": selected,
        "selected_reason": selected_reason,
        "healthy": tested["healthy"],
    }


def settings_cost_modes() -> set[str]:
    return {"balanced", "low", "quality"}


def _telemetry_path(workspace: str | Path) -> Path:
    root = resolve_workspace(workspace)
    return root / ".brain" / "provider_telemetry.jsonl"


def _append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _estimate_tokens(text: str) -> int:
    words = len(str(text or "").split())
    return max(1, int(words * 1.3))


def _infer_task_kind(task: str) -> str:
    lowered = str(task or "").lower()
    if any(token in lowered for token in {"refactor", "bug", "fix", "function", "code", "test", "implement"}):
        return "coding"
    if any(token in lowered for token in {"explain", "why", "compare", "tradeoff", "root cause", "rca"}):
        return "analysis"
    if any(token in lowered for token in {"summary", "summarize", "tl;dr"}):
        return "summarization"
    return "general"


def _infer_sensitivity(task: str) -> str:
    lowered = str(task or "").lower()
    sensitive_markers = {"token", "secret", "password", "credential", "pii", "confidential", "private key"}
    return "high" if any(marker in lowered for marker in sensitive_markers) else "normal"


def _invoke_provider(provider: ProviderSpec, prompt: str) -> dict:
    forced_failures = {name.strip().lower() for name in str(os.environ.get("ABW_PROVIDER_FORCE_FAIL", "")).split(",") if name.strip()}
    if provider.name in forced_failures:
        raise RuntimeError("forced failure for test path")

    health = _health_status(provider)
    if health["status"] != "healthy":
        raise RuntimeError(health["reason"])

    text = (
        f"[provider={provider.name}] draft response for task: "
        f"{str(prompt or '').strip()[:220]}"
    )
    return {"text": text, "token_estimate": _estimate_tokens(text)}


def execute_provider_chain(
    workspace: str | Path,
    *,
    prompt: str,
    task: str = "general",
    sensitivity: str = "normal",
    cost_mode: str = "balanced",
) -> dict:
    route = explain_route(workspace, task=task, sensitivity=sensitivity, cost_mode=cost_mode)
    telemetry_path = _telemetry_path(workspace)
    attempts: list[dict] = []
    fail_count = 0
    for provider_name in route["candidates"]:
        spec = _REGISTRY_BY_NAME[provider_name]
        started = time.perf_counter()
        try:
            response = _invoke_provider(spec, prompt)
            latency_ms = int((time.perf_counter() - started) * 1000)
            attempt = {
                "provider": provider_name,
                "status": "success",
                "latency_ms": latency_ms,
                "token_estimate": int(response["token_estimate"]),
                "fail_count": fail_count,
            }
            attempts.append(attempt)
            _append_jsonl(telemetry_path, attempt)
            return {
                "status": "success",
                "provider": provider_name,
                "draft": str(response["text"]),
                "latency_ms": latency_ms,
                "token_estimate": int(response["token_estimate"]),
                "fail_count": fail_count,
                "attempts": attempts,
                "route": route,
            }
        except Exception as exc:  # noqa: BLE001
            fail_count += 1
            latency_ms = int((time.perf_counter() - started) * 1000)
            attempt = {
                "provider": provider_name,
                "status": "failed",
                "reason": str(exc),
                "latency_ms": latency_ms,
                "token_estimate": 0,
                "fail_count": fail_count,
            }
            attempts.append(attempt)
            _append_jsonl(telemetry_path, attempt)

    return {
        "status": "failed",
        "provider": "",
        "draft": "",
        "latency_ms": 0,
        "token_estimate": 0,
        "fail_count": fail_count,
        "attempts": attempts,
        "route": route,
    }


def prepare_ask_task(workspace: str | Path, user_task: str) -> dict:
    settings = _effective_settings(workspace)
    ask_mode = settings["ask_mode"]
    task_kind = _infer_task_kind(user_task)
    sensitivity = _infer_sensitivity(user_task)
    cost_mode = settings.get("cost_mode") or "balanced"

    provider = {
        "mode": ask_mode,
        "task_kind": task_kind,
        "sensitivity": sensitivity,
        "cost_mode": cost_mode,
        "used": False,
    }

    if ask_mode == "local":
        return {"task": user_task, "provider": provider}

    execution = execute_provider_chain(
        workspace,
        prompt=user_task,
        task=task_kind,
        sensitivity=sensitivity,
        cost_mode=cost_mode,
    )
    provider.update(
        {
            "used": execution["status"] == "success",
            "selected": execution.get("provider"),
            "latency_ms": execution.get("latency_ms", 0),
            "token_estimate": execution.get("token_estimate", 0),
            "fail_count": execution.get("fail_count", 0),
            "attempts": execution.get("attempts", []),
        }
    )

    if execution["status"] != "success":
        provider["fallback"] = "local_runner"
        return {"task": user_task, "provider": provider}

    draft = execution["draft"]
    if ask_mode == "ai":
        effective_task = (
            f"{user_task}\n\n"
            "[provider_draft]\n"
            f"{draft}\n"
            "[/provider_draft]\n"
            "Use provider_draft as primary context and answer directly."
        )
    else:
        effective_task = (
            f"{user_task}\n\n"
            "[provider_draft]\n"
            f"{draft}\n"
            "[/provider_draft]\n"
            "Use provider_draft as supplemental context, but prefer grounded local ABW logic."
        )

    return {"task": effective_task, "provider": provider}


def provider_state_summary(workspace: str | Path) -> dict:
    settings = _effective_settings(workspace)
    health = run_provider_health_checks(workspace)
    return {
        "ask_mode": settings["ask_mode"],
        "default": settings["default"],
        "healthy_count": len(health["healthy"]),
        "healthy": list(health["healthy"]),
        "fallback_chain": list(settings["fallback_chain"]),
        "cost_mode": settings["cost_mode"],
    }


def render_provider_list(report: dict) -> str:
    lines = ["ABW Providers", ""]
    lines.append(f"default: {report['default']}")
    lines.append(f"ask_mode: {report.get('ask_mode', 'local')}")
    lines.append("")
    for row in report["providers"]:
        marker = "*" if row["is_default"] else "-"
        lines.append(
            f"{marker} {row['name']} [{row['kind']}] "
            f"health={row['health']} sensitive={'yes' if row['supports_sensitive'] else 'no'} "
            f"cost_tier={row['estimated_cost_tier']}"
        )
    return "\n".join(lines)


def render_provider_test(report: dict) -> str:
    lines = ["ABW Provider Health", ""]
    lines.append(f"default: {report['default']}")
    lines.append(f"ask_mode: {report.get('ask_mode', 'local')}")
    lines.append(f"healthy: {', '.join(report['healthy']) if report['healthy'] else '(none)'}")
    lines.append("")
    for row in report["results"]:
        lines.append(f"- {row['name']}: {row['status']} ({row['reason']})")
    return "\n".join(lines)


def render_provider_route(report: dict) -> str:
    lines = ["ABW Provider Route", ""]
    lines.append(f"task: {report['task']}")
    lines.append(f"sensitivity: {report['sensitivity']}")
    lines.append(f"cost_mode: {report['cost_mode']}")
    lines.append(f"default: {report['default']}")
    lines.append(f"candidates: {', '.join(report['candidates']) if report['candidates'] else '(none)'}")
    lines.append(f"selected: {report['selected']}")
    lines.append(f"reason: {report['selected_reason']}")
    return "\n".join(lines)
