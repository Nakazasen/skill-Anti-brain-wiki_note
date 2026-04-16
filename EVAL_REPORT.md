# Evaluation Report: Action & Outcome Governance
> Version: 1.3.1
> Status: HARDENED
> Test Case: `examples/resume-abw`
> Engine: Continuation Kernel v1 + Evaluation Kernel v1

## 1. Objective
To demonstrate that Hybrid ABW v1.3.1 provides **Closed-Loop Governance**. The system ensures discipline at both the start of a task (Action Gate) and the end of a task (Outcome Gate).

---

## 2. Gate 1: Action Governance (Continuation)
**Scenario**: Resuming work where a candidate step targets a user-protected "Unsafe Zone".

### Logic Execution
```bash
py scripts/continuation_gate.py --workspace examples/resume-abw
```

### Machine Verdict
```json
{
  "status": "selected",
  "selected": {
    "step_id": "step-safe-test",
    "allowed": true
  },
  "skipped": [
    {
      "step_id": "step-auth-change",
      "reason": "pre-filter: user-declared unsafe zone zone-auth"
    }
  ],
  "candidates": [
    {
      "step_id": "step-parser-impl",
      "allowed": false,
      "block_reasons": ["Missing dependencies: step-safe-test"]
    }
  ]
}
```
✅ **Evidence**: System hard-blocks unsafe zones and enforces dependency order before allowing any write operation.

---

## 3. Gate 2: Outcome Governance (Acceptance)
**Scenario**: Agent attempts to submit a task completion proposal that fails unit tests and lacks required documentation.

### Logic Execution
```bash
py scripts/abw_accept.py --workspace examples/resume-abw --request acceptance_request_fail.json
```

### Machine Verdict
```json
{
  "status": "evaluated",
  "verdict": "partial",
  "accepted": false,
  "fail_reasons": [
    "Unit tests for parser logic.",
    "Output must include verifiable test evidence."
  ],
  "rubric": [
    {
      "id": "r1",
      "description": "Output must include verifiable test evidence.",
      "passed": false,
      "required": true
    }
  ]
}
```
✅ **Evidence**: System rejects artifacts that fail the quality rubric. Work is halted; the next continuation step is blocked until the gate achieves `accepted: true`.

---

## 3.1. Evaluation Kernel v1.5: Evidence Contract

Evaluation Kernel v1.5 hardens acceptance from prose-only audit into an evidence contract. The gate is **machine-checkable where possible, explicitly human-reviewed where necessary**.

Required checks and required rubric items must include evidence, not just a `passed` claim:

- `evidence.type`: what kind of evidence is being submitted, such as `test_output`, `git_diff_name_only`, `filesystem_probe`, or `review_note`.
- `evidence.ref`: where the evidence can be inspected, such as a log path, artifact path, command output reference, or review note anchor.
- `evidence.status`: whether the evidence itself reports `passed` or `failed`.
- `evidence.machine_checkable`: `true` for evidence the gate or operator can mechanically verify; `false` only for explicit human review.
- `evidence.details`: concise context for the evidence.

The gate rejects or downgrades acceptance when:

- a required check or rubric item has no evidence payload,
- a machine-checkable check, such as tests or command exit code, is backed only by narrative evidence,
- declared check status contradicts evidence status,
- artifacts fall outside the governed `candidate_files` scope.

This keeps Evaluation focused on preventing "done fake" and "audit fake": a good-sounding report is not acceptance unless the evidence contract is satisfied.

---

## 3.2. Evaluation Kernel v1.6: Evidence Strength and Claim Mapping

Evaluation Kernel v1.6 hardens the contract from "evidence exists" to "evidence is admissible for this claim."

Each required check or rubric item now needs evidence that maps to a stable verdict unit:

