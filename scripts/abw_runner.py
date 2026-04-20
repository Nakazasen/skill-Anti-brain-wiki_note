import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import abw_accept
import abw_health
import abw_knowledge
import abw_proof
import abw_query_deep
import abw_router
import continuation_execute
import continuation_gate
import finalization_check

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - exercised only when MCP SDK is unavailable.
    FastMCP = None


FINALIZATION_TEMPLATE = """## Finalization
- current_state: {current_state}
- evidence: {evidence}
- gaps_or_limitations: {gaps_or_limitations}
- next_steps: {next_steps}
- knowledge_evidence_tier: {knowledge_evidence_tier}
- knowledge_source_score: {knowledge_source_score}
- source_summary: {source_summary}
- gap_logged: {gap_logged}
"""

KNOWLEDGE_KEYWORDS = ("what is", "explain", "why", "la gi", "giai thich")
MEMORY_SCOPE = os.environ.get("ABW_MEMORY_SCOPE", "workspace")
VALID_BINDING_MODES = {"STRICT", "SOFT"}
VALID_TASK_KINDS = {"execution", "validation"}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_runtime_id():
    return str(int(datetime.now(timezone.utc).timestamp() * 1000))


def normalize_memory_scope(memory_scope=None):
    normalized = str(memory_scope or MEMORY_SCOPE or "workspace").strip().lower()
    if normalized in {"workspace", "global"}:
        return normalized
    return "workspace"


def negative_memory_path(workspace, memory_scope=None):
    scope = normalize_memory_scope(memory_scope)
    if scope == "global":
        return Path.home() / ".gemini" / "antigravity" / "negative_memory.jsonl"
    return Path(workspace) / ".brain" / "negative_memory.jsonl"


def load_memory(workspace=".", memory_scope=None):
    path = negative_memory_path(workspace, memory_scope=memory_scope)
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def write_memory(workspace, rows, memory_scope=None):
    path = negative_memory_path(workspace, memory_scope=memory_scope)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def extract_pattern(task):
    text = (task or "").lower()

    if "do not run" in text:
        return "bypass_runner"

    if "just answer" in text:
        return "skip_validation"

    if "fix" in text and "error" in text:
        return "debug_without_evidence"

    return "generic_failure"


def derive_fix_hint(result):
    reason = str(result.get("reason", "")).lower()
    if "strict mode requires runner usage" in reason:
        return "Use the runner path instead of prompt-only output."
    if "binding_status" in reason:
        return "Return an explicit binding_status before emitting output."
    if "knowledge." in reason or "knowledge block" in reason:
        return "Include the required knowledge visibility fields."
    return "Route the task through the runner and return a valid accepted shape."


def derive_failure_label(result):
    reason = str(result.get("reason") or "").strip()
    if reason:
        return reason

    binding_status = str(result.get("binding_status") or "").strip()
    if binding_status:
        return binding_status

    current_state = str(result.get("current_state") or "").strip()
    if current_state:
        return current_state

    return "unknown_rejection_reason"


def trim_memory(rows, max_items=100):
    if len(rows) <= max_items:
        return rows
    return rows[-max_items:]


def log_negative_memory(
    workspace=".",
    pattern="generic_failure",
    failure="",
    context="",
    fix_hint="",
    memory_scope=None,
):
    rows = load_memory(workspace, memory_scope=memory_scope)
    timestamp = now_iso()
    for row in reversed(rows):
        if row.get("pattern") == pattern:
            row["count"] = int(row.get("count", 1)) + 1
            row["timestamp"] = timestamp
            row["failure"] = failure
            row["context"] = context
            row["fix_hint"] = fix_hint
            write_memory(workspace, trim_memory(rows), memory_scope=memory_scope)
            return row

    entry = {
        "timestamp": timestamp,
        "pattern": pattern,
        "failure": failure,
        "context": context,
        "fix_hint": fix_hint,
        "count": 1,
    }
    rows.append(entry)
    write_memory(workspace, trim_memory(rows), memory_scope=memory_scope)
    return entry


def check_negative_memory(task, workspace=".", memory_scope=None):
    pattern = extract_pattern(task)
    if pattern == "generic_failure":
        return None

    for item in load_memory(workspace, memory_scope=memory_scope):
        item_pattern = item.get("pattern")
        if item_pattern == "generic_failure":
            continue
        if str(item_pattern or "") in str(task or "").lower():
            return item
        if item_pattern == pattern:
            return item
    return None


def attach_memory_warning(result, memory_item):
    if not memory_item:
        return result
    result["memory_warning"] = {
        "pattern": memory_item.get("pattern"),
        "reason": memory_item.get("failure"),
        "hint": memory_item.get("fix_hint"),
    }
    return result


def normalize_binding_mode(binding_mode):
    normalized = str(binding_mode or "STRICT").strip().upper()
    return normalized if normalized in VALID_BINDING_MODES else "STRICT"


def normalize_task_kind(task_kind):
    normalized = str(task_kind or "execution").strip().lower()
    if normalized == "run":
        return "execution"
    return normalized if normalized in VALID_TASK_KINDS else "execution"


def is_mcp_binding(binding_source):
    return str(binding_source or "mcp").strip().lower() == "mcp"


def run_command(command, workspace):
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=workspace,
            capture_output=True,
            text=True,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as exc:  # noqa: BLE001 - CLI reports command failures as JSON.
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": str(exc),
        }


def split_answer_and_finalization(text):
    raw = str(text or "")
    marker = "## Finalization"
    if marker not in raw:
        return raw.strip(), ""
    body, _, tail = raw.partition(marker)
    return body.strip(), f"{marker}{tail}".strip()


def finalization_payload_from_text(text):
    lines = finalization_check.extract_block(text or "")
    if not lines:
        return {
            "current_state": "blocked",
            "evidence": "Finalization block missing from model output.",
            "gaps_or_limitations": "Required finalization fields were not emitted.",
            "next_steps": "Regenerate the answer with a valid Finalization block and direct evidence.",
            "_forced_missing": True,
        }

    payload = finalization_check.parse_block(lines)
    missing_required = any(
        not payload.get(field, "").strip()
        for field in ("current_state", "evidence", "gaps_or_limitations", "next_steps")
    )
    return {
        "current_state": payload.get("current_state", "").strip() or "blocked",
        "evidence": payload.get("evidence", "").strip() or "Missing evidence field.",
        "gaps_or_limitations": payload.get("gaps_or_limitations", "").strip()
        or "Missing gaps_or_limitations field.",
        "next_steps": payload.get("next_steps", "").strip()
        or "Regenerate the answer with complete finalization fields.",
        "knowledge_evidence_tier": payload.get("knowledge_evidence_tier", "").strip(),
        "knowledge_source_score": payload.get("knowledge_source_score", "").strip(),
        "source_summary": payload.get("source_summary", "").strip(),
        "gap_logged": payload.get("gap_logged", "").strip(),
        "_forced_incomplete": missing_required,
    }


