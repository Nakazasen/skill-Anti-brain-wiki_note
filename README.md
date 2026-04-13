# Hybrid ABW

> Version: 1.3.1  
> EN: Turn a fast-answering LLM into a grounded, stateful, evaluation-aware working system.  
> VI: Bien mot LLM tra loi nhanh thanh mot he thong lam viec co grounding, co bo nho, va co lop nghiem thu ro rang.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![TTC: Enabled](https://img.shields.io/badge/Test--Time%20Compute-Active-brightgreen)](https://github.com/Nakazasen/skill-Anti-brain-wiki_note)

Hybrid ABW is an operating discipline for AI work. It combines:

- grounded project knowledge in `wiki/`
- working state in `.brain/`
- bounded reasoning for hard questions
- explicit evaluation before acceptance

Hybrid ABW la mot ky luat van hanh cho agent AI. He thong ket hop:

- tri thuc du an co grounding trong `wiki/`
- trang thai lam viec trong `.brain/`
- suy luan co gioi han cho cau hoi kho
- lop danh gia truoc khi chap nhan dau ra

---

## Core Idea

**EN**

- Do not fake knowledge.
- Do not claim grounding when grounding is unavailable.
- Do not skip evaluation when output quality matters.

**VI**

- Khong duoc bia tri thuc.
- Khong duoc nhan la da grounding neu grounding khong san sang.
- Khong duoc bo qua nghiem thu khi chat luong dau ra quan trong.

This repo exists to help smaller, cheaper, faster models behave more like disciplined systems instead of impulsive chatbots.

Repo nay ton tai de giup cac mo hinh nho hon, re hon, nhanh hon hanh xu giong he thong co ky luat thay vi chatbot phan xa nhanh.

---

## Two Entrypoints

### `/abw-ask` = Work Entrypoint

Start here when you have a task, question, or request and want the router to choose the right lane.

Bat dau o day khi ban co task, cau hoi, hoac yeu cau va muon router chon lane phu hop.

### `/abw-eval` = Evaluation Entrypoint

Start here when work already exists and you want to audit, challenge, or accept the output.

Bat dau o day khi da co dau ra va ban muon audit, challenge, hoac chap nhan truoc khi coi la xong.

---

## Mental Model: 5 Lanes

1. **Kham pha va tu duy**  
   `/abw-ask`, `/abw-query`, `/abw-query-deep`, `/abw-bootstrap`, `/brainstorm`

2. **Dung nen tri thuc**  
   `/abw-init`, `/abw-setup`, `/abw-status`, `/abw-ingest`, `/abw-pack`, `/abw-sync`, `/abw-lint`

3. **Trien khai san pham**  
   `/plan`, `/design`, `/visualize`, `/code`, `/run`, `/debug`, `/test`, `/deploy`, `/refactor`, `/audit`

4. **Phien lam viec va ghi nho**  
   `/abw-start`, `/save-brain`, `/recap`, `/next`, `/abw-wrap`

5. **Danh gia va nghiem thu**  
   `/abw-review`, `/abw-audit`, `/abw-meta-audit`, `/abw-rollback`, `/abw-accept`, `/abw-eval`

---

## Quick Start / Install

Clone repo, then run the installer to register all Hybrid ABW commands into Gemini. Cloning alone does not activate the command surface.

Hay clone repo, sau do chay installer de dang ky toan bo lenh Hybrid ABW vao Gemini. Chi clone repo thi chua kich hoat command surface.

### Windows

```powershell
irm https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.ps1 | iex
```

### macOS / Linux

```bash
curl -fsSL https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.sh | sh
```

Sau khi cai xong:

1. Chay `/abw-setup` de cau hinh grounding.
2. Dung `/abw-ask` cho moi task hoac cau hoi chua ro lane.
3. Dung `/abw-eval` khi muon nghiem thu thay doi hoac dau ra.
4. Dung `/abw-update` khi muon keo ban command moi nhat vao Gemini runtime local.

---

## First Command Cheat Sheet

| If you want to... | First command |
|---|---|
| start but do not know where to begin | `/abw-ask` |
| ask a quick factual question from existing knowledge | `/abw-query` |
| analyze tradeoffs, RCA, or a complex question | `/abw-query-deep` |
| work on a greenfield idea with no usable knowledge yet | `/abw-bootstrap` |
| define product scope or MVP | `/brainstorm` |
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
| start a session with state and grounding checks | `/abw-start` |
| wrap a session and prepare handover | `/abw-wrap` |
| restore last-session context | `/recap` |
| decide what to do next | `/next` |
| review code or project state before a heavier audit | `/abw-review` |
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
