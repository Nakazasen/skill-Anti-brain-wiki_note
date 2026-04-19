# Hybrid ABW (Anti-Brain-Wiki)

Version: 1.3.x (CLI-first, proof-bound)

---

## 1. What ABW Actually Is

ABW là một execution boundary cho hệ AI, đảm bảo rằng:

- Output chỉ được chấp nhận nếu đi qua runner
- Output phải có bằng chứng nguồn gốc (validation_proof)
- Output phải tuân thủ finalization contract

ABW không làm AI thông minh hơn, mà làm AI không thể giả vờ đúng.

---

## 2. Core Execution Flow

User / CLI
↓
abw_entry.py
↓
abw_runner.py (execution / validation)
↓
enforce_output_acceptance()
↓
validation_proof (hash-bound)
↓
abw_output.py (outer shim)
↓
render_with_visibility_lock()
↓
Final Output

---

## 3. Trust Model

runner_enforced (HIGH TRUST)
- Execution thật
- Proof hợp lệ

runner_checked → checked_only (LOW TRUST)
- Chỉ validation
- KHÔNG chứng minh execution

rejected (NO TRUST)
- Không qua runner hoặc proof sai

---

## 4. Proof System

validation_proof = sha256(answer + finalization_block + runtime_id)

- tạo tại runner
- verify tại acceptance gate
- mismatch → reject

---

## 5. System Architecture

Entry → abw_entry.py  
Runner → abw_runner.py  
Acceptance → enforce_output_acceptance()  
Output Shim → abw_output.py  
Health → abw_health.py  

---

## 6. What ABW Guarantees

(only for accepted output)

- Proof gắn với nội dung
- Không rewrite được sau runner
- Có finalization hợp lệ
- Có thể audit lại

---

## 7. What ABW DOES NOT Guarantee

- Không đảm bảo logic đúng
- Không thay thế testing
- Không enforce ở host level
- Chỉ hoạt động ở CLI/runtime layer

---

## 8. Health System

Integrity:
- drift
- encoding
- mojibake

Cleanliness:
- clean_pass

Operational:
- validation_rate
- execution_rate
- fallback vs policy

Invariant:
- validation_rate == fallback + policy

Anomaly:
- DEGRADING
- RECOVERING
- WEAK_DEGRADING
- STABLE

---

## 9. CLI Usage

py scripts/abw_entry.py /abw-ask "task"

py scripts/abw_entry.py /abw-health

py scripts/abw_entry.py /abw-repair

---

## 10. Design Principles

- Trust = proof
- Validation ≠ execution
- Health = observer only
- Không thêm rule nếu chưa thêm signal
- Boundary phải rõ

---

## 11. Failure Scenarios

F1 Raw output → rejected  
F2 Fake proof → rejected  
F3 Rewrite → rejected  
F4 Reuse proof → rejected  
F5 Validation giả execution → downgraded  
F6 Missing finalization → blocked/downgraded  
F7 Shim bypass → depends on pipeline  
F8 Runtime drift → detected (health)  
F9 Encoding lỗi → detected  
F10 Mojibake → detected  
F11 Invariant mismatch → flagged  
F12 Không gọi CLI → không bảo vệ được  

---

## Final Note

ABW không làm AI đúng hơn.

ABW đảm bảo:

Nếu sai → không thể trông giống đúng.
