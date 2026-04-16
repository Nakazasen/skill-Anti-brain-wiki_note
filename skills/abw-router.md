# SKILL: abw-router — Smart Router Engine

**Mục tiêu:** Logic thực thi cho `/abw-ask` Smart Router. Nhận input user, phân loại intent, chạy safety guards, áp dụng Flash mode, và trả routing decision.

---

## Phase 1: Flash Mode Detection

```text
IF model hiện tại là Flash, mini, small, hoặc model yếu/nhỏ
→ flash_mode = true
   Áp dụng: scope giới hạn (1 file, 50 lines), eval sau 2 step, ưu tiên /next
ELSE
→ flash_mode = false
   Áp dụng: scope tiêu chuẩn (3 files, 200 lines), eval sau 3 step
```

---

## Phase 2: Context Scan

Kiểm tra nhanh trạng thái workspace:

```text
1. .brain/resume_state.json tồn tại?            → has_resume_state
2. .brain/resume_state.completed_steps có item?  → has_completed_steps
3. .brain/step_history.jsonl tồn tại?            → has_step_history
4. wiki/ có ≥1 file?                             → has_wiki
5. raw/ có ≥1 file?                              → has_raw
6. .brain/ directory tồn tại?                    → has_brain
```

Trạng thái:
- **Greenfield:** `has_wiki = false AND has_raw = false`
- **Knowledgeable:** `has_wiki = true OR has_raw = true`
- **Active Project:** `has_brain = true AND has_resume_state = true`
- **Cold Start:** `has_brain = false`

---

## Phase 3: Intent Classification

### 3.1: Pattern Matching Table

| Ưu tiên | Intent | Cue Patterns |
|---|---|---|
| **1** | `resume` | "tiếp tục", "đang dở", "resume", "continue", "project bị ngắt", "model yếu", "quota hết", "strong model quota is gone", "continue the interrupted project", "project is in the middle" |
| **2** | `next_step` | "tiếp theo làm gì", "next step", "giờ làm gì", "task tiếp", "bước kế", "làm gì tiếp", "next", "what should I do" |
| **3** | `execution` | "code", "viết code", "sửa lỗi", "debug", "test", "run", "deploy", "implement", "refactor", "viết", "tạo file", "fix", "build" |
| **4** | `evaluation` | "ok chưa", "xong chưa", "review", "kiểm tra", "nghiệm thu", "đánh giá", "eval", "xong rồi", "kiểm tra giùm", "check" |
| **5** | `knowledge` | "là gì", "giải thích", "tra cứu", "tìm trong wiki", "đã chốt gì", "so sánh", "tradeoff", "tại sao", "how does", "what is" |
| **6** | `ambiguous` | Không khớp pattern nào |

### 3.2: Disambiguation Rules

- **resume vs execution:** "tiếp tục code" → resume (ưu tiên 1 > 3)
- **next_step vs ambiguous:** "ừ thì làm đi" → ambiguous (không có "next"/"tiếp theo")
- **knowledge vs execution:** "giải thích rồi implement" → knowledge (ưu tiên 5 < 3, NHƯNG Mixed Intent Rule: thực hiện intent đầu tiên trong câu + ghi follow_up)
- **help vs ambiguous:** "tôi không hiểu gì cả" → route `/help` (ngoại lệ, bypass classification)

### 3.3: Mixed Intent Rule

```text
IF input chứa 2+ intent
→ Xử lý intent xuất hiện ĐẦU TIÊN trong câu
→ Ghi intent thứ 2 vào follow_up
→ NGOẠI LỆ: nếu 1 trong 2 intent là resume → resume LUÔN thắng
```

---

## Phase 4: Safety Guards

Chạy **tuần tự** 4 guard. Dừng tại guard đầu tiên trigger.

### Guard A: Resume-Before-Execute

```text
CONDITION:
  intent = execution
  AND (has_resume_state = false OR has_completed_steps = false)

ACTION:
  route_to = /abw-resume
  forced = true
  guard_triggered = "resume_before_execute"
  reason = "Chưa biết trạng thái project. Phải resume trước khi code."
```

### Guard B: Scope-Too-Large

```text
CONDITION:
  intent = execution
  AND (task ước lượng >3 files OR >200 lines
       OR flash_mode AND (>1 file OR >50 lines)
       OR cue chứa "toàn bộ", "viết lại", "migrate", "refactor all")

ACTION:
  route_to = /plan (nếu chưa có plan) hoặc /next (nếu có plan)
  forced = true
  guard_triggered = "scope_too_large"
  reason = "Task quá lớn cho 1 step. Chia nhỏ trước."
```

### Guard C: Missing-Evaluation

```text
CONDITION:
  intent = execution
  AND has_step_history = true
  AND step_history có ≥N step liên tiếp chưa acceptance_result
      (N = 2 nếu flash_mode, N = 3 nếu không)

ACTION:
  route_to = /abw-eval
  forced = true
  guard_triggered = "missing_evaluation"
  reason = "Đã N step chưa evaluation. Đánh giá trước khi tiếp."
```

### Guard D: Evidence-Before-Claim

