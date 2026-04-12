# SKILL: abw-bootstrap

**Triết lý cốt lõi:**
Khi chưa có tri thức đầu vào, KHÔNG ĐƯỢC compile knowledge. Chỉ được phép compile **reasoning state** (trạng thái tư duy). Không giả vờ biết sự thật; hãy quản lý sự không chắc chắn (uncertainty).

## Nguyên tắc vận hành (Strict Policy)

1. **Không nói như thể đã biết sự thật:** Mọi tuyên bố không có bằng chứng rõ ràng phải được gắn nhãn `[Assumption]` hoặc `[Hypothesis]`.
2. **Không ghi trực tiếp vào `wiki/`:** Tri thức chưa được verify KHÔNG ĐƯỢC lưu vào `wiki/`. Toàn bộ tư duy phải nằm trong thư mục `.brain/bootstrap/`.
3. **Định hướng hành động (Action-oriented):** Kết quả cuối cùng luôn phải là "Bằng cách nào để kiểm chứng điều này rẻ nhất?".

## Quy trình Bootstrap (4 Passes)

### Pass 1: Intent & Decomposition (Phân rã Ý tưởng)

- Người dùng muốn làm gì? Ai là user? Use case chính là gì?
- Trích xuất các ranh giới (Constraints) và mục tiêu thành công (Success Metrics) nếu có.
- Nếu thiếu thông tin trầm trọng, liệt kê các câu hỏi cần hỏi user thay vì tự bịa.

### Pass 2: Hypotheses Generation (Lập Giả thuyết Mở)

- Đề xuất 2-3 hướng tiếp cận (Architecture, UX flow, Tech stack, v.v.).
- Phân tích Pros/Cons/Open Risks của từng hướng.
- Ghi nhận vào `.brain/bootstrap/hypotheses.json`.

### Pass 3: Assumptions Extraction (Bóc tách Giả định)

- Liệt kê mọi niềm tin/giả định ẩn dưới các hướng tiếp cận trên.
- Đánh giá độ tự tin (Confidence: High/Medium/Low).
- Ghi nhận vào `.brain/bootstrap/assumptions.json`.

### Pass 4: Validation Plan (Kế hoạch Kiểm chứng)

- Từ các Giả định và Rủi ro ở trên, rút ra Next Minimal Steps (Những bước nhỏ nhất/rẻ nhất để kiểm chứng).
- Ghi nhận vào `.brain/bootstrap/validation_backlog.json`.
- (Tùy chọn) Nếu đã có quyết định tạm thời, ghi vào `.brain/bootstrap/decision_log.jsonl`.

## Output Format

Luôn trả lời user bằng một báo cáo ngắn gọn bao gồm:

1. **Understanding & Gaps:** Hiểu ý tưởng thế nào và đang thiếu mảng thông tin nào.
2. **Top Hypotheses:** Các hướng đi khả dĩ nhất.
3. **Critical Assumptions:** Những giả định rủi ro nhất đang được ngầm hiểu.
4. **Next Validation Step:** BƯỚC TIẾP THEO RẺ NHẤT.

> **Hành động:** Khởi tạo cấu trúc `.brain/bootstrap/` và sinh ra các file artifacts.
