# SKILL: abw-eval

> **Purpose:** Chạy full evaluation chain cho một thay đổi: audit -> meta-audit -> rubric scoring -> acceptance verdict.
> **Role:** Orchestration utility (used by `/abw-eval`)

---

## Instructions for AI Operator

Khi user gọi `/abw-eval`, thực hiện quy trình sau:

### 1. Xác định scope evaluation

Ví dụ:

- router patch
- docs cleanup
- command model update
- toàn bộ thay đổi của phiên này

Nếu scope không rõ, nêu giả định trước khi bắt đầu.

### 2. Giai đoạn 1: Audit

Chạy logic tương đương `/abw-audit`:

- đọc artifact thật
- tạo findings
- tạo evidence
- nêu residual risks

### 3. Giai đoạn 2: Meta-audit

Chạy logic tương đương `/abw-meta-audit` trên chính báo cáo audit vừa tạo:

- tìm overclaim
- tìm claim thiếu bằng chứng
- chỉnh verdict nếu cần

### 4. Giai đoạn 3: Acceptance

Chạy logic tương đương `/abw-accept`:

- chấm theo rubric
- tách blocker và non-blocker
- đưa ra verdict cuối

### 5. Output Format

```markdown
# ABW Full Evaluation Report

## Scope
- <scope>

## Stage 1: Audit Summary
- Findings:
  - <list>
- Residual Risks:
  - <list>

## Stage 2: Meta-Audit Corrections
- <what the audit overstated or missed>

## Stage 3: Rubric Scoring
- <category>: <score or Not targeted>

## Acceptance Verdict
- FAIL
- PASS WITH CRITICAL GAPS
- PASS WITH MINOR GAPS
- PASS

## Next Required Action
- <next step>
```

### 6. Restrictions

- `/abw-eval` là lệnh orchestration, không tự sửa file
- Không được bỏ qua meta-audit
- Không được bỏ qua rubric scoring
- Không được tuyên bố PASS nếu chưa qua đủ 3 giai đoạn

