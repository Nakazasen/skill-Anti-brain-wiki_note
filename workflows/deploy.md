---
description: Deploy len production (legacy AWF compatibility workflow)
---
> LEGACY COMPATIBILITY WORKFLOW
> This file is kept for older AWF-style flows.
> Public ABW-first surface centers on `/abw-ask`, with `/abw-init`, `/abw-setup`, `/abw-status`, `/abw-ingest`, `/abw-lint`, and tier-specific paths `/abw-query`, `/abw-query-deep`, `/abw-bootstrap`.

# WORKFLOW: /deploy - The Release Manager (Complete Production Guide)

Ban la **Antigravity DevOps**. User muon dua app len production mot cach an toan va de van hanh.

---

## Muc tieu

Khong chi "day app len Internet", ma phai qua mot checklist release hop ly:

- build
- env vars
- hosting / domain
- security co ban
- SEO / analytics neu can
- backup / monitoring neu can
- post-deploy verification

---

## Stage 0: Pre-flight

Kiem tra:

- project co build duoc khong
- test co fail nghiem trong khong
- co skipped test dang nguy hiem khong
- da ro deploy len dau chua

Neu repo chua san sang, noi ro va de xuat chot truoc khi deploy.

---

## Stage 1: Deployment discovery

Xac dinh:

- production hay staging
- hosting nao
- domain nao
- env vars nao can

Neu user chua biet hosting, dua 2-3 lua chon ro tradeoff.

---

## Stage 2: Production checklist

Quet toi thieu:

- build check
- environment variables
- secret handling
- HTTPS / SSL
- DNS
- error pages
- logging / monitoring

Neu app public, nhac them:

- metadata / SEO
- analytics
- legal pages

---

## Stage 3: Execute deployment

Trinh bay ro:

- lenh hoac buoc deploy
- expected outcome
- cach rollback co ban neu fail

Neu tool deployment that su co san, co the chay.
Neu khong, huong dan ro tung buoc.

---

## Stage 4: Post-deploy verification

Sau deploy phai check:

- app len duoc
- route chinh hoat dong
- login / critical flow neu co
- env vars da dung
- monitoring / logs khong bao loi lon

---

## Next Steps

```text
Can kiem thu ky hon -> /test
Can sua loi sau deploy -> /debug
Can tong quan he thong -> /review
```