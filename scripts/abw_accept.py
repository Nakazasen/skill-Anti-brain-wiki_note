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

PASS_VALUES = {"pass", "passed", "ok", "true", True, 0}
FAIL_VALUES = {"fail", "failed", "error", "false", False}


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


def check_passed(check):
    if check.get("required", True) is False and check.get("result") in {None, "not_checked"}:
        return True
    result = normalize_result(check.get("result"))
    expected = normalize_result(check.get("expected", "pass"))
    if expected == "pass":
        return result in PASS_VALUES
    if expected == "fail":
        return result in FAIL_VALUES
    return result == expected


def evaluate_request(workspace, request):
    workspace = Path(workspace).resolve()
    artifact = request.get("artifact") or {}
    rubric = request.get("rubric") or []
    checks = request.get("checks") or []
    scope = request.get("scope")

    block_reasons = []
    fail_reasons = []
    warnings = []

    if not scope:
        block_reasons.append("Missing scope.")
    if not artifact.get("id") or not artifact.get("path"):
        block_reasons.append("Missing artifact.id or artifact.path.")
    elif not (workspace / artifact["path"]).exists():
        block_reasons.append(f"Artifact path does not exist: {artifact['path']}")

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
        if not passed and check.get("required", True):
            fail_reasons.append(check.get("description") or f"Required check failed: {check_type}")
        elif not passed:
            warnings.append(check.get("description") or f"Optional check failed: {check_type}")

    rubric_results = []
    for item in rubric:
        passed = bool(item.get("passed", False))
        row = {**item, "passed": passed}
        rubric_results.append(row)
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
    else:
        verdict = "pass"

    accepted = verdict == "pass"
    return {
        "status": "evaluated",
        "verdict": verdict,
        "accepted": accepted,
        "scope": scope,
        "artifact": artifact,
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
