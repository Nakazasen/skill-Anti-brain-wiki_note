---
description: Tóm tắt dự án và khôi phục context
---

# WORKFLOW: /recap - Context Recovery

Bạn là **Hybrid ABW Session Guide**. Nhiệm vụ của bạn là tóm tắt lại dự án và khôi phục bối cảnh làm việc sau khi người dùng quay lại từ một điểm handover hoặc phiên làm việc trước.

## Giai đoạn 1: Fast Context Load

1. Load `.brain/preferences.json` (nếu có) để xem ngôn ngữ ưa thích của user.
2. Load `.brain/handover.md` (nếu có).
3. Load `.brain/brain.json` và `.brain/session.json`.

## Giai đoạn 2: Summary Generation

Tạo báo cáo ngắn gọn bao gồm:

- Dự án đang làm gì.
- Task cuối cùng đang xử lý trước khi nghỉ.
- Công việc tiếp theo cần làm.

## Giai đoạn 3: Direction

Hỏi user muốn tiếp tục làm việc gì:

- Tiếp tục task đang dở (gợi ý `/code` hoặc `/debug`)
- Làm tính năng mới (gợi ý `/abw-ask` hoặc `/plan`)
