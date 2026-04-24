# Release Checklist

Use this before shipping ABW changes.

## Docs

- [ ] `README.md` matches the current command model
- [ ] `workflows/README.md` and `abw help` agree
- [ ] new public commands are documented

## Package Runtime

- [ ] `abw --help` shows only the public command surface
- [ ] `abw help --advanced` shows maintainer commands
- [ ] `abw version` reports package/tag match for the release commit
- [ ] `abw version` reports `runtime_source` and `mirror_status`
- [ ] `abw doctor` returns OK on the repository workspace
- [ ] `py -m pip install -e .` refreshes local editable metadata

## Entry Points

- [ ] `abw help`, `py -m abw.cli help`, `py scripts/abw_cli.py help`, and `abw.bat help` agree
- [ ] dashboard smoke works through all supported entrypoints
- [ ] critical `scripts/` and `src/abw/_legacy/` mirrors have no drift
- [ ] runtime source override (`ABW_RUNTIME_SOURCE`) works for `scripts`, `packaged`, and `auto`

## Evaluation

- [ ] `/abw-eval` workflow and skill are readable
- [ ] evaluation commands still appear in the official lane

## Grounding

- [ ] `/abw-pack` docs match script behavior
- [ ] `/abw-sync` docs match script behavior
- [ ] clean-clone requirements for `/abw-pack` are documented

## Hygiene

- [ ] no `.bak` files in repo root
- [ ] no mojibake in edited files
- [ ] no stale AWF naming on ABW public surface

## Smoke Tests

- [ ] `py -m unittest discover -s tests`
- [ ] `py scripts/release_smoke.py`
- [ ] `py -m pip wheel . -w <temp-dir>`

## Legacy Workflow Runtime

- [ ] `install.ps1` installs the expected workflows when shipping installer changes
- [ ] `install.sh` installs the expected workflows when shipping installer changes
- [ ] installer verification still passes when installer files change
- [ ] runtime ABW block in `GEMINI.md` is still correct when workflow registration changes
