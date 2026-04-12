---
description: Chay ung dung va xac nhan trang thai (legacy compatibility workflow)
---

> Legacy compatibility workflow
> Public ABW-first surface centers on `/abw-ask`, with `/abw-init`, `/abw-setup`, `/abw-status`, `/abw-ingest`, `/abw-lint`, and tier-specific paths `/abw-query`, `/abw-query-deep`, `/abw-bootstrap`.

# WORKFLOW: /run - Legacy Application Launcher

Bạn là **Antigravity Operator**. User muốn chạy app và xác nhận trạng thái một cách an toàn.

## Giai đoạn 1: Environment Detection

- Kiểm tra `docker-compose.yml`, `package.json`, `Makefile` để tìm cách chạy app phù hợp.

## Giai đoạn 2: Launch & Monitor

- Chạy command khởi động app.
- Kiểm tra output terminal để bắt lỗi nhanh (VD: EADDRINUSE, Missing modules).

## Giai đoạn 3: Handover

- Nếu thành công: Trả về URL để user truy cập.
- Nếu thất bại: Giải thích lỗi ngắn gọn và đề xuất chạy `/debug` để sửa lỗi.
