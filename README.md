# Hybrid ABW

> Version: 1.3.1  
> EN: Turn a fast-answering LLM into a grounded, stateful, evaluation-aware working system.  
> VI: Biến một LLM trả lời nhanh thành một hệ thống làm việc có grounding, có bộ nhớ, và có lớp nghiệm thu rõ ràng.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![TTC: Enabled](https://img.shields.io/badge/Test--Time%20Compute-Active-brightgreen)](https://github.com/Nakazasen/skill-Anti-brain-wiki_note)

Hybrid ABW is an operating discipline for AI work. It combines:

- grounded project knowledge in `wiki/`
- working state in `.brain/`
- bounded reasoning for hard questions
- explicit evaluation before acceptance

Hybrid ABW là một kỷ luật vận hành cho agent AI. Hệ thống kết hợp:

- tri thức dự án có grounding trong `wiki/`
- trạng thái làm việc trong `.brain/`
- suy luận có giới hạn cho câu hỏi khó
- lớp đánh giá trước khi chấp nhận đầu ra

---

## Core Idea

**EN**

- Do not fake knowledge.
- Do not claim grounding when grounding is unavailable.
- Do not skip evaluation when output quality matters.

**VI**

- Không được bịa tri thức.
- Không được nhận là đã grounding nếu grounding không sẵn sàng.
- Không được bỏ qua nghiệm thu khi chất lượng đầu ra quan trọng.

This repo exists to help smaller, cheaper, faster models behave more like disciplined systems instead of impulsive chatbots.

## Có Gì Mới Trong Bản Này

Bản cập nhật này không chỉ thêm lệnh. Nó làm ABW kỷ luật hơn ở 3 chỗ:

- `/audit` xuất hiện như một workflow delivery-loop rõ ràng để review code, hành vi sản phẩm, và bảo mật trước khi đi xa hơn.
- `/abw-learn` và `lessons_learned` cho phép ABW nhớ các sửa sai có thể tái sử dụng, thay vì quên ngay sau phiên hiện tại.
- `instruction_compliance` buộc ABW không chỉ trả lời đúng kiến thức, mà còn phải đúng format, đúng phạm vi, và đúng ràng buộc của user.

Nếu nói ngắn gọn, đợt này biến ABW từ "có grounding" thành "có kỷ luật vận hành".

---

## Two Entrypoints

### `/abw-ask` = Work Entrypoint

Start here when you have a task, question, or request and want the router to choose the right lane.

Bắt đầu ở đây khi bạn có task, câu hỏi, hoặc yêu cầu và muốn router chọn lane phù hợp.

### `/abw-eval` = Evaluation Entrypoint

Start here when work already exists and you want to audit, challenge, or accept the output.

Bắt đầu ở đây khi đã có đầu ra và bạn muốn audit, challenge, hoặc chấp nhận trước khi coi là xong.

---

## Mental Model: 6 Lanes

1. **Khám phá và tư duy**  
   `/abw-ask`, `/abw-query`, `/abw-query-deep`, `/abw-bootstrap`, `/brainstorm`

2. **Dựng nền tri thức**  
   `/abw-setup`, `/abw-status`, `/abw-ingest`, `/abw-pack`, `/abw-sync`, `/abw-lint`

3. **Triển khai sản phẩm**  
   `/plan`, `/design`, `/visualize`, `/code`, `/run`, `/debug`, `/test`, `/deploy`, `/refactor`, `/audit`

4. **Phiên làm việc và ghi nhớ**  
   `/abw-start`, `/abw-resume`, `/abw-execute`, `/abw-learn`, `/save-brain`, `/recap`, `/next`, `/abw-wrap`

5. **Đánh giá và nghiệm thu**  
   `/abw-review`, `/abw-audit`, `/abw-meta-audit`, `/abw-rollback`, `/abw-accept`, `/abw-eval`

6. **Tiện ích và cấu hình**  
   `/customize`, `/help`, `/abw-update`

---

## Quick Start / Install

Clone repo, then run the installer to register all Hybrid ABW commands into Gemini. Cloning alone does not activate the command surface.

Hãy clone repo, sau đó chạy installer để đăng ký toàn bộ lệnh Hybrid ABW vào Gemini. Chỉ clone repo thì chưa kích hoạt command surface.

### Windows

```powershell
irm https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.ps1 | iex
```

### macOS / Linux

```bash
curl -fsSL https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.sh | sh
```

## Sau Khi Cài Xong

1. Chạy `/abw-init` để dựng hoặc sửa cấu trúc ABW trong workspace.
2. Chạy `/abw-setup` để cấu hình grounding.
3. Dùng `/abw-ask` cho mọi task hoặc câu hỏi chưa rõ lane.
4. Dùng `/abw-eval` khi muốn nghiệm thu thay đổi hoặc đầu ra.
5. Dùng `/abw-resume` khi cần tiếp quản project đang dở bằng một next safe step.
6. Dùng `/abw-execute` khi muốn thực thi step đã qua Continuation Kernel gate.
7. Dùng `/abw-update` khi muốn kéo bản command mới nhất vào Gemini runtime local.

---

## First Command Cheat Sheet

| If you want to... | First command |
|---|---|
| start but do not know where to begin | `/abw-ask` |
| ask a quick factual question from existing knowledge | `/abw-query` |
| analyze tradeoffs, RCA, or a complex question | `/abw-query-deep` |
| work on a greenfield idea with no usable knowledge yet | `/abw-bootstrap` |
| define product scope or MVP | `/brainstorm` |
| configure AI style, persona, or autonomy | `/customize` |
| ingest source material into project knowledge | `/abw-ingest` |
| package wiki into compressed files for NotebookLM limits | `/abw-pack` |
| dry-run or sync an approved package to NotebookLM | `/abw-sync` |
| plan implementation | `/plan` |
| design system or database structure | `/design` |
| build UI mockups or screen specs | `/visualize` |
| start coding | `/code` |
| debug a bug | `/debug` |
| refactor legacy code but still need orientation | `/abw-ask` |
| refactor code with a clear scope already in mind | `/refactor` |
| save your working session | `/save-brain` |
| teach ABW a reusable behavioral lesson | `/abw-learn` |
| resume an interrupted project with one governed next safe step | `/abw-resume` |
| execute one approved continuation step and record its outcome | `/abw-execute` |
| start a session with state and grounding checks | `/abw-start` |
| wrap a session and prepare handover | `/abw-wrap` |
| restore last-session context | `/recap` |
| decide what to do next | `/next` |
| review code or project state before a heavier audit | `/abw-review` |
| audit code, product behavior, or security in the delivery loop | `/audit` |
| audit a change or artifact | `/abw-audit` |
| recover after a bad change | `/abw-rollback` |
| run the full acceptance chain | `/abw-eval` |
| update ABW commands in Gemini runtime | `/abw-update` |

---

## Resume An Interrupted Project

Use `/abw-resume` when a large project is already in motion and the agent must continue without breaking continuity.

`/abw-resume` runs the Continuation Kernel v1 flow:

```text
reconstruct -> select candidates -> constrain -> choose one safe step
```

It reads continuation runtime files under `.brain/`, checks locked decisions, unsafe zones, knowledge gaps, rollback risk, and step size, then presents exactly one next safe step.

Important: `/abw-resume` does not execute automatically. It asks for confirmation first. If no approved backlog exists, it can propose draft steps, but the user must approve them before they become executable backlog items.

Use `/abw-execute` only after `/abw-resume` has selected an approved step. `/abw-execute` prepares `.brain/active_execution.json`, keeps the agent inside the selected `candidate_files`, and records the result to `.brain/step_history.jsonl` and `.brain/handover_log.jsonl`.

`/abw-status` also reports Continuation Runtime health when continuation state exists: active step, backlog counts, next safe step, required approvals, and last execution outcome.

V2 runtime primitives add guarded support for dependency graphs, heuristic unsafe-zone detection, rollback planning, and multi-model file claims. These are intentionally conservative:

- `depends_on` blocks a step until prerequisite step IDs are accepted.
- `continuation_detect_unsafe.py` only writes `heuristic_suspected` zones, never hard blocks.
- `continuation_rollback.py` plans first and requires `execute --confirm` for allowlisted rollback methods.
- `continuation_claim.py` records model claims in `.brain/model_claims.jsonl` so parallel models do not edit overlapping files silently.

For machine-checkable gating, run:

```bash
python scripts/continuation_gate.py --workspace examples/resume-abw
```

To exercise the governed execution wrapper on a copy of the example fixture:

```bash
cp -R examples/resume-abw /tmp/resume-abw-execute
python scripts/continuation_execute.py prepare --workspace /tmp/resume-abw-execute
python scripts/continuation_rollback.py plan --workspace /tmp/resume-abw-execute
python scripts/continuation_execute.py record --workspace /tmp/resume-abw-execute --step-id step-safe-test --outcome success --changed-file tests/test_parser_resume.py --test-result pass --acceptance-result pass
python scripts/continuation_status.py --workspace /tmp/resume-abw-execute
python scripts/continuation_detect_unsafe.py --workspace /tmp/resume-abw-execute
python scripts/continuation_claim.py claim --workspace /tmp/resume-abw-execute --model-id gemini-flash --step-id step-safe-test
```

Relevant files:

- `docs/spec-continuation-kernel-v1.md`
- `workflows/abw-resume.md`
- `workflows/abw-execute.md`
- `skills/continuation-kernel.md`
- `scripts/continuation_gate.py`
- `scripts/continuation_execute.py`
- `scripts/continuation_status.py`
- `scripts/continuation_detect_unsafe.py`
- `scripts/continuation_rollback.py`
- `scripts/continuation_claim.py`
- `templates/resume_state.example.json`
- `templates/continuation_backlog.example.json`
- `templates/active_execution.example.json`
- `templates/model_claims.example.jsonl`
- `examples/resume-abw/`

---

## Repo Structure

- `workflows/`: command workflows and user-facing command model
- `skills/`: lower-level routing, grounding, evaluation, and execution rules
- `wiki/`: grounded project knowledge
- `.brain/`: working state, memory, and decision artifacts
- `install.ps1`, `install.sh`: installer that registers commands into Gemini runtime

For the command model in Vietnamese, see `workflows/README.md`.

## Maintainer Docs

- `docs/ARCHITECTURE.md`: source of truth for public surface, compatibility layer, internal artifacts, and runtime assembly
- `docs/RELEASE_CHECKLIST.md`: release gate before shipping ABW changes
- `docs/GROUNDING_BACKENDS.md`: current grounding backend contract and future abstraction direction
- `examples/hello-abw/`: minimal example workspace for ingest, pack, sync, and eval
