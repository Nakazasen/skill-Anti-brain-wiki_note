# ABW Migration Playbook

Official runbook to migrate legacy projects into clean ABW package-workspace mode.

## Quick Migration

Use this checklist when you need a fast, safe migration:

1. Audit the project and identify embedded ABW runtime copies.
2. Preserve workspace data (`raw/`, `wiki/`, `drafts/`, `.brain/`, `abw_config.json`).
3. Quarantine (rename) legacy embedded ABW files instead of deleting.
4. Install or upgrade the external ABW package (`abw-skill`).
5. Reconnect the project as a workspace (`abw init`, `abw migrate`).
6. Normalize `.gitignore` to ignore runtime noise only.
7. Validate with `abw doctor`, `abw version`, and `abw ask "dashboard"`.
8. Commit only meaningful integration changes.

## Scope and Outcome

Target state:

- Project repository remains business-focused.
- ABW is used as an external package tool.
- Workspace knowledge is preserved.
- Git history is protected from transient runtime noise.

Out of scope:

- Rewriting business logic.
- Deleting business documents.
- Changing ABW trust core semantics.

## Red Flags

Stop and reassess if any of the following appears:

- You are about to delete `raw/`, `wiki/`, `drafts/`, or `abw_config.json`.
- You plan to ignore all `.brain/` blindly.
- You cannot distinguish embedded engine code from business scripts.
- `abw doctor` starts failing after migration steps.
- Git diff includes unrelated business code edits.
- You need `--force` push without a reviewed reason.

## 8-Phase Detailed Runbook

### Phase 0 - Safety Snapshot

Capture baseline before touching files:

```powershell
git status
git branch --show-current
git rev-parse --short HEAD
```

Optional rollback anchor:

```powershell
git checkout -b chore/abw-migration-backup-YYYYMMDD
```

### Phase 1 - Audit Current Project

Inspect repository and classify:

1. Business code.
2. Business docs/data.
3. ABW workspace knowledge.
4. Runtime artifacts/noise.

Look for legacy embedded ABW signs:

- `.\abw\`
- `.\scripts\abw_*.py`
- `.\workflows\abw-*`
- local runtime copies (`abw_runner.py`, `abw_output.py`, `abw_entry.py`, `abw_help.py`)
- launcher files pointing to local ABW runtime.

### Phase 2 - Preserve Data First

Do not remove workspace knowledge:

- `raw/`
- `wiki/`
- `drafts/`
- `.brain/` knowledge files
- `abw_config.json`

Treat these as project memory assets unless explicitly deprecated by the team.

### Phase 3 - Quarantine Legacy Embedded Engine

Do not hard-delete first. Rename only ABW engine artifacts:

- `abw/` -> `_old_abw_engine_backup/`
- `scripts/abw_*.py` -> `scripts/_old_abw_*.py`
- `workflows/abw-*` -> `workflows/_old_abw-*`
- legacy launchers -> `*_old_backup`

Only quarantine files that are clearly ABW engine/runtime components.

### Phase 4 - Install External ABW Package

Install from package index:

```powershell
py -m pip install -U abw-skill
```

Or pin from repository tag:

```powershell
py -m pip install -U git+https://github.com/Nakazasen/skill-Anti-brain-wiki_note.git@v0.2.3
```

Verify installed version:

```powershell
py -m pip show abw-skill
```

### Phase 5 - Reconnect Workspace

Run inside project root:

```powershell
abw init
abw migrate
abw doctor
abw version
abw ask "dashboard"
```

Expected behavior:

- Workspace structure remains intact.
- Package mode works without embedded runtime dependency.

### Phase 6 - Normalize Git Policy

Track:

- Business code and docs.
- Curated workspace knowledge (`wiki/`, selected `.brain/` knowledge files).
- `abw_config.json`.

Optional track:

- `raw/` if raw sources are intentional project knowledge.

Ignore runtime noise:

- nonce state, transient logs, cache/tmp, `__pycache__`, temp draft artifacts.

Recommended precise patterns:

```gitignore
__pycache__/
*.pyc
.brain/used_nonces.json
.brain/*.log
.brain/tmp/
.brain/cache/
drafts/*.tmp
```

Never blanket-ignore `wiki/`, `raw/`, or `abw_config.json`.

### Phase 7 - Validate and Commit Cleanly

Pre-commit checks:

```powershell
git status
abw doctor
abw ask "dashboard"
```

Commit only meaningful migration artifacts:

- `.gitignore`
- `abw_config.json`
- curated `wiki/*` updates
- optional local ABW usage note.

### Phase 8 - Sync Remote Safely

Use rebase sync flow:

```powershell
git fetch origin
git rev-list --left-right --count origin/main...main
git pull --rebase origin main
git push origin main
```

Conflict handling policy:

- Preserve migration-hygiene changes.
- Do not overwrite business logic blindly.
- Avoid force push unless explicitly justified and approved.

## Definition of Done

Migration is complete when:

- Project runs in ABW package-workspace mode.
- No embedded ABW runtime controls project operations.
- Workspace knowledge is preserved.
- Git status is clean or contains only intentional changes.
- `abw doctor` and `abw ask "dashboard"` are operational.

## Final Migration Report Template

Use this exact structure for handover:

1. Legacy ABW files found
2. Data preserved
3. Files quarantined
4. ABW installed version
5. doctor result
6. dashboard result
7. Final git status summary
8. Remaining risks
9. Project now clean package-mode? yes/no
