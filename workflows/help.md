---
description: Hướng dẫn lệnh và sơ đồ hệ thống Hybrid ABW
---

# WORKFLOW: /help

Bạn là người hướng dẫn của Hybrid ABW. Nhiệm vụ của bạn là giúp người dùng chọn đúng lệnh nhanh nhất, với ưu tiên rõ ràng cho khởi tạo workspace, routing, grounding, dự án tiếp diễn (continuation), và nghiệm thu.

---

## Bắt Đầu Đúng Chỗ

- **`/abw-init`**: Dựng hoặc sửa nền tảng ABW trong workspace (chạy đầu tiên sau khi clone).
- **`/abw-setup`**: Cấu hình grounding và kết nối NotebookLM MCP.
- **`/abw-ask`**: Entrypoint mặc định cho mọi task hoặc câu hỏi chưa rõ lane.
- **`/abw-resume`**: Khôi phục dự án đang dở và chọn một bước an toàn tiếp theo (Continuation Kernel).
- **`/abw-eval`**: Chạy toàn bộ chain đánh giá trước khi bàn giao (Evaluation Kernel).
- **`/abw-learn`**: Ghi một correction của user thành bài học hành vi tái sử dụng.

---

## Muốn làm gì? (Cheat Sheet)

| Mục tiêu | Lệnh gợi ý |
|---|---|
| Khởi tạo workspace mới / Sửa cấu trúc | `/abw-init` |
| Bắt đầu một nhiệm vụ chưa rõ lane | `/abw-ask` |
| Tra cứu nhanh dữ liệu trong wiki | `/abw-query` |
| Phân tích sâu, RCA, so sánh tradeoff | `/abw-query-deep` |
| Tư duy cho ý tưởng mới (greenfield) | `/abw-bootstrap` |
| Chốt brief sản phẩm và scope MVP | `/brainstorm` |
| Cấu hình NotebookLM MCP / Grounding | `/abw-setup` |
| Xử lý tài liệu nguồn (raw) thành wiki | `/abw-ingest` |
| Kiểm tra trạng thái MCP / Grounding queue | `/abw-status` |
| Đóng gói tri thức cho NotebookLM | `/abw-pack` |
| Đồng bộ dữ liệu lên NotebookLM | `/abw-sync` |
| Kiểm tra sức khỏe wiki và manifest | `/abw-lint` |
| **Tiếp tục dự án sau khi ngắt quãng** | `/abw-resume` |
| Thực thi một bước đã được phê duyệt | `/abw-execute` |
| Lập kế hoạch thực thi tính năng | `/plan` |
| Thiết kế kỹ thuật / DB / API | `/design` |
| Mockup UI/UX / Layout | `/visualize` |
| Bắt tay vào viết code | `/code` |
| Chạy ứng dụng cục bộ | `/run` |
| Tìm và sửa bug | `/debug` |
| Kiểm tra bằng unit/integration test | `/test` |
| Triển khai lên production / staging | `/deploy` |
| Tối ưu / Dọn dẹp code an toàn | `/refactor` |
| Đánh giá chất lượng / Bảo mật (delivery loop) | `/audit` |
| Review hiện trạng dự án (evaluation mode) | `/abw-review` |
| Tự audit artifact theo rubric ABW | `/abw-audit` |
| Audit lại báo cáo audit | `/abw-meta-audit` |
| Quay lại trạng thái an toàn trước đó | `/abw-rollback` |
| Chốt nghiệm thu cuối cùng (Pass/Fail) | `/abw-accept` |
| Lưu tiến độ và handover nhanh | `/save-brain` |
| Khôi phục bối cảnh phiên làm việc | `/recap` |
| Gợi ý bước hành động tiếp theo | `/next` |
| Đóng phiên làm việc (wrap-up) | `/abw-wrap` |
| Cài đặt persona / Autonomy của AI | `/customize` |
| Cập nhật Command Surface local | `/abw-update` |

---

## Hệ Thống 6 Lane

### 1. Khám phá và Tư duy (Ask & Think)
- `/abw-ask`: Router thông minh theo intent.
- `/abw-query`: Tra cứu wiki nhanh (1-pass).
- `/abw-query-deep`: Suy luận đa bước, TTC engine.
- `/abw-bootstrap`: Xử lý bài toán chưa có dữ liệu nền.
- `/brainstorm`: Hội thảo ý tưởng và chốt scope.

### 2. Dựng nền tri thức (Build Knowledge)
- `/abw-init`: Khởi tạo framework ABW.
- `/abw-setup`: Nối tầng grounding.
- `/abw-status`: Health check hệ thống grounding.
- `/abw-ingest`: Nạp tri thức thô vào hệ thống.
- `/abw-pack` & `/abw-sync`: Quản lý gói tri thức NotebookLM.
- `/abw-lint`: Đảm bảo tính nhất quán của dữ liệu.

### 3. Triển khai sản phẩm (Build Product)
- `/plan` → `/design` → `/visualize`: Chuẩn bị.
- `/code` → `/run` → `/debug` → `/test`: Thực thi.
- `/deploy`: Phát hành.
- `/refactor` & `/audit`: Duy trì và kiểm soát chất lượng.

### 4. Phiên làm việc và Ghi nhớ (Session & Memory)
- `/abw-start`: Mở phiên làm việc chính thức.
- **`/abw-resume`**: Khôi phục trạng thái qua Continuation Kernel.
- **`/abw-execute`**: Wrapper thực thi có giám sát bước.
- `/abw-learn`: Lưu bài học vào `.brain/lessons_learned.jsonl`.
- `/save-brain`: Snapshot project.
- `/recap`: Warm-up bối cảnh.
- `/next`: Gợi ý hành động ngắn hạn.
- `/abw-wrap`: Tổng kết và chuẩn bị handover.

### 5. Đánh giá và Nghiệm thu (Evaluation & Acceptance)
*Cơ chế Gated Execution:*
- `/abw-review`: Đánh giá tổng thể.
- `/abw-audit`: Kiểm tra chi tiết artifact/code.
- `/abw-meta-audit`: Kiểm soát chất lượng audit.
- `/abw-rollback`: Cơ chế an toàn khi fail gate.
- `/abw-accept`: Cổng phê duyệt cuối cùng.
- `/abw-eval`: Chạy full chain kiểm soát.

### 6. Tiện ích và Cấu hình (Utility & Config)
- `/customize`: Cá nhân hóa trải nghiệm.
- `/help`: Tài liệu này.
- `/abw-update`: Đồng bộ command surface local.

---

## Ghi nhớ nhanh

- Vừa clone repo? Gõ `/abw-init`.
- Mất ngữ cảnh / Bị ngắt quãng? Gõ `/abw-resume`.
- Muốn AI nhớ cách làm việc của bạn? Gõ `/abw-learn`.
- Muốn kết thúc task và bàn giao? Gõ `/abw-eval`.
- Có việc nhưng chưa biết lane? Gõ `/abw-ask`.
