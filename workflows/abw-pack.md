---
description: Nén tri thức và giảm tải cho NotebookLM (Orchestrator Mode)
---

# WORKFLOW: /abw-pack

**Muc dich:** Giải quyết giới hạn source limit của NotebookLM (tối đa 50 nguồn) bằng quy trình đóng gói tất định (Deterministic Compaction). Lệnh này gọi script Python lõi để tổng hợp các note `wiki/` thành các Wiki Packages rút gọn nhưng bảo lưu 100% bằng chứng truy vết.

**Hướng dẫn dành cho AI (Orchestrator):**
Kể từ Phase 2, bạn KHÔNG TỰ tay parse file hay sinh file bằng LLM nữa. Nhiệm vụ của bạn là chạy Script Python và cung cấp **Approval Menu** cho Người dùng.

---

## Các bước thực hiện

### 1. Khởi chạy Packager Script
Sử dụng công cụ `run_command` để chạy đoạn script Python cài sẵn:

**Bash / macOS / Linux:**
```bash
POLICY_FILE=".brain/pack_policy.json"
if [ ! -f "$POLICY_FILE" ]; then
  POLICY_FILE="$HOME/.gemini/antigravity/templates/notebook_pack_policy.example.json"
fi

python ~/.gemini/antigravity/scripts/abw_pack.py \
  --workspace . \
  --policy "$POLICY_FILE" \
  --output notebooks/packages \
  --package-id auto
```

**PowerShell / Windows:**
```powershell
$PolicyFile = ".brain\pack_policy.json"
if (-not (Test-Path $PolicyFile)) {
    $PolicyFile = "$env:USERPROFILE\.gemini\antigravity\templates\notebook_pack_policy.example.json"
}

python "$env:USERPROFILE\.gemini\antigravity\scripts\abw_pack.py" `
  --workspace . `
  --policy $PolicyFile `
  --output notebooks/packages `
  --package-id auto
```
*Lưu ý: Nếu bạn đang chạy trực tiếp trên kho phát triển `skill-Anti-brain-wiki_note-main`, thay đường dẫn script bằng `scripts/abw_pack.py`.*

### 2. Đọc Exit Code và Báo Cáo
Phân tích Exit code từ terminal:
- `0`: Pass hoàn hảo.
- `1`: Script gặp lỗi Runtime. Cần Debug.
- `2`: Needs review (Có thể do chạm mức Soft-limit).
- `3`: Fail (Có thể do vượt Hard-limit, hoặc Node/Manifest mismatch).

Dịch STDOUT JSON của script thành một báo cáo ngắn gọn (Operator Report):
> 📊 **BÁO CÁO CỤM TRI THỨC (ABW-PACK)**
> - X sources detected -> Y Critical kept
> - M compressed into N wiki files
> - Z packages need review...

### 3. Phục vụ Approval Menu
Hiển thị Menu hành động cho người dùng. Dừng lại chờ quyết định:
- 🟢 `approve package`: Duyệt, đóng khóa package chuẩn bị cho Phase 4.
- 🔴 `reject package`: Từ chối gói (Bạn hãy sửa `package_manifest.json` cập nhật `"package_status": "rejected"` - Không tự xóa thư mục).
- ⚙️ `force keep <file>` / `force compress <file>`: Cập nhật Policy. Bạn hãy tạo/sửa file `.brain/pack_policy.json` cho Người dùng và chạy lại script.

Bạn hãy tuân thủ triệt để [skills/notebooklm-knowledge-packager.md](../skills/notebooklm-knowledge-packager.md) để giải thích lỗi QA nếu xảy ra.
