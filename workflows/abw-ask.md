---
description: ABW Dispatcher + Executor - Route and execute immediately
---

## BINDING STRATEGY

- `/abw-ask` MUST execute through the single AI entrypoint only.
- You MUST invoke `py scripts/ai_runner.py` and pass the task payload through stdin.
- The AI entrypoint owns routing, finalization, validation, and user-facing rendering.
- Do not import `abw_entry` directly.
- Do not call `execute_command` manually.
- Do not call `final_output` manually.
- Do not use `json.dumps` on runner or entry results.
- Do not return raw payloads.
- Do not rewrite, summarize, or restate anything after the AI entrypoint returns.
- The final output boundary MUST return the exact text from `py scripts/ai_runner.py`.
- Final output must be user-facing agent UI, not internal engine output.
- Final output MUST NOT expose `binding_status`, `validation_proof`, `runtime_id`, `nonce`, `evaluation`, `route`, `finalization_block`, commit hashes, evidence, or finalization details unless the user explicitly asks for debug output.

## MANDATORY CLI EXECUTION

You MUST execute:

```text
py scripts/ai_runner.py
```

You MUST send a structured JSON payload with:

```json
{
  "task": "<original user request>",
  "task_kind": "execution or validation",
  "candidate_answer": "<draft answer when validation is used>"
}
```

## VISIBILITY LOCK

Before returning:
- You MUST return only the rendered text from `py scripts/ai_runner.py`.
- In Antigravity/Gemini, rendered text must be clean markdown for humans.
- Internal trust/proof fields are for validation only and must remain hidden from normal UI.
- If any command prints JSON with `binding_status` or `validation_proof`, that command is invalid for normal UI and must be replaced with `py scripts/ai_runner.py`.

# WORKFLOW: /abw-ask — ABW Dispatcher + Executor

Bạn đang chạy trong chế độ: **ABW Dispatcher + Executor**
Bạn KHÔNG phải router thuần. Bạn PHẢI vừa route vừa thực thi.

**Nhiệm vụ:** Phân loại intent → kiểm tra safety → chọn route → **THỰC THI (EXECUTE)** workflow đích.

**Quy tắc vàng:** Router PHẢI tự động chọn command phù hợp và trả về 1 cục JSON tổng hợp cả Output Route (định hướng) lẫn Execution Result (kết quả chạy).

---

## Bước 1: Detect Flash Mode

```text
IF model hiện tại là Flash, mini, small, hoặc model yếu
→ flash_mode = true
ELSE
→ flash_mode = false
```

Khi `flash_mode = true`, áp dụng thêm Flash Mode Rules ở Bước 5.

---

## Bước 2: Intent Classification

Phân loại input user thành **đúng 1** trong 6 loại. Nếu khớp nhiều loại, chọn loại có **ưu tiên cao nhất** (số nhỏ nhất).

| Ưu tiên | Intent | Trigger Patterns |
|---|---|---|
| **1** | `resume` | "tiếp tục", "đang dở", "resume", "continue", "project bị ngắt", "model yếu hơn", "quota hết", "strong model quota is gone" |
| **2** | `next_step` | "tiếp theo làm gì", "next step", "giờ làm gì", "task tiếp", "bước kế", "làm gì tiếp" |
| **3** | `execution` | "code", "viết code", "sửa lỗi", "debug", "test", "run", "deploy", "implement", "refactor", "viết", "tạo file" |
| **4** | `evaluation` | "ok chưa", "xong chưa", "review", "kiểm tra", "nghiệm thu", "đánh giá", "eval", "xong rồi" |
| **5** | `knowledge` | "là gì", "giải thích", "tra cứu", "tìm trong wiki", "đã chốt gì", "so sánh", "tradeoff" |
| **6** | `ambiguous` | Không khớp pattern nào ở trên |

**Quy tắc xung đột:** "tiếp tục code" → khớp `resume` (1) VÀ `execution` (3) → chọn `resume` (1).

**Ngoại lệ:** Nếu user hỏi cách dùng hệ thống, danh sách lệnh, hoặc bối rối → route `/help` ngay, bỏ qua classification.

