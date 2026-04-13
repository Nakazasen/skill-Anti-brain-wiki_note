# SKILL: abw-eval

> **Purpose:** Chay full evaluation chain cho mot thay doi: audit -> meta-audit -> rubric scoring -> acceptance verdict.
> **Role:** Orchestration utility, duoc goi boi `/abw-eval`

---

## Instructions for AI Operator

Khi user goi `/abw-eval`, thuc hien quy trinh sau:

### 1. Xac dinh scope evaluation

Vi du:

- router patch
- docs cleanup
- command model update
- toan bo thay doi cua phien nay

Neu scope khong ro, neu gia dinh truoc khi bat dau.

### 2. Giai doan 1: Audit

Chay logic tuong duong `/abw-audit`:

- doc artifact that
- tao findings
- tao evidence
- neu residual risks

### 3. Giai doan 2: Meta-audit

Chay logic tuong duong `/abw-meta-audit` tren chinh bao cao audit vua tao:

- tim overclaim
- tim claim thieu bang chung
- chinh verdict neu can

### 4. Giai doan 3: Acceptance

Chay logic tuong duong `/abw-accept`:

- cham theo rubric
- tach blocker va non-blocker
- dua ra verdict cuoi

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

- `/abw-eval` la lenh orchestration, khong tu sua file
- Khong duoc bo qua meta-audit
- Khong duoc bo qua rubric scoring
- Khong duoc tuyen bo PASS neu chua qua du 3 giai doan
