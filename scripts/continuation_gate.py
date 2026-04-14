import argparse
import fnmatch
import json
import sys
from pathlib import Path


VALID_PERMISSION_CLASSES = {
    "read_only",
    "safe_write",
    "multi_file_write",
    "decision_change",
    "requires_approval",
}

WIKI_TYPE_DIRS = ("concepts", "entities", "timelines", "sources")


def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def write_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def find_decision(decisions, decision_id):
    for decision in decisions.get("decisions", []):
        if decision.get("decision_id") == decision_id:
            return decision
    return None


def find_gap(gaps, gap_id):
    if not gap_id:
        return None
    if isinstance(gaps, list):
        candidates = gaps
    else:
        candidates = gaps.get("gaps", [])
    for gap in candidates:
        if gap.get("gap_id") == gap_id or gap.get("id") == gap_id:
            return gap
    return None


def glob_match(pattern, file_path):
    normalized_pattern = str(pattern).replace("\\", "/")
    normalized_path = str(file_path).replace("\\", "/")
    return fnmatch.fnmatch(normalized_path, normalized_pattern)


def matching_zones(candidate_files, zones, source=None, confidence=None):
    hits = []
    for zone in zones.get("zones", []):
        if source and zone.get("source") != source:
            continue
        if confidence and zone.get("confidence") != confidence:
            continue
        pattern = zone.get("path_pattern", "")
        for file_path in candidate_files:
            if glob_match(pattern, file_path):
                hits.append({"zone": zone, "file": file_path})
    return hits


def default_policy():
    return {
        "step_size_limits": {
            "max_files_for_safe_write": 3,
            "max_lines_for_safe_write": 150,
            "max_files_for_multi_file_write": 8,
            "max_lines_for_multi_file_write": 400,
        }
    }


def budget_for(state, policy):
    return state.get("effective_budget") or policy.get("step_size_limits") or default_policy()["step_size_limits"]


def latest_test_result(step_history, step_id):
    for row in reversed(step_history):
        if row.get("step_id") == step_id:
            return row.get("test_result")
    return None


def file_exists(workspace, subject):
    return (workspace / subject).exists()


def wiki_note_exists(workspace, subject):
    subject_path = workspace / subject
    if subject_path.exists():
        return True
    wiki_path = workspace / "wiki" / subject
    if wiki_path.exists():
        return True
    if not str(subject).endswith(".md"):
        for type_dir in WIKI_TYPE_DIRS:
            if (workspace / "wiki" / type_dir / f"{subject}.md").exists():
                return True
    return False


def resolve_evidence_ref(workspace, ref):
    direct = workspace / ref
    if direct.exists():
        return True

    manifest_prefix = "processed/manifest.jsonl#line-"
    if str(ref).startswith(manifest_prefix):
        raw_line = str(ref)[len(manifest_prefix) :]
        if not raw_line.isdigit():
            return False
        line_no = int(raw_line)
        manifest = workspace / "processed" / "manifest.jsonl"
        if not manifest.exists():
            return False
        lines = manifest.read_text(encoding="utf-8-sig").splitlines()
        if line_no < 1 or line_no > len(lines):
            return False
        try:
            entry = json.loads(lines[line_no - 1])
        except json.JSONDecodeError:
            return False
        return entry.get("status") in {"grounded", "compiled"}

    if (workspace / "wiki" / str(ref)).exists():
        return True

    if not str(ref).endswith(".md"):
        for type_dir in WIKI_TYPE_DIRS:
            if (workspace / "wiki" / type_dir / f"{ref}.md").exists():
                return True
    return False


def modules_related(a, b):
    if not a or not b:
        return False
    return a == b or a in b or b in a


def classify_gap(gap, step):
    if not gap:
        return "non_blocking"
    explicit = gap.get("classification")
    if explicit in {"blocking", "non_blocking", "advisory"}:
        return explicit

    gap_module = gap.get("module")
    step_module = step.get("module")
    if gap_module and step_module:
        return "advisory" if modules_related(gap_module, step_module) else "non_blocking"

    affected_topics = set(as_list(gap.get("affected_topics")))
    if affected_topics:
        haystack = " ".join(as_list(step.get("candidate_files")) + [step.get("title", ""), step.get("description", "")])
        if any(topic and topic in haystack for topic in affected_topics):
            return "blocking"

    for precondition in step.get("preconditions", []):
        if precondition.get("type") == "wiki_note_exists":
            subject = str(precondition.get("subject", ""))
            query = str(gap.get("query", ""))
            if subject and subject in query:
                return "blocking"
    return "advisory"


