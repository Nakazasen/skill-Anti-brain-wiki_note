# Hybrid ABW (Anti-Brain-Wiki)

🌐 **Language**
> 🇻🇳 **Tiếng Việt** | 🇬🇧 [English](#english)

---

# 🇻🇳 Tiếng Việt

## 🧠 ABW là gì

ABW là execution boundary cho hệ AI.

> 🔒 Chỉ output có proof hợp lệ mới được chấp nhận

---

## ⚙️ Luồng thực thi

User → Entry → Runner → Acceptance → Proof → Output

---

## 🔒 Trust Model

| State | Ý nghĩa |
|------|--------|
| runner_enforced | execution thật |
| runner_checked → checked_only | chỉ validation |
| rejected | bị chặn |

---

## 🧾 Proof System

sha256(answer + finalization_block + runtime_id)

---

## 🏗️ Kiến trúc

- Entry
- Runner
- Acceptance
- Output Shim
- Health

---

## 🛡️ Health

- drift
- encoding
- mojibake
- clean_pass
- validation_rate

---

## ⚠️ Failure Scenarios

<details>
<summary>Click</summary>

- Fake output → reject
- Rewrite → reject
- Fake proof → reject
- Validation giả execution → downgrade

</details>

---

# 🇬🇧 English

## 🧠 What ABW Is

ABW is an execution boundary for AI systems.

> Only proof-bound output is accepted

---

## ⚙️ Flow

User → Entry → Runner → Acceptance → Proof → Output

---

## 🔒 Trust Model

| State | Meaning |
|------|--------|
| runner_enforced | real execution |
| runner_checked → checked_only | validation only |
| rejected | blocked |

---

## 🧾 Proof

sha256(answer + finalization_block + runtime_id)

---

DONE WHEN:

- README updated
- commit created
- pushed to main
- preview printed
