# SKILL: abw-router — Smart Router Engine

Tích hợp vào quá trình **ABW Dispatcher + Executor**. Phân tích input user, phân loại intent, chạy safety guards, và thay vì dừng ở định tuyến, bạn **SẼ THỰC THI** ngay lệnh đã chọn và trả về kết hợp json (`route`, `execution`).

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

---

## Phase 3: Intent Classification
### 3.1: Pattern Matching Table
| Ưu tiên | Intent | Cue Patterns |
|---|---|---|
| **1** | `resume` | "tiếp tục", "đang dở", "resume", "continue", "project bị ngắt", "model yếu", "quota hết", "strong model quota is gone", "continue the interrupted project" |
| **2** | `next_step` | "tiếp theo làm gì", "next step", "giờ làm gì", "task tiếp", "bước kế" |
| **3** | `execution` | "code", "sửa lỗi", "debug", "test", "run", "deploy", "implement", "refactor", "viết", "fix" |
| **4** | `evaluation` | "ok chưa", "xong chưa", "review", "kiểm tra", "nghiệm thu", "đánh giá", "eval" |
| **5** | `knowledge` | "là gì", "giải thích", "tra cứu", "đã chốt gì", "so sánh", "tradeoff", "tại sao" |
| **6** | `ambiguous` | Không khớp pattern nào |

### 3.2: Disambiguation & Mixed Intents
- "tiếp tục code" → `resume` thắng (ưu tiên 1).
- Nếu 2 intent trở lên (không có resume) → xử lý intent xuất hiện ĐẦU TIÊN, intent sau vào `next_steps` hoặc `follow_up`.

---

## Phase 4: Safety Guards (Hard Blocks)
- **Guard A: Resume-Before-Execute** (Nếu `execution` mà không có `has_resume_state` / `has_completed_steps` → ép `/abw-resume`).
- **Guard B: Scope-Too-Large** (Nếu `execution` ước lượng vượt >3 files/200 lines, hoặc "viết lại", "refactor toàn bộ" → ép `/plan` hoặc `/next`).
- **Guard C: Missing-Evaluation** (Nếu đã có 2-3 step chưa pass acceptance → ép `/abw-eval`).
- **Guard D: Evidence-Before-Claim** (Nếu hỏi fact/decision mà không có `has_wiki` → ép `/abw-query` / `/abw-ingest` / `/abw-bootstrap`).

---

## Phase 5: Anti-Stupidity Rules (5 quy tắc cứng)
1. Không code nếu chưa biết state (ép `/abw-resume`).
2. Không skip evaluation.
3. Không suy luận thay evidence.
4. Không làm task lớn trong 1 bước.
5. Không tự động chèn step vào backlog.

---

## Phase 6: Execute và Trả payload JSON
Đừng chỉ in ra log. Hãy gọi trực tiếp workflow theo `route_to`, thực hiện các hành động của nó, và đúc kết chung lại ở ĐUÔI CÙNG bằng khối JSON:

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
*Lưu ý Anti-Fake: Bạn bắt buộc phải thực thi (run command, file view, vv.) trước khi cung cấp result. Không bịa.*