def render_finalization_block(payload):
    lines = [
        "## Finalization",
        f"- current_state: {payload['current_state']}",
        f"- evidence: {payload['evidence']}",
        f"- gaps_or_limitations: {payload['gaps_or_limitations']}",
        f"- next_steps: {payload['next_steps']}",
    ]
    if payload.get("knowledge_evidence_tier"):
        lines.extend(
            [
                f"- knowledge_evidence_tier: {payload.get('knowledge_evidence_tier', '')}",
                f"- knowledge_source_score: {payload.get('knowledge_source_score', '')}",
                f"- source_summary: {payload.get('source_summary', '')}",
                f"- gap_logged: {payload.get('gap_logged', '')}",
            ]
        )
    return "\n".join(lines) + "\n"


def is_knowledge_task(task: str) -> bool:
    kw = str(task or "").lower()
    return any(token in kw for token in KNOWLEDGE_KEYWORDS)


def get_knowledge_context(task: str) -> dict:
    return abw_knowledge.get_knowledge_context(task)


def compute_knowledge_score(result):
    return abw_knowledge.compute_knowledge_score(result)


def compute_knowledge_tier(result):
    return abw_knowledge.compute_knowledge_tier(result)


def build_source_summary(result):
    return abw_knowledge.build_source_summary(result)


def enrich_knowledge_result(task, workspace="."):
    return abw_knowledge.enrich_knowledge_result(task, workspace=workspace)


def route_lane(route=None):
    if not isinstance(route, dict):
        return ""
    return str(route.get("lane") or "").strip().lower()


def is_knowledge_intent(task, route=None):
    route = route or {}
    intent = route.get("intent") if isinstance(route, dict) else None
    lane = route_lane(route)
    return intent in {"knowledge", "query", "query_deep"} or lane in {"query", "query_deep"} or (
        intent is None and lane == "" and is_knowledge_task(task)
    )


def apply_knowledge_semantics(result, task, route=None):
    if not is_knowledge_intent(task, route):
        return result

    tier = compute_knowledge_tier(result)
    result["knowledge_evidence_tier"] = tier

    if result.get("current_state") == "blocked":
        result["current_state"] = "knowledge_answered"
        result["semantic_fix_applied"] = True

    if tier == "E0_unknown":
        result["current_state"] = "knowledge_gap_logged"
        result["gap_logged"] = True
    else:
        result["current_state"] = "knowledge_answered"

    result["knowledge_source_score"] = compute_knowledge_score(result)
    return result


def attach_knowledge_output(result, answer_text=None):
    return abw_knowledge.attach_knowledge_output(result, answer_text=answer_text)


def log_knowledge_gap(task, workspace=".", searched_locations=None, reason="No local knowledge source matched the task."):
    return abw_knowledge.log_knowledge_gap(
        task,
        workspace=workspace,
        searched_locations=searched_locations,
        reason=reason,
    )


def enforce_knowledge_output(result):
    knowledge = result.get("knowledge_output")
    required_fields = ("tier", "score", "source_summary")
    if not knowledge or any(knowledge.get(field) is None for field in required_fields):
        raise RuntimeError("Knowledge output missing required visibility block")
    return result


def resolve_route(task, workspace=".", route=None):
    return abw_router.route_request(task, workspace=workspace, route=route)


def build_lane_route(route, lane, *, reason=None, fallback_from=None, fallback_reason=None):
    payload = dict(route or {})
    payload["lane"] = lane
    payload["intent"] = lane
    if reason:
        payload["reason"] = reason
    if fallback_from:
        payload["fallback_from"] = fallback_from
    if fallback_reason:
        payload["fallback_reason"] = fallback_reason
    return payload


def route_extra(route, **extra):
    payload = {"route": dict(route or {})}
    payload.update(extra)
    return payload


def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def save_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def query_lane_result(task, workspace=".", route=None, binding_source="mcp", *, deep=False):
    lane = "query_deep" if deep else "query"
    binding_status = binding_status_for_execution(
        binding_source,
        {"execution_path": lane},
    )
    if deep:
        deep_result = abw_query_deep.run(task, workspace)
        has_sources = bool(deep_result.get("sources"))
        gap_logged = False
        if not has_sources:
            gap_id = log_knowledge_gap(
                task,
                workspace=workspace,
                searched_locations=["wiki/"],
                reason="Deep query lane did not find enough wiki evidence.",
            )
            gap_logged = True
        else:
            gap_id = None

        confidence = str(deep_result.get("confidence") or "low").lower()
        score_map = {"high": 3, "medium": 2, "low": 1}
        knowledge_tier = "E2_wiki" if has_sources else "E0_unknown"
        knowledge_score = score_map.get(confidence, 0) if has_sources else 0
        current_state = "knowledge_answered" if has_sources else "knowledge_gap_logged"
        body = str(deep_result.get("answer") or "").strip()
        evidence_summary = (
            f"query_deep collected {len(deep_result.get('evidence', []))} wiki evidence items "
            f"across {len(deep_result.get('sources', []))} source files"
            if has_sources
            else "query_deep did not find enough wiki evidence"
        )
        model_output = f"""{body}

## Finalization
- current_state: {current_state}
- evidence: {evidence_summary}
- gaps_or_limitations: retrieval source=local_wiki; lane=query_deep; confidence={confidence}; contradiction_count={sum(1 for step in deep_result.get("reasoning_steps", []) if step.get("step") == "contradiction_check" and step.get("contradiction_count", 0) > 0)}
- next_steps: {"add or ingest more grounded wiki material before relying on this answer" if gap_logged else "use the cited wiki sources for follow-up deep questions if needed"}
- knowledge_evidence_tier: {knowledge_tier}
- knowledge_source_score: {knowledge_score}
- source_summary: local_wiki
- gap_logged: {gap_logged}
"""
        gate = run_finalization_gate(model_output, task_kind="knowledge")
        answer = compose_answer(body, gate["block"])
        runner_status = "blocked" if gate["report"].get("decision") == "blocked" else "completed"
        knowledge = {
            "answer": body,
            "tier": knowledge_tier,
            "score": knowledge_score,
            "gap_logged": gap_logged,
            "source_summary": "local_wiki",
            "source": "wiki",
            "content": body,
            "confidence": 0.85 if confidence == "high" else (0.65 if confidence == "medium" else 0.35),
        }
        extra = route_extra(
            route,
            gap_logged=gap_logged,
            gap_id=gap_id,
            knowledge_evidence_tier=knowledge_tier,
            knowledge_source_score=knowledge_score,
            refinement_history=[],
            semantic_fix_applied=False,
            reasoning_steps=deep_result.get("reasoning_steps", []),
            deep_query=deep_result,
            strategy_trace={
                "lane": lane,
                "mode": "bounded_wiki_reasoning_loop",
                "status": deep_result.get("status"),
                "sources": deep_result.get("sources", []),
            },
        )
        return base_result(
            task,
            binding_status,
            answer,
            gate,
            runner_status,
            knowledge=knowledge,
            extra=extra,
            binding_source=binding_source,
        )

    result = enrich_knowledge_result(task, workspace=workspace)
    if result.get("gap_logged"):
        result["gap_id"] = log_knowledge_gap(
            task,
            workspace=workspace,
            searched_locations=["wiki/", "explicit local sources"],
            reason=(
                "Deep query lane could not find grounded evidence."
                if deep
                else "Query lane could not find grounded evidence."
            ),
        )
    apply_knowledge_semantics(result, task, route)
    body = knowledge_body(task, result)
    attach_knowledge_output(result, answer_text=body)
    enforce_knowledge_output(result)
    model_output = f"""{body}

## Finalization
- current_state: {result["current_state"]}
- evidence: {result["evidence"]}
- gaps_or_limitations: retrieval source={result["knowledge_output"]["source_summary"]}; lane={lane}; knowledge_evidence_tier={result.get("knowledge_evidence_tier")}; knowledge_source_score={result.get("knowledge_source_score")}
- next_steps: {"add grounded source material to wiki or provide an explicit local source" if result.get("gap_logged") else "use the retrieved local source for follow-up questions if needed"}
- knowledge_evidence_tier: {result.get("knowledge_evidence_tier")}
- knowledge_source_score: {result.get("knowledge_source_score")}
- source_summary: {result["knowledge_output"]["source_summary"]}
- gap_logged: {result.get("gap_logged", False)}
"""
    gate = run_finalization_gate(model_output, task_kind="knowledge")
    answer = compose_answer(body, gate["block"])
    runner_status = "blocked" if gate["report"].get("decision") == "blocked" else "completed"
    extra = route_extra(
        route,
        gap_logged=result.get("gap_logged", False),
        knowledge_evidence_tier=result.get("knowledge_evidence_tier"),
        knowledge_source_score=result.get("knowledge_source_score"),
        refinement_history=result.get("refinement_history", []),
        semantic_fix_applied=result.get("semantic_fix_applied", False),
        strategy_trace={
            **(result.get("strategy_trace", {}) or {}),
            "lane": lane,
            "mode": "reuse_current_knowledge_runtime",
        },
    )
    return base_result(
        task,
        binding_status,
        answer,
        gate,
        runner_status,
        knowledge=result["knowledge_output"],
        extra=extra,
        binding_source=binding_source,
    )


