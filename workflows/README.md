# Hybrid ABW: Mô hình lệnh thống nhất

Hybrid ABW cung cấp một mental model thống nhất cho người phát triển, đi từ giai đoạn khám phá ban đầu, dựng nền tri thức, triển khai sản phẩm, quản lý phiên làm việc, cho tới đánh giá và nghiệm thu. Hệ thống hiện được tổ chức thành **5 lane chức năng**.

## Bắt đầu từ đâu?

- **`/abw-ask`**: Entry mặc định để làm việc. Dùng khi bạn có task hoặc câu hỏi và muốn router chọn lane phù hợp.
- **`/abw-eval`**: Entry mặc định để nghiệm thu. Dùng khi đã có đầu ra và muốn đánh giá trước khi chấp nhận.
- **`/abw-start`**: Entry mở phiên khi muốn kiểm tra trạng thái hệ thống trước khi làm.
- **`/abw-wrap`**: Entry đóng phiên khi muốn chốt tiến độ và chuẩn bị handover.
- **`/next`**: Gợi ý bước hợp lý tiếp theo dựa trên trạng thái hiện tại.
- **`/help`**: Bản đồ hệ thống và danh sách lệnh.

---

## 5 lane của hệ thống

### 1. Khám phá và tư duy
Tập trung vào việc hình thành ý tưởng, làm rõ bài toán, hoặc hỏi trên tri thức hiện có.
- **`/abw-ask`** : **Entry chính của toàn hệ thống (Master Router)**.
- `/abw-query` : Tier 1, tra cứu nhanh trên tri thức đã có.
- `/abw-query-deep` : Tier 2, suy luận sâu và phân tích nhiều lớp.
- `/abw-bootstrap` : Tier 3, tư duy giả thuyết cho bài toán greenfield.
- `/brainstorm` : Khám phá sản phẩm và chốt phạm vi vấn đề.

### 2. Dựng nền tri thức
Tập trung vào việc duy trì nền dữ liệu đáng tin của dự án.
- `/abw-init` : Khởi tạo workspace và cấu trúc ABW.
- `/abw-setup` : Cấu hình MCP.
- `/abw-status` : Kiểm tra kết nối và trạng thái hệ thống.
- `/abw-ingest` : Nạp tri thức vào wiki.
- `/abw-lint` : Audit chất lượng nền tri thức.

### 3. Triển khai sản phẩm
Tập trung vào việc biến tri thức thành phần mềm chạy được.

Luồng delivery chính:
- `/plan` : Lập kế hoạch kỹ thuật và task.
- `/design` : Thiết kế kiến trúc và cơ sở dữ liệu.
- `/visualize` : Dựng mockup UI/UX và đặc tả màn hình.
- `/code` : Cài đặt tính năng.
- `/run` : Chạy ứng dụng cục bộ.
- `/debug` : Sửa lỗi.
- `/test` : Kiểm tra chất lượng.
- `/deploy` : Triển khai lên môi trường đích.

Workflow hỗ trợ trong delivery:
- `/refactor` : Dọn code an toàn sau khi đã hiểu rõ hành vi.
- `/audit` : Rà soát sản phẩm, code, hoặc bảo mật trong vòng delivery.

### 4. Phiên làm việc và ghi nhớ
Tập trung vào việc quản lý phiên làm việc và khôi phục bối cảnh.
- `/abw-start` : Mở phiên và kiểm tra trạng thái.
- `/save-brain` : Lưu phiên và chuẩn bị handover.
- `/recap` : Khôi phục bối cảnh.
- `/next` : Gợi ý bước tiếp theo.
- `/abw-wrap` : Chốt phiên và chuẩn bị quay lại.

### 5. Đánh giá và nghiệm thu
Tập trung vào việc đánh giá đầu ra, kiểm tra chất lượng lập luận, và quyết định có nên chấp nhận thay đổi hay không.
- `/abw-review` : Review code, thay đổi, hoặc hiện trạng dự án.
- `/abw-audit` : Tự audit một thay đổi hoặc artifact.
- `/abw-meta-audit` : Audit lại chính báo cáo audit.
- `/abw-rollback` : Quay về trạng thái an toàn.
- `/abw-accept` : Chạy cổng nghiệm thu cuối cùng.
- `/abw-eval` : Chạy toàn bộ chuỗi evaluation.

---

## Luồng khuyến nghị

1. **Khám phá và tư duy**: Bắt đầu với `/brainstorm` hoặc `/abw-ask`.
2. **Dựng nền tri thức**: Chạy `/abw-init` và `/abw-ingest` để xây wiki cho dự án.
3. **Triển khai**: Chuyển sang `/plan`, `/design`, `/visualize`, rồi `/code` khi nền tri thức đã đủ rõ.
4. **Handover**: Dùng `/save-brain` trước khi kết thúc phiên.
5. **Nghiệm thu**: Dùng `/abw-audit`, `/abw-accept`, hoặc `/abw-eval` trước khi coi công việc là hoàn tất.

---

## Định tuyến thông minh

Lệnh **`/abw-ask`** là entry mặc định cho hầu hết tương tác làm việc. Nó đánh giá intent của bạn và trạng thái hiện tại của dự án để chuyển tiếp sang workflow hoặc skill phù hợp nhất.

Ví dụ handoff:
- "Auth flow hiện tại là gì?" -> `[Router] Routing to /abw-query for knowledge-simple.`
- "Tôi muốn làm một marketplace" -> `[Router] Routing to /brainstorm for product-discovery.`
- "Giúp tôi lên kế hoạch API" -> `[Router] Routing to /plan for delivery-planning.`

Evaluation Layer tách riêng khỏi `/abw-ask`. Dùng nó sau khi đã có đầu ra:
- `/abw-audit` để tự rà soát
- `/abw-meta-audit` để chất vấn báo cáo audit
- `/abw-accept` để quyết định pass/fail
- `/abw-eval` để chạy toàn bộ chuỗi nghiệm thu

---

## Thiết kế ưu tiên trung thực

Hybrid ABW ưu tiên **trung thực** hơn là trả lời cho có. Nếu NotebookLM MCP bị lỗi hoặc grounding queue đang tắc, hệ thống phải báo rõ trạng thái như `draft` hoặc `pending_grounding`, thay vì giả vờ đã grounded.
