# Hybrid ABW Command Model (6 Lanes)

Tài liệu này mô tả command surface chính thức của Hybrid ABW trong repo.

## Bắt đầu từ đâu?

- **`/abw-ask`**: entrypoint mặc định cho mọi task, câu hỏi, và yêu cầu chưa rõ lane.
- **`/abw-eval`**: entrypoint mặc định cho đánh giá và nghiệm thu.
- **`/abw-start`**: mở phiên làm việc có kiểm tra trạng thái và grounding path.
- **`/abw-update`**: cập nhật command surface ABW vào Gemini runtime local.

## 6 lane

### 1. Khám phá và tư duy

- `/abw-ask` : Router chính theo intent
- `/abw-query` : Tra cứu nhanh trên wiki
- `/abw-query-deep` : Phân tích sâu, tradeoff, RCA
- `/abw-bootstrap` : Tư duy cho bài toán greenfield
- `/brainstorm` : Chốt brief sản phẩm và MVP

### 2. Dựng nền tri thức

- `/abw-init` : Khởi tạo cấu trúc ABW
- `/abw-setup` : Cấu hình NotebookLM MCP
- `/abw-status` : Kiểm tra MCP và queue
- `/abw-ingest` : Xử lý raw thành wiki
- `/abw-pack` : Đóng gói tri thức thành package gọn
- `/abw-sync` : Dry-run hoặc sync package đã duyệt lên NotebookLM
- `/abw-lint` : Audit sức khỏe wiki, grounding, và manifest

### 3. Triển khai sản phẩm

Luồng delivery chính:

- `/plan` : Lập kế hoạch thực thi tính năng
- `/design` : Thiết kế kỹ thuật và cơ sở dữ liệu
- `/visualize` : Dựng mockup UI/UX và đặc tả màn hình
- `/code` : Cài đặt tính năng
- `/run` : Chạy ứng dụng cục bộ
- `/debug` : Sửa lỗi có hệ thống
- `/test` : Chạy test và kiểm tra chất lượng
- `/deploy` : Triển khai lên môi trường đích

Workflow hỗ trợ:

- `/refactor` : Dọn code an toàn sau khi đã hiểu rõ hành vi
- `/audit` : Rà soát sản phẩm, code, hoặc bảo mật trong vòng delivery

### 4. Phiên làm việc và ghi nhớ

- `/abw-start` : Mở phiên làm việc và kiểm tra trạng thái
- `/abw-learn` : Ghi một bài học hành vi tái sử dụng vào lessons learned
- `/save-brain` : Lưu tiến độ và chuẩn bị handover
- `/recap` : Khôi phục bối cảnh từ phiên trước
- `/next` : Gợi ý bước tiếp theo
- `/abw-wrap` : Chốt phiên và wrap lại thay đổi

### 5. Đánh giá và nghiệm thu (Gated)

- `/abw-review` : Review code, thay đổi, hoặc hiện trạng dự án (evaluation mode)
- `/abw-audit` : Tự audit workflow, tài liệu, thay đổi, hoặc đầu ra
- `/abw-meta-audit` : Audit lại chính báo cáo audit
- `/abw-rollback` : Quay về trạng thái an toàn sau thay đổi lỗi
- `/abw-accept` : Chốt pass/fail cuối cùng
- `/abw-eval` : Chạy toàn bộ chuỗi evaluation từ đầu đến cuối

### 6. Tiện ích và Cấu hình

- `/customize` : Cài đặt phong cách giao tiếp, persona, và mức độ tự quyết của AI
- `/help` : Bản đồ hệ thống và bảng tra cứu nhanh
- `/abw-update` : Cập nhật Command Surface ABW mới nhất vào local runtime

## First Command Cheat Sheet

| Muốn làm gì | Lệnh đầu tiên |
|---|---|
| Không biết nên bắt đầu từ đâu | `/abw-ask` |
| Muốn nghiệm thu đầu ra | `/abw-eval` |
| Muốn cài đặt cá nhân hóa AI | `/customize` |
| Muốn refactor khi đã rõ phạm vi | `/refactor` |
| Muốn mở phiên làm việc có kiểm tra trạng thái | `/abw-start` |
| Muốn agent nhớ một correction để dùng lại | `/abw-learn` |
| Muốn chốt phiên và handover | `/abw-wrap` |
| Muốn cập nhật command surface local | `/abw-update` |

## Naming Policy

- Lệnh thuộc public surface chính của hệ thống nên ưu tiên tiền tố `abw-`.
- Lệnh `abw-*` dùng cho router, grounding, session, evaluation, và những capability ABW-first.
- Tên lệnh nên ngắn, rõ động từ, và phản ánh đúng mục đích.
- Không tự ý rename lệnh đang ở public surface nếu chưa cập nhật installer, docs, và runtime registration cùng lúc.
- Workflow cũ chỉ giữ tên không `abw-` nếu đó là compatibility path có giá trị thực tế hoặc là verb rất tự nhiên như `/plan`, `/code`, `/test`.
- Nếu sau này thêm alias, alias chỉ là lớp phụ; source of truth vẫn là tên lệnh chính trong `workflows/` và installer.
