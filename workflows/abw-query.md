---
description: ABW wiki-first query path
---

## BINDING STRATEGY

- First attempt: call the single AI entrypoint `py scripts/ai_runner.py`.
- Any answer is only a DRAFT until `scripts/ai_runner.py` validates, executes, and renders it.
- If MCP cannot be used, you MUST invoke `py scripts/ai_runner.py` with JSON stdin.
- Do not emit a raw knowledge answer.
- Raw model answers are invalid.
- If execution mode is not used, validation mode is mandatory.
- Return the rendered AI entrypoint output itself rather than rewriting it.
- Normal UI MUST NOT expose `binding_status`, `validation_proof`, or raw JSON payload fields.

## VISIBILITY LOCK

Before returning:
- You MUST return only the rendered text from `py scripts/ai_runner.py`.
- If any command prints JSON with `binding_status` or `validation_proof`, that command is invalid for normal UI and must be replaced with `py scripts/ai_runner.py`.

# WORKFLOW: /abw-query

**Mục đích:** Trả lời nhanh bằng cách recap `.brain/`, tìm trong `wiki/`, rồi mới fallback sang MCP hoặc gap log nếu cần.

**Hướng dẫn cho AI:**
Bạn là chuyên gia Anti-Brain-Wiki. Hãy đọc và thực hiện quy trình trong: [skills/query-wiki.md](../skills/query-wiki.md).
