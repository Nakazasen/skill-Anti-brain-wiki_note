---
description: Huong dan lenh va sua de he thong Hybrid ABW
---

# WORKFLOW: /help

Ban la nguoi huong dan cua Hybrid ABW. Nhiem vu cua ban la giup nguoi dung dinh huong that nhanh. Be mat lenh hien duoc to chuc thanh 5 lane chuc nang va 2 entrypoint chinh.

---

## Bat dau nhanh

Neu ban sap bat dau lam viec, hay di tu mot trong hai entrypoint nay:

- **`/abw-ask`**: entrypoint mac dinh de lam viec. Dung khi ban co task, cau hoi, hoac yeu cau nhung chua biet nen vao lane nao.
- **`/abw-eval`**: entrypoint mac dinh de nghiem thu. Dung khi da co dau ra va ban muon audit, challenge, hoac chap nhan truoc khi coi la xong.

## Khi nao dung lenh nao?

- **Dung `/abw-ask`** khi ban co viec can lam hoac cau hoi cu the nhung chua chac lenh nao phu hop.
- **Dung `/abw-eval`** khi ban muon chay vong danh gia cho thay doi, workflow, tai lieu, hoac dau ra cua mo hinh.
- **Dung `/abw-start`** khi ban muon mo phien lam viec theo cach co kiem tra trang thai va grounding path.
- **Dung `/abw-wrap`** khi ban muon chot phien, chuan bi handover, va nhac phan can ingest hoac nghiem thu.
- **Dung `/next`** khi ban dang o giua du an va can goi y buoc tiep theo dua tren trang thai hien tai.
- **Dung `/help`** khi ban can hieu mo hinh he thong, danh sach lenh, hoac mental model 5 lane.
- **Dung `/abw-update`** khi ban muon keo ban moi nhat cua command surface ABW vao Gemini runtime local.

## Muon lam X thi go gi dau tien?

| Truong hop | Lenh go dau tien |
|---|---|
| Khong biet nen bat dau tu dau | `/abw-ask` |
| Co cau hoi du an nhung chua ro nen tra cuu hay brainstorm | `/abw-ask` |
| Can tra cuu nhanh mot fact da co trong wiki | `/abw-query` |
| Can phan tich sau, so sanh, RCA, tradeoff | `/abw-query-deep` |
| Du an con greenfield, chua co raw/wiki | `/abw-bootstrap` |
| Muon chot y tuong, scope, hoac MVP | `/brainstorm` |
| Muon dung nen tri thuc tu tai lieu nguon | `/abw-ingest` |
| Muon dong goi tri thuc cho NotebookLM | `/abw-pack` |
| Muon dry-run hoac sync package da duyet len NotebookLM | `/abw-sync` |
| Muon kiem tra suc khoe wiki, grounding, manifest | `/abw-lint` |
| Muon kiem tra MCP hoac trang thai hang doi | `/abw-status` |
| Muon lap ke hoach tinh nang hoac chia task | `/plan` |
| Muon thiet ke ky thuat hoac DB | `/design` |
| Muon dung mockup UI/UX hoac dac ta man hinh | `/visualize` |
| Muon bat tay vao code | `/code` |
| Muon chay app cuc bo | `/run` |
| Muon sua bug | `/debug` |
| Muon kiem tra bang test | `/test` |
| Muon trien khai len moi truong dich | `/deploy` |
| Muon refactor legacy code nhung chua ro pham vi | `/abw-ask` |
| Muon refactor khi da ro pham vi | `/refactor` |
| Muon review code hoac hien trang truoc khi audit nang hon | `/abw-review` |
| Muon audit thay doi hoac artifact | `/abw-audit` |
| Muon audit lai chinh bao cao audit | `/abw-meta-audit` |
| Muon quay lai trang thai an toan sau mot thay doi sai | `/abw-rollback` |
| Muon chot pass/fail cuoi cung | `/abw-accept` |
| Muon chay toan bo chuoi nghiem thu | `/abw-eval` |
| Muon mo phien lam viec co kiem tra trang thai | `/abw-start` |
| Muon luu tien do va chuan bi handover | `/save-brain` |
| Muon khoi phuc boi canh tu phien truoc | `/recap` |
| Muon biet buoc tiep theo nen lam gi | `/next` |
| Muon chot phien va wrap lai thay doi | `/abw-wrap` |
| Muon cap nhat command surface ABW len ban moi nhat | `/abw-update` |

