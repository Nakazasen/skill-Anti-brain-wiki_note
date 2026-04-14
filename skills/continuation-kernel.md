# SKILL: continuation-kernel

Purpose: provide the reusable governance logic behind `/abw-resume` and `/abw-execute`. This skill decides whether a proposed continuation step is safe enough to present to the user as the next action, then records exactly one approved execution attempt.

Use this skill when:

- the user asks to resume an interrupted project,
- a workflow needs to select the next safe step from `.brain/continuation_backlog.json`,
- a step needs to be checked against unsafe zones, locked decisions, knowledge gaps, rollback risk, or step-size limits,
- the user asks to execute the selected continuation step.

Canonical spec: `docs/spec-continuation-kernel-v1.md`.

Machine gate: `scripts/continuation_gate.py`.

Governed executor: `scripts/continuation_execute.py`.

Prefer the machine gate whenever Python is available:

```bash
python scripts/continuation_gate.py --workspace .
```

Use this markdown skill as the fallback policy reference when the script cannot run.

For execution, prefer the governed executor whenever Python is available:

```bash
python scripts/continuation_execute.py prepare --workspace .
python scripts/continuation_execute.py record --workspace . --step-id <step_id> --outcome success --test-result pass --acceptance-result pass
```

The executor does not run arbitrary shell commands and does not edit files. It locks the active step, enforces approval requirements from the gate, and records the outcome after the host agent performs the bounded work.

---

## Core Rule

Truth OS governs what the model may claim.

Continuation Kernel governs what the model may do next.

Do not blur those roles. `wiki/` is knowledge. `.brain/continuation_*` is runtime action state.

---

## Required Runtime Files

Read these files if they exist:

- `.brain/resume_state.json`
- `.brain/continuation_backlog.json`
- `.brain/locked_decisions.json`
- `.brain/unsafe_zones.json`
- `.brain/continuation_policy.json`
- `.brain/knowledge_gaps.json`
- `.brain/step_history.jsonl`
- `.brain/handover_log.jsonl`

If required files are missing, do not invent final state. Use the templates under `templates/` to propose a bootstrap draft and ask the user to approve it.

---

## Permission Classes

| Class | Meaning |
|---|---|
| `read_only` | Read context only. No writes. |
| `safe_write` | Small bounded change, not security or migration. |
| `multi_file_write` | Larger bounded change, requires post-check. |
| `decision_change` | May override a locked decision, requires evidence and approval. |
| `requires_approval` | Any step outside safe classes. Must be approved before execution. |

---

## Constrain Gate

Run this gate before presenting any step as "next safe step".

Inputs:

- `step`
- `resume_state`
- `continuation_policy`
- `locked_decisions`
- `unsafe_zones`
- `knowledge_gaps`
- `step_history`

Output:

```json
{
  "allowed": true,
  "permission_class": "safe_write",
  "warnings": [],
  "block_reasons": [],
  "required_approvals": []
}
```

### Gate Checks

1. Permission class must be valid.
2. `estimated_files_touched` and `estimated_lines_changed` must fit `resume_state.effective_budget` when present, otherwise `continuation_policy.step_size_limits`.
3. `security` or `migration` surfaces cannot remain `safe_write`; downgrade to `requires_approval`.
4. Unsafe zones:
   - `user_declared + high`: hard block.
   - `historical + high`: allow only with `required_approvals` and `/abw-audit`.
   - `heuristic_suspected`: warning only.
5. Locked decisions:
   - if `override_allowed=false`, block.
   - if evidence delta is required, `evidence_delta_refs` must be present and resolvable.
   - if approval is required, add `required_approvals`.
6. Knowledge gaps:
   - `blocking`: block.
   - `advisory`: warn.
   - `non_blocking`: allow.
7. Rollback:
   - `cost=high`, `confidence=low`, or `method=not_rollbackable` downgrades to `requires_approval`.
8. Preconditions:
   - typed predicates must pass.
   - unknown types fail safe.

Never convert a blocked step into an allowed step using model confidence.

---

## Safety Score

Use safety score only to rank candidates before the full gate. It is not sufficient to allow a step.

