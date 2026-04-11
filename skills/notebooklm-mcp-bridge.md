# Skill: notebooklm-mcp-bridge

> **Version:** 1.0.0  
> **Status:** [!] MCP NOT DETECTED -- FALLBACK MODE  
> **Purpose:** Bridge configuration between Hybrid ABW skills and NotebookLM MCP server  
> **Dependencies:** NotebookLM MCP server (`notebooklm`), authenticated Google account

---

## [!] IMPORTANT: Current Status

```
+==============================================================+
|  MCP STATUS: NOT DETECTED -- FALLBACK MODE ACTIVE            |
|                                                              |
|  This file is a STUB configuration.                          |
|  NotebookLM MCP connectivity has NOT been verified.          |
|  All grounding operations will queue instead of execute.     |
|                                                              |
|  To activate: Complete the Setup Checklist below.            |
+==============================================================+
```

---

## What This Bridge Does

The NotebookLM MCP bridge provides the following capabilities to ABW skills:

| Capability | MCP Tool | Used By |
|------------|----------|---------|
| List notebooks | `notebook_list` | query-wiki, lint-wiki |
| Create notebook | `notebook_create` | ingest-wiki |
| Add source | `source_add` | ingest-wiki |
| Query notebook | `notebook_query` | query-wiki, ingest-wiki |
| Get notebook info | `notebook_get` | lint-wiki |
| Describe source | `source_describe` | ingest-wiki |

---

## Setup Checklist

Complete these steps to activate the MCP bridge:

### Step 1: Verify MCP Server Availability
```
TODO: Check if notebooklm MCP server is configured in your IDE
      Look for MCP server configuration in settings/config
      The server name should be "notebooklm"
```

### Step 2: Authenticate
```bash
# Run in terminal:
nlm login

# If nlm command not found, install first:
pip install notebooklm-mcp
# or
pipx install notebooklm-mcp

# Then authenticate:
nlm login
```

### Step 3: Verify Authentication
```
TODO: After nlm login, test connection by running one of:
      - notebook_list (should return your notebooks)
      - server_info (should return version info)
      
      If authentication fails:
      1. Run: nlm login switch <profile>
      2. Or use save_auth_tokens as manual fallback
```

### Step 4: Create ABW Notebook
```
TODO: Create a dedicated notebook for Hybrid ABW grounding:
      - Title: "Hybrid ABW -- Grounding Base"
      - This will be the primary grounding notebook
      - Record the notebook_id below after creation
```

### Step 5: Update This File
```
TODO: After completing steps 1-4, update the status section:
      - Change status from "MCP NOT DETECTED" to "MCP ACTIVE"
      - Fill in the connection_config section below
      - Set verified_at timestamp
```

---

## Connection Config

```yaml
# Fill in after completing setup:
mcp_server_name: "notebooklm"
mcp_status: "not_detected"           # TODO: Change to "active" after setup
verified_at: null                      # TODO: Set to ISO 8601 timestamp
last_successful_query: null            # Auto-updated by query-wiki

# Primary grounding notebook
primary_notebook:
  id: null                             # TODO: Set after notebook_create
  title: "Hybrid ABW -- Grounding Base"
  created_at: null
  source_count: 0

# Authentication
auth:
  method: "nlm_login"                  # nlm login (preferred) | manual cookies
  profile: "default"
  last_auth: null                      # TODO: Set after nlm login
  auth_status: "not_authenticated"     # TODO: Change to "authenticated"
```

---

## Fallback Behavior

When MCP is unavailable, ALL ABW skills degrade as follows:

### ingest-wiki (Stage 3 Fallback)
```
Normal:   raw -> processed -> NotebookLM grounding -> wiki (grounded)
Fallback: raw -> processed -> QUEUE grounding       -> wiki (draft)

Actions:
1. Skip NotebookLM grounding entirely
2. Create wiki note with status: "draft", grounding.engine: "none"
3. Add grounding request to .brain/grounding_queue.json
4. Log: "[!] Grounding queued -- MCP unavailable"
5. DO NOT set status: "grounded" -- this would be FAKE SUCCESS
```

### query-wiki (Layer 3 Fallback)
```
Normal:   wiki search -> NotebookLM deep grounding -> answer
Fallback: wiki search -> SKIP NotebookLM            -> partial answer + gap log

Actions:
1. Search wiki/ only (Layer 2)
2. Skip Layer 3 entirely
3. If wiki insufficient -> Layer 4 (gap logging)
4. Include note in answer: "NotebookLM unavailable for deep grounding"
```