---

## Mo hinh lenh (5 lane)

### 1. Kham pha va tu duy

Dung nhom nay khi can kham pha y tuong hoac hoi tren tri thuc hien co.

- `/abw-ask` : Entry chinh, tu dinh tuyen theo intent
- `/abw-query` : Tra cuu nhanh tren wiki
- `/abw-query-deep` : Suy luan sau va tong hop nhieu lop
- `/abw-bootstrap` : Tu duy cho bai toan greenfield
- `/brainstorm` : Chot brief san pham va pham vi MVP

### 2. Dung nen tri thuc

Dung nhom nay de xay va duy tri nen tri thuc co grounding.

- `/abw-init` : Khoi tao cau truc ABW
- `/abw-setup` : Cau hinh NotebookLM MCP
- `/abw-status` : Kiem tra MCP va hang doi
- `/abw-ingest` : Xu ly raw thanh wiki
- `/abw-pack` : Dong goi tri thuc thanh package gon cho NotebookLM
- `/abw-sync` : Dry-run hoac sync package da duyet len NotebookLM
- `/abw-lint` : Audit suc khoe wiki va manifest

### 3. Trien khai san pham

Dung nhom nay de bien tri thuc thanh phan mem chay duoc.

Luong delivery chinh:

- `/plan` : Lap ke hoach thuc thi tinh nang
- `/design` : Thiet ke ky thuat va co so du lieu
- `/visualize` : Dung mockup UI/UX va dac ta man hinh
- `/code` : Cai dat tinh nang
- `/run` : Chay ung dung cuc bo
- `/debug` : Sua loi co he thong
- `/test` : Chay test va kiem tra chat luong
- `/deploy` : Trien khai len moi truong dich

Workflow ho tro trong delivery:

- `/refactor` : Don code an toan sau khi da hieu ro hanh vi
- `/audit` : Ra soat san pham, code, hoac bao mat trong vong delivery

### 4. Phien lam viec va ghi nho

Dung nhom nay de quan ly phien lam viec va khoi phuc boi canh.

- `/abw-start` : Mo phien lam viec va kiem tra trang thai he thong
- `/save-brain` : Luu tien do va chuan bi handover
- `/recap` : Khoi phuc boi canh tu phien truoc
- `/next` : Goi y buoc tiep theo mot cach thong minh
- `/abw-wrap` : Chot phien, tong ket, va chuan bi quay lai

### 5. Danh gia va nghiem thu

Dung nhom nay de danh gia dau ra, chat van lap luan, va quyet dinh co nen chap nhan thay doi hay khong.

- `/abw-review` : Review code, thay doi, hoac hien trang du an
- `/abw-audit` : Tu audit workflow, tai lieu, thay doi, hoac dau ra
- `/abw-meta-audit` : Audit lai chinh bao cao audit
- `/abw-rollback` : Quay ve trang thai an toan sau thay doi loi
- `/abw-accept` : Chay cong nghiem thu cuoi cung
- `/abw-eval` : Chay toan bo chuoi evaluation tu dau den cuoi

### Utility

- `/help` : Ban do he thong va decision table
- `/abw-update` : Cap nhat command surface ABW vao Gemini runtime local

---

## Vi du phan hoi

### User: "Toi nen bat dau tu dau?"

```text
1. Chay /abw-init de khoi tao workspace.
2. Chay /abw-setup de ket noi NotebookLM.
3. Neu du an con mo ho, dung /brainstorm de chot brief.
4. Hoac don gian dung /abw-ask va noi: "Toi muon bat dau du an X".
```

### User: "Lam sao de viet code cho tinh nang nay?"

```text
1. Dam bao da co tri thuc ve tinh nang do trong wiki, hoac dung /abw-ask de kiem tra.
2. Dung /plan de len cau truc file va task.
3. Chay /code de thuc thi ke hoach.
```
