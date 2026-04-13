# Release Checklist

Use this before shipping ABW changes.

## Docs

- [ ] `README.md` matches the current command model
- [ ] `README.en.md` matches the current command model
- [ ] `workflows/README.md` and `workflows/help.md` agree
- [ ] new public commands are documented

## Runtime

- [ ] `install.ps1` installs the expected workflows
- [ ] `install.sh` installs the expected workflows
- [ ] installer verification still passes
- [ ] runtime ABW block in `GEMINI.md` is still correct

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

- [ ] clean clone + installer pass
- [ ] `/abw-pack` smoke test runs
- [ ] `/abw-sync` dry-run works
- [ ] `/abw-eval` prompt layer is readable after install
