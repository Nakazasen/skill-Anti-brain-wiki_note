# SKILL: abw-rollback

> **Purpose:** Quay lại trạng thái an toàn khi thay đổi vừa rồi làm hỏng hệ thống hoặc đi sai hướng.
> **Role:** Recovery utility (used by `/abw-rollback`)

---

## Instructions for AI Operator

Khi user gọi `/abw-rollback`, thực hiện theo trình tự:

### 1. Damage assessment

Xác định:
- thay đổi nào vừa diễn ra
- file nào bị ảnh hưởng
- lỗi hiện tại là gì
- user muốn rollback một phần hay toàn phần

### 2. Chọn chiến lược recovery

Ưu tiên một trong ba hướng:
- rollback file cụ thể
- rollback thay đổi gần nhất
- không rollback, chuyển sang `/debug` nếu user không muốn mất code mới

### 3. Safety gate

Trước khi đề xuất rollback:
- nói rõ phạm vi sẽ mất những gì
- nói rõ nếu cần backup hoặc diff trước khi rollback

### 4. Output format

```markdown
# ABW Rollback Plan

## Damage Summary
- <summary>

## Recommended Recovery Option
- <option>

## What Will Be Lost
- <list>

## Safer Alternative
- <alternative command if any>
```

### 5. Restrictions

- Không tự chạy lệnh destructive nếu user chưa rõ phạm vi rollback
- Không đánh đồng rollback với debug
- Nếu có thể giữ code mới và sửa được, phải nói rõ lựa chọn đó
