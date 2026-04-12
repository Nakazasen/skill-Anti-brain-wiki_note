---
description: Suggest the next ABW-first step
---

# WORKFLOW: /next

You are the Hybrid ABW navigator. The user is stuck or wants to know the next step. Your job is to recommend the next action across the **Discovery, Grounding, Delivery, or Session** lanes based on the repository state.

---

## Recommended Decision Chain

### 1. Discovery Lane
- No clear goal or MVP? -> **`/brainstorm`**
- Greenfield idea? -> **`/abw-ask`** (triggers Bootstrap)

### 2. Grounding Lane (Knowledge)
- No structure? -> **`/abw-init`**
- MCP not confirmed? -> **`/abw-setup`**
- Source files in `raw/`? -> **`/abw-ingest`**
- Want to audit knowledge? -> **`/abw-lint`**

### 3. Delivery Lane (Build)
- Ready to implementation? -> **`/plan`**
- Plan exists? -> **`/code`**
- Errors detected? -> **`/debug`**
- Testing needed? -> **`/test`**

### 4. Session Lane (Memory)
- Long session or task done? -> **`/save-brain`**
- Just starting? -> **`/recap`**

---

## Output Format

Always respond in this format:

```text
CURRENT STATE:
<short summary of project phase>

NEXT STEP:
<one command>

WHY:
<reason linked to the 4-lane model>

AFTER THAT:
<optional follow-up command>
```