```text
CONDITION:
  intent = knowledge
  AND user hỏi fact, decision, hoặc architecture conclusion
  AND has_wiki = false

ACTION:
  IF has_raw = true → route_to = /abw-ingest
  ELIF greenfield → route_to = /abw-bootstrap
  ELSE → route_to = /abw-query (sẽ ghi knowledge_gaps nếu không tìm thấy)
  forced = true
  guard_triggered = "evidence_before_claim"
  reason = "Không có evidence trong wiki. Nạp dữ liệu hoặc bootstrap trước."
```

---

## Phase 5: Flash Mode Rules

Chỉ áp dụng khi `flash_mode = true`:

| ID | Rule | Chi tiết |
|---|---|---|
| FM-1 | Default to /next | `ambiguous` → LUÔN route `/next`. KHÔNG route `/code` hay `/plan`. |
| FM-2 | Force resume check | `execution` → check resume_state. Step cuối failed hoặc không có → ép `/abw-resume`. |
| FM-3 | Hard scope limit | Max 1 file, max 50 lines. Vượt → ép `/next` để chia nhỏ. |
| FM-4 | No inline planning | Yêu cầu "lên kế hoạch" → route `/plan`. KHÔNG tự plan trong response. |
| FM-5 | Eval after 2 steps | ≥2 step chưa eval → ép `/abw-eval` (thay vì 3 ở mode thường). |

---

## Phase 6: Anti-Stupidity Rules

5 quy tắc cứng. **KHÔNG ĐƯỢC VI PHẠM:**

| ID | Rule | BLOCK | FORCE |
|---|---|---|---|
| AS-1 | Không code nếu chưa biết state | Mọi execution khi không có resume_state | `/abw-resume` |
| AS-2 | Không skip evaluation | ≥3 step (≥2 Flash) chưa eval | `/abw-eval` |
| AS-3 | Không suy luận thay evidence | Trả lời fact khi wiki trống | `/abw-query` / `/abw-ingest` / `/abw-bootstrap` |
| AS-4 | Không task lớn 1 bước | >3 files / >200 lines (Flash: >1/50) | `/next` / `/plan` |
| AS-5 | Không tự thêm step vào backlog | Ghi trực tiếp continuation_backlog | Đề xuất proposed_steps, chờ approve |

---

## Phase 7: Route Decision

### Decision Tree (tuần tự, dừng ở nhánh đầu tiên match)

```text
1. User hỏi cách dùng hệ thống?    → /help
2. intent = resume?                 → /abw-resume
3. intent = next_step?              → /next
4. intent = execution?              → Chạy Guard A → B → C → pass? → /code|/debug|/test|/run|/deploy
5. intent = evaluation?             → /abw-eval
6. intent = knowledge?              → Chạy Guard D → /abw-query | /abw-query-deep | /abw-bootstrap
7. intent = ambiguous + has_brain?  → /next (forced trong Flash)
8. intent = ambiguous + no brain?   → /abw-init hoặc /help
```

### Execution Sub-Router (cho intent = execution)

```text
IF cue chứa "debug", "sửa lỗi", "fix bug" → /debug
IF cue chứa "test", "kiểm thử"            → /test
IF cue chứa "run", "chạy", "start"         → /run
IF cue chứa "deploy", "triển khai"         → /deploy
IF cue chứa "refactor", "dọn dẹp"         → /refactor
ELSE                                        → /code
```

### Knowledge Sub-Router (cho intent = knowledge)

```text
IF câu hỏi đơn giản (definition, lookup)                → /abw-query
IF câu hỏi phức tạp (so sánh, tradeoff, RCA, mâu thuẫn) → /abw-query-deep
IF greenfield (wiki trống, raw trống)                     → /abw-bootstrap
```

---

## Phase 8: Output Format

### 📦 Output Format CỨNG (JSON)

Bạn không được phép chỉ in log rồi bắt User gõ lại lệnh. **Bạn phải tự động thực thi workflow đích mà Router vừa chọn (ví dụ `/next`, `/code`).**
Sau khi lệnh được chạy ngầm, bạn trả về toàn bộ payload bằng duy nhất một khối JSON:

```json
{
  "route": {
    "intent": "...",
    "route_to": "...",
    "forced": true,
    "reason": "..."
  },
  "execution": {
    "result": "..."
  }
}
```

### Flow đúng chuẩn Dispatcher (BẮT BUỘC)
- Bước 1: Quét Phase 2 - 7 => Ra được `route_to` (VD: `/code`).
- Bước 2: Tự động chạy Phase 1 - N của cái `/code` đó ngay trong đầu mình (viết code, thao tác file, ...).
- Bước 3: Đóng gói cả Route Decision và Kết quả Code vào `{ "result": "đã sinh ra file script.js..." }` ở JSON trên.

---

## Routing Priority Ladder (tóm tắt)

```text
Priority 1: /help           (user bối rối)
Priority 2: /abw-resume     (resume intent HOẶC Guard A trigger)
Priority 3: /next           (next_step intent HOẶC ambiguous trong Flash)
Priority 4: Guard B/C       (scope/eval blocks)
Priority 5: /code|/test|... (execution intent, all guards pass)
Priority 6: /abw-eval       (evaluation intent)
Priority 7: /abw-query*     (knowledge intent)
Priority 8: /abw-init|/help (ambiguous, no state)
```
