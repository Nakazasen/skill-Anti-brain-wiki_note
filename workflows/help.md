---
description: Hướng dẫn lệnh và sơ đồ hệ thống Hybrid ABW
---

# WORKFLOW: /help

Bạn là người hướng dẫn của Hybrid ABW. Nhiệm vụ của bạn là giúp người dùng định hướng thật nhanh. Bề mặt lệnh hiện được tổ chức thành 5 lane chức năng.

---

## Bắt đầu nhanh

Nếu bạn sắp bắt đầu làm việc, hãy đi từ một trong hai entrypoint này:

- **`/abw-ask`** : Entry mặc định để làm việc. Dùng khi bạn có task, câu hỏi, hoặc yêu cầu nhưng chưa biết nên đi lane nào.
- **`/abw-eval`** : Entry mặc định để nghiệm thu. Dùng khi đã có đầu ra và bạn muốn audit hoặc chốt accept trước khi coi là xong.

### Khi nào dùng lệnh nào?

- **Dùng `/abw-ask`** khi bạn có một việc cụ thể cần làm hoặc một câu hỏi cụ thể nhưng chưa nhớ chính xác lệnh nào.
- **Dùng `/abw-eval`** khi bạn muốn chạy vòng đánh giá cho một thay đổi, workflow, tài liệu, hoặc đầu ra của mô hình trước khi chấp nhận.
- **Dùng `/next`** khi bạn đang ở giữa dự án và cần gợi ý bước hợp lý tiếp theo dựa trên trạng thái hiện tại.
- **Dùng `/help`** khi bạn cần hiểu sơ đồ hệ thống, xem toàn bộ danh sách lệnh, hoặc học mental model 5 lane.

---

## Mô hình lệnh (5 lane)

### 1. Khám phá và tư duy

Dùng nhóm này khi cần khám phá ý tưởng hoặc hỏi trên tri thức hiện có.

- `/abw-ask` : Entry chính, tự định tuyến theo intent
- `/abw-query` : Tra cứu nhanh trên wiki
- `/abw-query-deep` : Suy luận sâu và tổng hợp nhiều lớp
- `/abw-bootstrap` : Tư duy cho bài toán greenfield
- `/brainstorm` : Chốt brief sản phẩm và phạm vi MVP

### 2. Dựng nền tri thức

Dùng nhóm này để duy trì nền tri thức của dự án và sức khỏe MCP.

- `/abw-init` : Khởi tạo cấu trúc ABW
- `/abw-setup` : Cấu hình NotebookLM MCP
- `/abw-status` : Kiểm tra MCP và hàng đợi
- `/abw-ingest` : Xử lý raw thành wiki
- `/abw-lint` : Audit sức khỏe wiki và manifest

### 3. Triển khai sản phẩm

Dùng nhóm này để biến tri thức thành phần mềm chạy được.

Luồng delivery chính:

- `/plan` : Lập kế hoạch thực thi tính năng
- `/design` : Thiết kế kỹ thuật và cơ sở dữ liệu
- `/visualize` : Dựng mockup UI/UX và đặc tả màn hình
- `/code` : Cài đặt tính năng
- `/run` : Chạy ứng dụng cục bộ
- `/debug` : Sửa lỗi có hệ thống
- `/test` : Chạy test và kiểm tra chất lượng
- `/deploy` : Triển khai lên môi trường đích

Workflow hỗ trợ trong delivery:

- `/refactor` : Dọn code an toàn sau khi đã hiểu rõ hành vi
- `/audit` : Rà soát sản phẩm, code, hoặc bảo mật trong vòng delivery

### 4. Phiên làm việc và ghi nhớ

Dùng nhóm này để quản lý phiên làm việc và khôi phục bối cảnh.

- `/save-brain` : Lưu tiến độ và chuẩn bị handover
- `/recap` : Khôi phục bối cảnh từ phiên trước
- `/next` : Gợi ý bước tiếp theo một cách thông minh

### 5. Đánh giá và nghiệm thu

Dùng nhóm này để đánh giá đầu ra, chất vấn lập luận yếu, và quyết định có nên chấp nhận thay đổi hay không.

- `/abw-audit` : Tự audit một thay đổi, workflow, tài liệu, hoặc đầu ra
- `/abw-meta-audit` : Audit lại chính báo cáo audit
- `/abw-accept` : Chạy cổng nghiệm thu cuối cùng
- `/abw-eval` : Chạy toàn bộ chuỗi evaluation từ đầu đến cuối

---

## Ví dụ phản hồi

### User: "Tôi nên bắt đầu từ đâu?"

```text
1. Chạy /abw-init để khởi tạo workspace.
2. Chạy /abw-setup để kết nối NotebookLM.
3. Nếu dự án còn mơ hồ, dùng /brainstorm để chốt brief.
4. Hoặc đơn giản dùng /abw-ask và nói: "Tôi muốn bắt đầu dự án X".
```

### User: "Làm sao để viết code cho tính năng này?"

```text
1. Đảm bảo đã có tri thức về tính năng đó trong wiki hoặc dùng /abw-ask để kiểm tra.
2. Dùng /plan để lên cấu trúc file và task.
3. Chạy /code để thực thi kế hoạch.
```
