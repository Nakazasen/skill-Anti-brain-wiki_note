# SKILL: abw-accept

> **Purpose:** Chạy acceptance gate cuối cùng cho một thay đổi hoặc artifact theo Hybrid ABW Rubric.
> **Role:** Acceptance utility (used by `/abw-accept`)

---

## Instructions for AI Operator

Khi user gọi `/abw-accept`, thực hiện quy trình sau:

### 1. Xác định đối tượng cần nghiệm thu

Ví dụ:

- router patch
- docs cleanup
- installer hardening
- toàn bộ thay đổi của phiên hiện tại

Nếu scope mơ hồ, nêu rõ giả định trước khi chấm.

### 2. Thu thập đầu vào nghiệm thu

Đọc:

- artifact thật
- audit trước đó nếu có
- meta-audit trước đó nếu có

Nếu chưa có audit/meta-audit, bạn vẫn có thể nghiệm thu, nhưng phải nói rõ mức độ tin cậy thấp hơn.

### 3. Chấm theo rubric

Tham chiếu:
- `HYBRID_ABW_RUBRIC.md`

Chỉ chấm các mục liên quan trực tiếp đến scope.

Với mỗi mục:

- cho điểm hoặc `Not targeted`
- nêu ngắn gọn lý do

### 4. Phân biệt blocker và non-blocker

Mọi vấn đề phải được tách thành:

- **Blocking issues**
- **Non-blocking issues**

Không được gộp chung.

### 5. Output Format

```markdown
# ABW Acceptance Report

## Scope Under Acceptance
- <scope>

## Inputs Considered
- <artifacts, audit reports, meta-audit reports>

## Rubric Scoring
- <category>: <score or Not targeted> - <reason>

## Blocking Issues
- <must-fix items>

## Non-Blocking Issues
- <minor gaps>

## Final Verdict
- FAIL
- PASS WITH CRITICAL GAPS
- PASS WITH MINOR GAPS
- PASS

## Required Next Action
- <what must happen next>
```

### Finalization Rule
Append the terminal block from `workflows/finalization.md`.
- Map `PASS` to `verified`.
- Map `PASS WITH MINOR GAPS` to `partially_verified`.
- Map `PASS WITH CRITICAL GAPS` to `blocked`.
- Map `FAIL` to `blocked`.
- Do not claim `PASS` unless the evidence is strong enough for the current scope.
- Before emitting the verdict, run `scripts/finalization_check.py` on the drafted Finalization block.
- If the checker returns `downgrade` or `blocked`, lower the state before finalizing.

### 6. Restrictions

- `/abw-accept` không được sửa file
- Không được để verdict mạnh hơn evidence thật
- Nếu còn blocker, không được PASS
