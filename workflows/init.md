---
description: Khoi tao du an moi (Build Product lane)
---

# WORKFLOW: /init - Khởi tạo dự án

**Vai tro:** Project Initializer  
**Muc tieu:** Thu thap y tuong, tao cau truc workspace co ban, va ghi lai diem bat dau cua du an.  
**Ngon ngu:** Luon tra loi bang tieng Viet.

---

## Flow Position

```text
/init
  -> /brainstorm (neu y tuong con mo)
  -> /plan
  -> /design
  -> /code
```

---

## Khi nao dung

Dung `/init` khi:

- du an moi bat dau
- workspace chua co cau truc ro rang
- can reset lai diem bat dau de team nhin cung mot huong

Khong dung `/init` de:

- cai package
- setup database
- viet code
- deploy

---

## Stage 1: Capture Vision

Hoi toi da 3 cau:

1. Ten du an la gi?
2. Du an nay dung de giai quyet van de nao?
3. Ai la nguoi dung chinh?

Neu user tra loi mo ho:

- tom tat lai bang 1-2 cau
- de xuat chuyen sang `/brainstorm` neu can lam ro hon

---

## Stage 2: Tao Workspace Co Ban

Tao hoac xac nhan cac file/folder toi thieu:

```text
.brain/
docs/
README.md
```

Neu du an la AWF-style project, co the tao them:

```text
docs/ideas.md
.brain/brain.json
```

Muc dich cua buoc nay la tao diem dat chan, khong phai scaffold day du cho production.

---

## Stage 3: Ghi Lai Khoi Tao

Luu thong tin toi thieu:

- ten du an
- mo ta ngan
- user target
- trang thai hien tai
- next step de xuat

Neu co `.brain/brain.json`, ghi vao do.
Neu khong, cap nhat `README.md` hoac `docs/ideas.md`.

---

## Output Mong Muon

Sau khi chay xong, user phai nhan duoc:

- ten du an da thong nhat
- mo ta 1-2 cau
- workspace co ban da tao
- mot next step ro rang

---

## Khong Lam

- khong tu y cai dependencies
- khong tu y setup cloud, db, auth
- khong viet spec qua chi tiet
- khong nhay sang code neu user chua dong y

---

## Next Steps

```text
Neu y tuong con mo -> /brainstorm
Neu da ro feature -> /plan
Neu da co plan va can thiet ke -> /design
```