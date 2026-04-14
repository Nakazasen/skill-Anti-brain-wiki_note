# Resume ABW Example

Minimal fixture for Continuation Kernel v1.

Run from the repository root:

```bash
python scripts/continuation_gate.py --workspace examples/resume-abw
```

Expected behavior:

- `step-safe-test` is selected.
- `step-auth-change` is skipped or blocked by a user-declared unsafe zone and blocking knowledge gap.
- `step-parser-impl` is allowed only with `/abw-audit` approval because it touches a historical high-confidence unsafe zone.
