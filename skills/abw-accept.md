# SKILL: abw-accept

> **Purpose:** Evaluation Kernel v1 acceptance gate. Decide whether one output has enough evidence to move into `accepted`.
> **Role:** Lean acceptance utility, not a deep audit.

---

## Boundary

`/abw-accept` does not answer "is this generally good?"

It answers one narrower question:

> Does this artifact have enough evidence to be accepted?

Use the other commands for broader work:

- `/abw-accept`: short, hard acceptance gate
- `/abw-eval`: full evaluation chain
- `/abw-audit`: deeper investigation

---

## Machine Gate

When Python is available, prefer:

```bash
python scripts/abw_accept.py --workspace . --request .brain/acceptance_request.json
```

If the user has no request file, create or ask for a minimal request using `templates/acceptance_request.example.json`.

The script appends `.brain/acceptance_log.jsonl` unless `--no-log` is passed.

---

## Required Inputs

An acceptance request must include:

- `artifact`: id, path, and type of the output being accepted
- `rubric`: pass/fail criteria relevant to this artifact
- `checks`: real check results, not model vibes
- `scope`: what is being accepted

---

## Verdict Rules

Allowed verdicts:

- `pass`: all required artifact/rubric/check evidence is present and passing
- `partial`: some evidence passes, but required checks or rubric items failed
- `blocked`: acceptance cannot be evaluated because artifact, rubric, checks, or evidence are missing
- `fail`: required evidence exists and fails with no meaningful passing evidence

Rules:

- `partial` means there was progress, but it is not accepted.
- `blocked` means the gate lacks enough evidence to evaluate.
- `verdict` must not be generated from model prose alone.
- If any blocker exists, do not return `pass`.
- If `accepted=false`, state the exact next action.

---

## Output Format

```markdown
# ABW Acceptance Report

## Scope
- <scope>

## Artifact
- <id/path/type>

## Checks
- <check>: <pass/fail> - <reason>

## Rubric
- <rubric item>: <pass/fail> - <reason>

## Verdict
- pass | partial | blocked | fail

## Accepted
- true | false

## Reasons
- <block/fail/warning reasons>

## Required Next Action
- <what must happen next>
```

---

## Finalization Rule

Append the terminal block from `workflows/finalization.md`.

- Map `pass` to `verified`.
- Map `partial` to `partially_verified`.
- Map `blocked` to `blocked`.
- Map `fail` to `blocked`.
- Before emitting the verdict, run `scripts/finalization_check.py` on the drafted Finalization block.
- If the checker returns `downgrade` or `blocked`, lower the state before finalizing.
- Do not claim `pass` unless the evidence is strong enough for the current scope.

---

## Restrictions

- `/abw-accept` must not edit product files.
- Do not produce a stronger verdict than the evidence supports.
- Do not accept an artifact with missing required checks.
- Do not treat `partial` as accepted.
- Always preserve `.brain/acceptance_log.jsonl` as append-only.
