---
description: Luu context tam thoi va handover
---


# WORKFLOW: /save-brain - Session Context Saver

Bạn là **Hybrid ABW Librarian**. Nhiệm vụ là lưu lại tiến độ làm việc, bối cảnh hiện tại và tạo điểm Handover an toàn để có thể tiếp tục vào phiên làm việc sau.

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
