# Spec: Continuation Kernel v1

> **Version:** 0.6.0-draft
> **Status:** Spec for review
> **Target:** Small/fast models such as Gemini Flash
> **Principle:** "Không cần giỏi hơn. Chỉ cần khó phá hơn."

Continuation Kernel v1 là lớp governance cho phép một model nhỏ tiếp quản project đang dang dở mà không phá continuity, không lật quyết định cũ vô cớ, và chỉ chọn bước đủ nhỏ để rollback được nếu sai.

Nó không thay thế ABW Truth OS. Nó bổ sung Action Governance: kiểm soát quyền hành động của model nhỏ.

Truth OS trả lời: cái gì đúng, có nguồn, đã grounded, stale, disputed, hay missing?
Continuation Kernel trả lời: model được phép làm gì tiếp theo mà không phá project?

---

## 0. Changelog

### v0.5.0 -> v0.6.0

| # | Severity | Finding | Fix |
|---|---|---|---|
| 1 | Medium | Approval risk chỉ xuất hiện sau gate, nên candidate ranking chưa phạt approval burden từ `historical+high` unsafe zones. | `safety_score()` thêm penalty cho `historical+high` overlaps và `heuristic_suspected` warnings trước gate. |
| 2 | Medium | Workflow chọn candidate đầu tiên có `allowed=true`, nên có thể ưu tiên step cần approval dù có step an toàn hơn. | Phase 3 thu tất cả allowed candidates rồi ưu tiên: không approval -> ít approval hơn -> ít warning hơn -> safety score cao hơn. |

### Previous review fixes

| Version | Main fixes |
|---|---|
| `0.5.0` | Tách unsafe-zone behavior thành `user_declared` hard block, `historical+high` approval, và `heuristic_suspected` warning. Thêm `not_rollbackable` handling. |
| `0.4.0` | Enforce cả file budget và line budget. Thêm ABW evidence-ref resolver thay vì chỉ dùng `os.path.exists`. |
| `0.3.0` | Thêm `effective_budget`, `evidence_delta_refs`, cached test lookup bằng `step_id`, và sửa pre-constrain behavior. |
| `0.2.1` | Thay `step.files` bằng `candidate_files`, typed predicates, `module`, `proposed_steps`, và workflow 4 pha. |
| `0.2.0` | Thêm candidate-file matching, gap classification adapter, decision-touch metadata, safety-score candidate selection. |

---

## 1. Goal

V1 trả lời 4 câu:

1. Project đang ở đâu?
2. Step nào là next safe step?
3. Step đó có được phép làm không?
4. Nếu fail thì rollback thế nào?

**V1 không phải execution engine.** V1 là gate trước khi execute. Execution vẫn cần user confirm.

---

## 2. Artifact Layers

### Layer 1: State

| File | Purpose |
|---|---|
| `.brain/resume_state.json` | Phase, objective, active step, completed steps, proposed steps, adaptive budget. |
| `.brain/continuation_backlog.json` | Approved pending steps, mỗi step có preconditions, exit criteria, candidate files, rollback contract. |

### Layer 2: Governance

| File | Purpose |
|---|---|
| `.brain/locked_decisions.json` | Quyết định đã chốt, không được lật nếu thiếu evidence delta và approval. |
| `.brain/unsafe_zones.json` | Vùng code model không được tự ý đụng. |
| `.brain/continuation_policy.json` | Base limits, permission classes, gap rules, step-size policy. |

### Layer 3: Execution Control

| Component | Purpose |
|---|---|
| Constrain Gate | Internal mandatory validation trước khi một backlog item được chọn làm next safe step. |
| Permission Class | Mức quyền hành động của step. |
| Rollback Contract | Cách undo step và độ rủi ro rollback. |

### Layer 4: Learning

| File | Purpose |
|---|---|
| `.brain/handover_log.jsonl` | Append-only history của resume, choice, approval, handover. |
| `.brain/step_history.jsonl` | Outcome từng step, dùng để co/giãn budget cho step tiếp theo. |

