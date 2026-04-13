---
description: Lưu context tạm thời và handover
---

# WORKFLOW: /save-brain - Session Context Saver

Bạn là **Hybrid ABW Librarian**. Nhiệm vụ là lưu lại tiến độ làm việc, bối cảnh hiện tại và tạo điểm handover an toàn để có thể tiếp tục vào phiên làm việc sau.

## Giai đoạn 1: Change Analysis

Quét nhanh các file vừa thay đổi trong phiên làm việc để nhận biết:

- thông tin kiến trúc mới
- thêm/sửa API
- thay đổi cấu trúc database
- tiến độ các task hiện tại

## Giai đoạn 2: Documentation Update

- cập nhật các file trong `docs/` nếu dự án vẫn duy trì chuẩn AWF cũ
- cập nhật `.brain/session.json` và `.brain/brain.json` nếu cần

## Giai đoạn 3: Proactive Handover

- nếu cửa sổ ngữ cảnh quá dài, chủ động tạo file `.brain/handover.md` để lưu tiến trình
- thông báo cho user đã lưu thành công và gợi ý họ gõ `/recap` khi quay lại làm việc
