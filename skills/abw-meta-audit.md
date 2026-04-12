# SKILL: abw-meta-audit

> **Purpose:** Audit lại chính báo cáo audit trước đó để phát hiện overclaim, thiếu bằng chứng, hoặc verdict quá mạnh.
> **Role:** Evaluation utility (used by `/abw-meta-audit`)

---

## Instructions for AI Operator

Khi user gọi `/abw-meta-audit`, thực hiện quy trình sau:

### 1. Xác định báo cáo audit đang bị review

Chỉ rõ:

- báo cáo audit nào đang được xem xét
- scope audit đó là gì
- verdict cũ là gì

Nếu không có báo cáo audit trước đó trong ngữ cảnh, phải nói rõ là không đủ đầu vào.

### 2. Đối chiếu lại với artifact thật

Đọc lại:

- báo cáo audit cũ
- các file thực tế liên quan đến patch đó

Không được lặp lại audit cũ một cách máy móc. Mục tiêu là so:

- claim cũ nói gì
- file thật chứng minh được đến đâu

### 3. Phân loại claim cũ

Với mỗi claim quan trọng, phân loại:

- `supported`
- `partially supported`
- `unsupported`

Phải đặc biệt bắt các lỗi kiểu:

- overclaim
- under-evidenced
- nhầm fact với inference
- PASS quá sớm

### 4. Correct the verdict if needed

Nếu verdict cũ quá lạc quan, phải hạ verdict.

Ví dụ:

- từ `PASS` xuống `PASS WITH MINOR GAPS`
- từ `PASS WITH MINOR GAPS` xuống `PASS WITH CRITICAL GAPS`
- hoặc `FAIL`

### 5. Output Format

```markdown
# ABW Meta-Audit Report

## Audit Report Under Review
- <summary of the previous audit>

## Meta-Findings
- <what the previous audit got right / wrong>

## Evidence Check
- Claim: <old claim>
  - Artifact: <file or output>
  - Verdict: supported | partially supported | unsupported

## Scoring Review
- <only the rubric categories relevant to the old report>

## Corrected Verdict
- FAIL
- PASS WITH CRITICAL GAPS
- PASS WITH MINOR GAPS
- PASS

## What Should Happen Next
- <next patch or next review step>
```

### 6. Restrictions

- Không được tự bảo vệ audit cũ
- Không được bỏ qua mâu thuẫn giữa report và file thật
- Không được sửa file trong `/abw-meta-audit`
