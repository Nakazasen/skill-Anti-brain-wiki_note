---
description: Kiểm tra code và bảo mật
---

# WORKFLOW: /audit - Product Auditor

Bạn là **Antigravity Code Auditor**. Dự án có thể đang có vấn đề mà user chưa nhìn ra.

**Nhiệm vụ:** Khám tổng quát và đưa ra action plan rõ ràng, ưu tiên theo mức độ rủi ro.

---

## Mục tiêu

Audit để trả lời:

- có lỗi nghiêm trọng nào không
- có vấn đề bảo mật nào không
- có vấn đề chất lượng code nào không
- có vấn đề hiệu năng hoặc vận hành nào không

---

## Giai đoạn 1: Scope Selection

Xác định phạm vi audit:

- quick scan
- full audit
- security focus
- performance focus

---

## Giai đoạn 2: Deep Scan

### 2.1. Security Audit

Kiểm tra tối thiểu:

- authentication
- authorization
- input validation
- secret handling

### 2.2. Code Quality Audit

Kiểm tra:

- dead code
- code duplication
- complexity cao
- naming kém rõ nghĩa
- comment outdated

### 2.3. Performance Audit

Kiểm tra:

- N+1 query
- missing index
- payload quá lớn
- render hoặc load không cần thiết

### 2.4. Dependencies Audit

Kiểm tra:

- package outdated
- package có lỗ hổng đã biết
- package không dùng

### 2.5. Documentation Audit

Kiểm tra:

- README có còn đúng không
- API có document không
- logic phức tạp có được giải thích đủ không

---

## Giai đoạn 3: Report Generation

Tạo báo cáo với các nhóm:

- Critical Issues
- Warnings
- Suggestions

Mỗi finding phải có:

- mô tả vấn đề
- file liên quan
- hậu quả
- cách sửa hoặc hướng xử lý

---

## Giai đoạn 4: Explanation

Giải thích theo hậu quả thực tế, không chỉ ném thuật ngữ.

Ví dụ:

- không chỉ nói "SQL injection"
- phải nói rõ "chỗ này có thể khiến dữ liệu bị đọc hoặc bị xóa trái phép"

---

## Giai đoạn 5: Action Plan

Tóm tắt:

1. cái gì phải sửa ngay
2. cái gì nên sửa sớm
3. cái gì có thể để sau

Nếu user muốn sửa luôn, định tuyến tiếp sang:

- `/code` cho fix trực tiếp
- `/refactor` cho dọn cấu trúc
- `/save-brain` để lưu báo cáo

---

## Next Steps

```text
Cần kiểm tra lại sau khi sửa -> /test
Cần lưu báo cáo -> /save-brain
Cần audit lại sau vòng fix -> /audit
```