def evaluate_precondition(workspace, precondition, gaps, step_history):
    kind = precondition.get("type")
    subject = precondition.get("subject")
    expected = precondition.get("expected", True)

    if kind == "file_exists":
        actual = file_exists(workspace, subject)
    elif kind == "file_not_exists":
        actual = not file_exists(workspace, subject)
    elif kind == "test_passes":
        actual = latest_test_result(step_history, subject) == "pass"
    elif kind == "wiki_note_exists":
        actual = wiki_note_exists(workspace, subject)
    elif kind == "gap_not_open":
        gap = find_gap(gaps, subject)
        actual = gap is None or gap.get("status") != "open"
    else:
        return False, f"Unknown or custom precondition type: {kind}"

    if actual != expected:
        return False, precondition.get("description") or f"Precondition failed: {kind}:{subject}"
    return True, None


def safety_score(step, zones, step_history):
    score = 100.0

    blast = step.get("blast_radius")
    if blast == "high":
        score -= 30
    elif blast == "medium":
        score -= 15

    reversibility = step.get("reversibility")
    if reversibility == "irreversible":
        score -= 40
    elif reversibility == "hard":
        score -= 25
    elif reversibility == "moderate":
        score -= 10

    permission = step.get("permission_class")
    if permission == "requires_approval":
        score -= 30
    elif permission == "decision_change":
        score -= 25
    elif permission == "multi_file_write":
        score -= 10

    score -= len(as_list(step.get("affects_decision_ids"))) * 15

    candidate_files = as_list(step.get("candidate_files"))
    score -= len(matching_zones(candidate_files, zones, source="historical", confidence="high")) * 20
    score -= len(matching_zones(candidate_files, zones, source="heuristic_suspected")) * 5

    rollback = step.get("rollback_contract", {})
    if rollback.get("cost") == "high":
        score -= 20
    if rollback.get("confidence") == "low":
        score -= 20
    if rollback.get("method") == "not_rollbackable":
        score -= 30

    score -= float(step.get("estimated_files_touched") or 0) * 5
    score -= float(step.get("estimated_lines_changed") or 0) / 50

    step_id = step.get("step_id")
    module = step.get("module")
    recent_failures = 0
    for row in step_history[-5:]:
        if row.get("outcome") != "failed":
            continue
        if row.get("step_id") == step_id or (module and row.get("module") == module):
            recent_failures += 1
    score -= recent_failures * 20
    return max(0.0, round(score, 2))


def block(result, reason):
    result["allowed"] = False
    result["block_reasons"].append(reason)


def constrain_gate(workspace, step, state, policy, decisions, zones, gaps, step_history):
    result = {
        "step_id": step.get("step_id"),
        "allowed": True,
        "permission_class": step.get("permission_class"),
        "warnings": [],
        "block_reasons": [],
        "required_approvals": [],
        "safety_score": safety_score(step, zones, step_history),
    }

    permission = step.get("permission_class")
    if permission not in VALID_PERMISSION_CLASSES:
        block(result, f"Invalid permission class: {permission}")
        return result

    candidate_files = as_list(step.get("candidate_files"))
    if permission != "read_only" and not candidate_files:
        block(result, "candidate_files is required for non-read-only steps")
        return result

    budget = budget_for(state, policy)
    files = int(step.get("estimated_files_touched") or 0)
    lines = int(step.get("estimated_lines_changed") or 0)

    if permission == "safe_write":
        if files > int(budget.get("max_files_for_safe_write", 3)):
            block(result, "Exceeds safe_write file budget")
            return result
        if lines > int(budget.get("max_lines_for_safe_write", 150)):
            block(result, "Exceeds safe_write line budget")
            return result

    if permission == "multi_file_write":
        if files > int(budget.get("max_files_for_multi_file_write", 8)):
            block(result, "Exceeds multi_file_write file budget")
            return result
        if lines > int(budget.get("max_lines_for_multi_file_write", 400)):
            block(result, "Exceeds multi_file_write line budget")
            return result

    if step.get("surface_type") in {"security", "migration"} and permission == "safe_write":
        result["permission_class"] = "requires_approval"
        result["warnings"].append("Surface type is incompatible with safe_write; downgraded to requires_approval")

    for hit in matching_zones(candidate_files, zones):
        zone = hit["zone"]
        file_path = hit["file"]
        source = zone.get("source")
        confidence = zone.get("confidence")
        zone_id = zone.get("zone_id", "unknown")
        if source == "user_declared" and confidence == "high":
            block(result, f"Blocked by user-declared unsafe zone {zone_id}: {file_path}")
            return result
        if source == "historical" and confidence == "high":
            result["required_approvals"].append(f"Historical unsafe zone {zone_id} requires /abw-audit before change")
        if source == "heuristic_suspected":
            result["warnings"].append(f"Heuristic-suspected unsafe zone {zone_id}: {zone.get('reason', '')}")

    for decision_id in as_list(step.get("affects_decision_ids")):
        decision = find_decision(decisions, decision_id)
        if not decision:
            continue
        if not decision.get("override_allowed", False):
            block(result, f"Decision does not allow override: {decision_id}")
            return result
        if decision.get("override_requires_evidence_delta", True):
            refs = as_list(step.get("evidence_delta_refs"))
            if not refs:
                block(result, f"Missing evidence_delta_refs for decision override: {decision_id}")
                return result
            for ref in refs:
                if not resolve_evidence_ref(workspace, ref):
                    block(result, f"Evidence ref not resolved: {ref}")
                    return result
        if decision.get("override_requires_approval", True):
            result["required_approvals"].append(f"Override locked decision: {decision_id}")

    gap_id = step.get("blocked_by_gap")
    if gap_id:
        gap = find_gap(gaps, gap_id)
        classification = classify_gap(gap, step)
        if classification == "blocking":
            block(result, f"Blocked by knowledge gap: {gap_id}")
            return result
        if classification == "advisory":
            result["warnings"].append(f"Advisory knowledge gap: {gap_id}")

    rollback = step.get("rollback_contract", {})
    if rollback.get("cost") == "high" or rollback.get("confidence") == "low":
        result["permission_class"] = "requires_approval"
        result["required_approvals"].append("Risky rollback requires approval")
    if rollback.get("method") == "not_rollbackable":
        result["permission_class"] = "requires_approval"
        result["required_approvals"].append("Step is not rollbackable")

    for precondition in step.get("preconditions", []):
        ok, reason = evaluate_precondition(workspace, precondition, gaps, step_history)
        if not ok:
            block(result, reason)
            return result

    return result


