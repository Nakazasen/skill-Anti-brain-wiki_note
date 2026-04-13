---
description: Cập nhật command surface ABW vào Gemini runtime local
---

# WORKFLOW: /abw-update

**Mục đích:** Cập nhật Antigravity Brain Wiki OS / Hybrid ABW lên bản mới nhất của repo và đăng ký lại command surface vào Gemini runtime local.

## Hướng dẫn cho AI

Khi user gọi `/abw-update`, thực hiện theo trình tự:

1. Nói rõ lệnh này dùng để cập nhật command surface ABW từ repo hiện tại vào Gemini runtime local.
2. Nếu user đã gọi trực tiếp `/abw-update` hoặc nói rõ muốn update ngay, xem đó là xác nhận đủ để thực hiện.
3. Nếu môi trường cho phép chạy lệnh, ưu tiên **chạy lại installer tự động** thay vì chỉ đưa command để user tự copy-paste.
4. Thứ tự ưu tiên khi update:

- Nếu đang ở trong local clone của repo trên Windows: chạy `powershell -ExecutionPolicy Bypass -File .\\install.ps1`
- Nếu đang ở trong local clone của repo trên macOS/Linux: chạy `bash ./install.sh`
- Nếu không có local clone hoặc không thể chạy shell, đưa đúng lệnh installer remote để user tự chạy

5. Khi cần đưa lệnh remote, dùng đúng lệnh sau:

### Windows

```powershell
irm https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.ps1 | iex
```

### macOS / Linux

```bash
curl -fsSL https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.sh | sh
```

6. Sau khi update, nhắc user reload IDE hoặc restart Gemini extension nếu slash menu chưa refresh.
7. Nhắc user gõ lại `/help` hoặc `/abw` để kiểm tra command surface mới.
8. Báo cáo rõ kết quả:

- installer có chạy thành công hay không
- command nào đã được đăng ký lại
- có cần reload IDE hay không

## Quy tắc

- Không gọi đây là update AWF.
- Không tự động giả định user muốn cập nhật runtime khác ngoài Gemini local.
- Không tự nhận update thành công nếu installer chưa thực sự được chạy.
- Nếu user chỉ hỏi cách update mà không yêu cầu thực hiện, lúc đó mới dùng chế độ hướng dẫn.