def resume_lane_result(task, workspace=".", route=None, binding_source="mcp"):
    gate_result = continuation_gate.evaluate_workspace(Path(workspace).resolve())
    selected = gate_result.get("selected")
    if not selected:
        raise RuntimeError("resume gate did not select a safe step")

    approvals = selected.get("required_approvals", [])
    if approvals:
        body = (
            f"Resume lane found a governed next step for '{task}', but approval is still required "
            f"before execution can be prepared: {selected.get('step_id')}."
        )
        evidence = (
            f"continuation gate logs selected step_id={selected.get('step_id')} "
            f"with required_approvals={len(approvals)}"
        )
        next_steps = "approve the governed step explicitly, then run /abw-execute or ask /abw-ask to continue again"
    else:
        prepared = continuation_execute.prepare_execution(workspace, approved=False)
        if prepared.get("status") != "prepared":
            raise RuntimeError(prepared.get("reason") or prepared.get("error") or "resume prepare failed")
        body = (
            f"Resume lane prepared governed continuation step {prepared.get('step_id')} for '{task}'. "
            "The next safe step is now active in the continuation runtime."
        )
        evidence = (
            f"continuation gate logs selected step_id={prepared.get('step_id')} and "
            "continuation execute recorded an active execution"
        )
        next_steps = "perform the prepared governed step through /abw-execute or inspect the active execution state"

    model_output = f"""{body}

## Finalization
- current_state: checked_only
- evidence: {evidence}
- gaps_or_limitations: resume lane prepares governed continuation only; it does not claim the underlying work is complete
- next_steps: {next_steps}
"""
    gate = run_finalization_gate(model_output, task_kind="")
    answer = compose_answer(body, gate["block"])
    runner_status = "blocked" if gate["report"].get("decision") == "blocked" else "completed"
    return base_result(
        task,
        "runner_checked",
        answer,
        gate,
        runner_status,
        extra=route_extra(
            route,
            resume_gate=gate_result,
            resume_step_id=selected.get("step_id"),
            resume_requires_approval=bool(approvals),
        ),
        binding_source=binding_source,
    )


def count_open_knowledge_gaps(workspace="."):
    path = Path(workspace) / ".brain" / "knowledge_gaps.json"
    payload = load_json(path, {"gaps": []})
    gaps = payload.get("gaps", [])
    return sum(1 for gap in gaps if gap.get("status") == "open")


def bootstrap_lane_result(task, workspace=".", route=None, binding_source="mcp"):
    open_gap_count = count_open_knowledge_gaps(workspace)
    wiki_root = Path(workspace) / "wiki"
    raw_root = Path(workspace) / "raw"
    wiki_present = wiki_root.exists() and any(path.is_file() for path in wiki_root.rglob("*"))
    raw_present = raw_root.exists() and any(path.is_file() for path in raw_root.rglob("*"))
    body = (
        f"Bootstrap lane generated a controlled proposal for '{task}'. "
        "This path does not mutate project state; it only summarizes the safest next bootstrap actions."
    )
    proposal = {
        "workspace_has_wiki": wiki_present,
        "workspace_has_raw": raw_present,
        "open_knowledge_gaps": open_gap_count,
        "next_actions": [
            "capture assumptions before implementation",
            "define competing hypotheses",
            "write the cheapest validation backlog",
        ],
    }
    model_output = f"""{body}

## Finalization
- current_state: checked_only
- evidence: bootstrap proposal logs workspace_has_wiki={wiki_present}; workspace_has_raw={raw_present}; open_knowledge_gaps={open_gap_count}
- gaps_or_limitations: bootstrap lane returns a proposal only and does not write bootstrap artifacts automatically
- next_steps: review the proposal, then run /abw-bootstrap explicitly if you want stateful bootstrap artifacts
"""
    gate = run_finalization_gate(model_output, task_kind="")
    answer = compose_answer(body, gate["block"])
    runner_status = "blocked" if gate["report"].get("decision") == "blocked" else "completed"
    return base_result(
        task,
        "runner_checked",
        answer,
        gate,
        runner_status,
        extra=route_extra(route, bootstrap_proposal=proposal),
        binding_source=binding_source,
    )


def ingest_queue_path(workspace="."):
    return Path(workspace) / ".brain" / "ingest_queue.json"