---

## 3. Minimal Schemas

### `.brain/resume_state.json`

```json
{
  "project_id": "string",
  "phase": "discovery | planning | implementation | testing | delivery",
  "current_objective": "string",
  "last_completed_step": "string | null",
  "active_step": "string | null",
  "blocked_steps": ["step_id"],
  "completed_steps": ["step_id"],
  "context_summary": "short summary under 500 characters",
  "continued_from_session": "session_id | null",
  "last_updated_at": "ISO 8601",
  "proposed_steps": [],
  "effective_budget": {
    "max_files_for_safe_write": 3,
    "max_lines_for_safe_write": 150,
    "max_files_for_multi_file_write": 8,
    "max_lines_for_multi_file_write": 400,
    "adjusted_from_history": false,
    "last_adjustment": "ISO 8601 | null",
    "consecutive_successes": 0,
    "recent_failure_count": 0
  }
}
```

### `.brain/continuation_backlog.json`

```json
{
  "steps": [
    {
      "step_id": "string",
      "title": "string",
      "description": "string",
      "permission_class": "read_only | safe_write | multi_file_write | decision_change | requires_approval",
      "candidate_files": ["path/or/glob"],
      "preconditions": [
        {
          "type": "file_exists | file_not_exists | test_passes | wiki_note_exists | gap_not_open | custom",
          "subject": "string",
          "expected": true,
          "description": "string"
        }
      ],
      "exit_criteria": [
        {
          "type": "file_exists | test_passes | lint_clean | user_verified | wiki_updated | custom",
          "subject": "string",
          "description": "string"
        }
      ],
      "affects_decision_ids": ["decision_id"],
      "evidence_delta_refs": ["wiki/concepts/example.md", "processed/manifest.jsonl#line-42", "raw/source.pdf"],
      "estimated_files_touched": 0,
      "estimated_lines_changed": 0,
      "blast_radius": "low | medium | high",
      "reversibility": "easy | moderate | hard | irreversible",
      "surface_type": "test | doc | feature | refactor | config | migration | security",
      "module": "string",
      "rollback_contract": {
        "method": "git revert | restore file | restore backup | manual undo | not_rollbackable | string",
        "cost": "low | medium | high",
        "confidence": "high | medium | low"
      },
      "blocked_by_gap": "gap_id | null",
      "status": "pending | active | completed | failed | blocked",
      "created_at": "ISO 8601"
    }
  ]
}
```

`candidate_files` là bắt buộc cho mọi step không phải `read_only`. Không có `candidate_files` thì gate không thể check unsafe zones và phải block step.

### `.brain/locked_decisions.json`

```json
{
  "decisions": [
    {
      "decision_id": "string",
      "title": "string",
      "decision": "string",
      "rationale": "string",
      "evidence_refs": ["wiki/manifest/source ref"],
      "locked_at": "ISO 8601",
      "locked_by": "user | model | agent",
      "override_allowed": true,
      "override_requires_evidence_delta": true,
      "override_requires_approval": true,
      "override_history": []
    }
  ]
}
```

### `.brain/unsafe_zones.json`

```json
{
  "zones": [
    {
      "zone_id": "string",
      "path_pattern": "src/auth/**",
      "reason": "security-sensitive area",
      "source": "user_declared | historical | heuristic_suspected",
      "confidence": "high | medium | low",
      "restrictions": ["no_refactor", "no_rename", "no_mass_edit", "requires_audit_before_change"],
      "created_at": "ISO 8601",
      "created_by": "user | model | heuristic"
    }
  ]
}
```

Unsafe-zone behavior:

- `user_declared + high confidence`: hard block until the user unlocks it.
- `historical + high confidence`: allowed only with required approval and `/abw-audit`.
- `heuristic_suspected`: allow with warning; never hard block by itself.

### `.brain/continuation_policy.json`

