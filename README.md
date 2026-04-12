# Hybrid Anti-Brain-Wiki (Hybrid ABW)

> Version: 1.2.0  
> EN: Turn a fast-answering LLM into a grounded, stateful, evaluation-aware working system.  
> VI: Biến một LLM trả lời nhanh thành một hệ thống làm việc có grounding, có bộ nhớ, và có lớp nghiệm thu rõ ràng.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![TTC: Enabled](https://img.shields.io/badge/Test--Time%20Compute-Active-brightgreen)](https://github.com/Nakazasen/skill-Anti-brain-wiki_note)

Hybrid ABW is a workflow architecture for AI agents that need more than "one-pass plausible answers". It combines:
- grounded project knowledge in `wiki/`
- working state in `.brain/`
- bounded reasoning for hard questions
- explicit evaluation before acceptance

Hybrid ABW là một kiến trúc workflow cho AI agent khi "trả lời nghe hợp lý" là chưa đủ. Hệ thống kết hợp:
- tri thức dự án có grounding trong `wiki/`
- trạng thái làm việc trong `.brain/`
- suy luận có giới hạn cho câu hỏi khó
- lớp đánh giá rõ ràng trước khi chấp nhận kết quả

---

## Core Idea

**EN**
- Do not fake knowledge.
- Do not claim grounding when grounding is unavailable.
- Do not skip evaluation when output quality matters.

**VI**
- Không bịa tri thức.
- Không giả vờ đã grounding khi grounding chưa sẵn sàng.
- Không bỏ qua nghiệm thu khi chất lượng đầu ra thực sự quan trọng.

This repo exists to help smaller, cheaper, faster models behave more like disciplined systems instead of impulsive chatbots.

Repository này tồn tại để giúp các mô hình nhỏ hơn, rẻ hơn, nhanh hơn hành xử giống một hệ thống có kỷ luật, thay vì chỉ là chatbot phản xạ nhanh.

---

## Two Entrypoints

### `/abw-ask` = Work Entrypoint

**EN:** Start here when you have a task, question, or request and want the router to choose the right lane.  
**VI:** Bắt đầu ở đây khi bạn có task, câu hỏi, hoặc yêu cầu và muốn router tự chọn lane phù hợp.

### `/abw-eval` = Evaluation Entrypoint

**EN:** Start here when work already exists and you want to audit, challenge, or accept the output.  
**VI:** Bắt đầu ở đây khi đã có đầu ra và bạn muốn audit, phản biện, hoặc chốt nghiệm thu.

---

## Mental Model: 5 Lanes

### 1. Khám phá và tư duy
**EN:** Explore ideas, clarify problems, and query what is already known.  
**VI:** Khám phá ý tưởng, làm rõ bài toán, và hỏi trên tri thức hiện có.

- `/abw-ask`
- `/abw-query`
- `/abw-query-deep`
- `/abw-bootstrap`
- `/brainstorm`

### 2. Dựng nền tri thức
**EN:** Build and maintain the grounded knowledge base.  
**VI:** Xây và duy trì nền tri thức có thể truy xuất ngược.

- `/abw-init`
- `/abw-setup`
- `/abw-status`
- `/abw-ingest`
- `/abw-lint`

### 3. Triển khai sản phẩm
**EN:** Turn knowledge into implementation.  
**VI:** Biến tri thức thành phần mềm chạy được.

Core flow:
- `/plan`
- `/design`
- `/visualize`
- `/code`
- `/run`
- `/debug`
- `/test`
- `/deploy`

Supporting workflows:
- `/refactor`
- `/audit`

### 4. Phiên làm việc và ghi nhớ
**EN:** Save progress, restore context, and decide the next step.  
**VI:** Lưu tiến độ, khôi phục bối cảnh, và quyết định bước tiếp theo.

- `/save-brain`
- `/recap`
- `/next`

### 5. Đánh giá và nghiệm thu
**EN:** Evaluate output quality before accepting work as done.  
**VI:** Đánh giá chất lượng đầu ra trước khi coi công việc là hoàn tất.

- `/abw-audit`
- `/abw-meta-audit`
- `/abw-accept`
- `/abw-eval`

---

## Reasoning Policy

Hybrid ABW follows a 3-tier reasoning policy:

- **Tier 1 - `/abw-query`**: fast retrieval from grounded wiki knowledge
- **Tier 2 - `/abw-query-deep`**: bounded deliberation for synthesis, comparison, RCA, and tradeoffs
- **Tier 3 - `/abw-bootstrap`**: hypothesis-driven mode for greenfield projects with no usable knowledge yet

If grounding is unavailable, the system must degrade honestly to `draft` or `pending_grounding`. It must never fake a grounded answer.

Nếu grounding chưa sẵn sàng, hệ thống phải hạ cấp trung thực về `draft` hoặc `pending_grounding`. Không được giả vờ đã grounded.

---

## Quick Start

### Install

Windows:

```powershell
irm https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.ps1 | iex
```

macOS / Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.sh | sh
```

Install NotebookLM MCP CLI:

```bash
uv tool install notebooklm-mcp-cli
```

### Recommended Path

```text
/abw-init
  -> /abw-setup
  -> /abw-ingest
  -> /abw-ask
  -> /abw-lint
  -> /abw-eval
```

### Typical Use

**EN**
1. Put source material into `raw/`.
2. Run `/abw-ingest`.
3. Use `/abw-ask` for normal work.
4. Use `/abw-eval` before accepting important output.

**VI**
1. Chép tài liệu nguồn vào `raw/`.
2. Chạy `/abw-ingest`.
3. Dùng `/abw-ask` cho luồng làm việc bình thường.
4. Dùng `/abw-eval` trước khi chốt các đầu ra quan trọng.

---

## Why It Matters

Hybrid ABW is not just a prompt pack. It is a discipline layer for AI work:
- memory instead of forgetting
- provenance instead of hand-waving
- bounded reasoning instead of endless overthinking
- evaluation instead of blind confidence

Hybrid ABW không chỉ là một bộ prompt. Nó là lớp kỷ luật cho công việc dùng AI:
- có bộ nhớ thay vì quên ngữ cảnh
- có provenance thay vì nói mơ hồ
- có suy luận có giới hạn thay vì nghĩ lan man
- có nghiệm thu thay vì tự tin mù quáng

---

## Important Files

- `AGENTS.md`: system invariants and reasoning rules
- `workflows/`: user-facing command wrappers
- `skills/`: execution logic
- `wiki/`: grounded project knowledge
- `.brain/`: runtime state, gaps, queues, and session memory

---

## Status

This repo is evolving from a pure ABW knowledge engine into a broader Hybrid ABW system with:
- a unified 5-lane command model
- a work entrypoint (`/abw-ask`)
- an evaluation entrypoint (`/abw-eval`)
- explicit acceptance workflows for weaker models
