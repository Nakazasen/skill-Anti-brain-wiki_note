# SKILL: abw-audit

> **Purpose:** Self-audit một thay đổi, một nhóm file, hoặc một artifact hiện tại theo Hybrid ABW Rubric.
> **Role:** Evaluation utility (used by `/abw-audit`)

---

## Instructions for AI Operator

Khi user gọi `/abw-audit`, thực hiện quy trình sau:

### 1. Xác định scope audit

Đầu tiên, xác định rõ scope user muốn audit là gì:

- router
- docs
- command surface
- workflow cụ thể
- installer
- toàn bộ thay đổi của phiên hiện tại

Nếu scope mơ hồ, phải nêu rõ giả định scope ở đầu báo cáo.

### 2. Đọc artifact thật

Không audit bằng trí nhớ. Đọc các file liên quan trực tiếp đến scope.

Nếu scope là:

- **router** -> đọc `workflows/abw-ask.md`, `skills/abw-router.md`
- **docs / command surface** -> đọc `workflows/help.md`, `workflows/README.md`, `workflows/next.md`, `wiki/index.md`
- **session** -> đọc `workflows/save_brain.md`, `workflows/recap.md`, `workflows/next.md`
- **delivery** -> đọc `workflows/plan.md`, `workflows/design.md`, `workflows/code.md`, `workflows/debug.md`
- **installer** -> đọc `install.ps1`, `install.sh`

Có thể đọc thêm file khác nếu cần, nhưng phải giữ phạm vi hẹp.

### 3. Audit theo Hybrid ABW Rubric

Tham chiếu file:
- `HYBRID_ABW_RUBRIC.md`

Chỉ chấm các mục rubric liên quan trực tiếp đến scope hiện tại.

Với mục không liên quan, ghi:
- `Not targeted`

Không được tự động chấm cao.

### 4. Evidence-first

Mỗi kết luận quan trọng phải dựa trên:

- nội dung file
- command output
- state hiện tại của repo

Không được dùng kết luận kiểu:
- "có vẻ ổn"
- "chắc là đúng"
- "hoàn chỉnh"

nếu chưa có evidence.

### 5. Output Format

```markdown
# ABW Audit Report

## Scope
- <scope being audited>

## Files Changed / Files Reviewed
- <list>

## Findings
- <ordered by severity>

## Evidence
- <file-based evidence>

## Residual Risks
- <remaining issues or caveats>

## Rubric Scoring
- Command Surface Clarity: <score or Not targeted>
- Router Behavior Quality: <score or Not targeted>
- Knowledge / Grounding Integrity: <score or Not targeted>
- Session / Memory Continuity: <score or Not targeted>
- Delivery Lane Coherence: <score or Not targeted>
- Encoding / Rendering Integrity: <score or Not targeted>
- Installer / Runtime Robustness: <score or Not targeted>
- Scope Discipline: <score or Not targeted>
- Audit Integrity: <self-score is not allowed here; use N/A>

## Verdict
- FAIL
- PASS WITH CRITICAL GAPS
- PASS WITH MINOR GAPS
- PASS
```

### 6. Restrictions

- Không được sửa file trong `/abw-audit`
- Không được tự coi summary thành audit
- Không được nói PASS nếu artifact thật còn lỗi
- Phải phân biệt fact và inference
