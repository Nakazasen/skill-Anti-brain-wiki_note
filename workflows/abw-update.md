---
description: Cap nhat command surface ABW vao Gemini runtime local
---

# WORKFLOW: /abw-update

**Muc dich:** Cap nhat Antigravity Brain Wiki OS / Hybrid ABW len ban moi nhat cua repo va dang ky lai command surface vao Gemini runtime local.

## Huong dan cho AI

Khi user goi `/abw-update`, thuc hien theo trinh tu:

1. Noi ro lenh nay dung de cap nhat command surface ABW tu repo hien tai vao Gemini runtime local.
2. Neu user da goi truc tiep `/abw-update` hoac noi ro muon update ngay, xem do la xac nhan du de thuc hien.
3. Neu moi truong cho phep chay lenh, uu tien **chay lai installer tu dong** thay vi chi dua command de user tu copy-paste.
4. Thu tu uu tien khi update:

- Neu dang o trong local clone cua repo tren Windows: chay `powershell -ExecutionPolicy Bypass -File .\\install.ps1`
- Neu dang o trong local clone cua repo tren macOS/Linux: chay `bash ./install.sh`
- Neu khong co local clone hoac khong the chay shell, dua dung lenh installer remote de user tu chay

5. Khi can dua lenh remote, dung dung lenh sau:

### Windows

```powershell
irm https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.ps1 | iex
```

### macOS / Linux

```bash
curl -fsSL https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.sh | sh
```

6. Sau khi update, nhac user reload IDE hoac restart Gemini extension neu slash menu chua refresh.
7. Nhac user go lai `/help` hoac `/abw` de kiem tra command surface moi.
8. Bao cao ro ket qua:

- installer co chay thanh cong hay khong
- command nao da duoc dang ky lai
- co can reload IDE hay khong

## Quy tac

- Khong goi day la update AWF.
- Khong tu dong gia dinh user muon cap nhat runtime khac ngoai Gemini local.
- Khong tu nhan update thanh cong neu installer chua thuc su duoc chay.
- Neu user chi hoi cach update ma khong yeu cau thuc hien, luc do moi dung che do huong dan.
