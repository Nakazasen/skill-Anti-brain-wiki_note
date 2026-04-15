# Skill: abw-status

> **Purpose:** Provide a very fast health check for the ABW NotebookLM MCP connection and the Grounding Queue.
> **Role:** Diagnostic utility (used by `/abw-status`)

---

## Instructions for AI Operator

When the user calls `/abw-status`, execute the following diagnostic check EXACTLY in this order:

### 1. Check NotebookLM MCP Bridge Config
Read `skills/notebooklm-mcp-bridge.md`:
- Locate the `Connection Config` section.
- Identify the value of `mcp_status`.
- Identify the value of `auth_status`.

### 2. Live MCP Ping (If Available)
If you have access to the NotebookLM MCP Tools (e.g. `mcp_notebooklm_server_info` or `notebooklm_notebook_list`):
- Attempt a quick harmless call (like `mcp_notebooklm_server_info`).
- **If it succeeds**: The MCP is truly ACTIVE.
- **If it times out or errors**: The MCP is UNAVAILABLE (you must report Fallback Mode).
- **If you do not have the tool**: State that MCP tools are not exposed in the current context.

### 3. Check Grounding Queue
Read `.brain/grounding_queue.json` (if it exists, otherwise assume 0):
- Count how many items have `"status": "pending"`.
- Count how many items have `"status": "failed"`.

---

## 4. Output Format

Generate a clean, Markdown-formatted report for the user based on your findings:

```markdown
# 📊 ABW Status Report

**MCP Connection:** `[ACTIVE]` | `[NOT DETECTED (Fallback Mode)]` | `[ERROR]`
**Bridge Config Status:** `[mcp_status from file]`

### 🚦 Grounding Queue
- **Pending Items:** `[Count]`
- **Failed Items:** `[Count]`

*(If there are pending items and MCP is ACTIVE)*: 
> 💡 **Tip:** MCP is active! You can run `/ingest-wiki` to process your pending queue.

*(If MCP is NOT DETECTED or ERROR)*: 
> ⚠️ **Fallback Mode Active:** Grounding operations will be queued. 
> Run `/abw-setup` to configure your connection.
```


---

## Continuation Runtime Addendum

If `scripts/continuation_status.py` exists, run:

```bash
python scripts/continuation_status.py --workspace .
```

Include this section in the status report:

```markdown
### Continuation Runtime
- **Health:** `[ready | active | needs_approval | blocked | error]`
- **Active Step:** `[active_step or none]`
- **Next Safe Step:** `[step_id or none]`
- **Pending Steps:** `[count]`
- **Last Outcome:** `[success | partial | failed | none]`
- **Dependency Blocks:** `[count]`
- **Active Model Claims:** `[count]`
```

If the script is unavailable, read `.brain/resume_state.json`, `.brain/continuation_backlog.json`, `.brain/active_execution.json`, and `.brain/step_history.jsonl` directly and summarize best-effort.

## Restrictions
- Do NOT run the full `lint-wiki` 12 checks. This is meant to take < 5 seconds.
- KEEP instructions and output completely in Vietnamese to match the ABW persona.