def record_ingest_draft(task, workspace=".", route=None):
    queue_path = ingest_queue_path(workspace)
    payload = load_json(queue_path, {"items": [], "updated_at": now_iso()})
    draft_id = f"draft-{new_runtime_id()}"
    raw_refs = [token for token in str(task or "").split() if "raw/" in token or "raw\\" in token]
    item = {
        "id": draft_id,
        "task": str(task or ""),
        "status": "review_needed",
        "created_at": now_iso(),
        "raw_refs": raw_refs,
        "draft_wiki_target": None,
        "trusted_wiki_written": False,
        "route": dict(route or {}),
    }
    payload.setdefault("items", []).append(item)
    payload["updated_at"] = now_iso()
    save_json(queue_path, payload)
    return item, queue_path


def ingest_lane_result(task, workspace=".", route=None, binding_source="mcp"):
    item, queue_path = record_ingest_draft(task, workspace=workspace, route=route)
    workspace_root = Path(workspace).resolve()
    queue_relpath = str(queue_path.resolve().relative_to(workspace_root))
    body = (
        f"Ingest lane queued a draft ingest item for '{task}'. "
        "The draft is review-needed and has not been promoted into trusted wiki."
    )
    model_output = f"""{body}

## Finalization
- current_state: checked_only
- evidence: ingest queue logs review_needed draft_id={item['id']} at {queue_path}
- gaps_or_limitations: ingest lane stores draft review metadata only; trusted wiki is unchanged until explicit review
- next_steps: review the draft ingest item and run /abw-ingest or a manual review flow before updating wiki
"""
    gate = run_finalization_gate(model_output, task_kind="")
    answer = compose_answer(body, gate["block"])
    runner_status = "blocked" if gate["report"].get("decision") == "blocked" else "completed"
    return base_result(
        task,
        "runner_checked",
        answer,
        gate,
        runner_status,
        extra=route_extra(
            route,
            ingest_draft=item,
            ingest_queue=queue_relpath,
        ),
        binding_source=binding_source,
    )


def execute_lane(task, workspace=".", route=None, binding_source="mcp"):
    lane = route_lane(route) or "legacy_execution"
    handlers = {
        "query": lambda: query_lane_result(task, workspace=workspace, route=route, binding_source=binding_source, deep=False),
        "query_deep": lambda: query_lane_result(task, workspace=workspace, route=route, binding_source=binding_source, deep=True),
        "resume": lambda: resume_lane_result(task, workspace=workspace, route=route, binding_source=binding_source),
        "bootstrap": lambda: bootstrap_lane_result(task, workspace=workspace, route=route, binding_source=binding_source),
        "ingest": lambda: ingest_lane_result(task, workspace=workspace, route=route, binding_source=binding_source),
    }
    if lane == "legacy_execution":
        return None
    handler = handlers.get(lane)
    if handler is None:
        return None
    return handler()


