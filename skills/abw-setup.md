# Skill: abw-setup

> **Purpose:** Interactive wizard to guide operators through NotebookLM MCP authentication and configuration.
> **Role:** Onboarding utility (used by `/abw-setup`)

---

## Instructions for AI Operator

When the user calls `/abw-setup`, you must execute this **Interactive Wizard**. Do NOT print the whole file at once. Follow these stages step-by-step, waiting for the user's response before proceeding.

Trò chuyện bằng tiếng Việt mượt mà, thân thiện.

### Stage 1: Check Pre-requisites
Ask the user:
"Để kích hoạt Hệ thống Grounding (xóa bỏ Fallback Mode), bạn cần đăng nhập Google NotebookLM thông qua CLI. 
Bạn đã cài đặt bộ công cụ `notebooklm-mcp` trên máy chưa?"
- [1] Rồi, tôi đã cài.
- [2] Chưa, hướng dẫn tôi cài.

*Wait for User response.*
If [2], provide the terminal command: `pip install notebooklm-mcp` (or pipx). After they confirm it's installed, proceed to Stage 2.
If [1], proceed to Stage 2.

### Stage 2: Authentication
Tell the user:
"Tuyệt vời. Bây giờ hãy mở một Terminal mới trong hệ thống của bạn và gõ lệnh sau:
`nlm login`
Trình duyệt sẽ mở ra để bạn đăng nhập Google. Sau khi màn hình Terminal báo thành công `[OK] Authentication successful`, hãy quay lại đây gõ **'Xong'** để tôi kiểm tra kết nối."

*Wait for User to say 'Xong'*

### Stage 3: Connection Test & Config Update
When the user says 'Xong':
1. As the Agent, attempt to run the MCP tool: `mcp_notebooklm_server_info` or `mcp_notebooklm_notebook_list`.
2. **If it connects successfully**:
   - Inform the user: "🎉 Kết nối MCP thành công!"
   - Use your file editing tools to update `skills/notebooklm-mcp-bridge.md`:
     - Change `mcp_status: "not_detected"` to `mcp_status: "active"`
     - Change `auth_status: "not_authenticated"` to `auth_status: "authenticated"`
   - Proceed to Stage 4.
3. **If it fails**:
   - Inform the user: "⚠️ Tôi chưa bắt được tín hiệu từ MCP. Bạn có chắc là lệnh `nlm login` không báo lỗi gì chứ?"
   - Ask them to double-check their MCP Server configuration in the Antigravity IDE settings (it must be named `notebooklm`).

### Stage 4: Wrap-up
If Stage 3 was successful, tell the user:
"Hệ thống **Hybrid ABW** của bạn hiện đã chạy với 100% công suất (Active Mode). Mọi tài liệu bạn đưa vào từ giờ sẽ được đối chiếu chéo tự động với NotebookLM.
Bạn có thể dùng `/abw-status` bất cứ lúc nào để kiểm tra lại. 
Cảm ơn bạn đã hoàn tất cài đặt!"
