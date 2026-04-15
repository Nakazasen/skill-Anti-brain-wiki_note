# SKILL: abw-start

> **Purpose:** Mở phiên làm việc Hybrid ABW theo cách có kiểm tra trạng thái, có kết nối grounding nếu khả dụng, và có hướng đi đầu tiên rõ ràng.
> **Role:** Session bootstrap utility (used by `/abw-start`)

---

## Instructions for AI Operator

Khi user gọi `/abw-start`, thực hiện theo trình tự:

### 1. Quét trạng thái hiện tại

Đọc nhanh:
- `.brain/brain.json` nếu có
- `.brain/session.json` nếu có
- `.brain/lessons_learned.jsonl` nếu có; lọc các lesson `status="active"` và chưa hết hạn
- thư mục `raw/`
- thư mục `wiki/`

Mục tiêu:
- biết dự án đang greenfield hay đã có tri thức
- biết có session cũ để khôi phục không
- biết có bài học nào cần áp dụng ngay từ đầu phiên không

### 2. Kiểm tra grounding path

Xác định:
- NotebookLM / MCP có vẻ sẵn sàng không
- có cần chạy `/abw-setup` hoặc `/abw-status` không

Nếu chưa thể xác minh grounding, nói rõ trạng thái là chưa sẵn sàng, không được giả vờ đã kết nối.

### 3. Chọn điểm bắt đầu đúng

Ưu tiên:
- nếu chưa có cấu trúc -> đề xuất `/abw-init`
- nếu chưa có kết nối -> đề xuất `/abw-setup`
- nếu có tài liệu raw chưa ingest -> đề xuất `/abw-ingest`
- nếu user đã có câu hỏi hoặc task -> chuyển sang `/abw-ask`
- nếu cần khôi phục bối cảnh -> chuyển sang `/recap`

### 4. Output format

```markdown
# ABW Start Report

## Workspace State
- <greenfield / knowledgeable / mixed>

## Grounding State
- <ready / not ready / unknown>

## Session State
- <fresh session / resumable session>

## Active Lessons
- <none / top relevant lessons from .brain/lessons_learned.jsonl>

## Recommended First Command
- <command>

## Why
- <short reason>

## Fallback
- <what to do if MCP / grounding is unavailable>
```

### 5. Restrictions

- Không được tự sửa file trong `/abw-start`
- Không được giả định NotebookLM đã sẵn sàng nếu chưa có bằng chứng
- Không được nhảy thẳng vào code nếu chưa rõ trạng thái tri thức
- Không được bỏ qua `.brain/lessons_learned.jsonl` khi file tồn tại; nếu chưa đọc được, báo rõ trong Active Lessons
