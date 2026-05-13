# ABW Architecture Audit - 2026-04-30

## Scope

Audited workspace:

```text
D:\Sandbox\skill-Anti-brain-wiki_note
```

NVIDIA was treated only as an integration target:

```text
D:\Sandbox\Nvidia
https://github.com/Nakazasen/nvidia-server
```

No NVIDIA files were read or written. This pass only wrote documentation in the ABW workspace.

## Snapshot

- Package: `abw-skill`
- Version in `pyproject.toml`: `1.1.0`
- Latest observed tag: `v1.1.0`
- Latest observed commit: `4f35b10 docs: add v1.1.0 release notes`
- Release note: `docs/releases/v1.1.0.md`
- Observed structure: 75 `src/abw` files, 44 workflows, 21 skills, 29 templates, 4 schemas, 63 test files.
- v1.1.0 release note reports: `673 passed, 7 warnings`.

The test suite was not rerun during this documentation-only audit.

## Findings

1. ABW is larger than the current README claims.
   `README.md` presents ABW mainly as a small CLI, but the repo contains a governance system: adaptive router, grounded memory, continuation gate, acceptance/evidence gates, local API, multi-workspace registry, workflows, skills, templates, and release discipline.

2. The canonical architectural framing should be upgraded.
   ABW should be described as a constitutional governance layer for agents, not as an inference provider, product command center, or product shell.

3. The adaptive router exists in both workflow and runtime form.
   `/abw-ask` is documented as the primary dispatcher, while `src/abw/_legacy/abw_router.py` and `src/abw/api.py` implement route and route-then-ask behavior.

4. Continuation Kernel v1 is a strong architectural asset.
   `docs/spec-continuation-kernel-v1.md`, `skills/continuation-kernel.md`, `workflows/abw-resume.md`, and `scripts/continuation_gate.py` align around unsafe zones, locked decisions, knowledge gaps, effective budget, rollback contracts, and approval gates.

5. The local API is ready to become an integration boundary.
   `src/abw/api.py` exposes health, inspect, gaps, recover, trend, improve, apply, ask, workspace intel, route-query, workspace registry, and promotion endpoints. This supports a future FastAPI/local service bridge after a CLI bridge is validated.

6. Documentation has encoding risk.
   Several Vietnamese workflow and skill files show mojibake. This does not invalidate the architecture, but it creates operator comprehension and matching risk.

7. Release truth is split.
   `docs/releases/v1.1.0.md` is current, while `CHANGELOG.md` appears to trail older versions. Release discipline should converge version files, changelog, release notes, tags, and package metadata.

8. NVIDIA integration is not yet proven.
   No running bridge was verified. ABW should not claim NVIDIA integration until a CLI or API contract exists and passes smoke tests.

## Recommended Direction

- Keep ABW as the canonical governance engine.
- Keep NVIDIA as product shell and active agent runtime.
- Use CLI bridge first for integration.
- Move to FastAPI/local service bridge only after CLI behavior and exit states are stable.
- Do not mechanically merge source trees.
- Add formal integration contract docs and API examples.
- Add schemas for governance-critical `.brain` files.
- Fix mojibake in a controlled docs-only pass.

## Files Produced

- `README.proposed.md`
- `docs/ABW_ARCHITECTURE_AUDIT_2026-04-30.md`

## Conclusion

ABW remains the canonical governance engine: grounded memory, reality checking, adaptive routing, continuation control, and evidence-based acceptance. NVIDIA remains the product shell and active agent runtime. Integration should be contractual, not a source merge.
