---
description: Legacy AWF updater notice
---

# WORKFLOW: /awf-update

This workflow is kept only as a legacy note for users who also maintain a separate upstream AWF install.

Hybrid ABW does **not** use `/awf-update` as its primary update path.

## For Hybrid ABW

To update Hybrid ABW, re-run this repository's installer:

### Windows

```powershell
irm https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.ps1 | iex
```

### macOS / Linux

```bash
curl -fsSL https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.sh | sh
```

## For Users Who Also Have Full AWF Installed

If you intentionally maintain the upstream AWF command suite, update it from the upstream AWF repository separately.
Do not assume Hybrid ABW and upstream AWF share the same installer lifecycle.