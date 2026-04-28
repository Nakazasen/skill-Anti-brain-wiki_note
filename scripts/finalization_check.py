import argparse
import json
import re
import sys
from pathlib import Path


STATE_ORDER = {
    "blocked": 0,
    "recoverable": 1,
    "code_changed_only": 1,
    "runs_one_case": 2,
    "checked_only": 3,
    "verified": 4,
    "knowledge_gap_logged": 1,
    "knowledge_answered": 2,
}

KNOWLEDGE_STATES = {
    "knowledge_answered",
    "knowledge_gap_logged",
}

KNOWLEDGE_EVIDENCE_TIERS = {
    "E0_unknown",
    "E1_fallback",
    "E2_wiki",
    "E3_grounded",
}

TASK_RUNTIME_REQUIRED = {
    "fix",
    "debug",
    "run",
    "reproduce",
    "verify",
}

STATIC_ONLY_EVIDENCE = (
    "code changed",
    "code edits",
    "static reasoning",
    "static analysis",
    "prompt only",
    "docs only",
)

WEAK_RUNTIME_HINTS = (
    "one case",
    "single case",
    "smoke test",
    "smoke",
    "one run",
    "example run",
)

RUNTIME_EVIDENCE = (
    "terminal output",
    "test output",
    "log",
    "logs",
    "stdout",
    "stderr",
    "exit code",
    "passed",
    "failed",
    "executed",
    "ran",
    "reproduced",
    "verified by",
)

CONTRADICTION_HINTS = (
    "not rerun",
    "not tested",
    "not verified",
    "uncertain",
    "unverified",
    "no runtime",
    "no proof",
    "not checked",
)