```json
{
  "step_size_limits": {
    "max_files_for_safe_write": 3,
    "max_lines_for_safe_write": 150,
    "max_files_for_multi_file_write": 8,
    "max_lines_for_multi_file_write": 400
  },
  "gate_exit_rules": {
    "step_fail_action": "log to step_history and shrink next step size by 50%",
    "step_success_3x": "increase effective budget by 20%, never above policy max",
    "irreversible_step": "always requires approval"
  }
}
```

Policy limits là base limits. Runtime selection dùng `resume_state.effective_budget` nếu có.

---

## 4. Permission Classes

| Class | Allowed scope | Limit | Approval |
|---|---|---|---|
| `read_only` | Read files, wiki, state, logs. | No writes. | No |
| `safe_write` | Small local change. | `safe_write` budget; not security/migration. | Usually no |
| `multi_file_write` | Larger bounded change. | `multi_file_write` budget; not security/migration. | Post-check required |
| `decision_change` | May override a locked decision. | Must follow decision override rules. | Required |
| `requires_approval` | Anything outside the safe classes. | Explicit user confirmation. | Required |

---

## 5. Constrain Gate

Constrain Gate là internal mandatory validation. Nó không phải public command trong v1.

Machine-checkable implementation: `scripts/continuation_gate.py`.

Preferred invocation:

```bash
python scripts/continuation_gate.py --workspace .
```

The script output is JSON and should be treated as the source of truth when available. The markdown rules below define the policy and fallback behavior.

### Inputs

- step từ `.brain/continuation_backlog.json`
- `.brain/resume_state.json`
- `.brain/locked_decisions.json`
- `.brain/unsafe_zones.json`
- `.brain/continuation_policy.json`
- `.brain/knowledge_gaps.json`
- `.brain/step_history.jsonl`

### Output

```json
{
  "allowed": true,
  "permission_class": "safe_write",
  "warnings": [],
  "block_reasons": [],
  "required_approvals": []
}
```

### Checks

| # | Check | Rule |
|---|---|---|
| 1 | Permission class | Unknown class blocks the step. |
| 2 | Size | Enforce both `estimated_files_touched` and `estimated_lines_changed` against `effective_budget`. |
| 3 | Surface type | `security` and `migration` cannot be `safe_write`; downgrade to `requires_approval`. |
| 4 | Unsafe zones | `user_declared+high` blocks; `historical+high` adds approval; `heuristic_suspected` emits warning. |
| 5 | Locked decisions | Any affected locked decision must allow override and have explicit evidence delta refs. |
| 6 | Knowledge gaps | Blocking gaps block; advisory gaps warn; non-blocking gaps pass. |
| 7 | Rollback | `cost=high`, `confidence=low`, or `method=not_rollbackable` downgrades to `requires_approval`. |
| 8 | Preconditions | Typed preconditions must pass. Unknown predicates fail safe. |

### Pseudocode

