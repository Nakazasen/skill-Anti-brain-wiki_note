🇻🇳 [Tiếng Việt](#tiếng-việt) | 🇬🇧 [English](#english)

---

## English

# Hybrid ABW (Anti-Brain-Wiki)

Version: 1.3.x (CLI-first, proof-bound)

---

## 1. What ABW Actually Is

ABW is an execution boundary for AI systems, ensuring that:

- Output is accepted only if it passes through the runner
- Output must carry provenance evidence (`validation_proof`)
- Output must satisfy the finalization contract

ABW does not make AI smarter. It makes AI unable to pretend it is correct.

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
- Real execution
- Valid proof

runner_checked → checked_only (LOW TRUST)
- Validation only
- Does NOT prove execution

rejected (NO TRUST)
- Did not go through the runner or proof is invalid

---

## 4. Proof System

validation_proof = sha256(answer + finalization_block + runtime_id)

- generated at the runner
- verified at the acceptance gate
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

- Proof is bound to content
- Output cannot be rewritten after the runner
- Finalization is valid
- Output can be audited later

---

## 7. What ABW DOES NOT Guarantee

- It does not guarantee logic is correct
- It does not replace testing
- It does not enforce at the host level
- It only operates at the CLI/runtime layer

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
- Do not add a rule before adding a signal
- The boundary must stay explicit

---

## 11. Failure Scenarios

F1 Raw output → rejected  
F2 Fake proof → rejected  
F3 Rewrite → rejected  
F4 Reuse proof → rejected  
F5 Validation pretending to be execution → downgraded  
F6 Missing finalization → blocked/downgraded  
F7 Shim bypass → depends on pipeline  
F8 Runtime drift → detected (health)  
F9 Encoding error → detected  
F10 Mojibake → detected  
F11 Invariant mismatch → flagged  
F12 CLI not called → protection cannot apply  

---

## Final Note

ABW does not make AI more correct.

ABW guarantees:

If it is wrong, it cannot look correct.

---

## Tiếng Việt

# Hybrid ABW (Anti-Brain-Wiki)

Phiên bản: 1.3.x (CLI-first, proof-bound)

---

## 1. ABW thực sự là gì

ABW là một execution boundary cho hệ AI, đảm bảo rằng:

- Output chỉ được chấp nhận nếu đi qua runner
- Output phải có bằng chứng nguồn gốc (`validation_proof`)
- Output phải tuân thủ finalization contract

ABW không làm AI thông minh hơn. ABW làm cho AI không thể giả vờ là nó đúng.

---

## 2. Luồng thực thi cốt lõi

User / CLI
↓
abw_entry.py
↓
abw_runner.py (execution / validation)
↓
enforce_output_acceptance()
↓
validation_proof (gắn bằng hash)
↓
abw_output.py (outer shim)
↓
render_with_visibility_lock()
↓
Final Output

---

## 3. Mô hình trust

runner_enforced (TRUST CAO)
- Có execution thật
- Proof hợp lệ

runner_checked → checked_only (TRUST THẤP)
- Chỉ validation
- KHÔNG chứng minh execution

rejected (KHÔNG CÓ TRUST)
- Không đi qua runner hoặc proof sai

---

## 4. Hệ proof

validation_proof = sha256(answer + finalization_block + runtime_id)

- được tạo tại runner
- được verify tại acceptance gate
- mismatch → reject

---

## 5. Kiến trúc hệ thống

Entry → abw_entry.py  
Runner → abw_runner.py  
Acceptance → enforce_output_acceptance()  
Output Shim → abw_output.py  
Health → abw_health.py  

---

## 6. ABW đảm bảo điều gì

(chỉ áp dụng cho output đã được chấp nhận)

- Proof gắn chặt với nội dung
- Không rewrite được sau runner
- Finalization hợp lệ
- Có thể audit lại về sau

---

## 7. ABW KHÔNG đảm bảo điều gì

- Không đảm bảo logic luôn đúng
- Không thay thế testing
- Không enforce ở host level
- Chỉ hoạt động ở lớp CLI/runtime

---

## 8. Hệ health

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

## 9. Cách dùng CLI

py scripts/abw_entry.py /abw-ask "task"

py scripts/abw_entry.py /abw-health

py scripts/abw_entry.py /abw-repair

---

## 10. Nguyên tắc thiết kế

- Trust = proof
- Validation ≠ execution
- Health = chỉ quan sát
- Chưa có signal thì không thêm rule
- Boundary phải luôn rõ ràng

---

## 11. Các kịch bản lỗi

F1 Raw output → rejected  
F2 Fake proof → rejected  
F3 Rewrite → rejected  
F4 Reuse proof → rejected  
F5 Validation giả execution → bị hạ mức  
F6 Thiếu finalization → blocked/downgraded  
F7 Bypass shim → phụ thuộc pipeline  
F8 Runtime drift → bị detect (health)  
F9 Lỗi encoding → bị detect  
F10 Mojibake → bị detect  
F11 Invariant mismatch → bị flag  
F12 Không gọi CLI → không thể bảo vệ  

---

## Ghi chú cuối

ABW không làm AI đúng hơn.

ABW đảm bảo:

Nếu AI sai, nó không thể trông giống như đúng.
