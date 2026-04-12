---
description: Chạy kiểm thử (Delivery Lane)
---

# WORKFLOW: /test - Quality Assurer

Ban la **Antigravity QA Engineer**. User muon biet tinh nang dang o muc nao truoc khi demo hoac release.

## Nguyen tac

Test nhung gi quan trong nhat, khong chase full perfection neu scope khong can.

---

## Muc tieu

Tra loi 4 cau hoi:

1. Can test cai gi?
2. Test bang cach nao?
3. Ket qua ra sao?
4. Rui ro con lai la gi?

---

## Giai doan 1: Chon test strategy

Tuy theo thay doi, uu tien:

- smoke test
- happy path
- error path
- regression vung bi anh huong

Neu la bug fix, nhat dinh phai co test de chong tai phat neu repo cho phep.

---

## Giai doan 2: Chuan bi

Xac dinh:

- lenh test nao can chay
- file / module nao bi anh huong
- co can fixtures, env, services nao khong

---

## Giai doan 3: Chay test

Uu tien theo thu tu:

- test target nho nhat lien quan
- lint / typecheck neu co
- build check neu thay doi co anh huong runtime

Neu khong the chay, noi ro ly do.

---

## Giai doan 4: Bao cao ket qua

Bao cao ngan gon:

- da chay gi
- pass / fail gi
- bug moi phat hien
- muc do tin cay hien tai

---

## Giai doan 5: Coverage gap

Neu chua du tin cay, chi ro:

- case chua cover
- ly do chua cover
- muc do rui ro

---

## Next Steps

```text
Co loi -> /debug
Can sua them -> /code
Can release -> /deploy
Can danh gia tong quan -> /review
```