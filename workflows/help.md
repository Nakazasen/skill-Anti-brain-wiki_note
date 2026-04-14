---
description: Hướng dẫn lệnh và sơ đồ hệ thống Hybrid ABW
---

# WORKFLOW: /help

Bạn là người hướng dẫn của Hybrid ABW. Nhiệm vụ của bạn là giúp người dùng chọn đúng lệnh nhanh nhất, với ưu tiên rõ ràng cho khởi tạo workspace, routing, grounding, ghi nhớ, và nghiệm thu.

---

## Bắt Đầu Đúng Chỗ

- **`/abw-init`**: dùng trước tiên khi vừa clone repo, hoặc khi workspace chưa có cấu trúc ABW đầy đủ. Lệnh này dựng hoặc sửa nền tảng ABW trong workspace.
- **`/abw-setup`**: dùng ngay sau `/abw-init` để cấu hình grounding và kiểm tra đường kết nối tri thức.
- **`/abw-ask`**: dùng khi bạn có task, câu hỏi, hoặc yêu cầu nhưng chưa biết lane nào.
- **`/abw-eval`**: dùng khi đã có đầu ra và bạn muốn audit, challenge, hoặc chấp nhận trước khi coi là xong.
- **`/abw-learn`**: dùng khi một correction của user cần trở thành bài học hành vi tái sử dụng.

---

## Khi Nào Dùng Lệnh Nào?

- **Dùng `/abw-init`** khi workspace chưa có cấu trúc ABW, hoặc bạn vừa clone repo xong.
- **Dùng `/abw-setup`** khi cần cấu hình grounding sau khi khởi tạo xong workspace.
- **Dùng `/abw-ask`** khi có việc cần làm hoặc câu hỏi cần router chọn lane phù hợp.
- **Dùng `/abw-eval`** khi muốn chạy vòng đánh giá cho thay đổi, workflow, tài liệu, hoặc đầu ra của mô hình.
- **Dùng `/abw-learn`** khi user correction cần ghi vào `.brain/lessons_learned.jsonl` để dùng lại.
- **Dùng `/abw-start`** khi muốn mở phiên làm việc theo cách có kiểm tra trạng thái và grounding path.
- **Dùng `/abw-wrap`** khi muốn chốt phiên, chuẩn bị handover, và nhắc phần cần ingest hoặc nghiệm thu tiếp.
- **Dùng `/next`** khi đang ở giữa dàn ý và cần gợi ý bước tiếp theo dựa trên trạng thái hiện tại.
- **Dùng `/help`** khi cần hiểu toàn bộ hệ thống lệnh, lane, hoặc cách chọn command.
- **Dùng `/abw-update`** khi muốn kéo bản command surface mới nhất vào Gemini runtime local.
- **Dùng `/customize`** khi muốn thay đổi phong cách giao tiếp, persona, hoặc mức tự chủ của AI.

---

## Muốn Làm X Thì Gõ Gì Trước?

| Trường hợp | Lệnh gợi ý đầu tiên |
|---|---|
| Vừa clone repo, cần tạo cấu trúc ABW | `/abw-init` |
| Chưa biết nên bắt đầu từ đâu | `/abw-ask` |
| Có câu hỏi dự án nhưng chưa rõ nên tra cứu hay brainstorm | `/abw-ask` |
| Cần tra cứu nhanh một fact đã có trong wiki | `/abw-query` |
| Cần phân tích sâu, so sánh, RCA, tradeoff | `/abw-query-deep` |
| Dự án greenfield, chưa có raw/wiki | `/abw-bootstrap` |
| Muốn chốt brief sản phẩm hoặc scope | `/brainstorm` |
| Muốn dựng nền tri thức từ tài liệu nguồn | `/abw-ingest` |
| Muốn đóng gói tri thức cho NotebookLM | `/abw-pack` |
| Muốn dry-run hoặc sync package đã duyệt lên NotebookLM | `/abw-sync` |
| Muốn kiểm tra sức khỏe wiki, grounding, manifest | `/abw-lint` |
| Muốn kiểm tra MCP hoặc trạng thái hàng đợi | `/abw-status` |
| Muốn lập kế hoạch thực thi hoặc chia task | `/plan` |
| Muốn thiết kế kỹ thuật hoặc DB | `/design` |
| Muốn mockup UI/UX hoặc screen spec | `/visualize` |
| Muốn bắt tay vào code | `/code` |
| Muốn chạy app cục bộ | `/run` |
| Muốn sửa bug | `/debug` |
| Muốn kiểm tra bằng test | `/test` |
| Muốn triển khai lên môi trường đích | `/deploy` |
| Muốn refactor khi đã rõ phạm vi | `/refactor` |
| Muốn review code hoặc trạng thái dự án trước audit sâu hơn | `/abw-review` |
| Muốn audit code, sản phẩm, hoặc bảo mật trong vòng delivery | `/audit` |
| Muốn audit thay đổi hoặc artifact theo ABW rubric | `/abw-audit` |
| Muốn quay về trạng thái an toàn sau thay đổi lỗi | `/abw-rollback` |
| Muốn chốt pass/fail cuối cùng | `/abw-accept` |
| Muốn chạy toàn bộ chain evaluation | `/abw-eval` |
| Muốn ghi một correction thành bài học dùng lại | `/abw-learn` |
| Muốn lưu tiến độ và chuẩn bị handover | `/save-brain` |
| Muốn khôi phục bối cảnh phiên trước | `/recap` |
| Muốn biết bước tiếp theo nên làm gì | `/next` |
| Muốn cập nhật command surface ABW | `/abw-update` |

