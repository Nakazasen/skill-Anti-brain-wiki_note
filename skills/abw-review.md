# SKILL: abw-review

> **Purpose:** Review code, thay đổi, hoặc hiện trạng dự án theo hướng đọc hiểu, nhận xét, và chỉ ra bước tiếp theo hợp lý.
> **Role:** Review utility (used by `/abw-review`)

---

## Instructions for AI Operator

Khi user gọi `/abw-review`, thực hiện theo trình tự:

### 1. Xác định scope review

Review cái gì:
- một file
- một thay đổi
- một module
- toàn bộ hiện trạng dự án

Nếu scope mơ hồ, nêu giả định scope ở đầu báo cáo.

### 2. Đọc artifact thật

Không review bằng trí nhớ. Đọc các file hoặc diff liên quan trực tiếp.

### 3. Chế độ review

Tùy ngữ cảnh, ưu tiên một trong ba mode:
- code review
- project review
- handover review

### 4. Output format

```markdown
# ABW Review Report

## Scope
- <scope>

## What Looks Good
- <list>

## What Needs Attention
- <list>

## Recommended Next Action
- <command and reason>
```

### 5. Escalation rule

Nếu có vấn đề nghiêm trọng:
- chuyển sang `/abw-audit` nếu cần audit chặt hơn
- chuyển sang `/debug` nếu là bug cụ thể
- chuyển sang `/abw-rollback` nếu thay đổi vừa rồi làm hỏng trạng thái an toàn

### 6. Restrictions

- Không được nhầm review với audit severity đầy đủ
- Không được kết luận PASS/FAIL kiểu nghiệm thu cuối trong `/abw-review`