```text
function constrain_gate(step, state, policy, decisions, zones, gaps, step_history):
    result = {
        allowed: true,
        permission_class: step.permission_class,
        warnings: [],
        block_reasons: [],
        required_approvals: []
    }

    budget = state.effective_budget if state.effective_budget else policy.step_size_limits

    if step.permission_class not in permission_class_rules:
        block("Invalid permission class")

    if step.permission_class == "safe_write":
        enforce step.estimated_files_touched <= budget.max_files_for_safe_write
        enforce step.estimated_lines_changed <= budget.max_lines_for_safe_write

    if step.permission_class == "multi_file_write":
        enforce step.estimated_files_touched <= budget.max_files_for_multi_file_write
        enforce step.estimated_lines_changed <= budget.max_lines_for_multi_file_write

    if step.surface_type in ["security", "migration"] and step.permission_class == "safe_write":
        result.permission_class = "requires_approval"
        warn("Surface type incompatible with safe_write")

    for zone in zones:
        for file in step.candidate_files:
            if not glob_match(zone.path_pattern, file):
                continue
            if zone.source == "user_declared" and zone.confidence == "high":
                block("Blocked by user-declared unsafe zone")
            if zone.source == "historical" and zone.confidence == "high":
                require_approval("Historical unsafe zone requires /abw-audit")
            if zone.source == "heuristic_suspected":
                warn("Heuristic-suspected unsafe zone")

    for decision_id in step.affects_decision_ids:
        decision = find_decision(decision_id)
        if decision is null:
            continue
        if not decision.override_allowed:
            block("Decision does not allow override")
        if decision.override_requires_evidence_delta:
            if step.evidence_delta_refs is empty:
                block("Missing evidence_delta_refs")
            for ref in step.evidence_delta_refs:
                if not resolve_evidence_ref(ref):
                    block("Evidence ref not resolved")
        if decision.override_requires_approval:
            require_approval("Override locked decision")

    if step.blocked_by_gap:
        gap = find_gap(step.blocked_by_gap)
        classification = get_gap_classification(gap, step)
        if classification == "blocking":
            block("Blocked by knowledge gap")
        if classification == "advisory":
            warn("Advisory knowledge gap")

    if step.rollback_contract.cost == "high" or step.rollback_contract.confidence == "low":
        result.permission_class = "requires_approval"
        require_approval("Risky rollback")

    if step.rollback_contract.method == "not_rollbackable":
        result.permission_class = "requires_approval"
        require_approval("Step is not rollbackable")

    for precondition in step.preconditions:
        if not evaluate_precondition(precondition, state, gaps, decisions, step_history):
            block("Precondition not met")

    return result
```

---

## 6. Typed Preconditions

| Type | Subject | Evaluation |
|---|---|---|
| `file_exists` | file path | Check filesystem. |
| `file_not_exists` | file path | Check filesystem. |
| `test_passes` | `step_id` only | Read latest matching entry in `.brain/step_history.jsonl`; never execute tests inside the gate. |
| `wiki_note_exists` | wiki note id or path | Resolve under `wiki/`. |
| `gap_not_open` | gap id | Pass if gap is absent or not open. |
| `custom` | string | Allowed only as a warning-producing model judgment; avoid in v1 when possible. |

Unknown precondition types fail safe.

---

## 7. Knowledge Gap Classification

| Classification | When | Action |
|---|---|---|
| `blocking` | Gap directly affects the step module, candidate files, or required wiki precondition. | Block and suggest `/abw-ingest` or grounding first. |
| `non_blocking` | Gap belongs to a clearly unrelated module. | Allow without warning. |
| `advisory` | Relevant but not required, or unclear. | Allow with warning. |

Default is `advisory`, not `blocking`, unless direct dependency is detected.

---

## 8. Evidence Ref Resolver

`evidence_delta_refs` must be explicit typed data, not inferred from free-form description.

Valid refs:

- file path: `raw/benchmark.pdf`
- wiki path: `wiki/concepts/topic.md`
- manifest line ref: `processed/manifest.jsonl#line-42`
- wiki note id: `kubernetes-networking`, resolved under known wiki folders

```text
function resolve_evidence_ref(ref):
    if file_exists(ref): return true
    if ref starts with "processed/manifest.jsonl#line-":
        return manifest line exists and status in ["grounded", "compiled"]
    for dir in ["concepts", "entities", "timelines", "sources"]:
        if file_exists("wiki/" + dir + "/" + ref + ".md"): return true
    if file_exists("wiki/" + ref): return true
    return false
```

---

## 9. Decision Override

To override a locked decision:

1. `affects_decision_ids` must explicitly reference the decision.
2. The decision must have `override_allowed = true`.
3. If required, `evidence_delta_refs` must resolve through the ABW evidence resolver.
4. If required, user approval is mandatory.
5. The override must be appended to `override_history`.

The model is never allowed to reverse a locked decision because the new option "seems better".

---

## 10. Unsafe Zone Override

| Zone type | Gate behavior |
|---|---|
| `user_declared + high` | Hard block. Only the user can unlock. |
| `historical + high` | Allowed only with required approval and `/abw-audit` before change. |
| `heuristic_suspected` | Allow with warning and reduced safety score. |