def hard_pre_filter(step, decisions, zones, gaps):
    candidate_files = as_list(step.get("candidate_files"))
    for hit in matching_zones(candidate_files, zones, source="user_declared", confidence="high"):
        return False, f"pre-filter: user-declared unsafe zone {hit['zone'].get('zone_id')}"

    for decision_id in as_list(step.get("affects_decision_ids")):
        decision = find_decision(decisions, decision_id)
        if decision and not decision.get("override_allowed", False):
            return False, f"pre-filter: decision does not allow override {decision_id}"

    gap_id = step.get("blocked_by_gap")
    if gap_id:
        classification = classify_gap(find_gap(gaps, gap_id), step)
        if classification == "blocking":
            return False, f"pre-filter: blocking knowledge gap {gap_id}"
    return True, None


def choose_allowed(results):
    allowed = [r for r in results if r.get("allowed")]
    if not allowed:
        return None
    return sorted(
        allowed,
        key=lambda r: (
            len(r.get("required_approvals", [])) > 0,
            len(r.get("required_approvals", [])),
            len(r.get("warnings", [])),
            -float(r.get("safety_score", 0)),
        ),
    )[0]


def load_workspace(workspace):
    brain = workspace / ".brain"
    return {
        "state": load_json(brain / "resume_state.json", {}),
        "backlog": load_json(brain / "continuation_backlog.json", {"steps": []}),
        "decisions": load_json(brain / "locked_decisions.json", {"decisions": []}),
        "zones": load_json(brain / "unsafe_zones.json", {"zones": []}),
        "policy": load_json(brain / "continuation_policy.json", default_policy()),
        "gaps": load_json(brain / "knowledge_gaps.json", {"gaps": []}),
        "step_history": load_jsonl(brain / "step_history.jsonl"),
    }


def evaluate_workspace(workspace, step_id=None, top=3):
    data = load_workspace(workspace)
    steps = data["backlog"].get("steps", [])
    if step_id:
        steps = [s for s in steps if s.get("step_id") == step_id]
    else:
        steps = [s for s in steps if s.get("status") == "pending"]

    prefiltered = []
    skipped = []
    for step in steps:
        keep, reason = hard_pre_filter(step, data["decisions"], data["zones"], data["gaps"])
        if keep:
            prefiltered.append(step)
        else:
            skipped.append({"step_id": step.get("step_id"), "reason": reason})

    ranked = sorted(
        prefiltered,
        key=lambda s: safety_score(s, data["zones"], data["step_history"]),
        reverse=True,
    )
    candidates = ranked if step_id else ranked[:top]
    results = [
        constrain_gate(
            workspace,
            step,
            data["state"],
            data["policy"],
            data["decisions"],
            data["zones"],
            data["gaps"],
            data["step_history"],
        )
        for step in candidates
    ]
    selected = choose_allowed(results)
    return {
        "status": "selected" if selected else "blocked",
        "selected": selected,
        "candidates": results,
        "skipped": skipped,
        "candidate_count": len(candidates),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Evaluate Continuation Kernel next-safe-step gate.")
    parser.add_argument("--workspace", default=".", help="Workspace root containing .brain/")
    parser.add_argument("--step-id", help="Evaluate only this step_id")
    parser.add_argument("--top", type=int, default=3, help="Number of ranked pending candidates to gate")
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).resolve()
    try:
        result = evaluate_workspace(workspace, step_id=args.step_id, top=args.top)
    except Exception as exc:  # noqa: BLE001 - CLI should return machine-readable error.
        write_json({"status": "error", "error": str(exc)})
        return 1

    write_json(result)
    return 0 if result["status"] == "selected" else 2


if __name__ == "__main__":
    sys.exit(main())