- `evidence.strength`: one of `required_machine`, `allowed_human`, or `supporting_only`.
- `evidence.claim_id`: the exact claim being supported, such as `check:unit-tests` or `rubric:scope_discipline`.
- `evidence.proves`: the short claim the evidence is meant to prove.
- `evidence.mechanism`: one of `test_result`, `diff_inspection`, `artifact_presence`, `human_review`, or `consistency_check`.
- `evidence.result`: `passed`, `failed`, or `inconclusive`.

The v1.6 gate applies these rules:

- machine-checkable claims require `required_machine` evidence;
- `allowed_human` evidence is valid only where human review is the right mechanism;
- `supporting_only` evidence cannot upgrade a required claim to pass;
- evidence mapped to the wrong `claim_id` is rejected;
- inconclusive evidence cannot satisfy required acceptance.

In short: v1.5 asks, "Is there evidence?" v1.6 asks, "Is this evidence the right kind, mapped to the right claim, and strong enough to support the verdict?"

---

## 3.3. Evaluation Kernel v1.7: Reality-bound Evidence

Evaluation Kernel v1.7 hardens required machine evidence from declared metadata into filesystem-backed evidence.

Required machine evidence now needs a verifiable artifact reference:

- `evidence.ref`: path to the evidence artifact.
- `evidence.ref_type`: currently `file`.
- `evidence.ref_check`: currently `contains: <text>` for a simple content check.

The v1.7 gate applies these rules:

- `required_machine` evidence must point to an existing file;
- `contains:` checks must match the actual file content;
- missing files, unsupported ref types, and content mismatches reject acceptance;
- declared `passed` cannot override observed failure text in the referenced artifact.

In short: v1.6 asks, "Is the evidence admissible for this claim?" v1.7 asks, "Does the evidence leave a real artifact trail?"

---

## 3.4. Evaluation Kernel v1.8: Minimal Command Execution

Evaluation Kernel v1.8 adds exit-code-only command evidence for required machine checks.

Required machine evidence can now use:

- `evidence.ref_type`: `command`.
- `evidence.ref`: a simple space-split command.
- `evidence.ref_check`: `exit_code:<number>`.

The v1.8 gate applies these rules:

- command evidence is executed with `subprocess.run()` and `shell=False`;
- only the process exit code is checked;
- command output is captured but not parsed;
- empty commands and dangerous commands such as `rm`, `del`, `git reset`, `git clean`, and `shutdown` are rejected;
- a non-matching exit code overrides declared `passed` evidence and rejects acceptance.

In short: v1.7 verifies artifact traces; v1.8 verifies minimal command reality without trusting command prose.

---

## 3.5. Evaluation Kernel v1.9: Trusted Source

Evaluation Kernel v1.9 adds source trust classification to required machine evidence.

Evidence may now declare:

- `evidence.source`: `trusted` or `untrusted`.

The v1.9 gate applies these rules:

- `required_machine` evidence must resolve to `source=trusted`;
- command evidence defaults to `trusted` when `source` is missing;
- file evidence defaults to `untrusted` when `source` is missing;
- explicitly untrusted evidence cannot satisfy `required_machine`, even when the file exists or the command succeeds;
- `allowed_human` and `supporting_only` evidence are not blocked by the trust rule.

In short: v1.8 verifies minimal command reality; v1.9 prevents artifact existence alone from becoming trusted machine proof.

---

## 3.6. Evaluation Kernel v1.10: Context-bound Trusted Evidence

Evaluation Kernel v1.10 binds trusted machine evidence to the current step and rejects stale file artifacts.

Required machine file evidence now needs:

- `request.step_id`: the current governed step.
- `evidence.context_id`: the step context that produced the evidence.

The v1.10 gate applies these rules:

- trusted required machine file evidence must have `context_id`;
- request must have `step_id`;
- `context_id` must equal `step_id`;
- file evidence older than 60 seconds is rejected as `stale_evidence`;
- command evidence is treated as freshly generated and does not require `context_id`.

In short: v1.9 asks, "Is this evidence trusted?" v1.10 asks, "Is this trusted evidence fresh and from this step?"

---