### lint-wiki (Check 9 Fallback)
```
Normal:   Verify notebook health, source counts, grounding status
Fallback: Report queue status only

Actions:
1. Report: "NotebookLM MCP Status: UNAVAILABLE"
2. Count pending items in grounding_queue.json
3. Report last known successful grounding timestamp
4. Suggest: "Run 'nlm login' to restore connection"
```

---

## MCP Availability Detection

### How Skills Detect MCP Status

Each skill should check MCP availability before attempting NotebookLM operations:

```
METHOD 1 (Recommended): 
    Try notebook_list with timeout=10s
    IF success -> MCP available
    IF timeout/error -> MCP unavailable, use fallback

METHOD 2 (Quick check):
    Read this file's connection_config -> check mcp_status
    IF "active" -> attempt MCP operation
    IF "not_detected" -> skip to fallback immediately

METHOD 3 (Server info):
    Try server_info
    IF returns version -> MCP available
    IF error -> MCP unavailable
```

### Post-Detection Actions
```
IF MCP becomes available after being unavailable:
    1. Update this file: mcp_status -> "active"
    2. Check .brain/grounding_queue.json for pending items
    3. Suggest: "MCP restored! <N> items pending grounding. Run ingest-wiki to process queue."

IF MCP becomes unavailable after being active:
    1. Update this file: mcp_status -> "not_detected"
    2. Log: "[!] MCP connection lost -- all grounding operations will queue"
    3. DO NOT retry aggressively (respect rate limits)
```

---

## Grounding Queue Processing

When MCP becomes available, process the grounding queue:

```
FOR EACH item in .brain/grounding_queue.json WHERE status == "pending":
    1. Set status -> "in_progress"
    2. Execute grounding operation:
       - Ensure notebook exists (create if needed)
       - Add source if not already added
       - Query for verification
    3. On success:
       - Set status -> "completed"
       - Update manifest entry
       - Update wiki note: status -> "grounded"
       - Record result_summary
    4. On failure:
       - Set status -> "failed"
       - Record error message
       - Keep in queue for retry
    5. Update .brain/grounding_queue.json timestamps
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `nlm login` fails | Check internet, try `nlm login switch default` |
| MCP server not found | Verify MCP server config in IDE settings |
| Auth token expired | Run `nlm login` again |
| Notebook query timeout | Increase timeout, try smaller queries |
| Rate limit hit | Wait 60s, reduce query frequency |
| Wrong Google account | `nlm login switch <profile>` |
| `pip install` fails | Try `pipx install notebooklm-mcp` |

---

## Security Notes

- Auth tokens are stored locally by `nlm login` (not in this repo)
- Do NOT commit auth cookies or tokens to version control
- NotebookLM data remains in your Google account
- Sources added to notebooks are subject to Google's data policies
- This bridge does NOT send raw data to external services beyond NotebookLM

---

## TTC Deliberation Support (v1.1.0)

When `query-wiki-deliberative` invokes NotebookLM, it passes additional context to enable budget-controlled grounding:

### Query Budget Tracking
```
Each deliberation run has:
  query_budget: <int>          # starts at policy.limits.max_notebooklm_queries
  queries_used: <int>          # incremented after each call
  budget_remaining: <int>      # query_budget - queries_used

When budget_remaining == 0:
  -> NO more NotebookLM calls for this run
  -> Pass 3 is skipped in subsequent rounds
  -> Run continues with existing evidence only
```

### Retry Reason (for query deduplication)
```
Each NotebookLM query in a deliberation run logs:
  query_text: "<targeted question>"
  retry_reason: "initial | gap_fill | contradiction_check | re_verify"
  pass_number: <int>

Circuit breaker checks:
  IF same query_text appears >= 2 times AND score did not increase:
      -> BREAK (duplicate_notebooklm_query)
```

### Evidence Delta (for stall detection)
```
After each NotebookLM query, compute:
  new_facts_added: <int>       # claims not already in evidence inventory
  confidence_change: <delta>   # change in exit gate score
  evidence_delta = new_facts_added + abs(confidence_change)

Circuit breaker checks:
  IF evidence_delta == 0 for >= 2 consecutive queries:
      -> BREAK (no_new_evidence)
```

### Fallback Behavior
```
When MCP is unavailable:
  -> query_budget is set to 0 (no MCP calls possible)
  -> All deliberation passes that need MCP are skipped
  -> Run proceeds with wiki-only evidence
  -> Exit gate scores grounding_status accordingly (0 or 1, never 2)
```

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-04-11 | Initial stub -- MCP NOT DETECTED |
| 1.1.0 | 2026-04-11 | Added TTC deliberation support (query_budget, retry_reason, evidence_delta) |

---

*This file is a configuration stub. It will be updated to active status once NotebookLM MCP connectivity is verified. See Setup Checklist above.*
