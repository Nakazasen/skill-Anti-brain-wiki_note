Bạn là kiến trúc sư Antigravity IDE + Hybrid Anti-Brain-Wiki, nhiệm vụ là nâng năng lực thực chiến của Gemini Flash bằng workflow, memory, grounding và knowledge compilation, không phải bằng việc giả định model thông minh hơn.

Mục tiêu:

- Tách rõ operational memory và persistent knowledge
- Dùng NotebookLM MCP làm primary grounding engine cho dữ liệu private
- Biến Gemini Flash thành một hệ thống có thể ingest, query, lint, recap và tự ghi nhận knowledge gaps

Kiến trúc bắt buộc:

- `.brain/` = operational memory duy nhất
  Giữ session state, blockers, pending tasks, handover, recap metadata, grounding queue, knowledge gaps.
- `raw/` = nguồn gốc chưa chuẩn hóa
- `processed/` = normalized evidence layer
  Mọi dữ liệu trước khi vào wiki phải có manifest hoặc provenance rõ ràng tại đây.
- `wiki/` = persistent knowledge base theo tinh thần Karpathy LLM Wiki
  Chỉ chứa tri thức đã compile, linked, có citation và grounding status.
- `NotebookLM MCP` = primary grounding engine
  Dùng để verify, synthesize, cross-check, deep-query dữ liệu private trước khi cập nhật wiki.

Quy tắc bất biến:

- Không dùng `.brain/` để lưu tri thức dài hạn.
- Không update `wiki/` trực tiếp từ `raw/`.
- Chỉ update `wiki/` sau khi dữ liệu đã đi qua `processed/` và có grounding status rõ ràng.
- Không coi NotebookLM là source of truth tuyệt đối.
  Source of truth là evidence đã được lưu và trace được trong `raw/`, `processed/`, và `wiki/`.
- Nếu NotebookLM MCP không khả dụng, phải degrade an toàn:
  tạo draft, queue, hoặc TODO rõ ràng; không được fake success.

Hãy thực hiện trong workspace hiện tại:

1. Tạo hoặc cập nhật cấu trúc:
   - `raw/`
   - `processed/`
   - `wiki/`
   - `wiki/entities/`
   - `wiki/concepts/`
   - `wiki/timelines/`
   - `wiki/sources/`
   - `wiki/_indexes/`
   - `wiki/_schemas/`
   - `.brain/`
   - `notebooks/`
   - `skills/`
   - `AGENTS.md`
   - `brain-state-helper-bridge.md`

2. Reuse AWF hiện có trong repo làm nền cho `.brain/`.
   Nếu repo đã có workflow hoặc skill tương đương thì bridge hoặc tham chiếu, không copy mù quáng.

3. Tạo bốn skill:
   - `skills/ingest-wiki.md`
   - `skills/query-wiki.md`
   - `skills/lint-wiki.md`
   - `skills/notebooklm-mcp-bridge.md`

4. Tạo các artifact bắt buộc:
   - `processed/manifest.jsonl`
   - `.brain/grounding_queue.json`
   - `.brain/knowledge_gaps.json`
   - `wiki/index.md`
   - `wiki/_schemas/note.schema.md`

5. Thiết kế ingest pipeline theo thứ tự:
   `raw -> processed extraction -> NotebookLM grounding -> wiki compile -> index/link update -> .brain log update`

6. Thiết kế query policy:
   - recap trước nếu có `.brain/`
   - trả lời từ `wiki/` nếu đủ
   - nếu cần synthesis sâu thì gọi NotebookLM MCP
   - nếu vẫn thiếu dữ liệu thì trả lời với citation hiện có và ghi gap vào `.brain/knowledge_gaps.json`

7. Thiết kế lint policy:
   - orphan notes
   - dead links
   - duplicate entities
   - contradiction candidates
   - ungrounded notes
   - stale notes
   - notebook grounding health

8. Cập nhật `AGENTS.md` mô tả rõ:
   - separation of memory layers
   - grounding policy
   - compile policy
   - fallback khi NotebookLM MCP unavailable
   - query policy: wiki-first, NotebookLM-second, gap-log-if-insufficient

9. Nếu môi trường có NotebookLM MCP sẵn sàng, tạo notebook demo đầu tiên và thêm source mẫu.
   Nếu MCP chưa khả dụng, tạo stub config hoặc TODO rõ ràng thay vì báo thành công giả.

10. Chỉ commit nếu các artifact cốt lõi đã được tạo thật và không có bước nào bị fake success.

Yêu cầu chất lượng:

- Mỗi note trong `wiki/` phải có metadata tối thiểu:
  `status`, `sources`, `grounding`, `updated_at`, `confidence`
- Mọi thay đổi quan trọng phải để lại dấu vết ở `.brain/` hoặc `processed/manifest.jsonl`
- Ingest phải idempotent tối đa có thể
- Query phải ưu tiên câu trả lời có citation thay vì câu trả lời nghe có vẻ đúng
- Lint phải báo cả lỗi cấu trúc lẫn rủi ro tri thức

Kết quả cuối cùng phải nêu rõ:

- những gì đã được tạo thật trong workspace
- những gì đang hoạt động thật
- những gì còn pending vì phụ thuộc NotebookLM MCP hoặc runtime
- cách dùng `ingest-wiki`, `query-wiki`, `lint-wiki`
