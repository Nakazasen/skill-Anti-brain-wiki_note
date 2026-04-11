# Hybrid ABW for Antigravity IDE

## Problem

Gemini Flash trong Antigravity IDE phản hồi nhanh nhưng thua rõ khi phải giữ context dài, truy tri thức nội bộ, kiểm chứng nguồn, và duy trì chất lượng suy luận qua nhiều phiên làm việc.

## Goal

Xây một lớp hybrid quanh Gemini Flash để tăng năng lực thực chiến bằng:

- operational memory rõ ràng
- persistent knowledge có cấu trúc
- grounding sâu trên dữ liệu private
- query và audit có citation, contradiction tracking, và gap logging

## Core Idea

Tách hệ thống thành ba lớp có vai trò cố định:

- `.brain/`: operational memory. Giữ session state, blockers, pending tasks, handover, recap metadata.
- `wiki/`: persistent knowledge. Giữ entity, concept, timeline, source note, cross-links, contradiction notes.
- `NotebookLM MCP`: primary grounding engine. Dùng để verify, synthesize, deep-query dữ liệu private trước khi compile vào wiki.

`processed/` là lớp chuẩn hóa trung gian bắt buộc giữa `raw/` và `wiki/`.

## Non-Goals

- Không biến `.brain/` thành nơi lưu kiến thức dài hạn.
- Không ghi thẳng từ `raw/` vào `wiki/`.
- Không coi NotebookLM là source of truth tuyệt đối.
- Không phụ thuộc một lần prompt để giải quyết toàn bộ ingest, query, lint, commit, demo.

## Target Users

- Người dùng Antigravity IDE làm việc với dữ liệu nội bộ, tài liệu công ty, research note, specs, meeting note.
- Team muốn một wiki sống, có citation, và có thể recap lại qua nhiều session.

## MVP Scope

1. Folder structure chuẩn:
   `raw/`, `processed/`, `wiki/`, `.brain/`, `notebooks/`, `skills/`
2. Bridge rule giữa `.brain`, `processed`, `wiki`, và NotebookLM MCP
3. Ba luồng chính:
   `ingest-wiki`, `query-wiki`, `lint-wiki`
4. Artifact tối thiểu:
   `processed/manifest.jsonl`, `.brain/grounding_queue.json`, `.brain/knowledge_gaps.json`, `wiki/index.md`
5. Query policy:
   wiki-first, NotebookLM-second, gap-log-if-insufficient

## Workflow

### Ingest

`raw -> processed extraction -> NotebookLM grounding -> wiki compile -> index/link update -> .brain log update`

### Query

`recap -> search wiki -> if needed NotebookLM deep grounding -> answer with citations -> log knowledge gap if unresolved`

### Lint

`structural audit + contradiction candidates + ungrounded note check + notebook grounding health`

## Key Rules

- Chỉ update `wiki/` khi note đã đi qua `processed/` và có grounding status rõ ràng.
- Mỗi note trong wiki phải có source reference, updated_at, và trạng thái grounding.
- `.brain/` chỉ giữ state điều phối, không giữ prose knowledge dài hạn.
- Nếu NotebookLM MCP unavailable, hệ thống phải degrade an toàn:
  tạo draft hoặc queue, không fake success.

## Risks

- NotebookLM MCP có thể không ổn định hoặc phụ thuộc auth/browser runtime.
- Markdown wiki dễ thành đống note đẹp nhưng khó kiểm chứng nếu thiếu schema và manifest.
- Nếu không có lint/gap queue thì knowledge base sẽ drift dần.

## Success Criteria

- Ingest một nguồn tạo ra processed artifact và ít nhất một wiki note có citation.
- Query trả lời được từ wiki hoặc NotebookLM với path nguồn rõ ràng.
- Khi thiếu dữ liệu, hệ thống ghi gap vào `.brain/knowledge_gaps.json`.
- Lint phát hiện được orphan, duplicate, dead link, contradiction candidate, và ungrounded note.
