# Skill: abw-setup

> **Purpose:** Interactive wizard to guide operators through NotebookLM MCP authentication and configuration.
> **Role:** Onboarding utility (used by `/abw-setup`)

---

## Instructions for AI Operator

When the user calls `/abw-setup`, execute this interactive wizard. Do not print the whole file at once. Follow the stages step-by-step and wait for the user's response before proceeding.

Tra loi bang tieng Viet ro rang, ngan gon.

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

"Ban muon lien ket NotebookLM voi Google account nao? Hay tra loi bang email day du, vi du `buiducvinhct1102@gmail.com`."

Record the answer as `expected_google_account`.

If the user does not provide a full email address, stop and explain:

"Toi can email Google ro rang de tranh lien ket nham tai khoan. ABW se khong suy luan tu username Windows, IDE, browser, hay notebook list."

### Stage 1: Check Pre-requisites

Ask the user:

"De kich hoat he thong Grounding va thoat Fallback Mode, ban can dang nhap Google NotebookLM thong qua CLI. Ban da cai `notebooklm-mcp` / `nlm` tren may chua?

- [1] Roi, toi da cai.
- [2] Chua, huong dan toi cai."

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

"Bay gio mo terminal trong dung moi truong ban dang dung va chay:

```bash
nlm login <expected_google_account>
```

Neu phien ban `nlm` cua ban khong nhan email argument, chay:

```bash
nlm login
```

Khi trinh duyet mo ra, hay chon dung tai khoan `<expected_google_account>`. Khong chon tai khoan Windows/IDE/browser neu no khac email nay.

Sau khi terminal bao dang nhap thanh cong, chay mot lenh chan doan neu CLI ho tro, vi du:

```bash
nlm auth status
```

hoac:

```bash
nlm notebook list
```

Quay lai day va dan output chan doan. Neu output khong hien email mong muon, noi ro la khong khop thay vi go 'Xong'."

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
   - Inform the user: "Ket noi MCP thanh cong va dung tai khoan Google da xac nhan."
   - Update `skills/notebooklm-mcp-bridge.md`:
     - Change `mcp_status: "not_detected"` to `mcp_status: "active"`.
     - Change `auth_status: "not_authenticated"` to `auth_status: "authenticated"`.
     - Set `profile` to `expected_google_account`.
     - Set `last_auth` and `verified_at` when a reliable timestamp is available.
   - Proceed to Stage 5.
3. If the MCP test fails:
   - Inform the user: "Toi chua bat duoc tin hieu tu MCP. Dang nhap co the dung, nhung bridge NotebookLM MCP chua san sang."
   - Ask the user to verify the Antigravity IDE MCP server configuration. The server should be named `notebooklm`.
   - Do not mark the bridge as authenticated unless both account match and MCP connectivity are verified.

### Stage 5: Wrap-up

If Stage 4 was successful, tell the user:

"He thong Hybrid ABW da chay Active Mode voi NotebookLM MCP va dung tai khoan Google da xac nhan. Ban co the dung `/abw-status` bat cu luc nao de kiem tra lai trang thai ket noi."
