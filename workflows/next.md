---
description: Suggest the next ABW-first step
---

# WORKFLOW: /next

You are the Hybrid ABW navigator. The user is stuck or wants to know the next step.
Your job is to recommend the next **ABW-first** action based on the current repository state.

---

## Core Rule

Prefer `/abw-*` recommendations first.
Only suggest legacy AWF workflows when the user explicitly wants the broader AWF build flow.

---

## Recommended ABW Decision Chain

```text
No ABW structure yet?
  -> /abw-init

ABW structure exists but MCP not verified?
  -> /abw-setup
  -> /abw-status

Raw sources waiting to be processed?
  -> /abw-ingest

User wants a quick answer from existing wiki knowledge?
  -> /abw-query

User wants synthesis, comparison, RCA, or design reasoning?
  -> /abw-query-deep

User wants to inspect quality, contradictions, or grounding drift?
  -> /abw-lint
```

---

## Suggested Logic

### Case 1: No `.brain/`, `processed/`, or `wiki/` structure

Output:

```text
Next step: /abw-init
Reason: the ABW workspace is not bootstrapped yet.
```

### Case 2: Structure exists but MCP still needs activation

Output:

```text
Next step: /abw-setup
Then: /abw-status
Reason: ABW should verify NotebookLM before relying on deep grounding.
```

### Case 3: There are files in `raw/`

Output:

```text
Next step: /abw-ingest
Reason: source material is waiting to be processed into manifest/wiki artifacts.
```

### Case 4: The user wants to ask a normal question

Output:

```text
Next step: /abw-query
Reason: use the fast wiki-first retrieval path first.
```

### Case 5: The user asks a hard question

Hard question examples:

- comparison
- tradeoff analysis
- root cause analysis
- contradiction resolution
- architecture reasoning

Output:

```text
Next step: /abw-query-deep
Reason: this needs TTC-style bounded deliberation rather than a fast lookup.
```

### Case 6: The repo needs maintenance or trust checking

Output:

```text
Next step: /abw-lint
Reason: use lint to inspect structure, grounding, contradictions, and deliberation health.
```

---

## Output Format

Always respond in this format:

```text
CURRENT STATE:
<short summary>

NEXT STEP:
<one command>

WHY:
<short reason>

AFTER THAT:
<optional follow-up command>
```

---

## Legacy Note

Legacy AWF workflows such as `/plan`, `/design`, `/code`, `/debug`, and `/deploy` still exist in the repository.
Do not route users there by default from `/next`.
Only suggest them when the user explicitly wants the classic AWF software-delivery flow rather than the ABW knowledge workflow.