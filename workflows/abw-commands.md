# WORKFLOW SURFACE: ABW Canonical Commands

This file is the workflow-side reference for ABW command naming.

## Canonical CLI <-> Slash Map

| CLI | Slash |
|---|---|
| `abw doctor` | `/abw-doctor` |
| `abw version` | `/abw-version` |
| `abw ask "..."` | `/abw-ask "..."` |
| `abw review` | `/abw-review` |
| `abw migrate` | `/abw-migrate` |

## Legacy Slash Aliases

- `/abw-health` -> `/abw-doctor`
- `/abw-status` -> `/abw-doctor`

## Guidance

- Canonical docs/help should display slash names above.
- Legacy aliases stay for backward compatibility.
- This is naming policy only; trust-core behavior is unchanged.
