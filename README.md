# Hybrid ABW (Anti-Brain-Wiki)

🌐 **Language**
> 🇻🇳 **Tiếng Việt** | 🇬🇧 [English](#english)

---

<details open>
<summary>🇻🇳 <b>Tiếng Việt</b> (đang xem)</summary>

---

## 🧠 ABW là gì

ABW là một execution boundary cho hệ AI.

- Chỉ cho phép output đi qua runner
- Yêu cầu proof (validation_proof)
- Ngăn AI “giả vờ đúng”

---

## ⚙️ Luồng thực thi


User → abw_entry → abw_runner → acceptance → proof → output → result


---

## 🔒 Trust Model

- 🟢 `runner_enforced` → execution thật
- 🟡 `runner_checked` → `checked_only`
- 🔴 `rejected`

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

## 🛡️ Hệ thống Health

- integrity → drift / encoding / mojibake
- cleanliness → clean_pass
- operational → validation_rate
- invariant check

---

## ⚠️ Failure Scenarios

<details>
<summary>Click để xem</summary>

- Fake output → reject
- Rewrite → reject
- Fake proof → reject
- Validation giả execution → downgrade
- Drift runtime → detect
- Mojibake → detect

</details>

---

## 💻 CLI


/abw-ask
/abw-health
/abw-repair


---

</details>

---

<details>
<summary>🇬🇧 <b>English</b></summary>

---

## 🧠 What ABW Is

ABW is an execution boundary for AI systems.

- Forces runner usage
- Requires proof-bound output
- Prevents fake correctness

---

## ⚙️ Execution Flow


User → abw_entry → abw_runner → acceptance → proof → output → result


---

## 🔒 Trust Model

- 🟢 runner_enforced → real execution
- 🟡 runner_checked → checked_only
- 🔴 rejected

---

## 🧾 Proof System


sha256(answer + finalization_block + runtime_id)


---

## 🏗️ Architecture

- Entry
- Runner
- Acceptance
- Output Shim
- Health

---

## 🛡️ Health System

- integrity → drift / encoding / mojibake
- cleanliness → clean_pass
- operational → validation_rate

---

## ⚠️ Failure Scenarios

<details>
<summary>Click to expand</summary>

- Fake output → rejected
- Rewrite → rejected
- Fake proof → rejected
- Validation pretending execution → downgraded
- Runtime drift → detected
- Mojibake → detected

</details>

---

## 💻 CLI


/abw-ask
/abw-health
/abw-repair


---

</details>

---

## 📌 Final Note

ABW does not make AI smarter.

It ensures:

> If the system is wrong → it cannot appear correct.
