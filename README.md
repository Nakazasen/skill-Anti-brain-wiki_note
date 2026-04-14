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

Nếu nói ngắn gọn, đợt này biến ABW từ “có grounding” thành “có kỷ luật vận hành”.

Repo này tồn tại để giúp các mô hình nhỏ hơn, rẻ hơn, nhanh hơn hành xử giống hệ thống có kỷ luật thay vì chatbot phản xạ nhanh.

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
    `/abw-start`, `/abw-learn`, `/save-brain`, `/recap`, `/next`, `/abw-wrap`
 
 5. **Đánh giá và nghiệm thu**  
    `/abw-review`, `/abw-audit`, `/abw-meta-audit`, `/abw-rollback`, `/abw-accept`, `/abw-eval`
 
 6. **Tiện ích và Cấu hình**  
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
5. Dùng `/abw-update` khi muốn kéo bản command mới nhất vào Gemini runtime local.

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
