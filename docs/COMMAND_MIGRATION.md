# ABW Command Surface Migration

Use this guide to roll out canonical command naming in ABW-based runtimes and embedded projects.

## Target State

Adopt canonical CLI <-> slash mapping:

| Package CLI | Canonical Slash |
|---|---|
| `abw doctor` | `/abw-doctor` |
| `abw version` | `/abw-version` |
| `abw ask "..."` | `/abw-ask "..."` |
| `abw review` | `/abw-review` |
| `abw migrate` | `/abw-migrate` |

Keep legacy slash aliases active:

- `/abw-health` -> `/abw-doctor`
- `/abw-status` -> `/abw-doctor`

## Rollout Plan

1. Release canonical names while keeping legacy aliases.
2. Update help/docs/examples to canonical names first.
3. Run smoke checks for canonical and legacy routes.
4. Monitor legacy alias usage and plan deprecation later.

## Smoke Checklist

- `abw doctor` and `/abw-doctor`
- `/abw-health` and `/abw-status` still resolve to doctor behavior
- `abw version` and `/abw-version`
- `abw ask "ping"` and `/abw-ask "ping"`
- `abw review` and `/abw-review`
- `abw migrate` and `/abw-migrate`

## Embedded Projects (Multi-repo)

For each project that embeds ABW:

1. Sync workflow docs from ABW engine repo.
2. Keep legacy alias declarations to avoid breaking old prompts.
3. Update local onboarding/help text to canonical names.
4. Execute smoke checks in that project runtime.

## Non-Goals

- No trust-core changes.
- No behavioral change to review/ask/migrate logic.