---

## Bước 3: Decision Tree

Đánh giá **tuần tự từ trên xuống**, dừng tại nhánh đầu tiên match.

### CHECK 0: System Help

```text
IF user bối rối, hỏi cách dùng hệ thống, hoặc hỏi danh sách lệnh
→ route: /help
```

### CHECK 1: Resume

```text
IF intent = resume
→ route: /abw-resume
→ follow_up: /abw-execute
```

### CHECK 2: Next Step

```text
IF intent = next_step
→ route: /next
```

### CHECK 3: Execution (có Safety Guards)

```text
IF intent = execution
│
├─ [GUARD A] .brain/resume_state.json KHÔNG tồn tại
│  HOẶC resume_state.completed_steps trống?
│  └─ YES → FORCED route: /abw-resume
│           reason: "Chưa biết trạng thái project. Phải resume trước khi code."
│           guard_triggered: "resume_before_execute"
│           forced: true
│
├─ [GUARD B] Task ước lượng >3 files HOẶC >200 lines?
│  HOẶC user nói "refactor toàn bộ", "viết lại", "migrate"?
│  └─ YES → FORCED route: /plan hoặc /next
│           reason: "Task quá lớn cho 1 step. Chia nhỏ trước."
│           guard_triggered: "scope_too_large"
│           forced: true
│
├─ [GUARD C] step_history.jsonl có ≥3 step liên tiếp
│  (hoặc ≥2 trong Flash mode) chưa có acceptance_result?
│  └─ YES → FORCED route: /abw-eval
│           reason: "Đã nhiều step chưa evaluation. Đánh giá trước."
│           guard_triggered: "missing_evaluation"
│           forced: true
│
└─ Tất cả guard pass
   → route: /code, /debug, /test, /run, /deploy (tùy cue)
   → forced: false
```

### CHECK 4: Evaluation

```text
IF intent = evaluation
→ route: /abw-eval
→ follow_up: /abw-accept
```

### CHECK 5: Knowledge

```text
IF intent = knowledge
│
├─ wiki/ có dữ liệu?
│  ├─ Câu hỏi đơn giản (tra cứu, definition) → route: /abw-query
│  └─ Câu hỏi phức tạp (so sánh, tradeoff, RCA) → route: /abw-query-deep
│
└─ wiki/ trống VÀ raw/ trống?
   → route: /abw-bootstrap
```

### CHECK 6: Ambiguous

```text
IF intent = ambiguous
│
├─ Có .brain/ state?
│  └─ route: /next (forced trong Flash mode)
│     reason: "Không rõ ý định. Xem bước tiếp theo."
│
└─ Không có .brain/ state?
   └─ route: /abw-init hoặc /help
      reason: "Chưa có workspace. Khởi tạo trước."
```

---

## Bước 4: Safety Guards (chi tiết)

### Guard A: Resume-Before-Execute

```text
CONDITION: intent = execution
       AND (.brain/resume_state.json KHÔNG tồn tại
            HOẶC resume_state.completed_steps trống)
ACTION:  BLOCK → FORCED /abw-resume
```

### Guard B: Scope-Too-Large

```text
CONDITION: intent = execution
       AND (task chạm >3 files HOẶC >200 lines
            HOẶC cue "refactor toàn bộ", "viết lại", "migrate")
ACTION:  BLOCK → FORCED /plan hoặc /next
```

### Guard C: Missing-Evaluation

```text
CONDITION: intent = execution
       AND step_history có ≥3 step (≥2 Flash) chưa acceptance_result
ACTION:  BLOCK → FORCED /abw-eval
```

### Guard D: Evidence-Before-Claim

```text
CONDITION: user hỏi fact/decision/architecture
       AND wiki/ không có evidence liên quan
ACTION:  BLOCK trả lời trực tiếp
         → /abw-query, /abw-ingest, hoặc /abw-bootstrap
```

---

## Bước 5: Flash Mode Rules

Khi `flash_mode = true`, áp dụng thêm:

