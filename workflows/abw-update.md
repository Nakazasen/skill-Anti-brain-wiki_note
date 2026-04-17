---
description: Update the Hybrid ABW command surface and runtime scripts in local Antigravity/Gemini runtime
---

# WORKFLOW: /abw-update

Purpose: update the local Antigravity/Gemini Hybrid ABW runtime from the current repo or from the verified remote snapshot.

This is an operational update command, not an AWF update.

## Execution

When the user calls `/abw-update` or clearly asks to update now, treat that as enough confirmation to run the installer.

Preferred commands:

- Windows, from a local clone:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

- macOS/Linux, from a local clone:

```bash
bash ./install.sh
```

If there is no usable local clone, provide the remote installer command.

Windows:

```powershell
irm https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.ps1 | iex
```

macOS/Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.sh | sh
```

## Required Verification

Do not report update success just because the installer printed output. Verify the installed runtime.

Required runtime scripts:

- `abw_accept.py`
- `abw_runner.py`
- `finalization_check.py`
- `continuation_gate.py`
- `continuation_execute.py`
- `continuation_status.py`
- `continuation_claim.py`
- `continuation_rollback.py`
- `continuation_detect_unsafe.py`

Required runtime workflows:

- `finalization.md`

On Windows, verify:

```powershell
Get-ChildItem "$env:USERPROFILE\.gemini\antigravity\scripts" |
  Select-Object Name,Length
```

On macOS/Linux, verify:

```bash
ls -la "$HOME/.gemini/antigravity/scripts"
```

If any required runtime script is missing, classify the update as `failed`, not `partial` or `successful`.
If `finalization.md` is missing from the runtime workflow directory, also classify the update as `failed`.

## Workspace Freshness Check

If running inside a git clone of this repo, check whether the workspace itself is stale:

```bash
git status --short --branch
```

If the branch is behind `origin/main`, say clearly:

- the Antigravity/Gemini runtime may have been updated from the verified remote snapshot;
- the IDE workspace clone is still stale;
- audits that claim to represent the public repo must not use the stale workspace until it is updated.

Do not silently equate "runtime updated" with "workspace clone updated".

## Report

Report:

- whether the installer actually ran;
- install source mode if available: `LOCAL` or `REMOTE`;
- whether all required runtime scripts exist;
- whether `finalization_check.py` exists in the runtime scripts directory;
- whether `finalization.md` exists in the runtime workflow directory;
- whether the current IDE workspace is behind `origin/main`;
- whether the user needs to reload the IDE or Gemini extension.

## Rules

- Do not call this an AWF update.
- Do not claim success if the installer was not actually run.
- Do not claim success if `finalization_check.py` or another required runtime script is missing.
- Do not claim success if `finalization.md` is missing.
- Do not hide a stale workspace clone behind a successful runtime install.
- If the user only asks how to update, explain the command instead of running it.