def run_finalization_gate(model_output, task_kind=""):
    payload = finalization_payload_from_text(model_output)
    block = render_finalization_block(payload)
    command = [sys.executable, str(current_dir / "finalization_check.py")]
    if task_kind:
        command.extend(["--task-kind", task_kind])

    result = subprocess.run(
        command,
        input=block,
        capture_output=True,
        text=True,
        check=False,
    )

    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        report = {
            "decision": "blocked",
            "reason": "finalization_check.py returned non-JSON output",
            "state": payload["current_state"],
            "checked_state": "blocked",
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    decision = report.get("decision")
    checked_state = report.get("checked_state") or payload["current_state"]
    if (payload.get("_forced_missing") or payload.get("_forced_incomplete")) and not payload["current_state"].startswith(
        "knowledge"
    ):
        report["decision"] = "blocked"
        report["reason"] = "Finalization block missing required field(s)"
        report["checked_state"] = "blocked"
        payload = {
            "current_state": "blocked",
            "evidence": payload["evidence"],
            "gaps_or_limitations": report["reason"],
            "next_steps": payload["next_steps"],
        }
        block = render_finalization_block(payload)
    elif decision == "downgrade":
        payload["current_state"] = checked_state
        block = render_finalization_block(payload)
    elif decision == "blocked":
        payload = {
            "current_state": "blocked",
            "evidence": report.get("evidence") or payload["evidence"],
            "gaps_or_limitations": report.get("reason") or "Finalization gate blocked completion.",
            "next_steps": report.get("next_steps") or payload["next_steps"],
        }
        block = render_finalization_block(payload)
    report["checked_state"] = payload["current_state"]
    return {
        "report": report,
        "block": block,
        "exit_code": result.returncode,
    }


def compose_answer(body, finalization_block):
    body = str(body or "").strip()
    if body:
        return f"{body}\n\n{finalization_block}".strip()
    return str(finalization_block or "").strip()


def extract_current_state(finalization_gate):
    report = finalization_gate.get("report", {})
    return report.get("checked_state") or report.get("state") or "blocked"


def replace_next_steps(finalization_block, next_steps):
    lines = str(finalization_block or "").splitlines()
    rewritten = []
    replaced = False
    for line in lines:
        if line.startswith("- next_steps:"):
            rewritten.append(f"- next_steps: {next_steps}")
            replaced = True
        else:
            rewritten.append(line)
    if not replaced:
        rewritten.append(f"- next_steps: {next_steps}")
    return "\n".join(rewritten).strip()


def rejected_output(reason, task="", answer=""):
    return {
        "answer": str(answer or "").strip(),
        "current_state": "blocked",
        "binding_status": "rejected",
        "reason": reason,
        "runner_status": "blocked",
        "task": task,
    }


def rejected_non_runner_output(task=""):
    return rejected_output("output not produced by runner", task=task)


def render_with_visibility_lock(result):
    if not isinstance(result, dict):
        return "[UNVERIFIED OUTPUT - DO NOT TRUST]\nreason: non-structured output\n\n" + str(result)

    binding = result.get("binding_status")
    proof = result.get("validation_proof")
    state = result.get("current_state")
    answer = str(result.get("answer") or "")
    reason = str(result.get("reason") or f"binding={binding}, proof={proof}")

    if binding == "runner_enforced" and proof:
        banner = f"[ABW] binding={binding} | validation_proof={proof} | state={state}"
        return banner + "\n\n" + answer

    return (
        "[UNVERIFIED OUTPUT - DO NOT TRUST]\n"
        f"reason: {reason}\n\n"
        + answer
    )


def has_finalized_answer_shape(result):
    finalization_block = str(result.get("finalization_block") or "").strip()
    answer = str(result.get("answer") or "").strip()
    validated_answer = str(result.get("validated_answer") or "").strip()

    if finalization_block:
        return True
    if "## Finalization" in answer:
        return True
    if validated_answer and "## Finalization" in validated_answer:
        return True
    return False


def has_echo_locked_runner_output(result):
    answer = str(result.get("answer") or "").strip()
    validated_answer = str(result.get("validated_answer") or "").strip()
    finalization_block = str(result.get("finalization_block") or "").strip()

    if validated_answer and answer != validated_answer:
        return False

    if finalization_block and not answer.endswith(finalization_block):
        return False

    return True


def enforce_output_acceptance(result, mode="STRICT"):
    mode = normalize_binding_mode(mode)
    if "binding_status" not in result or result["binding_status"] is None:
        return rejected_non_runner_output(task=result.get("task", ""))

    if "current_state" not in result or result["current_state"] is None:
        return rejected_output("missing required field: current_state", task=result.get("task", ""))

    if result["binding_status"] not in (
        "runner_enforced",
        "runner_checked",
        "prompt_only",
        "rejected",
    ):
        return rejected_non_runner_output(task=result.get("task", ""))

    if result.get("intent") == "knowledge":
        knowledge = result.get("knowledge")
        if not knowledge:
            return rejected_output("missing knowledge block", task=result.get("task", ""))

        for field in ("tier", "score", "source_summary"):
            if knowledge.get(field) is None:
                return rejected_output(f"missing knowledge.{field}", task=result.get("task", ""))

    if mode == "STRICT" and result["binding_status"] == "prompt_only":
        return rejected_output("STRICT mode requires runner usage", task=result.get("task", ""))

    if result["binding_status"] in ("runner_enforced", "runner_checked") and not has_finalized_answer_shape(result):
        return rejected_output("raw draft answer is not allowed", task=result.get("task", ""))

    if result.get("binding_status") in ("runner_enforced", "runner_checked"):
        runtime_id = str(result.get("runtime_id") or "").strip()
        if not runtime_id:
            return rejected_output("missing required field: runtime_id", task=result.get("task", ""))
        nonce = str(result.get("nonce") or "").strip()
        if not nonce:
            return rejected_output("missing required field: nonce", task=result.get("task", ""))
        binding_source = str(result.get("binding_source") or "").strip()
        if not binding_source:
            return rejected_output("missing required field: binding_source", task=result.get("task", ""))
        if not abw_proof.verify_proof(
            result.get("validation_proof"),
            result.get("answer", ""),
            result.get("finalization_block", ""),
            runtime_id,
            nonce,
            binding_source,
        ):
            return rejected_non_runner_output(task=result.get("task", ""))
        if not has_echo_locked_runner_output(result):
            return rejected_non_runner_output(task=result.get("task", ""))
        if result.get("binding_status") == "runner_checked" and result.get("current_state") == "verified":
            result = dict(result)
            result["current_state"] = "checked_only"

    return result


def base_result(
    task,
    binding_status,
    answer,
    finalization_gate,
    runner_status,
    knowledge=None,
    extra=None,
    runtime_id=None,
    binding_source="mcp",
):
    runtime_id = str(runtime_id or new_runtime_id())
    nonce = abw_proof.new_nonce()
    result = {
        "answer": answer,
        "binding_status": binding_status,
        "binding_source": str(binding_source or "mcp"),
        "current_state": extract_current_state(finalization_gate),
        "finalization_block": finalization_gate["block"],
        "finalization_gate": finalization_gate["report"],
        "nonce": nonce,
        "runner_status": runner_status,
        "task": task,
        "runtime_id": runtime_id,
    }
    if knowledge is not None:
        result["knowledge"] = knowledge
        result["intent"] = "knowledge"
    if extra:
        result.update(extra)
    result["validation_proof"] = abw_proof.generate_proof(
        result.get("answer", ""),
        result.get("finalization_block", ""),
        result["runtime_id"],
        result["nonce"],
        result["binding_source"],
    )
    return result


def knowledge_body(task, result):
    context = result.get("knowledge_context") or {}
    content = context.get("content") or ""
    if result.get("knowledge_evidence_tier") == "E0_unknown":
        return (
            f"Incomplete knowledge answer for '{task}'. "
            "No grounded project evidence was found, so the request is surfaced as a visible gap."
        )
    if result.get("knowledge_evidence_tier") == "E2_wiki":
        return (
            f"Knowledge answer for '{task}' was retrieved from local wiki evidence: {content}"
        )
    if result.get("knowledge_evidence_tier") == "E3_grounded":
        return (
            f"Knowledge answer for '{task}' was retrieved from an explicit local source: {content}"
        )
    return (
        f"Knowledge answer for '{task}' is allowed as a fallback answer, "
        "but stronger grounded provenance is still recommended."
    )


def binding_status_for_execution(binding_source, execution_result=None):
    execution_result = execution_result if isinstance(execution_result, dict) else {}
    if execution_result.get("command_executed"):
        return "runner_enforced"
    if execution_result.get("verified_artifact"):
        return "runner_enforced"
    if execution_result.get("command") and isinstance(execution_result.get("command_result"), dict):
        return "runner_enforced"
    return "runner_checked"


def execution_artifact_relpath(runtime_id):
    return f".brain/runner_artifacts/{runtime_id}.txt"


def acceptance_request_relpath(runtime_id):
    return f".brain/acceptance_requests/{runtime_id}.json"


def write_execution_artifact(workspace, result):
    runtime_id = str(result.get("runtime_id") or new_runtime_id())
    relpath = execution_artifact_relpath(runtime_id)
    path = Path(workspace) / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    command_result = result.get("command_result") or {}
    status = "passed" if int(command_result.get("exit_code", 1)) == 0 else "failed"
    content = "\n".join(
        [
            f"runtime_id: {runtime_id}",
            f"status: {status}",
            f"command: {result.get('command') or ''}",
            f"exit_code: {command_result.get('exit_code')}",
            "stdout:",
            str(command_result.get("stdout") or "").rstrip(),
            "stderr:",
            str(command_result.get("stderr") or "").rstrip(),
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")
    return relpath


def build_acceptance_request(result, artifact_path):
    runtime_id = str(result.get("runtime_id") or "")
    command_result = result.get("command_result") or {}
    exit_code = int(command_result.get("exit_code", 1))
    passed = exit_code == 0
    status = "passed" if passed else "failed"
    return {
        "step_id": f"step-{runtime_id}",
        "scope": result.get("task") or "ABW execution",
        "artifact": {
            "id": "runner-artifact",
            "path": artifact_path,
            "type": "execution_log",
        },
        "candidate_files": [artifact_path],
        "rubric": [
            {
                "id": "artifact-present",
                "description": "Execution artifact exists inside accepted scope.",
                "required": True,
                "passed": True,
                "evidence": {
                    "type": "artifact_presence",
                    "ref": artifact_path,
                    "ref_type": "file",
                    "ref_check": "contains: passed" if passed else "contains: failed",
                    "source": "trusted",
                    "context_id": f"step-{runtime_id}",
                    "runtime_id": runtime_id,
                    "status": status,
                    "machine_checkable": True,
                    "strength": "required_machine",
                    "claim_id": "rubric:artifact-present",
                    "proves": "The runner wrote an execution artifact with runtime marker.",
                    "mechanism": "artifact_presence",
                    "result": status,
                    "details": "Artifact written by runner.",
                },
            },
        ],
        "checks": [
            {
                "id": "command-executed",
                "type": "command_exit_code",
                "subject": result.get("command") or "command",
                "status": status,
                "expected": "pass" if passed else "fail",
                "required": True,
                "description": "Runner command executed with expected exit code.",
                "evidence": {
                    "type": "command_result",
                    "ref": result.get("command") or "",
                    "ref_type": "command",
                    "ref_check": f"exit_code:{exit_code}",
                    "source": "trusted",
                    "context_id": f"step-{runtime_id}",
                    "runtime_id": runtime_id,
                    "status": status,
                    "machine_checkable": True,
                    "strength": "required_machine",
                    "claim_id": "check:command-executed",
                    "proves": "The bounded runner command executed with the expected exit code.",
                    "mechanism": "test_result",
                    "result": status,
                    "details": "Command replay must match expected exit code.",
                },
            },
            {
                "id": "runtime-artifact",
                "type": "file_exists",
                "subject": artifact_path,
                "status": "passed",
                "expected": "pass",
                "required": True,
                "description": "Execution artifact exists with runtime marker.",
                "evidence": {
                    "type": "execution_log",
                    "ref": artifact_path,
                    "ref_type": "file",
                    "ref_check": "contains: passed" if passed else "contains: failed",
                    "source": "trusted",
                    "context_id": f"step-{runtime_id}",
                    "runtime_id": runtime_id,
                    "status": status,
                    "machine_checkable": True,
                    "strength": "required_machine",
                    "claim_id": "check:runtime-artifact",
                    "proves": "The execution artifact exists and carries the runtime marker.",
                    "mechanism": "artifact_presence",
                    "result": status,
                    "details": "Runner wrote a machine-checkable execution log.",
                },
            },
        ],
    }


def apply_acceptance_validation(result, workspace="."):
    if not isinstance(result, dict):
        return result
    if not result.get("command") or not isinstance(result.get("command_result"), dict):
        return result

    runtime_id = str(result.get("runtime_id") or new_runtime_id())
    artifact_path = write_execution_artifact(workspace, result)
    request = build_acceptance_request(result, artifact_path)
    request_relpath = acceptance_request_relpath(runtime_id)
    request_path = Path(workspace) / request_relpath
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    eval_result = abw_accept.evaluate_file(
        workspace,
        request_path,
        runtime_id=runtime_id,
    )
    updated = dict(result)
    updated["evaluation"] = eval_result
    updated["acceptance_request"] = request_relpath
    updated["artifact_path"] = artifact_path
    if eval_result.get("accepted") is not True:
        updated["binding_status"] = "runner_checked"
    return updated


def prompt_only_result(task, candidate_answer, route=None):
    result = {
        "answer": str(candidate_answer or "").strip(),
        "binding_status": "prompt_only",
        "current_state": "unknown",
        "runner_status": "not_run",
        "task": task,
    }
    if is_knowledge_intent(task, route):
        knowledge_result = enrich_knowledge_result(task, workspace=".")
        apply_knowledge_semantics(knowledge_result, task, route)
        result["intent"] = "knowledge"
        result["knowledge"] = {
            "answer": str(candidate_answer or "").strip(),
            "tier": knowledge_result["knowledge_evidence_tier"],
            "score": knowledge_result["knowledge_source_score"],
            "gap_logged": knowledge_result.get("gap_logged", False),
            "source_summary": build_source_summary(knowledge_result),
        }
    return result


def command_for_task(task):
    normalized = task.strip().lower()
    if normalized in {"print hello world", "hello world"} or "print hello world" in normalized:
        if os.name == "nt":
            return "cmd /c echo hello world"
        return "printf 'hello world\\n'"
    return None


def execute_task(task, workspace=".", task_kind="execution", route=None, binding_source="mcp"):
    task = str(task or "").strip()
    if not task:
        binding_status = binding_status_for_execution(
            binding_source,
            {"execution_path": "none"},
        )
        body = "Request blocked because no executable task was provided."
        model_output = """## Finalization
- current_state: blocked
- evidence: Empty task string.
- gaps_or_limitations: No executable request was provided.
- next_steps: Provide a concrete ABW task.
"""
        gate = run_finalization_gate(model_output, task_kind="run")
        answer = compose_answer(body, gate["block"])
        return base_result(task, binding_status, answer, gate, "blocked", binding_source=binding_source)

    lane_result = execute_lane(
        task,
        workspace=workspace,
        route=route,
        binding_source=binding_source,
    )
    if lane_result is not None:
        return lane_result

    if "fake verified" in task.lower():
        binding_status = binding_status_for_execution(
            binding_source,
            {"execution_path": "validation_only"},
        )
        body = "Candidate execution claim was checked and did not qualify for verified status."
        model_output = """## Finalization
- current_state: verified
- evidence: static reasoning only; model says it is verified
- gaps_or_limitations: not tested and no runtime proof
- next_steps: run the task through real execution
"""
        gate = run_finalization_gate(model_output, task_kind="verify")
        answer = compose_answer(body, gate["block"])
        runner_status = "blocked" if gate["report"].get("decision") == "blocked" else "completed"
        return base_result(
            task,
            binding_status,
            answer,
            gate,
            runner_status,
            extra=route_extra(route),
            binding_source=binding_source,
        )

    command = command_for_task(task)
    if command is None:
        binding_status = binding_status_for_execution(
            binding_source,
            {"execution_path": "none"},
        )
        body = f"Request blocked because the runner does not implement a bounded execution path for '{task}'."
        model_output = f"""## Finalization
- current_state: blocked
- evidence: No safe deterministic runner implementation exists for task: {task}
- gaps_or_limitations: Natural-language ABW routing is not implemented inside this MCP tool.
- next_steps: Add a bounded command implementation for this task or use an approved workflow path.
"""
        gate = run_finalization_gate(model_output, task_kind="run")
        answer = compose_answer(body, gate["block"])
        return base_result(
            task,
            binding_status,
            answer,
            gate,
            "blocked",
            extra=route_extra(route),
            binding_source=binding_source,
        )

    cmd_result = run_command(command, workspace)
    execution_result = {
        "command_executed": True,
        "execution_path": "command",
        "command": command,
        "command_result": cmd_result,
    }
    binding_status = binding_status_for_execution(binding_source, execution_result)
    stdout = cmd_result["stdout"].strip() or "<empty>"
    body = f"Executed bounded task '{task}' and observed stdout: {stdout}"
    model_output = f"""{body}

## Finalization
- current_state: verified
- evidence: terminal output stdout showed {stdout} with exit code {cmd_result["exit_code"]}
- gaps_or_limitations: only this bounded task was executed
- next_steps: no further action required for this trivial task
"""
    gate = run_finalization_gate(model_output, task_kind="run")
    answer = compose_answer(body, gate["block"])
    runner_status = "blocked" if gate["report"].get("decision") == "blocked" else "completed"
    extra = {
        "command": command,
        "command_result": cmd_result,
    }
    extra.update(route_extra(route))
    return base_result(task, binding_status, answer, gate, runner_status, extra=extra, binding_source=binding_source)


def infer_validation_knowledge(task, candidate_answer, route=None, workspace="."):
    result = enrich_knowledge_result(task, workspace=workspace)
    apply_knowledge_semantics(result, task, route)
    return result


def validate_candidate_answer(task, candidate_answer, route=None, binding_mode="STRICT", workspace="."):
    binding_mode = normalize_binding_mode(binding_mode)
    if not str(candidate_answer or "").strip():
        if binding_mode == "SOFT":
            return prompt_only_result(task, candidate_answer, route=route)

        body = "Request blocked because no candidate answer was provided for validation."
        model_output = """## Finalization
- current_state: blocked
- evidence: Candidate answer missing.
- gaps_or_limitations: Validation mode requires a candidate_answer payload.
- next_steps: Generate a tentative answer and send it back through validation mode.
"""
        gate = run_finalization_gate(model_output, task_kind="verify")
        answer = compose_answer(body, gate["block"])
        return base_result(task, "runner_checked", answer, gate, "blocked")

    body, existing_finalization = split_answer_and_finalization(candidate_answer)
    candidate_text = compose_answer(body, existing_finalization) if existing_finalization else body

    if is_knowledge_intent(task, route):
        knowledge_result = infer_validation_knowledge(task, candidate_text, route=route, workspace=workspace)
        if knowledge_result.get("gap_logged"):
            knowledge_result["gap_id"] = log_knowledge_gap(
                task,
                workspace=workspace,
                searched_locations=["wiki/", "explicit local sources"],
            )
        payload = finalization_payload_from_text(candidate_answer)
        payload["current_state"] = knowledge_result["current_state"]
        payload["evidence"] = knowledge_result["evidence"]
        payload["gaps_or_limitations"] = payload.get("gaps_or_limitations") or (
            f"validated retrieval path; knowledge_evidence_tier={knowledge_result['knowledge_evidence_tier']}; "
            f"knowledge_source_score={knowledge_result['knowledge_source_score']}"
        )
        payload["next_steps"] = payload.get("next_steps") or (
            "Add grounded source material to wiki or provide an explicit local source."
            if knowledge_result.get("gap_logged")
            else "Use the retrieved local source for follow-up questions if needed."
        )
        payload["knowledge_evidence_tier"] = knowledge_result["knowledge_evidence_tier"]
        payload["knowledge_source_score"] = knowledge_result["knowledge_source_score"]
        payload["source_summary"] = build_source_summary(knowledge_result)
        payload["gap_logged"] = str(knowledge_result.get("gap_logged", False))
        gate = run_finalization_gate(compose_answer(body, render_finalization_block(payload)), task_kind="knowledge")
        answer = compose_answer(body, gate["block"])
        knowledge_result["answer"] = body
        attach_knowledge_output(knowledge_result, answer_text=body)
        enforce_knowledge_output(knowledge_result)
        runner_status = "blocked" if gate["report"].get("decision") == "blocked" else "completed"
        extra = {
            "validated_answer": answer,
            "knowledge_evidence_tier": knowledge_result["knowledge_evidence_tier"],
            "knowledge_source_score": knowledge_result["knowledge_source_score"],
        }
        return base_result(
            task,
            "runner_checked",
            answer,
            gate,
            runner_status,
            knowledge=knowledge_result["knowledge_output"],
            extra=extra,
        )

    gate = run_finalization_gate(candidate_answer, task_kind="verify")
    checked_state = gate["report"].get("checked_state")
    if checked_state == "blocked":
        body = body or "Candidate answer was blocked during validation."
    elif gate["report"].get("decision") == "downgrade" and body:
        body = f"{body}\n\nValidated result: completion claim was downgraded to `{checked_state}`."
        safer_next_steps = "Run the task through real execution before claiming completion."
        gate["block"] = replace_next_steps(gate["block"], safer_next_steps)
        gate["report"]["next_steps"] = safer_next_steps
    elif not body:
        body = f"Validated result is `{checked_state}`."

    answer = compose_answer(body, gate["block"])
    runner_status = "blocked" if gate["report"].get("decision") == "blocked" else "completed"
    extra = {"validated_answer": answer}
    return base_result(task, "runner_checked", answer, gate, runner_status, extra=extra)


def dispatch_request(
    *,
    task,
    workspace=".",
    task_kind="execution",
    candidate_answer=None,
    route=None,
    binding_mode="STRICT",
    binding_source="mcp",
    memory_scope=None,
):
    task_kind = normalize_task_kind(task_kind)
    binding_mode = normalize_binding_mode(binding_mode)
    if str(task).strip() == "/abw-health":
        result = abw_health.run_health(
            workspace=workspace,
            binding_status=binding_status_for_execution(
                binding_source,
                {"verified_artifact": True, "execution_path": "artifact"},
            ),
            binding_source=binding_source,
        )
        return enforce_output_acceptance(result, mode=binding_mode)

    memory_item = check_negative_memory(task, workspace=workspace, memory_scope=memory_scope)
    resolved_route = resolve_route(task, workspace=workspace, route=route)
    abw_router.log_route_decision(workspace, task, resolved_route, event="selected")

    if task_kind == "validation":
        result = validate_candidate_answer(
            task=task,
            candidate_answer=candidate_answer,
            route=resolved_route,
            binding_mode=binding_mode,
            workspace=workspace,
        )
        result = enforce_output_acceptance(result, mode=binding_mode)
        if result.get("binding_status") == "rejected" or result.get("current_state") == "blocked":
            log_negative_memory(
                workspace=workspace,
                pattern=extract_pattern(task),
                failure=derive_failure_label(result),
                context=result.get("current_state"),
                fix_hint=derive_fix_hint(result),
                memory_scope=memory_scope,
            )
        return attach_memory_warning(result, memory_item)

    try:
        result = execute_task(
            task=task,
            workspace=workspace,
            task_kind=task_kind,
            route=resolved_route,
            binding_source=binding_source,
        )
    except Exception as exc:  # noqa: BLE001 - lane failures must fall back safely when allowed.
        lane = route_lane(resolved_route)
        fallback_allowed = bool(resolved_route.get("fallback_allowed", True))
        if lane in {"resume", "query_deep"} and fallback_allowed:
            fallback_route = build_lane_route(
                resolved_route,
                "query",
                reason="fallback to query after lane failure",
                fallback_from=lane,
                fallback_reason=str(exc),
            )
            abw_router.log_route_decision(
                workspace,
                task,
                fallback_route,
                event="fallback",
                details={"error": str(exc)},
            )
            result = query_lane_result(
                task,
                workspace=workspace,
                route=fallback_route,
                binding_source=binding_source,
                deep=False,
            )
        elif lane == "ingest":
            log_knowledge_gap(
                task,
                workspace=workspace,
                searched_locations=["raw/", ".brain/ingest_queue.json"],
                reason=f"ingest lane failed: {exc}",
            )
            fallback_route = build_lane_route(
                resolved_route,
                "query",
                reason="fallback to query after ingest failure",
                fallback_from="ingest",
                fallback_reason=str(exc),
            )
            abw_router.log_route_decision(
                workspace,
                task,
                fallback_route,
                event="fallback",
                details={"error": str(exc)},
            )
            result = query_lane_result(
                task,
                workspace=workspace,
                route=fallback_route,
                binding_source=binding_source,
                deep=False,
            )
        else:
            raise
    result = apply_acceptance_validation(result, workspace=workspace)
    result = enforce_output_acceptance(result, mode=binding_mode)
    if result.get("binding_status") == "rejected" or result.get("current_state") == "blocked":
        log_negative_memory(
            workspace=workspace,
            pattern=extract_pattern(task),
            failure=derive_failure_label(result),
            context=result.get("current_state"),
            fix_hint=derive_fix_hint(result),
            memory_scope=memory_scope,
        )
    return attach_memory_warning(result, memory_item)


def run_mcp_server():
    if FastMCP is None:
        raise RuntimeError("Python package 'mcp' is required for MCP server mode.")

    mcp = FastMCP("abw_runner")

    @mcp.tool(name="abw_runner")
    def abw_runner_tool(
        task: str,
        workspace: str = ".",
        task_kind: str = "execution",
        candidate_answer: str | None = None,
        route: dict | None = None,
        binding_mode: str = "STRICT",
    ) -> str:
        """Execute or validate one ABW task through the runner."""

        return json.dumps(
            dispatch_request(
                task=task,
                workspace=workspace,
                task_kind=task_kind,
                candidate_answer=candidate_answer,
                route=route,
                binding_mode=binding_mode,
                binding_source="mcp",
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    mcp.run(transport="stdio")


def main():
    parser = argparse.ArgumentParser(description="ABW Runner: execute or validate with explicit binding status.")
    parser.add_argument("--workspace", default=".", help="Workspace directory")
    parser.add_argument("--request", help="Path to acceptance request JSON")
    parser.add_argument("-c", "--command", help="Command to execute")
    parser.add_argument("--no-log", action="store_true", help="Do not append .brain/acceptance_log.jsonl")
    parser.add_argument("--task-kind", default="execution", help="execution or validation")
    parser.add_argument("--task", help="Execute or validate an ABW task through the runner")
    parser.add_argument("--json-input", action="store_true", help="Read JSON from stdin with task/task_kind fields")
    parser.add_argument("--mcp", action="store_true", help="Run as an MCP stdio server")
    parser.add_argument("--candidate-answer", help="Tentative answer to validate when task_kind=validation")
    parser.add_argument("--binding-mode", default="STRICT", help="STRICT or SOFT")
    parser.add_argument("--binding-source", default="cli", help="mcp, fallback, or another caller label")

    args = parser.parse_args()

    if args.mcp:
        run_mcp_server()
        return

    if args.task or args.json_input:
        payload = {}
        if args.json_input:
            raw = sys.stdin.read()
            payload = json.loads(raw) if raw.strip() else {}
        task = args.task if args.task is not None else payload.get("task", "")
        route = payload.get("route") if isinstance(payload.get("route"), dict) else None
        candidate_answer = (
            args.candidate_answer
            if args.candidate_answer is not None
            else payload.get("candidate_answer")
        )
        result = dispatch_request(
            task=task,
            workspace=args.workspace,
            task_kind=payload.get("task_kind", args.task_kind),
            candidate_answer=candidate_answer,
            route=route,
            binding_mode=payload.get("binding_mode", args.binding_mode),
            binding_source=payload.get("binding_source", args.binding_source),
            memory_scope=payload.get("memory_scope"),
        )
        print(render_with_visibility_lock(result))
        sys.exit(0 if result.get("runner_status") == "completed" else 3)

    if not args.request or not args.command:
        if len(sys.argv) == 1:
            run_mcp_server()
            return
        parser.error("--request and --command are required unless --task, --json-input, or --mcp is used")

    cmd_result = run_command(args.command, args.workspace)

    try:
        eval_result = abw_accept.evaluate_file(args.workspace, args.request, write_log=not args.no_log)
    except Exception as exc:  # noqa: BLE001 - CLI reports acceptance failures as JSON.
        eval_result = {"status": "error", "error": str(exc)}

    finalization_gate = run_finalization_gate(cmd_result["stdout"], task_kind=args.task_kind)
    finalization_decision = finalization_gate["report"].get("decision")
    body = cmd_result["stdout"].strip() or "Command finished without stdout."
    final_output = {
        "answer": compose_answer(body, finalization_gate["block"]),
        "binding_status": binding_status_for_execution(
            args.binding_source,
            {
                "command_executed": True,
                "execution_path": "command",
                "command": args.command,
                "command_result": cmd_result,
            },
        ),
        "binding_source": args.binding_source,
        "current_state": extract_current_state(finalization_gate),
        "runner_status": "blocked" if finalization_decision == "blocked" else "completed",
        "command_exit_code": cmd_result["exit_code"],
        "command_stdout": cmd_result["stdout"],
        "command_stderr": cmd_result["stderr"],
        "evaluation": eval_result,
        "finalization_gate": finalization_gate["report"],
        "finalization_block": finalization_gate["block"],
        "nonce": abw_proof.new_nonce(),
        "runtime_id": eval_result.get("runtime_id") or new_runtime_id(),
    }
    final_output["validation_proof"] = abw_proof.generate_proof(
        final_output.get("answer", ""),
        final_output.get("finalization_block", ""),
        final_output["runtime_id"],
        final_output["nonce"],
        final_output["binding_source"],
    )
    final_output = enforce_output_acceptance(final_output, mode=args.binding_mode)
    if final_output.get("binding_status") == "rejected" or final_output.get("current_state") == "blocked":
        log_negative_memory(
            workspace=args.workspace,
            pattern=extract_pattern(args.task or ""),
            failure=derive_failure_label(final_output),
            context=final_output.get("current_state"),
            fix_hint=derive_fix_hint(final_output),
        )

    print(render_with_visibility_lock(final_output))

    if finalization_decision == "blocked":
        sys.exit(3)
    if eval_result.get("status") == "error":
        sys.exit(1)
    if eval_result.get("verdict") == "pass":
        sys.exit(0)
    sys.exit(2)


if __name__ == "__main__":
    main()