## 3.7. Execution-aware Evaluation: Runtime Injection Layer

The Runtime Injection Layer introduces a system-issued `runtime_id` into the evaluation lifecycle.

The layer applies these rules:

- `evaluate_request()` generates a local in-memory `runtime_id`;
- command evidence receives the runtime id through `ABW_RUNTIME_ID`;
- evaluation results include `runtime_id` for visibility;
- evidence may optionally declare `runtime_id`;
- declared runtime ids must match the system-generated runtime id;
- file evidence is checked for the runtime id only when runtime validation is requested.

This introduces runtime_id injection into command execution, enables future strict runtime binding in v1.11, keeps backward compatibility, and bridges execution and evaluation.

---

## 3.8. Evaluation Kernel v1.11: Narrow Strict Runtime Binding

Evaluation Kernel v1.11 applies strict runtime binding only to trusted required machine file evidence.

The strict scope is:

- `evidence.strength`: `required_machine`;
- `evidence.ref_type`: `file`;
- `evidence.source`: `trusted`.

Within that scope:

- `evidence.runtime_id` must exist;
- `evidence.runtime_id` must match the system-generated runtime id;
- the referenced file content must contain the runtime id.

Outside that scope, runtime binding remains in bridge mode. Command evidence still receives `ABW_RUNTIME_ID` but is not forced through strict file runtime checks. Untrusted file evidence, `allowed_human`, and `supporting_only` evidence do not require runtime ids.

This is the first strict enforcement step after the runtime injection bridge.

---

## 3.9. Evaluation Kernel v1.12: Command Runtime Reflection

Evaluation Kernel v1.12 adds optional runtime reflection for trusted required machine command evidence.

The reflection scope is:

- `evidence.strength`: `required_machine`;
- `evidence.ref_type`: `command`;
- `evidence.source`: `trusted`;
- `evidence.runtime_reflection`: `stdout`.

Within that scope:

- command evidence still receives `ABW_RUNTIME_ID`;
- command evidence must exit with the expected code;
- stdout must contain the system-generated runtime id;
- missing runtime reflection rejects acceptance as `runtime_not_reflected_by_command`.

Without `runtime_reflection`, command evidence remains backward compatible. Untrusted command evidence, `allowed_human`, `supporting_only`, and file evidence are not forced through stdout reflection.

This upgrades command evidence from injected runtime to observed runtime reflection while keeping enforcement narrow.

---

## 3.10. Evaluation Kernel v1.13: Strict File Runtime Marker

Evaluation Kernel v1.13 replaces loose runtime substring checks for trusted required machine file evidence.

The strict file marker scope is:

- `evidence.strength`: `required_machine`;
- `evidence.ref_type`: `file`;
- `evidence.source`: `trusted`.

Within that scope, the referenced file must contain an exact marker line:

```text
runtime_id: <runtime_id>
```

Loose runtime substring presence is no longer enough. A file that contains the runtime id outside the exact marker format is rejected as `runtime_marker_missing_or_invalid`.

Untrusted file evidence, `allowed_human`, `supporting_only`, and command evidence are not forced through the strict file marker rule.

---

## 3.11. Evaluation Kernel v1.14: Strict Command Runtime Marker

Evaluation Kernel v1.14 replaces loose runtime substring checks for trusted required machine command stdout reflection.

The strict command marker scope is:

- `evidence.strength`: `required_machine`;
- `evidence.ref_type`: `command`;
- `evidence.source`: `trusted`;
- `evidence.runtime_reflection`: `stdout`.

Within that scope, stdout must contain an exact marker line:

```text
runtime_id: <runtime_id>
```

Loose runtime substring presence in stdout is no longer enough. A command that prints the runtime id outside the exact marker format is rejected as `runtime_marker_missing_or_invalid_in_stdout`.

Command evidence without `runtime_reflection=stdout`, untrusted command evidence, `allowed_human`, `supporting_only`, and file evidence are not forced through the strict command marker rule.

---

