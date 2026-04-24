# ABW

ABW is a small CLI for grounded local AI work. The public surface is intentionally small: init, ask, ingest, review, doctor, version, migrate, help.

## Quick Start

Run commands from the repository folder:

```powershell
cd d:\Sandbox\skill-Anti-brain-wiki_note
```

Initialize a workspace:

```powershell
.\abw.bat init
```

Use this for most tasks:

```powershell
.\abw.bat ask "what you want to do"
```

Add knowledge from a local source:

```powershell
.\abw.bat ingest raw\<file>
```

Review pending drafts:

```powershell
.\abw.bat review
```

Check system health:

```powershell
.\abw.bat doctor
```

Inspect the installed engine and workspace:

```powershell
.\abw.bat version
```

Normalize an older ABW project layout safely:

```powershell
.\abw.bat migrate
```

## New in Phase 1

Overview:

```powershell
.\abw.bat overview
```

Save ideas quickly:

```powershell
.\abw.bat save "..."
```

Ingest now checks for possible contradictions and creates review reports instead of silently overwriting trusted knowledge.

Show product help:

```powershell
.\abw.bat help
```

Run release smoke checks:

```powershell
py scripts\release_smoke.py
```

## One-command Rule

If you are not sure which command to use, start with:

```powershell
.\abw.bat ask "..."
```

ABW will route the request through the existing runtime instead of asking you to learn internal command names.

## Menu

If you prefer a simple menu:

```powershell
.\abw.bat
```

The menu only shows the public v2 surface:

1. View system
2. Ask something
3. Add file
4. Review drafts
0. Exit

## Advanced Commands

These are maintainer-facing commands. They stay out of normal help and menu output:

```powershell
.\abw.bat help --advanced
.\abw.bat upgrade
.\abw.bat rollback
.\abw.bat repair
```

`research` is reserved but not implemented as a separate runtime command yet.

`upgrade` is guidance-only in the package CLI. The legacy governed runtime update path remains `/abw-update` for installed workflow runtimes.

## Multi-Project Use

### New project

```powershell
py -m pip install abw-skill
abw init
abw ask "dashboard"
```

### Existing project using older ABW

```powershell
abw migrate
abw doctor
abw ask "dashboard"
```

### Update ABW engine

```powershell
abw version
abw upgrade
abw doctor
```

Each project is isolated by default. The current working directory is the workspace unless `ABW_WORKSPACE` is set.

## Developer Notes

The public UX is intentionally smaller than the repo contents. Many files under `workflows/` are internal guidance or compatibility docs, not equal public runtime commands.

High-level runtime flow:

```text
CLI facade -> package workspace/report helpers or abw_entry.py -> abw_runner.py -> abw_output.py
```

The runner, proof generation, and trust logic are kept intact for routed work. `v0.2.3` keeps `scripts/` as canonical runtime in editable/dev installs and preserves `src/abw/_legacy/` as packaged fallback with mirror drift guards.
