# SKILL: abw-router

**Mục tiêu:** Đánh giá câu hỏi của người dùng và trạng thái của workspace hiện tại để kích hoạt 1 trong 3 nhánh tư duy (Tier 1, Tier 2, hoặc Tier 3).

---

## Quy trình Định tuyến (Routing Logic)

### Bước 1: Quét bối cảnh (Context Scan)

Kiểm tra nhanh xem các thư mục `raw/` và `wiki/` có chứa dữ liệu dự án không.

- Trạng thái **Greenfield**: Cả `raw/` và `wiki/` đều trống.
- Trạng thái **Knowledgeable**: Có dữ liệu (ít nhất 1 file) trong `raw/` hoặc `wiki/`.

### Bước 2: Đánh giá Câu hỏi (Intent Classification)

- **Simple**: Câu hỏi tra cứu sự thật, định nghĩa, thao tác rõ ràng.
- **Complex**: Câu hỏi phân tích, so sánh, thiết kế kiến trúc, tìm nguyên nhân (RCA), cần tổng hợp.
- **Ambiguous/Idea**: Ý tưởng mơ hồ, "Tôi muốn làm app...", "Bắt đầu từ đâu?", xin lời khuyên định hướng dự án mới.

### Bước 3: Khởi tạo Runtime (Nếu cần) & Ra quyết định (Handoff)

Dựa vào tổ hợp bối cảnh và loại câu hỏi, hãy chọn 1 nhánh duy nhất:

**Trường hợp 1: Greenfield + Ambiguous/Idea**

- Hệ thống chưa có dữ liệu và user mới có ý tưởng.
- 👉 **Hành động:**
  1. Đảm bảo thư mục `.brain/bootstrap/` tồn tại.
  2. Chuyển quyền điều khiển hoàn toàn cho `skills/abw-bootstrap.md`.

**Trường hợp 2: Greenfield + Simple/Complex**

- Chưa có dữ liệu dự án nhưng hỏi kiến thức chung.
- 👉 **Hành động:**
  1. Nếu `.brain/knowledge_gaps.json` chưa tồn tại, khởi tạo từ `templates/knowledge_gaps.example.json`.
  2. Trả lời dựa trên kiến thức base của bạn, nhưng bắt buộc phải log vào `.brain/knowledge_gaps.json` cảnh báo "Thiếu tri thức neo cho topic này" và khuyên user thêm tài liệu.

**Trường hợp 3: Knowledgeable + Simple**

- Đã có dữ liệu, user hỏi tra cứu nhanh.
- 👉 **Hành động:** Chuyển quyền điều khiển hoàn toàn cho `skills/query-wiki.md`.

**Trường hợp 4: Knowledgeable + Complex**

- Đã có dữ liệu, user yêu cầu phân tích, quyết định khó.
- 👉 **Hành động:** Chuyển quyền điều khiển hoàn toàn cho `skills/query-wiki-deliberative.md` để kích hoạt Test-Time Compute (TTC).

---

> **Lệnh Thực Thi Ngay (Dynamic Dispatch):**
>
> 1. In ra màn hình một dòng log ngắn: `[Router] Đang định tuyến sang <Tên_Path_Đã_Chọn>...`
> 2. ĐỌC và TUÂN THEO TOÀN BỘ quy tắc trong file skill đã chọn (chuyển control hoàn toàn, không quay lại router logic).
