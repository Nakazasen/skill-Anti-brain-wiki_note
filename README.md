# Hybrid ABW (Anti-Brain-Wiki)

🌐 **Language**
> 🇻🇳 **Tiếng Việt** | 🇬🇧 [English](#english)

---

# 🇻🇳 Tiếng Việt

## 🧠 ABW là gì

ABW là một **execution boundary cho hệ AI**.

> 🔒 Chỉ output có proof hợp lệ mới được chấp nhận

ABW không làm AI thông minh hơn.  
ABW đảm bảo:

> Nếu sai → không thể trông giống đúng

---

## ⚙️ Execution Flow (ASCII)

          ┌────────────┐
          │   User     │
          └─────┬──────┘
                │
                ▼
        ┌───────────────┐
        │  abw_entry.py │
        └─────┬─────────┘
              │
              ▼
        ┌───────────────┐
        │ abw_runner.py │
        │ (exec/validate)
        └─────┬─────────┘
              │
              ▼
   ┌──────────────────────────┐
   │ enforce_output_acceptance│
   └─────┬────────────────────┘
         │
         ▼
   ┌──────────────────────────┐
   │ validation_proof (hash)  │
   └─────┬────────────────────┘
         │
         ▼
   ┌──────────────────────────┐
   │   abw_output.py (shim)   │
   └─────┬────────────────────┘
         │
         ▼
   ┌──────────────────────────┐
   │ render_with_visibility   │
   └─────┬────────────────────┘
         │
         ▼
   ┌──────────────────────────┐
   │      FINAL OUTPUT        │
   └──────────────────────────┘

---

## 🔒 Trust State Machine

                  ┌────────────────────┐
                  │  runner_enforced   │
                  │  (execution thật)  │
                  └─────────┬──────────┘
                            │
                            │ validation path
                            ▼
                  ┌────────────────────┐
                  │  runner_checked    │
                  │  ↓                │
                  │  checked_only     │
                  │ (NO execution)    │
                  └─────────┬──────────┘
                            │
                            │ invalid / tampered
                            ▼
                  ┌────────────────────┐
                  │      rejected      │
                  │      (blocked)     │
                  └────────────────────┘

---

## 🔍 Acceptance Logic (REAL)

INPUT RESULT
     │
     ▼
Is dict?
 ├─ NO → rejected
 └─ YES
      │
      ▼
Has binding_status + proof?
 ├─ NO → rejected
 └─ YES
      │
      ▼
Recompute hash proof
 ├─ mismatch → rejected
 └─ match
      │
      ▼
Check echo-lock
 ├─ mismatch → rejected
 └─ OK
      │
      ▼
binding_status?
 ├─ runner_enforced → VERIFIED
 ├─ runner_checked → checked_only
 └─ other → rejected

---

## 🧾 Proof System

validation_proof = sha256(answer + finalization_block + runtime_id)

### Enforcement

- Sinh tại `abw_runner`
- Verify tại `enforce_output_acceptance()`
- Sai → reject ngay

### Đảm bảo

- Không thể sửa output sau runner
- Không thể fake runner output
- Không thể reuse proof

---

## 🏗️ Kiến trúc hệ

| Layer | Vai trò |
|------|--------|
| Entry (`abw_entry.py`) | Nhận command |
| Runner (`abw_runner.py`) | Thực thi / validate |
| Acceptance | Kiểm proof + contract |
| Output Shim (`abw_output.py`) | Chặn output không hợp lệ |
| Health (`abw_health.py`) | Quan sát hệ |

---

## 🛡️ Health System

### Integrity
- drift
- encoding
- mojibake

### Cleanliness
- clean_pass

### Operational
- validation_rate
- execution_rate
- fallback / policy split

### Invariant
validation_rate == fallback + policy

- Sai → flag invariant_violation
- Không crash hệ

### Anomaly
- DEGRADING
- RECOVERING
- WEAK_DEGRADING
- STABLE

> ⚠️ Chỉ là signal, không trigger action

---

## 💻 CLI Usage

- `py scripts/abw_entry.py /abw-ask "task"`
- `py scripts/abw_entry.py /abw-health`
- `py scripts/abw_entry.py /abw-repair`

---

## ⚠️ Failure Scenarios

<details>
<summary>Click để xem</summary>

### F1 Raw output
→ reject

### F2 Fake proof
→ reject

### F3 Rewrite sau runner
→ reject

### F4 Reuse proof
→ reject

### F5 Validation giả execution
→ downgrade → checked_only

### F6 Missing finalization
→ blocked / downgrade

### F7 Runtime drift
→ detect (health)

### F8 Encoding lỗi
→ detect

### F9 Mojibake
→ detect (không auto-fix)

### F10 Không gọi CLI
→ ABW không can thiệp được

</details>

---

## ❌ ABW KHÔNG đảm bảo

- Logic business đúng
- Không thay thế testing
- Không enforce ở IDE / host
- Không sửa lỗi logic

---

## 🎯 Design Principles

- Trust = proof, không phải format
- Validation ≠ execution
- Health = observer, không phải controller
- Không thêm rule nếu chưa thêm signal
- Boundary phải rõ

---

## 📌 Final Note

ABW không làm AI đúng hơn.

ABW đảm bảo:

> Nếu sai → không thể trông giống đúng

---

# English

## 🧠 What ABW Is

ABW is an **execution boundary for AI systems**.

> 🔒 Only outputs with valid proof are accepted

ABW does not make AI smarter.  
It ensures:

> If the system is wrong → it cannot appear correct

---

## ⚙️ Execution Flow (ASCII)

          ┌────────────┐
          │   User     │
          └─────┬──────┘
                │
                ▼
        ┌───────────────┐
        │  abw_entry.py │
        └─────┬─────────┘
              │
              ▼
        ┌───────────────┐
        │ abw_runner.py │
        │ (exec/validate)
        └─────┬─────────┘
              │
              ▼
   ┌──────────────────────────┐
   │ enforce_output_acceptance│
   └─────┬────────────────────┘
         │
         ▼
   ┌──────────────────────────┐
   │ validation_proof (hash)  │
   └─────┬────────────────────┘
         │
         ▼
   ┌──────────────────────────┐
   │   abw_output.py (shim)   │
   └─────┬────────────────────┘
         │
         ▼
   ┌──────────────────────────┐
   │ render_with_visibility   │
   └─────┬────────────────────┘
         │
         ▼
   ┌──────────────────────────┐
   │      FINAL OUTPUT        │
   └──────────────────────────┘

---

## 🔒 Trust State Machine

                  ┌────────────────────┐
                  │  runner_enforced   │
                  │  (real execution)  │
                  └─────────┬──────────┘
                            │
                            │ validation path
                            ▼
                  ┌────────────────────┐
                  │  runner_checked    │
                  │  ↓                │
                  │   checked_only    │
                  │  (NO execution)   │
                  └─────────┬──────────┘
                            │
                            │ invalid / tampered
                            ▼
                  ┌────────────────────┐
                  │      rejected      │
                  │      (blocked)     │
                  └────────────────────┘

---

## 🔍 Acceptance Logic (REAL)

INPUT RESULT
     │
     ▼
Is dict?
 ├─ NO → rejected
 └─ YES
      │
      ▼
Has binding_status + proof?
 ├─ NO → rejected
 └─ YES
      │
      ▼
Recompute hash proof
 ├─ mismatch → rejected
 └─ match
      │
      ▼
Check echo-lock
 ├─ mismatch → rejected
 └─ OK
      │
      ▼
binding_status?
 ├─ runner_enforced → VERIFIED
 ├─ runner_checked → checked_only
 └─ other → rejected

---

## 🧾 Proof System

validation_proof = sha256(answer + finalization_block + runtime_id)

### Enforcement

- Generated in `abw_runner`
- Verified in `enforce_output_acceptance()`
- Mismatch → reject

### Guarantees

- Output cannot be modified after runner
- Fake runner output cannot pass
- Old proof cannot be reused

---

## 🏗️ System Architecture

| Layer | Role |
|------|------|
| Entry (`abw_entry.py`) | Command dispatch |
| Runner (`abw_runner.py`) | Execute / validate |
| Acceptance | Verify proof + contract |
| Output Shim (`abw_output.py`) | Block invalid output |
| Health (`abw_health.py`) | Observe system state |

---

## 🛡️ Health System

### Integrity
- drift
- encoding
- mojibake

### Cleanliness
- clean_pass

### Operational
- validation_rate
- execution_rate
- fallback / policy split

### Invariant
validation_rate == fallback + policy

- Mismatch → flag invariant_violation
- Does not crash the system

### Anomaly
- DEGRADING
- RECOVERING
- WEAK_DEGRADING
- STABLE

> ⚠️ Signal only, never an action trigger

---

## 💻 CLI Usage

- `py scripts/abw_entry.py /abw-ask "task"`
- `py scripts/abw_entry.py /abw-health`
- `py scripts/abw_entry.py /abw-repair`

---

## ⚠️ Failure Scenarios

<details>
<summary>Click to expand</summary>

### F1 Raw output
→ rejected

### F2 Fake proof
→ rejected

### F3 Post-runner rewrite
→ rejected

### F4 Proof reuse
→ rejected

### F5 Validation pretending to be execution
→ downgraded → checked_only

### F6 Missing finalization
→ blocked / downgraded

### F7 Runtime drift
→ detected (health)

### F8 Encoding errors
→ detected

### F9 Mojibake
→ detected (no auto-fix)

### F10 No CLI execution
→ ABW cannot protect against this

</details>

---

## ❌ What ABW Does NOT Guarantee

- Business logic correctness
- Replacement for testing
- Host-level enforcement
- Automatic logic repair

---

## 🎯 Design Principles

- Trust = proof, not format
- Validation ≠ execution
- Health = observer, not controller
- No new rules without new signals
- Boundaries must stay explicit

---

## 📌 Final Note

ABW does not make AI smarter.

ABW guarantees:

> If the system is wrong → it cannot appear correct