| Rule | Mô tả |
|---|---|
| **FM-1** | `ambiguous` → LUÔN route `/next`. Không bao giờ `/code` hoặc `/plan` trực tiếp. |
| **FM-2** | `execution` → LUÔN check resume_state trước. Step cuối failed → ép `/abw-resume`. |
| **FM-3** | Max 1 file, max 50 lines per step. Vượt → ép `/next` chia nhỏ. |
| **FM-4** | User yêu cầu "lên kế hoạch" → route `/plan`. KHÔNG tự plan inline. |
| **FM-5** | ≥2 step chưa eval → ép `/abw-eval` (thay vì ≥3 ở mode thường). |

---

## Bước 6: Anti-Stupidity Rules (5 quy tắc cứng)

Không được vi phạm dưới bất kỳ hình thức nào:

| Rule | Điều kiện | Hành động |
|---|---|---|
| **AS-1** | Không có resume_state hoặc trống | BLOCK mọi execution → `/abw-resume` |
| **AS-2** | ≥3 step (≥2 Flash) chưa eval | BLOCK execution tiếp → `/abw-eval` |
| **AS-3** | Hỏi fact nhưng wiki không có data | BLOCK trả lời → `/abw-query` hoặc `/abw-ingest` |
| **AS-4** | Task >3 files hoặc >200 lines (>50 Flash) | BLOCK → `/next` hoặc `/plan` |
| **AS-5** | Model muốn thêm step vào backlog | BLOCK ghi trực tiếp → đề xuất proposed_steps, chờ approve |

---

## Bước 7: Output

### 📦 Output Format (BẮT BUỘC)

Không được in JSON payload nội bộ trong giao diện Antigravity/Gemini.
Không được tự tạo output từ `route`, `execution`, `binding_status`, hoặc `validation_proof`.

Luôn trả đúng text đã render từ:

```text
py scripts/ai_runner.py
```

Output hợp lệ là markdown ngắn, ví dụ:

```text
### ABW Dashboard

### Answer
- Raw files: 1
- Draft files: 0
- Wiki files: 9
- Coverage: 1.0

### Next Actions
- ingest raw/<file>
```

### Hành động sau khi xác định được Route

**BẮT BUỘC** để `scripts/ai_runner.py` thực thi toàn bộ logic và render.
Nếu cần debug raw payload, user phải yêu cầu debug rõ ràng; normal UI không được dump JSON.

---

## Ví dụ minh họa

### 1. Resume rõ ràng

```text
INPUT:  "tiếp tục dự án hôm qua"
→ [Router] intent=resume → /abw-resume | reason: User nói "tiếp tục" | forced: false
→ Thực thi /abw-resume workflow
```

### 2. Code khi chưa resume (bị chặn)

```text
INPUT:  "viết API endpoint cho orders"
STATE:  resume_state.json KHÔNG tồn tại
→ [Router] ⚠️ GUARD resume_before_execute → FORCED /abw-resume | reason: Chưa biết trạng thái project
→ Thực thi /abw-resume workflow
```

### 3. Task quá lớn (bị chặn)

```text
INPUT:  "refactor toàn bộ module authentication"
→ [Router] ⚠️ GUARD scope_too_large → FORCED /plan | reason: Task quá lớn, chia nhỏ trước
→ Thực thi /plan workflow
```

### 4. Hỏi "xong chưa" → evaluation

```text
INPUT:  "xong rồi, kiểm tra giùm"
→ [Router] intent=evaluation → /abw-eval | reason: User xin đánh giá | forced: false
→ Thực thi /abw-eval workflow
```

### 5. Flash mode, input mơ hồ

```text
INPUT:  "ừ thì làm đi"
STATE:  flash_mode = true, có .brain/
→ [Router] intent=ambiguous → /next | reason: Flash mode, intent không rõ | forced: true
→ Thực thi /next workflow
```

### 6. Flash mode, thiếu evaluation

```text
INPUT:  "code thêm tính năng export"
STATE:  flash_mode = true, 2 step chưa eval
→ [Router] ⚠️ GUARD missing_evaluation → FORCED /abw-eval | reason: Flash mode, 2 step chưa eval
→ Thực thi /abw-eval workflow
```
