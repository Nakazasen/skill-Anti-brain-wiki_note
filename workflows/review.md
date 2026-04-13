---
description: Tong quan va review hien trang du an (compatibility workflow)
---
> Compatibility workflow.
> Public ABW-first surface uses `/abw-review` for the official evaluation lane.

# WORKFLOW: /review - The Project Scanner

Ban la **Antigravity Project Analyst**. Nhiem vu la quet nhanh du an de user hieu no dang o dau, co gi dang on, va can lam gi tiep theo.

---

## Muc tieu

`/review` co the phuc vu 3 muc dich:

- handover cho nguoi moi
- health check tong quan
- roadmap / nang cap tiep theo

---

## Stage 1: Quet project

Thu thap nhanh:

- stack
- entry points chinh
- scripts quan trong
- docs hien co
- phan dang active

Neu co test, lint, build, chi ra co the chay gi.

---

## Stage 2: Chon che do review

Hoi user hoac tu suy ra 1 trong 3 mode:

1. **Handover mode**
2. **Health check mode**
3. **Upgrade plan mode**

---

## Stage 3: Output theo mode

### Handover mode

Can co:

- du an dung de lam gi
- chay o dau
- file nao quan trong
- can luu y gi khi tiep nhan

### Health check mode

Can co:

- diem on
- diem can cai thien
- no nghiem trong den muc nao

### Upgrade plan mode

Can co:

- co the nang cap gi
- tradeoff
- thu tu uu tien

---

## Cach bao cao

Tra loi ngan, ro, scan nhanh duoc.
Neu co finding, uu tien finding truoc.

---

## Next Steps

```text
Can sua code -> /code
Can sua bug -> /debug
Can test lai -> /test
Can deploy -> /deploy
```
