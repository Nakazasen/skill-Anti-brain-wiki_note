# SKILL: abw-router

**Mục tiêu:** Đánh giá câu hỏi của người dùng và trạng thái của workspace hiện tại để kích hoạt nhánh tư duy hoặc workflow phù hợp nhất (Ask/Think, Build Knowledge, Build Product, Session/Memory, Evaluation/Acceptance, Utility/Customization).

---

## Quy trình Định tuyến (Routing Logic)

### Bước 1: Quét bối cảnh (Context Scan)

Kiểm tra nhanh xem các thư mục raw/ và wiki/ có chứa dữ liệu dự án không.

- Trạng thái **Greenfield**: Cả raw/ và wiki/ đều trống.
- Trạng thái **Knowledgeable**: Có dữ liệu (ít nhất 1 file) trong raw/ hoặc wiki/.

### Bước 2.1: Quy tắc Phân biệt (Disambiguation Rules)

Để giảm thiểu sự mơ hồ giữa các intent tương đồng:

- **Query vs Brainstorm (Biết vs Khám phá)**: 
    - Query (/abw-query): Hỏi về thông tin "đã có" trong wiki (VD: "Tính năng X đã chốt là gì?"). 
    - Brainstorm (/brainstorm): Hỏi về ý tưởng "chưa có", "cần định nghĩa" hoặc "scoping" (VD: "MVP nên có những gì?").
- **Recap vs Next (Quá khứ vs Tương lai)**:
    - Recap (/recap): Nhìn lại "quá khứ" (VD: "Chúng ta đã làm gì?", "Tóm tắt bối cảnh").
    - Next (/next): Đề xuất bước tiếp theo từ trạng thái hiện tại (VD: "Tôi làm gì tiếp theo?", "Task tiếp theo là gì?").
- **Ask vs Help (Hành động vs Hỗ trợ)**:
    - Ask (/abw-ask): Có ý định thực thi task cụ thể nhưng chưa biết lệnh.
    - Help (/help): Không hiểu cách hệ thống vận hành hoặc danh sách các lệnh/lane.

### Bước 2.2: Từ khóa nhận diện (Action Keywords)

| Intent | Cue Patterns / Keywords |
|--------|-------------------------|
| knowledge | "là gì", "đã chốt", "tra cứu", "đọc wiki", "giải thích nội dung cũ" |
| product-discovery | "MVP", "scope", "brainstorm", "lên ý tưởng", "định nghĩa", "chốt tính năng" |
| delivery-planning | "lên kế hoạch", "plan", "phases", "chia task", "roadmap" |
| delivery-execution | "code", "viết", "sửa lỗi", "debug", "test", "run", "deploy" |
| session-recap | "tóm tắt", "recap", "đang làm gì", "nhắc lại", "context", "hôm qua làm gì" |
| session-next | "làm gì tiếp", "next step", "tiếp theo là gì", "task tiếp theo" |

---

## Routing Priority Ladder

### Continuation Kernel Routing Addendum

Route to `/abw-resume` instead of `/next` when the user is not merely asking for a suggestion, but is resuming an interrupted project with risk of state drift.

Use `/abw-resume` for cues such as:

- `resume this project`
- `continue the interrupted project`
- `project is in the middle`
- `what can the small model safely do next?`
- `strong model quota is gone; continue with a small model`

Difference:

- `/next` suggests a general next action from session memory.
- `/abw-resume` reconstructs continuation state, runs the machine gate when available, checks unsafe zones, locked decisions, knowledge gaps, rollback risk, and presents one governed next safe step.

Để đảm bảo AI đưa ra quyết định nhất quán khi có nhiều ý định chồng lấn:

1. **Confusion/System Query** -> `/help` (Nếu user không biết cách dùng hệ thống).
2. **Mixed Intent** -> Thực hiện command hành động đầu tiên + ghi log Follow-up.
3. **Past Context Recovery** -> `/recap` (Nếu câu hỏi nhắm vào lịch sử phiên làm việc).
4. **Next-Action Guidance** -> `/next` (Nếu user hỏi "giờ làm gì" dựa trên tiến độ).
5. **Knowledge Lookup** -> `/abw-query` (nhanh) hoặc `/abw-query-deep` (sâu).
6. **Undefined Product Scope** -> `/brainstorm` (lên ý tưởng, chốt brief).
7. **Greenfield (No Anchors)** -> `/abw-bootstrap` (khi chưa có bất kỳ dữ liệu raw/wiki nào).
8. **Delivery Execution** -> `/plan`, `/design`, `/code`, `/debug`, `/test` (theo luồng sản xuất).

---

### Bước 3: Preflight Check (Action Safety & Anti-Assumption)
Trước khi định tuyến, tự hỏi nhanh:
- **Chống giả định:** Câu hỏi có chứa giả định ẩn cần verify không? (VD: "Tại sao X hỏng?" -> Phải xác định "X có thực sự hỏng không?").
- **An toàn hệ thống:** Hành động sắp tới có rủi ro tạo side-effect phá hủy không (VD: xóa file, migration DB, overwrite mass refactor)? Nếu có, tự động đưa vào mode an toàn (đề xuất dry-run hoặc yêu cầu user xác nhận impact trước khi thực thi).

---

> [!IMPORTANT]
> **Lệnh Thực Thi Ngay (Dynamic Dispatch):**
>
> 1. In ra màn hình log: `[Router] Routing to /<cmd> for <intent>. [Optional] Follow-up: /<next_cmd>.`
> 2. ĐỌC và TUÂN THEO TOÀN BỘ quy tắc trong file workflow/skill đã chọn.
