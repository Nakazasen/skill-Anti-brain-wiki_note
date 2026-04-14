# Hybrid ABW (Anti-Brain-Wiki)
> Version: 1.3.1

Small LLMs do not fail because they lack intelligence. They fail because they lose control over long-running tasks. As context grows and instructions stack, even capable models break project continuity, invent hallucinations, or execute unsafe changes without grounding.

Hybrid ABW is an operating discipline for AI work. It establishes **Action Governance** to prevent common agent failure modes.

### Behavior Contrast: The Governance Delta

| Failure Mode | Wild Agent (Ungoverned) | ABW-Governed Agent |
|---|---|---|
| **Security/Scope** | Blindly overwrites protected auth/config files. | **Blocked** by Unsafe Zone pre-filters. |
| **Continuity** | Loses track of long tasks; invents steps. | **Forced** to one safe, dependency-aware step. |
| **Logic/Grounding** | Hallucinates or talks "around" missing data. | **Halted** until Truth Layer gap is closed. |
| **Completion** | Declares "Done" with failing tests (Silent Debt). | **Rejected** by Evaluation Kernel gate. |

---

## What ABW Does

This framework enforces a strict execution boundary at runtime:
- **Prevents Hallucination**: Blocks output when grounding evidence is missing or stale.
- **Prevents Unsafe Continuation**: Blocks task resumption when context is lost or boundaries are violated.
- **Prevents Uncontrolled Execution**: Wraps writes in a governed executor that locks candidate files.
- **Prevents False Completion**: Blocks "done fake" by requiring verifiable acceptance evidence.

---

## System Architecture

Hybrid ABW operates on a four-pillar governance stack:

1. **Truth Layer (Truth OS)**: Epistemic layer. Enforces grounding in `wiki/` and `raw/` sources.
2. **Continuation Kernel**: State layer. Manages project continuity via `.brain/` artifacts.
3. **Governed Execution**: Action layer. Gated candidate file selection via `scripts/continuation_gate.py`.
4. **Evaluation Kernel**: Verdict layer. Mandatory acceptance gate before output delivery.

---

## Execution Proof (Action Governance)

The following trace demonstrates the **Continuation Kernel v1** gating a project resumption in a dirty environment (`examples/resume-abw`).

**Scenario**: User attempts `abw-resume` while the project has a pending security-sensitive step.

**Gate Execution**:
```bash
py scripts/continuation_gate.py --workspace examples/resume-abw
```

**System Verdict (Gated Logic)**:
```json
{
  "status": "selected",
  "selected": {
    "step_id": "step-safe-test",
    "permission_class": "safe_write",
    "allowed": true,
    "safety_score": 93.4
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
**Conclusion**: The system successfully hard-blocked an unsafe zone change and prevented out-of-order execution, selecting only the high-confidence safe step.

## Execution Proof 2: Outcome Governance (Failure Case)

When an agent fails to meet explicit acceptance criteria, the **Evaluation Kernel** blocks work. This prevents silent technical debt and "done fake" completions.

**System Verdict (Gated Rejection)**:
```json
{
  "verdict": "partial",
  "accepted": false,
  "fail_reasons": [
    "Unit tests for parser logic.",
    "Output must include verifiable test evidence."
  ],
  "status": "evaluated"
}
```
**Conclusion**: The system halts the workflow and requires corrective action. Work cannot progress until the gate is satisfied.

---

## Core Commands

- **/abw-resume**: Reconstructs project state and selects exactly one next safe step via the continuation gate.
- **/abw-execute**: Prepares a governed execution environment for the selected step and records append-only logs.
- **/abw-accept**: Runs the final evaluation loop to confirm that output meets explicit acceptance criteria.

---

## What This Is NOT

- Hybrid ABW is **not** an agent framework (like LangChain or AutoGPT).
- Hybrid ABW is **not** an "AI OS" or an autonomous agent platform.
- Hybrid ABW is **not** a general AI system; it is a repository-level operating discipline.

---

## Closing Statement

This system does not make models smarter. It makes them harder to fail silently by enforcing boundaries that LLMs cannot maintain on their own.

---
*Created by the Hybrid ABW maintainers.*
