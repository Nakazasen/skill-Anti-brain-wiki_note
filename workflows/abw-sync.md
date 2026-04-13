---
description: Dry-run or execute NotebookLM sync for an ABW package
---

# WORKFLOW: /abw-sync

**Mục đích:** Đồng bộ một package đã sinh bởi `/abw-pack` lên NotebookLM bằng `nlm`, với `dry-run` là mặc định. Lệnh này không xóa nguồn NotebookLM và không upload nếu người dùng chưa yêu cầu `--execute`.

## Hướng dẫn cho AI

1. Xác định package cần sync, ví dụ `notebooks/packages/test_final_clean`.
2. Xác định NotebookLM notebook ID hoặc alias. Nếu người dùng chưa cung cấp, hỏi đúng một câu ngắn để lấy notebook ID.
3. Chạy dry-run trước:

```powershell
python "$env:USERPROFILE\.gemini\antigravity\scripts\abw_sync.py" `
  --package-dir notebooks/packages/<package_id> `
  --notebook-id <notebook_id>
```

Bash/macOS/Linux:

```bash
python "$HOME/.gemini/antigravity/scripts/abw_sync.py" \
  --package-dir notebooks/packages/<package_id> \
  --notebook-id <notebook_id>
```

4. Đọc JSON stdout và `sync_report.json`, rồi báo cáo:
   - package ID
   - `qa_status`
   - số source sẽ upload
   - danh sách source
   - trạng thái `dry_run`, `blocked`, hoặc `synced`
5. Chỉ chạy upload thật khi người dùng xác nhận rõ:

```powershell
python "$env:USERPROFILE\.gemini\antigravity\scripts\abw_sync.py" `
  --package-dir notebooks/packages/<package_id> `
  --notebook-id <notebook_id> `
  --execute
```

## Quy tắc an toàn

- Không sync package `fail`.
- Không sync package `needs_review` trừ khi người dùng yêu cầu rõ và dùng `--allow-needs-review`.
- Không xóa nguồn NotebookLM trong Phase 4.
- Không tự tạo notebook mới nếu người dùng chưa yêu cầu rõ.
- Nếu `nlm` lỗi auth/network, báo lỗi và dừng; không retry hung hăng.