def extract_block(text):
    match = re.search(r"## Finalization\s*(.*)", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None

    block = match.group(1)
    lines = []
    for raw in block.splitlines():
        stripped = raw.strip()
        if not stripped:
            if lines:
                break
            continue
        if stripped.startswith("```") and lines:
            break
        if stripped.startswith("```"):
            continue
        lines.append(stripped)
    return lines


def parse_block(lines):
    parsed = {}
    for line in lines:
        if not line.startswith("- "):
            continue
        body = line[2:]
        if ":" not in body:
            continue
        key, value = body.split(":", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def classify_evidence(evidence_text):
    lowered = evidence_text.lower()
    has_runtime = any(token in lowered for token in RUNTIME_EVIDENCE)
    has_weak_runtime = any(token in lowered for token in WEAK_RUNTIME_HINTS)
    static_only = any(token in lowered for token in STATIC_ONLY_EVIDENCE)
    return {
        "runtime": has_runtime,
        "weak_runtime": has_weak_runtime,
        "static_only": static_only and not has_runtime,
    }


def classify_gaps(gaps_text):
    lowered = gaps_text.lower()
    return any(token in lowered for token in CONTRADICTION_HINTS)


def downgrade_state(current_state, evidence_kind, task_kind):
    if current_state == "blocked":
        return "blocked"

    if current_state == "knowledge_answered" and task_kind == "knowledge":
        return "knowledge_gap_logged"

    if current_state == "verified":
        if evidence_kind["static_only"]:
            return "code_changed_only"
        if evidence_kind["weak_runtime"]:
            return "runs_one_case"
        if task_kind in TASK_RUNTIME_REQUIRED and not evidence_kind["runtime"]:
            return "blocked"
        if not evidence_kind["runtime"]:
            return "checked_only"

    if current_state == "checked_only":
        if evidence_kind["static_only"]:
            return "code_changed_only"
        if evidence_kind["weak_runtime"]:
            return "runs_one_case"

    if current_state == "runs_one_case":
        if evidence_kind["static_only"]:
            return "code_changed_only"

    return current_state


def check_finalization(payload, task_kind):
    current_state = payload.get("current_state", "").strip()
    evidence = payload.get("evidence", "").strip()
    gaps = payload.get("gaps_or_limitations", "").strip()
    next_steps = payload.get("next_steps", "").strip()
    knowledge_tier = payload.get("knowledge_evidence_tier", "").strip()

    if current_state.startswith("knowledge"):
        return "pass", "knowledge state is classified without hard blocking"

    if not current_state or not evidence or not gaps or not next_steps:
        return "blocked", "missing required finalization field(s)"

    evidence_kind = classify_evidence(evidence)
    has_contradiction = classify_gaps(gaps)

    if current_state == "blocked":
        if not next_steps:
            return "blocked", "blocked state requires non-empty next_steps"
        return "pass", "blocked state is consistent"

    if current_state in KNOWLEDGE_STATES:
        if not evidence:
            return "blocked", "knowledge state requires evidence"
        if knowledge_tier and knowledge_tier not in KNOWLEDGE_EVIDENCE_TIERS:
            return "downgrade", f"unknown knowledge_evidence_tier: {knowledge_tier}"
        if current_state == "knowledge_answered" and knowledge_tier == "E0_unknown":
            return "downgrade", "E0_unknown knowledge answer must be downgraded unless a gap is logged"
        return "pass", "knowledge state is acceptable"

    if current_state == "verified":
        if evidence_kind["static_only"]:
            return "downgrade", "verified requires runtime-style evidence, but evidence is static only"
        if evidence_kind["weak_runtime"]:
            return "downgrade", "verified is too strong for a single weak runtime signal"
        if not evidence_kind["runtime"]:
            return "downgrade", "verified lacks directly checkable evidence"

    if current_state == "checked_only":
        if evidence_kind["static_only"]:
            return "downgrade", "static-only evidence supports at most code_changed_only"
        if evidence_kind["weak_runtime"]:
            return "downgrade", "weak runtime evidence supports at most runs_one_case"

    if current_state == "runs_one_case":
        if evidence_kind["static_only"]:
            return "downgrade", "evidence is static only, so strongest allowed state is code_changed_only"

    if task_kind in TASK_RUNTIME_REQUIRED and not evidence_kind["runtime"]:
        if evidence_kind["weak_runtime"]:
            return "downgrade", f"{task_kind}-style task only has one weak runtime signal"
        if evidence_kind["static_only"]:
            return "downgrade", f"{task_kind}-style task only has static evidence"
        return "downgrade", f"{task_kind}-style task lacks runtime evidence"

    if has_contradiction and current_state in {"verified", "checked_only"}:
        return "downgrade", "gaps_or_limitations contradict strong completion"

    if current_state == "verified" and not evidence_kind["runtime"] and evidence_kind["static_only"]:
        return "downgrade", "verified cannot rest on static reasoning alone"

    if current_state not in STATE_ORDER:
        return "blocked", f"unknown current_state: {current_state}"

    return "pass", "finalization state is acceptable"


def read_input(args):
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    return sys.stdin.read()


def main():
    parser = argparse.ArgumentParser(description="Sanity-check an ABW finalization block.")
    parser.add_argument("--file", help="Path to a text file containing a Finalization block")
    parser.add_argument("--task-kind", default="", help="Optional task kind: fix/debug/run/reproduce/verify")
    args = parser.parse_args()

    text = read_input(args)
    lines = extract_block(text)
    if not lines:
        report = {
            "decision": "blocked",
            "reason": "Finalization block not found",
            "state": None,
            "checked_state": None,
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 2

    payload = parse_block(lines)
    current_state = payload.get("current_state", "").strip()
    decision, reason = check_finalization(payload, args.task_kind.strip().lower())
    checked_state = current_state
    if decision == "downgrade":
        checked_state = downgrade_state(
            current_state,
            classify_evidence(payload.get("evidence", "")),
            args.task_kind.strip().lower(),
        )

    report = {
        "decision": decision,
        "reason": reason,
        "state": current_state,
        "checked_state": checked_state,
        "evidence": payload.get("evidence", ""),
        "gaps_or_limitations": payload.get("gaps_or_limitations", ""),
        "next_steps": payload.get("next_steps", ""),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if decision == "pass":
        return 0
    if decision == "downgrade":
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
