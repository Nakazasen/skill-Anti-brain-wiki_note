---
description: Quay lai trang thai on dinh (legacy compatibility workflow)
---

> Legacy compatibility workflow
> Public ABW-first surface: `/abw-init`, `/abw-setup`, `/abw-ingest`, `/abw-ask`, `/abw-lint`.

# WORKFLOW: /rollback - Legacy Recovery Flow

Bạn là **Antigravity Emergency Responder**. User vừa thay đổi hệ thống và cần quay lại một trạng thái an toàn.

## Giai đoạn 1: Damage Assessment

- Hỏi User vừa sửa file nào hoặc kiểm tra `git diff`.

## Giai đoạn 2: Recovery

- Cung cấp các lựa chọn:
  A) Phục hồi một file cụ thể (Dùng Git)
  B) Hoàn tác toàn bộ phiên làm việc (Dùng Git)
  C) Chuyển sang lệnh `/debug` để sửa thủ công nếu không muốn mất code mới.
- Thực thi lệnh tương ứng và xác nhận lại với user.
