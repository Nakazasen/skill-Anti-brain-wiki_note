# Hybrid Anti-Brain-Wiki (Hybrid ABW)

> Version: 1.2.0
> Tagline: Bien AI tu trang thai tra loi nhanh thanh mot he thong tri thuc co grounding (neo du lieu thuc te), co bo nho, va co suy luan ranh gioi (bounded deliberation).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![TTC: Enabled](https://img.shields.io/badge/Test--Time%20Compute-Active-brightgreen)](https://github.com/Nakazasen/skill-Anti-brain-wiki_note)

Hybrid ABW la mot kien truc quan ly tri thuc va suy luan danh cho AI Agent. Muc tieu cua no la giai quyet 2 diem yeu pho bien nhat cua LLM:

- Thieu bo nho dai han dang tin cay.
- Tra loi nghe co ve hop ly (plausible) nhung khong co nguon goc ro rang (provenance).

---

## Tai sao lai la Hybrid ABW?

Thay vi de AI tra loi theo kieu "single-pass" (nghi mot lan roi noi luon), Hybrid ABW buoc mo hinh phai di qua mot khung lam viec ro rang va chat che:

1. doc context van hanh trong `.brain/`.
2. Tim tri thuc da duoc bien soan trong thu muc `wiki/`.
3. Neu can thiet, thuc hien grounding qua NotebookLM de lay chung cu.
4. Neu chua du bang chung, he thong bat buoc phai "log gap" (ghi nhan lo hong kien thuc) thay vi "fake success" (gia vo biet va bia ra cau tra loi).

## Kien truc 4 lop

- `raw/`: Nguon goc tai lieu tho, chua qua xu ly.
- `processed/`: Lop luu tru bang chung va nguon goc (provenance).
- `wiki/`: Tri thuc ben vung, tuan thu schema va co trich dan (citation) ro rang.
- `.brain/`: Trang thai van hanh, bao gom cac hang doi (queue), lich su lo hong kien thuc (gap log), va nhat ky suy luan (deliberation log).

\* *Luu y: NotebookLM duoc su dung nhu mot co may neo du lieu (deep grounding engine), hoan toan khong phai la "than thanh hoa" hay "oracle" tuyet doi.*

---

## He thong suy luan TTC (Test-Time Compute Deliberation Engine)

Hybrid ABW cung cap duong dan lenh `/abw-query-deep` danh cho cac cau hoi cuc kho nhu:

- Tong hop thong tin (Synthesis)
- So sanh (Comparison)
- Phan tich nguyen nhan goc re (Root Cause Analysis - RCA)
- danh doi trong thiet ke (Design tradeoff)
- Cac prompt co nhieu yeu to mau thuan (Contradiction-heavy prompts)

Luong TTC trai qua 5 buoc (passes):

1. **Decomposition:** Chia nho van de.
2. **Evidence Assembly:** Tap hop bang chung.
3. **Grounding:** Neo du lieu thuc te voi NotebookLM.
4. **Self-Critique:** Tu danh gia va phan bien noi bo.
5. **Repair or Exit:** Sua chua phan hoi hoac thoat vong lap.

Qua trinh suy luan (Deliberation) duoc chan lai an toan bang:

- Cong thoat (exit gate) dua tren muc diem danh gia (score).
- Cau dao tu dong ngat (circuit breaker) neu bi ket trong vong lap.
- Ngan sach truy van (query budget) danh cho NotebookLM de tiet kiem token/thoi gian.

---

## Fallback-first, Khong bao gio Fake Success

day la **nguyen tac quan trong nhat** cua repository nay.

Neu NotebookLM MCP chua san sang hoac gap loi:

- Lenh `/abw-ingest` chi duoc phep tao artifact o dang `draft` hoac `pending_grounding`.
- Lenh `/abw-query` se tra loi theo uu tien tu `wiki/` (wiki-first) va tao log gap neu thieu bang chung.
- Lenh `/abw-query-deep` van chay, nhung se chu dong bo qua Buoc 3 (Grounding) hoac dat budget = 0 de he thong khong treo cho.
- Lenh `/abw-lint` phai canh bao ro rang rang he thong dang trong trang thai fallback mode (thieu kha nang grounding sau).

**Hybrid ABW luon uu tien su trung thuc hon la nhung cau tra loi "nghe co ve thong minh nhung sao rong".**

---

## Quick Start (Bat dau nhanh)

### 1. Cai dat cac Installer / Workflows

Tren Windows:

```powershell
irm https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.ps1 | iex
```

Tren macOS / Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.sh | sh
```

### 2. Cai dat cau noi NotebookLM CLI

```bash
uv tool install notebooklm-mcp-cli
```

### 3. Khoi chay luong quy trinh chinh

```text
/abw-init
   -> /abw-setup
   -> /abw-status
   -> /abw-ingest
   -> /abw-ask 
        |-> (Tier 1) /abw-query
        |-> (Tier 2) /abw-query-deep
        |-> (Tier 3) /abw-bootstrap
   -> /abw-lint
```

### 4. Quy trinh lam viec khuyen nghi

1. Chep tai lieu tho vao `raw/`.
2. Chay `/abw-ingest`.
3. Thay vi phai "bat benh", ban hay su dung `/abw-ask` cho bat ky cau hoi nao. He thong Smart Router se tu dong phan loai va dinh tuyen cau hoi sang luong tu duy nhanh (Fast path), sau (Deep path), hoac khoi tao y tuong moi (Bootstrap path).
4. Thuong xuyen bao tri du an bang `/abw-lint`.

---

## Bang lenh he thong (Command Surface)

| Command | Muc dich |
|---------|----------|
| `/abw-init` | Khoi tao hoac sua chua cau truc thu muc Hybrid ABW. |
| `/abw-setup` | dang nhap va xac nhan ket noi NotebookLM MCP. |
| `/abw-status` | Kiem tra tinh trang MCP bridge va grounding queue. |
| `/abw-ingest` | Xu ly tai lieu raw de tao manifest va wiki artifacts. |
| `/abw-ask` | **Smart Router: Tu dong phan luong (dinh tuyen) sang query nhanh, suy luan sau hoac bootstrap y tuong moi!** |

**Cac nhanh phia sau Router:**
| Lenh noi bo / Mo rong | Muc dich |
|---------|----------|
| `/abw-query` | Tra loi nhanh dua vao duong dan wiki-first (Tier 1). |
| `/abw-query-deep` | Tra loi cho cac cau hoi kho, yeu cau TTC deliberation (Tier 2). |
| `/abw-lint` | Audit kiem tra chuan wiki, qua trinh grounding, mau thuan va muc do khoe cua TTC. |
| `/abw-bootstrap` | Kich hoat he thong suy luan y tuong moi (Tier 3), tao quan ly gia dinh (assumptions) & tap lenh xac nhan gia dinh (validation). |

---

## Tuong thich voi di san AWF (Legacy AWF compatibility)

Repository nay van giu mot so quy trinh/workflow tu AWF doi cu de tai cau truc tuong thich nguoc va phuc vu tham khao.

Tuy nhien, trong mot du an Hybrid ABW thuan tuy, bo lenh cot loi truc tiep luon bat dau voi tien to `/abw-*`. Xin dung nham lan repository nay nhu mot ban cai dat AWF thong thuong.

Neu ban muon co mot trai nghiem AWF ban tieu chuan theo phien ban goc (upstream), vui long cai dat AWF upstream rieng.

---

## Nguyen tac neo du lieu thuc te (Grounding Principle)

> "Mot cau tra loi co trich dan nguon van tot hon la mot cau doan mo chap va tu tin."
> 
> "Chu dong ghi log lai su thieu hut kien thuc (knowledge gap) van tot hon la tra loi sai su that (fake answer)."

Moi thay doi chinh trong nhom thu muc kien thuc chung `wiki/` phai luon luon truy xuat nguoc lai duoc ve:

- Nguon tai goc (raw source).
- Dong mo ta trong manifest (manifest line).
- Tinh trang xu ly du lieu (grounding outcome).
- Muc do tu tin cua du lieu (confidence status).

---

## Cac tai lieu quan trong khac

- `AGENTS.md`: Tom luoc kien truc he thong va cac bat bien (invariants) bat buoc phai co.
- Thu muc `skills/`: Chua cac logic thuc thi quan trong cua workflow.
- Thu muc `workflows/`: Chua cac lenh wrapper boc ngoai (chay truc tiep tren IDE).
- `wiki/_schemas/note.schema.md`: Khuon rap chuan (schema) quy dinh khung luu tru cua tung Note Kien thuc lau dai.

---

## dong gop (Contributing)

Hoan nghenh moi dong gop, dac biet trong cac linh vuc sau:

- Tinh chinh thong so gioi han (TTC tuning).
- Nang cao chat luong cho cau noi neo du lieu (grounding bridge).
- Tang do phu toan dien cho bo tu dong kiem tra `lint`.
- Nang cap phien ban tien hoa cho he thong `wiki schema`.
- Cai thien muc do trung thuc va tinh kha dung cua quy trinh du phong fallback.

Chi tiet co the xem trong file `CONTRIBUTING.md`.
