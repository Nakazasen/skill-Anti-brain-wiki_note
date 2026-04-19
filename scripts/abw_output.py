import argparse
import json
import sys
from pathlib import Path


REJECTED_OUTPUT = {
    "binding_status": "rejected",
    "current_state": "blocked",
    "reason": "output not produced by runner",
}


def enforce_runner_output(result):
    if not isinstance(result, dict):
        return dict(REJECTED_OUTPUT)

    if "binding_status" not in result or "validation_proof" not in result:
        return dict(REJECTED_OUTPUT)

    if "runtime_id" not in result:
        return dict(REJECTED_OUTPUT)

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
