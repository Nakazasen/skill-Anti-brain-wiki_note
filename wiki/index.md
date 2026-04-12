# Hybrid Anti-Brain-Wiki -- Knowledge Index

> **Auto-generated index.** Updated by `ingest-wiki` and `lint-wiki` skills.  
> Last updated: 2026-04-11T23:58:00+07:00

---

## How This Wiki Works

```
raw/  ->  processed/  ->  NotebookLM grounding  ->  wiki/  ->  index update  ->  .brain/ log
```

- **Never** write directly from `raw/` to `wiki/`.
- Every note follows [`wiki/_schemas/note.schema.md`](./_schemas/note.schema.md).
- Every processed source has a line in [`processed/manifest.jsonl`](../processed/manifest.jsonl).

---

## Entities

<!-- AUTO-GENERATED: Do not manually edit below this marker -->
<!-- ENTITY_INDEX_START -->

_No entities yet. Run `ingest-wiki` to populate._

<!-- ENTITY_INDEX_END -->

---

## Concepts

<!-- AUTO-GENERATED: Do not manually edit below this marker -->
<!-- CONCEPT_INDEX_START -->

| ID | Title | Status | Confidence | Updated |
|----|-------|--------|------------|--------|
| `postgresql-selection-rationale` | [PostgreSQL Selection Rationale](concepts/postgresql-selection-rationale.md) | grounded | medium | 2026-04-11 |
| `mongodb-evaluation` | [MongoDB Evaluation](concepts/mongodb-evaluation.md) | disputed | low | 2026-04-11 |

<!-- CONCEPT_INDEX_END -->

---

## Timelines

<!-- AUTO-GENERATED: Do not manually edit below this marker -->
<!-- TIMELINE_INDEX_START -->

_No timelines yet. Run `ingest-wiki` to populate._

<!-- TIMELINE_INDEX_END -->

---

## Sources

<!-- AUTO-GENERATED: Do not manually edit below this marker -->
<!-- SOURCE_INDEX_START -->

_No sources yet. Run `ingest-wiki` to populate._

<!-- SOURCE_INDEX_END -->

---

## Knowledge Health

| Metric | Count |
|--------|-------|
| Total notes | 2 |
| Grounded | 1 |
| Draft | 0 |
| Stale | 0 |
| Disputed | 1 |
| Open gaps | See [`.brain/knowledge_gaps.json`](../.brain/knowledge_gaps.json) |
| Pending grounding | See [`.brain/grounding_queue.json`](../.brain/grounding_queue.json) |

---

## Cross-Reference Map

_Empty -- will be populated as notes with `related` fields are added._

---

## Quick Commands (Unified Model)

| Lane | Command | Purpose |
|------|---------|---------|
| **Khám phá và tư duy** | `/abw-ask` | **Entry mặc định (Smart Router)** |
| **Khám phá và tư duy** | `/brainstorm` | Chốt brief sản phẩm, phạm vi MVP, và discovery |
| **Dựng nền tri thức** | `/abw-ingest` | Xử lý nguồn raw thành tri thức trong wiki |
| **Dựng nền tri thức** | `/abw-query` | Tra cứu nhanh và truy hồi theo wiki-first |
| **Triển khai sản phẩm** | `/plan` | Lập kế hoạch thực thi và chia task |
| **Triển khai sản phẩm** | `/code` | Cài đặt tính năng và phát triển |
| **Phiên làm việc và ghi nhớ** | `/save-brain` | Lưu tiến độ và chuẩn bị handover |
| **Phiên làm việc và ghi nhớ** | `/abw-start` | Mở phiên và kiểm tra trạng thái hệ thống |
| **Phiên làm việc và ghi nhớ** | `/abw-wrap` | Chốt phiên và chuẩn bị quay lại |
| **Đánh giá và nghiệm thu** | `/abw-audit` | Tự audit một thay đổi, tài liệu, workflow, hoặc đầu ra |
| **Đánh giá và nghiệm thu** | `/abw-review` | Review code, thay đổi, hoặc hiện trạng dự án |
| **Đánh giá và nghiệm thu** | `/abw-meta-audit` | Audit lại chính báo cáo audit |
| **Đánh giá và nghiệm thu** | `/abw-rollback` | Quay về trạng thái an toàn sau thay đổi lỗi |
| **Đánh giá và nghiệm thu** | `/abw-accept` | Chạy cổng nghiệm thu cuối cùng |
| **Đánh giá và nghiệm thu** | `/abw-eval` | Chạy toàn bộ chuỗi evaluation |
| **Dựng nền tri thức** | `/abw-lint` | Audit sức khỏe wiki, manifest, và grounding |
| **Dựng nền tri thức** | `/abw-status` | Kiểm tra cầu nối MCP và trạng thái hàng đợi |
| **Dựng nền tri thức** | `/abw-setup` | Cấu hình kết nối NotebookLM MCP |

---

*Schema: [`wiki/_schemas/note.schema.md`](./_schemas/note.schema.md)*  
*Manifest: [`processed/manifest.jsonl`](../processed/manifest.jsonl)*