```text
score = 100

blast_radius:
  high: -30
  medium: -15

reversibility:
  irreversible: -40
  hard: -25
  moderate: -10

permission_class:
  requires_approval: -30
  decision_change: -25
  multi_file_write: -10

approval risk:
  each affects_decision_ids: -15
  each historical+high unsafe-zone hit: -20
  each heuristic_suspected unsafe-zone hit: -5
  rollback cost high: -20
  rollback confidence low: -20
  rollback method not_rollbackable: -30

step size:
  each estimated file touched: -5
  estimated lines changed / 50: subtract that value

recent failures:
  each recent failure for this module or step family: -20
```

Return `max(0, score)`.

---

## Candidate Selection

Preferred implementation: call `scripts/continuation_gate.py` and use its JSON output.

Manual fallback:

1. Collect pending steps.
2. Pre-filter only obvious hard blockers:
   - `user_declared + high` unsafe zone.
   - locked decision with `override_allowed=false`.
   - directly blocking knowledge gap.
3. Keep `historical + high` unsafe-zone steps for the full gate so `/abw-audit` remains reachable.
4. Compute safety score.
5. Take the top 3.
6. Run Constrain Gate for each.
7. Collect all `allowed=true` candidates.
8. Choose by:
   - no `required_approvals`,
   - fewer `required_approvals`,
   - fewer `warnings`,
   - higher `safety_score`.

If none pass, return `no safe step available` and list the blocking actions.

---

## Evidence Ref Resolver

Valid refs:

- direct file path, for example `raw/benchmark.pdf`,
- wiki path, for example `wiki/concepts/topic.md`,
- manifest line ref, for example `processed/manifest.jsonl#line-42`,
- wiki note id resolvable under `wiki/concepts`, `wiki/entities`, `wiki/timelines`, or `wiki/sources`.

Do not infer evidence from prose. Use explicit `evidence_delta_refs`.

---

## Step Synthesis Boundary

If no backlog step exists, the model may create draft `proposed_steps` in `resume_state.json`.

The model must not append proposed steps directly to `.brain/continuation_backlog.json`. User approval is required before proposed steps become executable backlog steps.

---

## Output Contract

When a next step is selected, report:

- project id and phase,
- current objective,
- selected step id and title,
- permission class after gate,
- estimated files and lines,
- blast radius and reversibility,
- rollback contract,
- warnings,
- required approvals,
- why this step was chosen over alternatives.

End with a clear user confirmation question. Do not execute automatically.

---

## Governed Execution

`/abw-execute` is allowed only after `/abw-resume` has selected or evaluated a specific backlog step.

Execution phases:

1. `prepare`: call `scripts/continuation_execute.py prepare --workspace .`.
2. If the result is `approval_required`, stop and ask for explicit user approval. Do not infer approval from vague language.
3. If the result is `blocked`, return the gate reasons and go back to `/abw-resume`.
4. If the result is `prepared`, perform only the selected step within `candidate_files`.
5. `record`: call `scripts/continuation_execute.py record ...` with outcome, changed files, test result, errors introduced, acceptance result, and handover note.

The record phase writes a completion artifact into `.brain/step_history.jsonl` and `.brain/handover_log.jsonl`:

- `acceptance_result`
- `handover_note`
- `lessons_learned`
- `post_execute_audit`

The post-execute audit is deterministic and lightweight. It fails if changed files escape `candidate_files`, tests fail, or errors are introduced. It warns when the outcome is partial/failed or validation was not checked. If it returns `requires_abw_audit = true`, the step must not be treated as accepted until `/abw-audit` runs.

Completion is strict: a step enters `completed_steps` only when `outcome=success`, `acceptance_result=pass`, and `post_execute_audit.status=pass`. Any audit failure or missing acceptance keeps the attempt recorded but not accepted.

Execution invariants:

- No prepare, no execute.
- No implicit approval.
- No scope expansion without returning to `/abw-resume`.
- No overwrite of `.brain/handover_log.jsonl` or `.brain/step_history.jsonl`.
- Partial and failed outcomes must be recorded honestly.
- Scope deviations must be surfaced through `post_execute_audit`; do not hide them in prose.
