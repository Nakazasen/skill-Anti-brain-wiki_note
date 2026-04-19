import argparse
import json
import re
import sys
from pathlib import Path


REJECTED_OUTPUT = {
    "binding_status": "rejected",
    "current_state": "blocked",
    "reason": "output not produced by runner",
}
ALLOWED_BINDING_STATUS = {
    "runner_enforced",
    "runner_checked",
    "prompt_only",
    "rejected",
}
ALLOWED_BINDING_SOURCES = {"cli", "mcp"}
RUNTIME_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
NONCE_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def strict_schema_validation(result):
    if not isinstance(result, dict):
        return "output not produced by runner"

    binding_status = str(result.get("binding_status") or "").strip()
    if binding_status not in ALLOWED_BINDING_STATUS:
        return "invalid binding_status"

    runtime_id = str(result.get("runtime_id") or "").strip()
    if not runtime_id or not RUNTIME_ID_PATTERN.fullmatch(runtime_id):
        return "invalid runtime_id"

    validation_proof = str(result.get("validation_proof") or "").strip()
    if not SHA256_PATTERN.fullmatch(validation_proof):
        return "invalid validation_proof"

    binding_source = str(result.get("binding_source") or "").strip().lower()
    if binding_source not in ALLOWED_BINDING_SOURCES:
        return "invalid binding_source"

    nonce = str(result.get("nonce") or "").strip().lower()
    if not NONCE_PATTERN.fullmatch(nonce):
        return "invalid nonce"

    answer = str(result.get("answer") or "").strip()
    if not answer:
        return "empty answer"

    finalization_block = str(result.get("finalization_block") or "").strip()
    if not finalization_block:
        return "missing finalization_block"

    return None


def enforce_runner_output(result):
    reason = strict_schema_validation(result)
    if reason:
        rejected = dict(REJECTED_OUTPUT)
        rejected["reason"] = reason
        return rejected

    return result


def _load_payload(args):
    if args.file:
        return json.loads(Path(args.file).read_text(encoding="utf-8"))

    raw = sys.stdin.read()
    if not raw.strip():
        return None
    return json.loads(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Outer binding shim for ABW runner outputs.")
    parser.add_argument("--file", help="Path to a JSON payload to validate.")
    args = parser.parse_args(argv)

    try:
        result = enforce_runner_output(_load_payload(args))
    except Exception:
        result = dict(REJECTED_OUTPUT)

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("binding_status") != "rejected" else 3


if __name__ == "__main__":
    raise SystemExit(main())
