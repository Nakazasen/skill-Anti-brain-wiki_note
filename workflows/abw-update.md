---
description: Cap nhat command surface ABW vao Gemini runtime local
---

# WORKFLOW: /abw-update

**Muc dich:** Cap nhat Antigravity Brain Wiki OS / Hybrid ABW len ban moi nhat cua repo va dang ky lai command surface vao Gemini runtime local.

## Huong dan cho AI

Khi user goi `/abw-update`, thuc hien theo trinh tu:

1. Noi ro lenh nay dung de cap nhat command surface ABW tu repo hien tai vao Gemini runtime local.
2. Hoi mot cau ngan xac nhan user co muon update ngay khong.
3. Neu user dong y, huong dan chay lai installer cua repo hien tai:

### Windows

```powershell
irm https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.ps1 | iex
```

### macOS / Linux

```bash
curl -fsSL https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.sh | sh
```

4. Neu user dang dung local clone cua repo, uu tien de xuat chay installer local de test nhanh.
5. Sau khi update, nhac user reload IDE hoac restart Gemini extension neu slash menu chua refresh.
6. Nhac user go lai `/help` hoac `/abw` de kiem tra command surface moi.

## Quy tac

- Khong goi day la update AWF.
- Khong tu dong gia dinh user muon cap nhat runtime khac ngoai Gemini local.
- Khong tu nhan update thanh cong neu user chua chay installer.