---

## Mô Hình 6 Lane

### 1. Khám phá và tư duy

- `/abw-ask`: router chính theo intent
- `/abw-query`: tra cứu nhanh trên wiki
- `/abw-query-deep`: suy luận sâu, RCA, tradeoff
- `/abw-bootstrap`: tư duy cho bài toán greenfield
- `/brainstorm`: chốt brief và scope MVP

### 2. Dựng nền tri thức

- `/abw-init`: dựng hoặc sửa cấu trúc ABW
- `/abw-setup`: cấu hình NotebookLM MCP
- `/abw-status`: kiểm tra MCP và queue
- `/abw-ingest`: xử lý raw thành wiki
- `/abw-pack`: đóng gói tri thức thành package
- `/abw-sync`: dry-run hoặc sync package lên NotebookLM
- `/abw-lint`: audit sức khỏe wiki, grounding, manifest

### 3. Triển khai sản phẩm

- `/plan`: lập kế hoạch thực thi
- `/design`: thiết kế kỹ thuật và data
- `/visualize`: mockup UI/UX và layout
- `/code`: cài đặt tính năng
- `/run`: chạy ứng dụng cục bộ
- `/debug`: sửa lỗi hành vi hoặc runtime
- `/test`: kiểm tra chất lượng bằng test
- `/deploy`: triển khai lên môi trường đích
- `/refactor`: dọn code an toàn khi đã rõ hành vi
- `/audit`: review code, sản phẩm, hoặc bảo mật trong delivery loop

### 4. Phiên làm việc và ghi nhớ

- `/abw-start`: mở phiên làm việc và kiểm tra trạng thái
- `/abw-learn`: ghi một lesson hành vi tái sử dụng vào `.brain/lessons_learned.jsonl`
- `/save-brain`: lưu tiến độ, handover, và lessons learned
- `/recap`: khôi phục bối cảnh phiên trước
- `/next`: gợi ý bước tiếp theo
- `/abw-wrap`: chốt phiên và chuẩn bị quay lại

### 5. Đánh giá và nghiệm thu

- `/abw-review`: review code hoặc trạng thái dự án
- `/abw-audit`: audit workflow, tài liệu, thay đổi, hoặc đầu ra
- `/abw-meta-audit`: audit lại báo cáo audit
- `/abw-rollback`: quay về trạng thái an toàn
- `/abw-accept`: chốt pass/fail cuối cùng
- `/abw-eval`: chạy full evaluation chain

### 6. Tiện ích và Cấu hình

- `/customize`: chỉnh phong cách giao tiếp, persona, và autonomy
- `/help`: xem bản đồ lệnh và quyết định nhanh
- `/abw-update`: cập nhật command surface ABW vào Gemini runtime local

---

## Ghi Nhớ Nhanh

- Nếu bạn vừa clone repo, gõ `/abw-init` trước.
- Nếu workspace đã có cấu trúc rồi, gõ `/abw-setup` để nối grounding.
- Nếu bạn chưa biết lane, gõ `/abw-ask`.
- Nếu user sửa sai và muốn agent nhớ về sau, gõ `/abw-learn`.
- Nếu bạn muốn chốt đầu ra, gõ `/abw-eval`.
- Nếu bạn muốn sửa code an toàn sau khi hiểu rõ, gõ `/refactor`.