## 3.12. Evaluation Kernel v1.15: Scope-bound Evidence

Evaluation Kernel v1.15 binds trusted required machine file evidence to the approved request scope.

The scope-bound file evidence rule applies to:

- `evidence.strength`: `required_machine`;
- `evidence.ref_type`: `file`;
- `evidence.source`: `trusted`.

Within that scope, `evidence.ref` must be listed in `candidate_files` or match a declared artifact path from `artifact` or `artifacts`.

Valid evidence outside the approved scope is rejected as `evidence_ref_outside_scope` and cannot be used to pass acceptance.

Command evidence, `allowed_human`, `supporting_only`, and untrusted file evidence are not forced through the scope-bound trusted machine file evidence rule.

---

## 3.13. Evaluation Kernel v1.16: Performance Guard

Evaluation Kernel v1.16 bounds acceptance evaluation cost.

The performance guard applies these limits:

- total evaluation time is capped by `MAX_EVAL_TIME_SECONDS`;
- file evidence reads are capped by `MAX_FILE_READ_BYTES`;
- command evidence execution is capped by `COMMAND_TIMEOUT_SECONDS`;
- repeated evidence checks reuse an in-memory cache keyed by `ref`, `ref_type`, and `ref_check`.

If evaluation exceeds the time limit, acceptance fails with `evaluation_timeout`. If a command exceeds its execution limit, the evidence check fails with `command_timeout`.

This keeps evaluation fast and bounded instead of allowing slow checks, repeated heavy work, or long-running command execution.

---

## 3.14. Recovery Kernel v0.1

Recovery Kernel v0.1 maps evaluation failure reasons to suggested next actions.

The recovery mapping is static and non-agentic:

- `runtime_mismatch`: regenerate evidence with correct runtime_id;
- `runtime_marker_missing_or_invalid`: rerun command and write correct runtime marker;
- `runtime_marker_missing_or_invalid_in_stdout`: fix command to print runtime marker;
- `evidence_ref_outside_scope`: move artifact into candidate_files or artifact paths;
- `command_timeout`: simplify or fix command execution;
- `evaluation_timeout`: reduce evaluation complexity or fix blocking logic.

When acceptance fails, the evaluation result includes `next_steps` entries with the original failure reason and the mapped action.

This is the first step toward a self-correcting system without adding planning, loops, or auto execution.

---

## 4. Final Compliance Summary

| Layer | Governance Control | Status |
|---|---|---|
| Truth Layer | Grounding in `wiki/` and `raw/` | **VERIFIED** |
| Continuation Kernel | State management in `.brain/` | **VERIFIED** |
| Governed Execution | Unsafe zone & Dependency checks | **HARDENED** |
| Evaluation Kernel | Mandatory rubric & check gate | **HARDENED** |

---

## 4. Counter-Evidence: The Wild Agent (Ungoverned Run)

To evaluate the effectiveness of the v1.3.1 gates, we contrast the governed trace against the typical behavior of an ungoverned LLM in the same `examples/resume-abw` scenario.

| Scenario Component | Wild Agent (No ABW) | Hybrid ABW v1.3.1 |
|---|---|---|
| **Unsafe Zone** | Executes `step-auth-change` blindly. | **Hard-blocked** by pre-filter logic. |
| **Dependencies** | Attempts `step-parser-impl` out of order. | **Blocked**; required `step-safe-test` first. |
| **Logic Gaps** | Hallucinates missing API documentation. | **Halts** execution via Truth Layer gap signal. |
| **Quality Control** | Declares "Task Success" despite 1 error. | **Rejected** by Evaluation Kernel gate. |

---

## 5. Final Compliance Summary

**Conclusion**: Hybrid ABW v1.3.1 enforces explicit acceptance constraints at runtime. By utilizing a machine-checkable gate and append-only state tracking, it prevents the agent from making impulsive moves and blocks them from declaring success on failed work.

---
*Verified by Hybrid ABW Hardening Logic.*
