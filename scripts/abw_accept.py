import argparse
import json
import sys
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


def validate_evidence(item, *, expected_claim_id=None, require_machine=False):
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


def evaluate_request(workspace, request):
    workspace = Path(workspace).resolve()
    artifact = request.get("artifact") or {}
    artifacts = request.get("artifacts") or ([artifact] if artifact else [])
    rubric = request.get("rubric") or []
    checks = request.get("checks") or []
    scope = request.get("scope") or request.get("task_id")
    candidate_files = set(as_list(request.get("candidate_files")))

    block_reasons = []
    fail_reasons = []
    warnings = []

    if not scope:
        block_reasons.append("Missing scope.")
    if not artifacts:
        block_reasons.append("Missing artifact(s).")
    for artifact_item in artifacts:
        if not artifact_item.get("path"):
            block_reasons.append("Missing artifact.path.")
            continue
        if not (workspace / artifact_item["path"]).exists():
            block_reasons.append(f"Artifact path does not exist: {artifact_item['path']}")
        if candidate_files and artifact_item["path"] not in candidate_files:
            fail_reasons.append(f"Artifact outside candidate_files scope: {artifact_item['path']}")

    if not rubric:
        block_reasons.append("Missing rubric.")
    if not checks:
        block_reasons.append("Missing checks.")

    evaluated_checks = []
    for check in checks:
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
        if "status" in item:
            passed = normalize_result(item.get("status")) in PASS_VALUES
        else:
            passed = bool(item.get("passed", False))
        row = {**item, "passed": passed}
        rubric_results.append(row)
        expected_claim_id = claim_id_for(item, "rubric")
        evidence_issues, evidence_warnings = validate_evidence(
            item,
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
    return {
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
        "timestamp": now_iso(),
    }


def evaluate_file(workspace, request_path, write_log=True):
    request = load_json(request_path)
    if request is None:
        return {"status": "error", "error": f"Acceptance request not found: {request_path}"}
    result = evaluate_request(workspace, request)
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
