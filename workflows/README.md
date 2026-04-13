# Hybrid ABW Command Model

Tai lieu nay mo ta command surface chinh thuc cua Hybrid ABW trong repo.

## Bat dau tu dau?

- **`/abw-ask`**: entrypoint mac dinh cho moi task, cau hoi, va yeu cau chua ro lane.
- **`/abw-eval`**: entrypoint mac dinh cho danh gia va nghiem thu.
- **`/abw-start`**: mo phien lam viec co kiem tra trang thai va grounding path.
- **`/abw-update`**: cap nhat command surface ABW vao Gemini runtime local.

## 5 lane

### 1. Kham pha va tu duy

- `/abw-ask` : Router chinh theo intent
- `/abw-query` : Tra cuu nhanh tren wiki
- `/abw-query-deep` : Phan tich sau, tradeoff, RCA
- `/abw-bootstrap` : Tu duy cho bai toan greenfield
- `/brainstorm` : Chot brief san pham va MVP

### 2. Dung nen tri thuc

- `/abw-init` : Khoi tao cau truc ABW
- `/abw-setup` : Cau hinh NotebookLM MCP
- `/abw-status` : Kiem tra MCP va queue
- `/abw-ingest` : Xu ly raw thanh wiki
- `/abw-pack` : Dong goi tri thuc thanh package gon
- `/abw-sync` : Dry-run hoac sync package da duyet len NotebookLM
- `/abw-lint` : Audit suc khoe wiki, grounding, va manifest

### 3. Trien khai san pham

Luong delivery chinh:

- `/plan` : Lap ke hoach thuc thi tinh nang
- `/design` : Thiet ke ky thuat va co so du lieu
- `/visualize` : Dung mockup UI/UX va dac ta man hinh
- `/code` : Cai dat tinh nang
- `/run` : Chay ung dung cuc bo
- `/debug` : Sua loi co he thong
- `/test` : Chay test va kiem tra chat luong
- `/deploy` : Trien khai len moi truong dich

Workflow ho tro:

- `/refactor` : Don code an toan sau khi da hieu ro hanh vi
- `/audit` : Ra soat san pham, code, hoac bao mat trong vong delivery

### 4. Phien lam viec va ghi nho

- `/abw-start` : Mo phien lam viec va kiem tra trang thai
- `/save-brain` : Luu tien do va chuan bi handover
- `/recap` : Khoi phuc boi canh tu phien truoc
- `/next` : Goi y buoc tiep theo
- `/abw-wrap` : Chot phien va wrap lai thay doi

### 5. Danh gia va nghiem thu

- `/abw-review` : Review code, thay doi, hoac hien trang du an
- `/abw-audit` : Tu audit workflow, tai lieu, thay doi, hoac dau ra
- `/abw-meta-audit` : Audit lai chinh bao cao audit
- `/abw-rollback` : Quay ve trang thai an toan sau thay doi loi
- `/abw-accept` : Chot pass/fail cuoi cung
- `/abw-eval` : Chay toan bo chuoi evaluation tu dau den cuoi

### Utility

- `/help` : Ban do he thong va decision table
- `/abw-update` : Keo ban moi nhat cua command surface ABW vao Gemini runtime local

## First Command Cheat Sheet

| Muon lam gi | Lenh dau tien |
|---|---|
| Khong biet nen bat dau tu dau | `/abw-ask` |
| Muon nghiem thu dau ra | `/abw-eval` |
| Muon refactor legacy code nhung chua ro pham vi | `/abw-ask` |
| Muon refactor khi da ro pham vi | `/refactor` |
| Muon mo phien lam viec co kiem tra trang thai | `/abw-start` |
| Muon chot phien va handover | `/abw-wrap` |
| Muon cap nhat command surface local | `/abw-update` |

## Naming Policy

- Lenh thuoc public surface chinh cua he thong nen uu tien tien to `abw-`.
- Lenh `abw-*` dung cho router, grounding, session, evaluation, va nhung capability ABW-first.
- Ten lenh nen ngan, ro dong tu, va phan anh dung muc dich.
- Khong tu y rename lenh dang o public surface neu chua cap nhat installer, docs, va runtime registration cung luc.
- Workflow cu chi giu ten khong `abw-` neu do la compatibility path co gia tri thuc te hoac la verb rat tu nhien nhu `/plan`, `/code`, `/test`.
- Neu sau nay them alias, alias chi la lop phu; source of truth van la ten lenh chinh trong `workflows/` va installer.
