import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


VALID_CHECK_TYPES = {
    "test_result",
    "file_exists",
    "command_exit_code",
    "scope_check",
    "instruction_compliance",
    "locked_decision_check",
    "manual_review",
}

MACHINE_REQUIRED_CHECK_TYPES = VALID_CHECK_TYPES - {"manual_review"}
VALID_EVIDENCE_STRENGTHS = {"required_machine", "allowed_human", "supporting_only"}
VALID_EVIDENCE_MECHANISMS = {
    "test_result",
    "diff_inspection",
    "artifact_presence",
    "human_review",
    "consistency_check",
}
PASS_VALUES = {"pass", "passed", "ok", "true", True, 0}
FAIL_VALUES = {"fail", "failed", "error", "false", False}
INCONCLUSIVE_VALUES = {"inconclusive", "unknown", "not_checked", None}
VALID_REF_TYPES = {"file", "command"}
RECENT_FILE_SECONDS = 5
DANGEROUS_COMMANDS = {"rm", "del", "shutdown"}
MAX_EVIDENCE_AGE_SECONDS = 60
MAX_EVAL_TIME_SECONDS = 2
MAX_FILE_READ_BYTES = 5000
COMMAND_TIMEOUT_SECONDS = 2
FAILURE_ACTIONS = {
    "runtime_mismatch": "regenerate evidence with correct runtime_id",
    "runtime_marker_missing_or_invalid": "rerun command and write correct runtime marker",
    "runtime_marker_missing_or_invalid_in_stdout": "fix command to print runtime marker",
    "evidence_ref_outside_scope": "move artifact into candidate_files or artifact paths",
    "command_timeout": "simplify or fix command execution",
    "evaluation_timeout": "reduce evaluation complexity or fix blocking logic",
}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def append_jsonl(path, row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def suggested_action_for(reason):
    for key, action in FAILURE_ACTIONS.items():
        if key in reason:
            return action
    return "inspect failure reason and repair evidence"


def next_steps_for(fail_reasons):
    return [
        {
            "reason": reason,
            "suggested_action": suggested_action_for(reason),
        }
        for reason in fail_reasons
    ]


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_result(value):
    if isinstance(value, str):
        return value.strip().lower()
    return value


def status_value(item):
    if "status" in item:
        return normalize_result(item.get("status"))
    return normalize_result(item.get("result"))


def evidence_payload(item):
    evidence = item.get("evidence")
    if isinstance(evidence, dict):
        return evidence
    return {
        "type": item.get("evidence_type"),
        "ref": item.get("evidence_ref"),
        "status": item.get("evidence_status"),
        "machine_checkable": item.get("machine_checkable"),
        "details": item.get("details"),
        "strength": item.get("evidence_strength"),
        "claim_id": item.get("claim_id"),
        "proves": item.get("proves"),
        "mechanism": item.get("mechanism"),
        "result": item.get("evidence_result"),
        "ref_type": item.get("evidence_ref_type"),
        "ref_check": item.get("evidence_ref_check"),
        "source": item.get("evidence_source"),
        "context_id": item.get("evidence_context_id"),
        "runtime_id": item.get("evidence_runtime_id"),
        "runtime_reflection": item.get("evidence_runtime_reflection"),
    }


def evidence_has_payload(evidence):
    return bool(evidence.get("type") and evidence.get("ref"))


def evidence_status_conflicts(item, evidence):
    item_status = status_value(item)
    evidence_status = evidence_result(evidence)
    if evidence_status is None:
        return False
    if item_status in PASS_VALUES and evidence_status in FAIL_VALUES:
        return True
    if item_status in FAIL_VALUES and evidence_status in PASS_VALUES:
        return True
    return False


def claim_id_for(item, prefix):
    item_id = item.get("id") or item.get("type")
    if not item_id:
        return None
    if str(item_id).startswith("check:") or str(item_id).startswith("rubric:"):
        return str(item_id)
    return f"{prefix}:{item_id}"


def evidence_result(evidence):
    if "result" in evidence:
        return normalize_result(evidence.get("result"))
    return normalize_result(evidence.get("status"))


def is_pass_status(value):
    return normalize_result(value) in PASS_VALUES


def strip_check_value(value):
    return str(value).strip().strip("\"'")


def normalize_text(content):
    return " ".join(str(content).lower().split())


def token_count(content, token):
    return len(re.findall(rf"\b{re.escape(token)}\b", content, flags=re.IGNORECASE))


def error_failure_count(content):
    patterns = [
        r"\b[1-9]\d*\s+errors?\b",
        r"\berrors?\s*[:=]\s*[1-9]\d*\b",
        r"^\s*errors?\s*$",
    ]
    return sum(len(re.findall(pattern, content, flags=re.IGNORECASE | re.MULTILINE)) for pattern in patterns)


def observed_result_from_text(content):
    normalized = normalize_text(content)
    failed_count = token_count(normalized, "failed") + error_failure_count(content)
    passed_count = token_count(normalized, "passed")

    if failed_count > 0:
        return "failed"
    if passed_count > 0:
        return "passed"
    return None


def command_tokens(command):
    return str(command).split()


def command_is_safe(tokens):
    if not tokens:
        return False, "empty_command"
    lowered = [token.lower() for token in tokens]
    if any(token in DANGEROUS_COMMANDS for token in lowered):
        return False, "dangerous_command"
    for first, second in zip(lowered, lowered[1:]):
        if first == "git" and second in {"reset", "clean"}:
            return False, "dangerous_command"
    return True, "ok"


def parse_exit_code_check(ref_check):
    if not ref_check:
        return None, "missing_ref_check"
    if not str(ref_check).startswith("exit_code:"):
        return None, "unsupported_ref_check"
    raw_code = str(ref_check).split("exit_code:", 1)[1].strip()
    if not raw_code:
        return None, "missing_exit_code"
    try:
        return int(raw_code), "ok"
    except ValueError:
        return None, "invalid_exit_code"


def read_evidence_file(path):
    with path.open("r", encoding="utf-8-sig", errors="ignore") as f:
        return f.read(MAX_FILE_READ_BYTES)


def check_command_ref(workspace, evidence):
    tokens = command_tokens(evidence.get("ref"))
    safe, reason = command_is_safe(tokens)
    if not safe:
        return False, reason

    expected_exit_code, reason = parse_exit_code_check(evidence.get("ref_check"))
    if reason != "ok":
        return False, reason

    try:
        env = dict(os.environ)
        env["ABW_RUNTIME_ID"] = str(evidence.get("_runtime_id"))
        result = subprocess.run(
            tokens,
            cwd=workspace,
            capture_output=True,
            check=False,
            env=env,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return False, "command_timeout"
    except OSError:
        return False, "command_run_failed"

    if result.returncode != expected_exit_code:
        declared = evidence_result(evidence)
        if declared in PASS_VALUES:
            return False, "command_exit_code_contradicts_declared_pass"
        return False, "exit_code_mismatch"
    if strict_command_runtime_reflection_required(evidence):
        stdout = result.stdout
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="ignore")
        marker = f"runtime_id: {evidence.get('_runtime_id')}"
        marker_pattern = rf"(?m)^\s*{re.escape(marker)}\s*$"
        if not re.search(marker_pattern, str(stdout)):
            return False, "runtime_marker_missing_or_invalid_in_stdout"
    return True, "ok"


def evidence_source(evidence):
    source = evidence.get("source")
    if source:
        return str(source).strip().lower()
    if evidence.get("ref_type") == "command":
        return "trusted"
    if evidence.get("ref_type") == "file":
        return "untrusted"
    return "untrusted"


def normalize_ref_path(value):
    return str(Path(str(value))).replace("\\", "/")


def allowed_evidence_paths(request):
    paths = set()
    for path in as_list(request.get("candidate_files")):
        paths.add(normalize_ref_path(path))
    artifact = request.get("artifact") or {}
    artifacts = request.get("artifacts") or ([artifact] if artifact else [])
    for artifact_item in artifacts:
        if artifact_item.get("path"):
            paths.add(normalize_ref_path(artifact_item["path"]))
    return paths


def evidence_ref_within_scope(evidence, allowed_paths):
    return normalize_ref_path(evidence.get("ref")) in allowed_paths


def check_evidence_ref(workspace, evidence):
    ref = evidence.get("ref")
    ref_type = evidence.get("ref_type")
    ref_check = evidence.get("ref_check")

    if not ref:
        return False, "missing_ref"
    if ref_type not in VALID_REF_TYPES:
        return False, "missing_or_invalid_ref_type"

    if ref_type == "command":
        return check_command_ref(workspace, evidence)

    path = Path(workspace) / ref
    if ref_type == "file":
        if not path.exists():
            return False, "file_not_found"
        if not path.is_file():
            return False, "ref_not_file"
        if path.stat().st_size <= 0:
            return False, "empty_file"
        max_age_seconds = int(evidence.get("max_age_seconds", MAX_EVIDENCE_AGE_SECONDS))
        if time.time() - path.stat().st_mtime > max_age_seconds:
            return False, "stale_evidence"
        if evidence.get("recent_file_policy") == "fail":
            age_seconds = time.time() - path.stat().st_mtime
            if age_seconds >= 0 and age_seconds <= int(evidence.get("recent_file_seconds", RECENT_FILE_SECONDS)):
                return False, "recent_file"

        content = None
        if ref_check:
            if not str(ref_check).startswith("contains:"):
                return False, "unsupported_ref_check"
            needle = strip_check_value(str(ref_check).split("contains:", 1)[1])
            if not needle:
                return False, "missing_contains_value"
            content = read_evidence_file(path)
            if not re.search(rf"\b{re.escape(needle)}\b", content):
                return False, "content_mismatch"

        if content is None:
            content = read_evidence_file(path)
        if strict_runtime_required(evidence):
            marker = f"runtime_id: {evidence.get('_runtime_id')}"
            marker_pattern = rf"(?m)^\s*{re.escape(marker)}\s*$"
            if not re.search(marker_pattern, content):
                return False, "runtime_marker_missing_or_invalid"
        elif evidence.get("_runtime_validation_requested") and str(evidence.get("_runtime_id")) not in content:
            return False, "runtime_not_found_in_artifact"
        observed = observed_result_from_text(content)
        declared = evidence_result(evidence)
        if declared in PASS_VALUES and observed in FAIL_VALUES:
            return False, "observed_result_contradicts_declared_pass"
        if declared in FAIL_VALUES and observed in PASS_VALUES:
            return False, "observed_result_contradicts_declared_fail"
        if observed is None:
            return False, "observed_result_unknown"

    return True, "ok"


def context_bound(evidence, request_step_id):
    if evidence.get("ref_type") == "command":
        return True
    context_id = evidence.get("context_id")
    return bool(context_id and request_step_id and context_id == request_step_id)


def strict_runtime_required(evidence):
    return (
        evidence.get("strength") == "required_machine"
        and evidence.get("ref_type") == "file"
        and evidence_source(evidence) == "trusted"
    )


def strict_command_runtime_reflection_required(evidence):
    return (
        evidence.get("strength") == "required_machine"
        and evidence.get("ref_type") == "command"
        and evidence_source(evidence) == "trusted"
        and evidence.get("runtime_reflection") == "stdout"
    )


def runtime_bound(evidence, runtime_id):
    claimed_runtime_id = evidence.get("runtime_id")
    evidence["_runtime_id"] = runtime_id
    if strict_runtime_required(evidence) and claimed_runtime_id == "TO_BE_FILLED_BY_RUNNER":
        claimed_runtime_id = runtime_id
        evidence["runtime_id"] = runtime_id
    if strict_runtime_required(evidence):
        evidence["_runtime_validation_requested"] = True
        return bool(claimed_runtime_id and runtime_id and str(claimed_runtime_id) == str(runtime_id))
    if claimed_runtime_id in {None, "", "TO_BE_FILLED_BY_RUNNER", "OPTIONAL_RUNTIME_ID"}:
        evidence["_runtime_validation_requested"] = False
        return True
    evidence["_runtime_validation_requested"] = True
    return bool(runtime_id and str(claimed_runtime_id) == str(runtime_id))


def validate_evidence(
    item,
    *,
    workspace=None,
    request_step_id=None,
    runtime_id=None,
    allowed_paths=None,
    evidence_cache=None,
    expected_claim_id=None,
    require_machine=False,
):
    required = item.get("required", True)
    evidence = evidence_payload(item)
    issues = []
    warnings = []

    if not required and not evidence_has_payload(evidence):
        warnings.append("Optional evidence is missing.")
        return issues, warnings

    if not evidence_has_payload(evidence):
        issues.append("Missing evidence.type or evidence.ref.")
        return issues, warnings

    strength = evidence.get("strength")
    if strength not in VALID_EVIDENCE_STRENGTHS:
        issues.append("Missing or invalid evidence.strength.")

    claim_id = evidence.get("claim_id")
    if not claim_id:
        issues.append("Missing evidence.claim_id.")
    elif expected_claim_id and claim_id != expected_claim_id:
        issues.append(f"Evidence claim_id does not match item id: expected {expected_claim_id}.")

    if not evidence.get("proves"):
        issues.append("Missing evidence.proves.")

    mechanism = evidence.get("mechanism")
    if mechanism not in VALID_EVIDENCE_MECHANISMS:
        issues.append("Missing or invalid evidence.mechanism.")

    if require_machine and evidence.get("machine_checkable") is not True:
        issues.append("Machine-checkable evidence is required for this check type.")

    if require_machine and strength != "required_machine":
        issues.append("Machine-checkable claim requires required_machine evidence.")

    if evidence_result(evidence) in INCONCLUSIVE_VALUES and required:
        issues.append("Inconclusive evidence cannot satisfy required acceptance.")

    if strength == "supporting_only" and required and is_pass_status(status_value(item)):
        issues.append("supporting_only evidence cannot support a passed required claim.")

    if strength == "required_machine":
        if evidence_source(evidence) != "trusted":
            issues.append("required_machine evidence requires trusted source.")
        elif evidence.get("ref_type") == "file" and not evidence_ref_within_scope(evidence, allowed_paths or set()):
            issues.append("evidence_ref_outside_scope")
        elif not runtime_bound(evidence, runtime_id):
            issues.append("runtime_mismatch")
        elif not context_bound(evidence, request_step_id):
            issues.append("context_mismatch")
        cache_key = (evidence.get("ref"), evidence.get("ref_type"), evidence.get("ref_check"))
        if evidence_cache is not None and cache_key in evidence_cache:
            ok, reason = evidence_cache[cache_key]
        else:
            ok, reason = check_evidence_ref(workspace, evidence)
            if evidence_cache is not None:
                evidence_cache[cache_key] = (ok, reason)
        if not ok:
            issues.append(f"Reality-bound evidence check failed: {reason}.")

    if evidence_status_conflicts(item, evidence):
        issues.append("Evidence status contradicts declared check status.")

    if evidence.get("machine_checkable") is False and not evidence.get("details"):
        warnings.append("Human-reviewed evidence should include details.")

    return issues, warnings


def check_passed(check):
    if check.get("required", True) is False and check.get("result") in {None, "not_checked"}:
        return True
    result = status_value(check)
    expected = normalize_result(check.get("expected", "pass"))
    if expected == "pass":
        return result in PASS_VALUES
    if expected == "fail":
        return result in FAIL_VALUES
    return result == expected


def evaluate_request(workspace, request, runtime_id=None):
    workspace = Path(workspace).resolve()
    start_time = time.time()
    runtime_id = str(runtime_id or int(start_time * 1000))
    allowed_paths = allowed_evidence_paths(request)
    artifact = request.get("artifact") or {}
    artifacts = request.get("artifacts") or ([artifact] if artifact else [])
    rubric = request.get("rubric") or []
    checks = request.get("checks") or []
    scope = request.get("scope") or request.get("task_id")
    request_step_id = request.get("step_id")
    candidate_files = set(as_list(request.get("candidate_files")))

    block_reasons = []
    fail_reasons = []
    warnings = []
    evidence_cache = {}

    def timeout_result():
        fail_reasons.append("evaluation_timeout")
        result = {
            "status": "evaluated",
            "verdict": "fail",
            "accepted": False,
            "scope": scope,
            "artifact": artifact,
            "artifacts": artifacts,
            "checks": [],
            "rubric": [],
            "block_reasons": block_reasons,
            "fail_reasons": fail_reasons,
            "warnings": warnings,
            "runtime_id": runtime_id,
            "timestamp": now_iso(),
        }
        result["next_steps"] = next_steps_for(fail_reasons)
        return result

    def evaluation_timed_out():
        return time.time() - start_time > MAX_EVAL_TIME_SECONDS

    if not scope:
        block_reasons.append("Missing scope.")
    if not artifacts:
        block_reasons.append("Missing artifact(s).")
    if evaluation_timed_out():
        return timeout_result()
    for artifact_item in artifacts:
        if evaluation_timed_out():
            return timeout_result()
        if not artifact_item.get("path"):
            block_reasons.append("Missing artifact.path.")
            continue
        if not (workspace / artifact_item["path"]).exists():
            block_reasons.append(f"Artifact path does not exist: {artifact_item['path']}")
        if candidate_files and artifact_item["path"] not in candidate_files:
            fail_reasons.append(f"Artifact outside candidate_files scope: {artifact_item['path']}")
        if artifact_item.get("evidence"):
            evidence_issues, evidence_warnings = validate_evidence(
                artifact_item,
                workspace=workspace,
                request_step_id=request_step_id,
                runtime_id=runtime_id,
                allowed_paths=allowed_paths,
                evidence_cache=evidence_cache,
            )
            for issue in evidence_issues:
                fail_reasons.append(f"{artifact_item.get('id') or 'artifact'}: {issue}")
            for warning in evidence_warnings:
                warnings.append(f"{artifact_item.get('id') or 'artifact'}: {warning}")

    if not rubric:
        block_reasons.append("Missing rubric.")
    if not checks:
        block_reasons.append("Missing checks.")

    evaluated_checks = []
    for check in checks:
        if evaluation_timed_out():
            return timeout_result()
        check_type = check.get("type")
        if check_type not in VALID_CHECK_TYPES:
            block_reasons.append(f"Unknown check type: {check_type}")
            continue
        passed = check_passed(check)
        row = {**check, "passed": passed}
        evaluated_checks.append(row)
        expected_claim_id = claim_id_for(check, "check")
        evidence_issues, evidence_warnings = validate_evidence(
            check,
            workspace=workspace,
            request_step_id=request_step_id,
            runtime_id=runtime_id,
            allowed_paths=allowed_paths,
            evidence_cache=evidence_cache,
            expected_claim_id=expected_claim_id,
            require_machine=check_type in MACHINE_REQUIRED_CHECK_TYPES,
        )
        for issue in evidence_issues:
            fail_reasons.append(f"{check.get('id') or check_type}: {issue}")
        for warning in evidence_warnings:
            warnings.append(f"{check.get('id') or check_type}: {warning}")
        if not passed and check.get("required", True):
            fail_reasons.append(check.get("description") or f"Required check failed: {check_type}")
        elif not passed:
            warnings.append(check.get("description") or f"Optional check failed: {check_type}")

    rubric_results = []
    for item in rubric:
        if evaluation_timed_out():
            return timeout_result()
        if "status" in item:
            passed = normalize_result(item.get("status")) in PASS_VALUES
        else:
            passed = bool(item.get("passed", False))
        row = {**item, "passed": passed}
        rubric_results.append(row)
        expected_claim_id = claim_id_for(item, "rubric")
        evidence_issues, evidence_warnings = validate_evidence(
            item,
            workspace=workspace,
            request_step_id=request_step_id,
            runtime_id=runtime_id,
            allowed_paths=allowed_paths,
            evidence_cache=evidence_cache,
            expected_claim_id=expected_claim_id,
            require_machine=False,
        )
        for issue in evidence_issues:
            fail_reasons.append(f"{item.get('id') or 'rubric'}: {issue}")
        for warning in evidence_warnings:
            warnings.append(f"{item.get('id') or 'rubric'}: {warning}")
        if not passed and item.get("required", True):
            fail_reasons.append(item.get("description") or f"Required rubric failed: {item.get('id')}")
        elif not passed:
            warnings.append(item.get("description") or f"Optional rubric failed: {item.get('id')}")

    if block_reasons:
        verdict = "blocked"
    elif fail_reasons and any(row.get("passed") for row in evaluated_checks + rubric_results):
        verdict = "partial"
    elif fail_reasons:
        verdict = "fail"
    elif warnings:
        verdict = "partial"
    else:
        verdict = "pass"

    accepted = verdict == "pass"
    result = {
        "status": "evaluated",
        "verdict": verdict,
        "accepted": accepted,
        "scope": scope,
        "artifact": artifact,
        "artifacts": artifacts,
        "checks": evaluated_checks,
        "rubric": rubric_results,
        "block_reasons": block_reasons,
        "fail_reasons": fail_reasons,
        "warnings": warnings,
        "runtime_id": runtime_id,
        "timestamp": now_iso(),
    }
    if not accepted:
        result["next_steps"] = next_steps_for(fail_reasons)
    return result


def evaluate_file(workspace, request_path, write_log=True, runtime_id=None):
    request = load_json(request_path)
    if request is None:
        return {"status": "error", "error": f"Acceptance request not found: {request_path}"}
    result = evaluate_request(workspace, request, runtime_id=runtime_id)
    if write_log:
        append_jsonl(Path(workspace) / ".brain" / "acceptance_log.jsonl", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate a lean ABW acceptance request.")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--request", required=True, help="Path to acceptance request JSON.")
    parser.add_argument("--no-log", action="store_true", help="Do not append .brain/acceptance_log.jsonl.")
    args = parser.parse_args(argv)

    try:
        result = evaluate_file(args.workspace, args.request, write_log=not args.no_log)
    except Exception as exc:  # noqa: BLE001 - machine-readable CLI errors.
        write_json({"status": "error", "error": str(exc)})
        return 1

    write_json(result)
    if result.get("status") == "error":
        return 1
    return 0 if result.get("verdict") == "pass" else 2


if __name__ == "__main__":
    sys.exit(main())
