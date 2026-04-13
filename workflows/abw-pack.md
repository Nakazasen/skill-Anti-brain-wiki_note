---
description: Dong goi tri thuc cho NotebookLM (Orchestrator Mode)
---

# WORKFLOW: /abw-pack

**Muc dich:** Giai quyet gioi han source cua NotebookLM bang quy trinh dong goi xac dinh. Lenh nay goi script Python de tong hop cac note trong `wiki/` thanh cac package gon nhung van giu truy vet.

**Huong dan danh cho AI (Orchestrator):**
Tu phase nay tro di, khong tu tay parse wiki va tao package bang LLM. Nhiem vu cua ban la chay script Python va trinh bay Approval Menu cho nguoi dung.

> Luu y: Tren clone sach, muon `/abw-pack` dat `pass` thi can chay `/abw-ingest` truoc hoac phai co `processed/manifest.jsonl` hop le.

---

## Cac buoc thuc hien

### 1. Khoi chay packager script

Su dung script da cai san:

**Bash / macOS / Linux**
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

**PowerShell / Windows**
```powershell
$PolicyFile = ".brain\\pack_policy.json"
if (-not (Test-Path $PolicyFile)) {
    $PolicyFile = "$env:USERPROFILE\\.gemini\\antigravity\\templates\\notebook_pack_policy.example.json"
}

python "$env:USERPROFILE\\.gemini\\antigravity\\scripts\\abw_pack.py" `
  --workspace . `
  --policy $PolicyFile `
  --output notebooks/packages `
  --package-id auto
```

Neu dang chay truc tiep trong repo local, co the thay duong dan script bang `scripts/abw_pack.py`.

### 2. Doc exit code va bao cao

Phan tich exit code:

- `0`: pass
- `1`: runtime error
- `2`: needs review
- `3`: fail

Doc JSON stdout cua script va tom tat thanh operator report:

- so source da phat hien
- so file critical duoc giu nguyen
- so package da tao
- package nao can review

### 3. Phuc vu Approval Menu

Dung lai cho nguoi dung quyet dinh:

- `approve package`: duyet package cho phase sync
- `reject package`: cap nhat `package_manifest.json` thanh `package_status: rejected`
- `force keep <file>` / `force compress <file>`: tao hoac sua `.brain/pack_policy.json`, sau do chay lai script

Neu QA bao loi, tham chieu `skills/notebooklm-knowledge-packager.md` de giai thich ro ly do.
