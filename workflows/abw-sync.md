---
description: Dry-run hoac execute NotebookLM sync cho mot ABW package
---

# WORKFLOW: /abw-sync

**Muc dich:** Dong bo mot package duoc sinh boi `/abw-pack` len NotebookLM bang `nlm`, voi `dry-run` la mac dinh. Lenh nay khong xoa source trong NotebookLM va khong upload neu nguoi dung chua yeu cau `--execute`.

## Huong dan cho AI

1. Xac dinh package can sync, vi du `notebooks/packages/<package_id>`.
2. Xac dinh NotebookLM notebook ID hoac alias. Neu user chua cung cap, hoi mot cau ngan de lay dung notebook ID.
3. Chay dry-run truoc:

```powershell
python "$env:USERPROFILE\\.gemini\\antigravity\\scripts\\abw_sync.py" `
  --package-dir notebooks/packages/<package_id> `
  --notebook-id <notebook_id>
```

Bash / macOS / Linux:

```bash
python "$HOME/.gemini/antigravity/scripts/abw_sync.py" \
  --package-dir notebooks/packages/<package_id> \
  --notebook-id <notebook_id>
```

4. Doc JSON stdout va `sync_report.json`, roi bao cao:
   - package ID
   - `qa_status`
   - so source se upload
   - danh sach source
   - trang thai `dry_run`, `blocked`, hoac `synced`
5. Chi chay upload that khi nguoi dung xac nhan ro:

```powershell
python "$env:USERPROFILE\\.gemini\\antigravity\\scripts\\abw_sync.py" `
  --package-dir notebooks/packages/<package_id> `
  --notebook-id <notebook_id> `
  --execute
```

## Quy tac an toan

- Khong sync package `fail`
- Khong sync package `needs_review` tru khi user yeu cau ro va dung `--allow-needs-review`
- Khong xoa source NotebookLM trong phase nay
- Khong tu tao notebook moi neu user chua yeu cau ro
- Neu `nlm` loi auth hoac network, bao loi va dung; khong retry hung huc