Heuristics do not have sovereign power. They create suspicion, not law.

---

## 11. Rollback Contract

Every writable step needs a rollback contract.

```json
{
  "method": "git revert | restore file | restore backup | manual undo | not_rollbackable",
  "cost": "low | medium | high",
  "confidence": "high | medium | low"
}
```

Rules:

- `cost = high` requires approval and downgrades permission to `requires_approval`.
- `confidence = low` requires approval and downgrades permission to `requires_approval`.
- `method = not_rollbackable` requires approval and downgrades permission to `requires_approval`.

A step is not safe merely because it is small. It must also be reversible enough.

---

## 12. Workflow: `/abw-resume` v1

### Trigger

Run when the user says variants of:

- "tiếp tục project"
- "resume"
- "làm tiếp"
- "giờ làm gì"
- "project đang dở"

### Phase 1: Reconstruct

1. Read `.brain/resume_state.json`.
2. If missing, infer initial state from `.brain/`, `wiki/`, and git history.
3. Read `.brain/continuation_backlog.json`.
4. Read `.brain/step_history.jsonl`.
5. Compute `effective_budget`:
   - last step failed: shrink by 50%
   - three consecutive successes: increase by 20%, never above policy max

### Step Synthesis Boundary

If backlog is empty:

- The model may propose draft steps in `resume_state.proposed_steps`.
- The model must not directly add those steps to `continuation_backlog.json`.
- The user must approve, reject, or edit proposed steps before they become real backlog items.

### Phase 2: Select Candidate Steps

1. Collect steps with `status = pending`.
2. Run Pre-Constrain Filter:
   - skip steps touching `user_declared + high` unsafe zones
   - skip steps touching decisions with `override_allowed = false`
   - skip steps blocked by `blocking` gaps
3. Do not skip `historical + high` unsafe zones here. Keep them for the full gate so `/abw-audit` override remains reachable.
4. Compute `safety_score(step)`.
5. Sort descending and take top 3 candidates.

### Safety Score

```text
function safety_score(step, zones, step_history):
    score = 100

    if step.blast_radius == "high": score -= 30
    if step.blast_radius == "medium": score -= 15

    if step.reversibility == "irreversible": score -= 40
    if step.reversibility == "hard": score -= 25
    if step.reversibility == "moderate": score -= 10

    if step.permission_class == "requires_approval": score -= 30
    if step.permission_class == "decision_change": score -= 25
    if step.permission_class == "multi_file_write": score -= 10

    score -= len(step.affects_decision_ids) * 15

    historical_hits = count_matching_zones(step.candidate_files, zones, "historical", "high")
    score -= historical_hits * 20

    heuristic_hits = count_matching_zones(step.candidate_files, zones, "heuristic_suspected")
    score -= heuristic_hits * 5

    if step.rollback_contract.cost == "high": score -= 20
    if step.rollback_contract.confidence == "low": score -= 20
    if step.rollback_contract.method == "not_rollbackable": score -= 30

    score -= step.estimated_files_touched * 5
    score -= step.estimated_lines_changed / 50
    score -= count_recent_failures(step, step_history) * 20

    return max(0, score)
```

### Phase 3: Constrain

1. Run Constrain Gate on each candidate.
2. Collect all candidates with `allowed = true`.
3. If multiple candidates are allowed, choose in this order:
   - no `required_approvals`
   - fewer `required_approvals`
   - fewer `warnings`
   - higher `safety_score`
4. If none pass, report `no safe step available` and surface the blocking action.

### Phase 4: Choose One Safe Step

Display:

```text
[Resume] Project: <project_id>
Phase: <phase>
Current objective: <objective>
Last completed: <last_completed_step>

Next safe step:
- Step: <step_id> - <title>
- Description: <description>
- Permission: <permission_class>
- Estimated impact: <files> files, <lines> lines
- Blast radius: <blast_radius>
- Reversibility: <reversibility>
- Rollback: <method> (cost: <cost>, confidence: <confidence>)

Warnings:
- <warning>

Approvals required:
- <approval>

Execute this step? (yes / no / show alternatives)
```

