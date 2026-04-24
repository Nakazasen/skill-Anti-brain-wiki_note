# ABW Command Surface Standard

This document defines the canonical command naming between the package CLI and the Antigravity slash surface.

## Canonical Mapping

| Package CLI | Slash Command |
|---|---|
| `abw doctor` | `/abw-doctor` |
| `abw version` | `/abw-version` |
| `abw ask "..."` | `/abw-ask "..."` |
| `abw review` | `/abw-review` |
| `abw migrate` | `/abw-migrate` |

## Legacy Alias Compatibility

Legacy slash aliases must remain supported:

- `/abw-health` -> alias of `/abw-doctor`
- `/abw-status` -> alias of `/abw-doctor`

## Canonical Naming Rule

- Canonical slash names must mirror CLI verb names.
- Docs and help should show canonical names first.
- Legacy aliases are compatibility-only labels.

## Scope

- Documentation and workflow surface naming only.
- No trust-core behavior changes.

## Related Files

- `docs/COMMAND_MIGRATION.md`
- `workflows/abw-commands.md`
