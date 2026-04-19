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


def is_knowledge_intent(task, route=None):
    route = route or {}
    intent = route.get("intent") if isinstance(route, dict) else None
    return intent == "knowledge" or (intent is None and is_knowledge_task(task))


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

    if is_knowledge_intent(task, route):
        binding_status = binding_status_for_execution(
            binding_source,
            {"execution_path": "knowledge"},
        )
        result = enrich_knowledge_result(task, workspace=workspace)
        if result.get("gap_logged"):
            result["gap_id"] = log_knowledge_gap(
                task,
                workspace=workspace,
                searched_locations=["wiki/", "explicit local sources"],
            )
        apply_knowledge_semantics(result, task, route)
        body = knowledge_body(task, result)
        attach_knowledge_output(result, answer_text=body)
        enforce_knowledge_output(result)
        model_output = f"""{body}

## Finalization
- current_state: {result["current_state"]}
- evidence: {result["evidence"]}
- gaps_or_limitations: retrieval source={result["knowledge_output"]["source_summary"]}; knowledge_evidence_tier={result.get("knowledge_evidence_tier")}; knowledge_source_score={result.get("knowledge_source_score")}
- next_steps: {"add grounded source material to wiki or provide an explicit local source" if result.get("gap_logged") else "use the retrieved local source for follow-up questions if needed"}
- knowledge_evidence_tier: {result.get("knowledge_evidence_tier")}
- knowledge_source_score: {result.get("knowledge_source_score")}
- source_summary: {result["knowledge_output"]["source_summary"]}
- gap_logged: {result.get("gap_logged", False)}
"""
        gate = run_finalization_gate(model_output, task_kind="knowledge")
        answer = compose_answer(body, gate["block"])
        runner_status = "blocked" if gate["report"].get("decision") == "blocked" else "completed"
        extra = {
            "gap_logged": result.get("gap_logged", False),
            "knowledge_evidence_tier": result.get("knowledge_evidence_tier"),
            "knowledge_source_score": result.get("knowledge_source_score"),
            "refinement_history": result.get("refinement_history", []),
            "semantic_fix_applied": result.get("semantic_fix_applied", False),
            "strategy_trace": result.get("strategy_trace", {}),
        }
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
        return base_result(task, binding_status, answer, gate, runner_status, binding_source=binding_source)

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
        return base_result(task, binding_status, answer, gate, "blocked", binding_source=binding_source)

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

    if task_kind == "validation":
        result = validate_candidate_answer(
            task=task,
            candidate_answer=candidate_answer,
            route=route,
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

    result = execute_task(
        task=task,
        workspace=workspace,
        task_kind=task_kind,
        route=route,
        binding_source=binding_source,
    )
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