If user says `yes`, log handover and execute according to the host agent's normal execution policy. If user says `no`, show alternatives. If user says `show alternatives`, show the other allowed candidates.

---

## 13. Post-Execute Minimal Artifact

After a step finishes, append to `.brain/step_history.jsonl`:

```json
{
  "step_id": "string",
  "outcome": "success | partial | failed",
  "changed_files": ["string"],
  "test_result": "pass | fail | skipped | null",
  "errors_introduced": 0,
  "executed_at": "ISO 8601"
}
```

Lookup contract:

- `test_passes.subject` is always a `step_id`.
- `get_last_test_result_by_step_id(step_id)` returns the latest `test_result` for that step.
- The gate never runs test commands by itself.

Append to `.brain/handover_log.jsonl`:

```json
{
  "event": "step_completed",
  "step_id": "string",
  "outcome": "success | partial | failed",
  "session_id": "string",
  "timestamp": "ISO 8601"
}
```

Update `resume_state.json`:

- `last_completed_step = step_id` when successful
- `active_step = null`
- append to `completed_steps` when successful
- adjust `effective_budget` from recent outcomes

---

## 14. Invariants

1. Do not mix continuation state into `wiki/`. Wiki is knowledge, not a task board.
2. Do not let the model add steps directly to backlog. Proposed steps require user approval.
3. Do not reverse locked decisions without evidence delta.
4. Do not use confident language as a substitute for acceptance criteria.
5. Do not overwrite handover history. All handover records are append-only.
6. Do not let `/abw-resume` jump directly into action. It must go through: reconstruct -> select candidates -> constrain -> choose one safe step.
7. Do not treat heuristics as authority. Heuristics warn; policy and user decisions govern.

---

## 15. Integration With Existing ABW

| ABW component | Integration |
|---|---|
| `wiki/` | Read for context reconstruction; do not store task state here. |
| `.brain/knowledge_gaps.json` | Classify gaps as blocking, non-blocking, or advisory for the current step. |
| `/abw-ingest` | Suggested when a blocking gap prevents a step. |
| `/abw-query` | May support reconstructing context from existing wiki. |
| `/abw-query-deep` | May support hard tradeoff checks before decision override. |
| `/abw-audit` | Required before changing `historical + high` unsafe zones. |
| `/abw-learn` | Suggested after failed steps to capture lessons. |
| `processed/manifest.jsonl` | Used by evidence-ref resolver. |

---

## 16. V1 Scope: Not Included

V1 does not implement:

- automatic execution without user confirmation,
- full completion artifact with rich acceptance evidence,
- automatic unsafe-zone discovery from code analysis,
- multi-model coordination,
- parallel step execution,
- complex dependency graphs,
- automatic rollback execution.

V1 is deliberately small: state, governance, gate, one safe next step.

---

## 17. Success Criteria

V1 is successful if:

1. A small model can resume an interrupted project without touching unsafe files by accident.
2. The user can see where the project is, what the next step is, and why that step was chosen.
3. Governance violations are blocked before execution.
4. Failed steps shrink the next allowed step size.
5. Locked decisions are not reversed silently.
6. Steps requiring approval are not ranked as equally safe as no-approval steps.

---

## 18. File Quick Reference

```text
resume_state.json        -> .brain/resume_state.json
continuation_backlog     -> .brain/continuation_backlog.json
locked_decisions         -> .brain/locked_decisions.json
unsafe_zones             -> .brain/unsafe_zones.json
continuation_policy      -> .brain/continuation_policy.json
handover_log             -> .brain/handover_log.jsonl
step_history             -> .brain/step_history.jsonl
```

These are runtime state files. Add them to `.gitignore` unless a project explicitly chooses to version a sanitized example.

---

*Spec v1 draft for review.*

*"Truth giúp Flash bớt nói sai. Continuation Governance giúp Flash bớt sửa sai thành phá hoại."*
