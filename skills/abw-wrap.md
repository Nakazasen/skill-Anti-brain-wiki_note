# SKILL: abw-wrap

> **Purpose:** Đóng phiên làm việc theo cách có lưu tiến độ, có handover, và có nhắc các thay đổi cần ingest hoặc nghiệm thu.
> **Role:** Session wrap utility (used by `/abw-wrap`)

---

## Instructions for AI Operator

Khi user gọi `/abw-wrap`, thực hiện theo trình tự:

### 1. Tóm tắt phần đã làm

Tóm tắt ngắn:
- thay đổi chính
- file hoặc khu vực chính đã đụng vào
- phần nào đã xong
- phần nào còn mở

### 2. Kiểm tra nhu cầu lưu và ingest

Xác định:
- có cần `/save-brain` để lưu state không
- có tri thức mới cần đưa vào `raw/` hoặc `wiki/` không
- có thay đổi quan trọng cần nghiệm thu bằng `/abw-eval` không

### 3. Chuẩn bị handover

Nêu rõ:
- nếu quay lại thì nên bắt đầu từ đâu
- lệnh đầu tiên nên gọi ở phiên sau là gì
- nhắc phiên sau chạy `/recap` trước để nạp `.brain/handover.md`, `.brain/session.json`, và `.brain/lessons_learned.jsonl`
- nếu đã biết scope tiếp theo, ghi rõ lệnh sau `/recap`, ví dụ `/code`, `/debug`, `/test`, `/refactor`, hoặc `/abw-ask`

### 4. Output format

```markdown
# ABW Wrap Report

## What Was Done
- <list>

## Open Items
- <list>

## Save / Ingest / Eval Recommendations
- <list>

## Recommended First Command For Next Session
- <command>

## Lessons To Re-Apply
- <active lessons or "Run /recap to load active lessons before continuing">
```

### 5. Restrictions

- Không được giả định mọi thay đổi đã được ingest
- Không được tuyên bố “xong hoàn toàn” nếu còn open items
- Nếu cần, phải nhắc user dùng `/save-brain` hoặc `/abw-eval`
