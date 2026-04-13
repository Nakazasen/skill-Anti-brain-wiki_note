# Skill: abw-setup

> **Purpose:** Interactive wizard to guide operators through NotebookLM MCP authentication and configuration.
> **Role:** Onboarding utility (used by `/abw-setup`)

---

## Instructions for AI Operator

When the user calls `/abw-setup`, execute this interactive wizard. Do not print the whole file at once. Follow the stages step-by-step and wait for the user's response before proceeding.

Trả lời bằng tiếng Việt rõ ràng, ngắn gọn.

### Account Safety Rule

Never infer the NotebookLM/Google account from:

- Windows username or machine username
- IDE, browser, or OS profile
- git config
- notebook names returned by `nlm notebook list`
- email-like strings found in the workspace

The authenticated account is valid only when the user explicitly provides or confirms the Google email in this setup flow. If the email cannot be confirmed, do not mark the bridge as authenticated.

### Stage 0: Confirm Target Account

Ask the user:

"Bạn muốn liên kết NotebookLM với Google account nào? Hãy trả lời bằng email đầy đủ, ví dụ `buiducvinhct1102@gmail.com`."

Record the answer as `expected_google_account`.

If the user does not provide a full email address, stop and explain:

"Tôi cần email Google rõ ràng để tránh liên kết nhầm tài khoản. ABW sẽ không suy luận từ username Windows, IDE, browser, hay notebook list."

### Stage 1: Check Pre-requisites

Ask the user:

"Để kích hoạt hệ thống Grounding và thoát Fallback Mode, bạn cần đăng nhập Google NotebookLM thông qua CLI. Bạn đã cài `notebooklm-mcp` / `nlm` trên máy chưa?

- [1] Rồi, tôi đã cài.
- [2] Chưa, hướng dẫn tôi cài."

Wait for the user response.

If the user chooses [2], provide one of these commands and wait until they confirm it is installed:

```bash
uv tool install notebooklm-mcp-cli
```

or:

```bash
pipx install notebooklm-mcp
```

or:

```bash
pip install notebooklm-mcp
```

Then proceed to Stage 2.

If the user chooses [1], proceed to Stage 2.

### Stage 2: Authentication

Tell the user:

"Bây giờ mở terminal trong đúng môi trường bạn đang dùng và chạy:

```bash
nlm login <expected_google_account>
```

Nếu phiên bản `nlm` của bạn không nhận email argument, chạy:

```bash
nlm login
```

Khi trình duyệt mở ra, hãy chọn đúng tài khoản `<expected_google_account>`. Không chọn tài khoản Windows/IDE/browser nếu nó khác email này.

Sau khi terminal báo đăng nhập thành công, chạy một lệnh chẩn đoán nếu CLI hỗ trợ, ví dụ:

```bash
nlm auth status
```

hoặc:

```bash
nlm notebook list
```

Quay lại đây và dán output chẩn đoán. Nếu output không hiện email mong muốn, nói rõ là không khớp thay vì gõ 'Xong'."

Wait for the user to provide diagnostic output or say `Xong`.

### Stage 3: Account Match Check

Before testing MCP, verify that the authenticated Google account matches `expected_google_account`.

Use this rule:

- If diagnostic output explicitly shows an account/email, it must equal `expected_google_account`.
- If diagnostic output shows a different account, stop and tell the user to log out or switch profile, then repeat Stage 2 with the correct account.
- If diagnostic output does not show any account/email, ask the user to confirm the active Google account shown in the browser or NotebookLM UI.
- Do not accept notebook titles, workspace paths, Windows username, or domain email guesses as proof of account identity.

If the account cannot be confirmed, do not update `skills/notebooklm-mcp-bridge.md`.

### Stage 4: Connection Test & Config Update

When the account matches:

1. As the Agent, attempt to run the MCP tool: `mcp_notebooklm_server_info`, `mcp_notebooklm_notebook_list`, `notebooklm_notebook_list`, or another available NotebookLM MCP list/info tool.
2. If it connects successfully:
   - Inform the user: "Kết nối MCP thành công và đúng tài khoản Google đã xác nhận."
   - Update `skills/notebooklm-mcp-bridge.md`:
     - Change `mcp_status: "not_detected"` to `mcp_status: "active"`.
     - Change `auth_status: "not_authenticated"` to `auth_status: "authenticated"`.
     - Set `profile` to `expected_google_account`.
     - Set `last_auth` and `verified_at` when a reliable timestamp is available.
   - Proceed to Stage 5.
3. If the MCP test fails:
   - Inform the user: "Tôi chưa bắt được tín hiệu từ MCP. Đăng nhập có thể đúng, nhưng bridge NotebookLM MCP chưa sẵn sàng."
   - Ask the user to verify the Antigravity IDE MCP server configuration. The server should be named `notebooklm`.
   - Do not mark the bridge as authenticated unless both account match and MCP connectivity are verified.

### Stage 5: Wrap-up

If Stage 4 was successful, tell the user:

"Hệ thống Hybrid ABW đã chạy Active Mode với NotebookLM MCP và đúng tài khoản Google đã xác nhận. Bạn có thể dùng `/abw-status` bất cứ lúc nào để kiểm tra lại trạng thái kết nối."
