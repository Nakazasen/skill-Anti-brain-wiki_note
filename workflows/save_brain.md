---
description: Luu context tam thoi va handover (legacy compatibility workflow)
---

> Legacy compatibility workflow
> Public ABW-first surface centers on `/abw-ask`, with `/abw-init`, `/abw-setup`, `/abw-status`, `/abw-ingest`, `/abw-lint`, and tier-specific paths `/abw-query`, `/abw-query-deep`, `/abw-bootstrap`.

# WORKFLOW: /save-brain - Legacy Context Saver

Bạn là **Antigravity Librarian**. Nhiệm vụ là lưu lại context tạm thời và tạo điểm Handover an toàn.

## Giai đoạn 1: Change Analysis

Quét nhanh các file vừa thay đổi trong phiên làm việc để nhận biết:

- Thông tin kiến trúc mới
- Thêm/sửa API
- Thay đổi cấu trúc Database
- Tiến độ các task hiện tại

## Giai đoạn 2: Documentation Update

- Cập nhật các file trong `docs/` (nếu dự án vẫn duy trì chuẩn AWF cũ).
- Cập nhật `.brain/session.json` và `.brain/brain.json` (tùy chọn).

## Giai đoạn 3: Proactive Handover

- Nếu cửa sổ ngữ cảnh (Context Window) quá dài, chủ động tạo file `.brain/handover.md` để lưu tiến trình.
- Thông báo cho user đã lưu thành công và gợi ý họ gõ `/recap` khi quay lại làm việc.
