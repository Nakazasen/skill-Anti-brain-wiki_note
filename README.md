# Hybrid Anti-Brain-Wiki (Hybrid ABW)

> Version: 1.1.1
> Tagline: Bien AI tu tra loi nhanh thanh he thong tri thuc co grounding, co bo nho, va co bounded deliberation.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![TTC: Enabled](https://img.shields.io/badge/Test--Time%20Compute-Active-brightgreen)](https://github.com/Nakazasen/skill-Anti-brain-wiki_note)

Hybrid ABW la mot kien truc quan ly tri thuc va suy luan cho AI agent. Muc tieu cua no la giai quyet 2 diem yeu pho bien cua LLM:

- thieu bo nho dai han dang tin cay
- tra loi nghe hop ly nhung khong co provenance ro rang

---

## Tai sao la Hybrid ABW?

Thay vi de model tra loi theo kieu single-pass, Hybrid ABW buoc model di qua mot khung lam viec ro rang:

1. doc context van hanh trong `.brain/`
2. tim tri thuc da bien soan trong `wiki/`
3. neu can thi grounding qua NotebookLM
4. neu chua du bang chung thi log gap thay vi fake success

## Kien truc 4 lop

- `raw/`: nguon goc chua xu ly
- `processed/`: lop bang chung va provenance
- `wiki/`: tri thuc ben vung, co schema va citation
- `.brain/`: trang thai van hanh, queue, gap log, deliberation log

NotebookLM duoc dung nhu deep grounding engine, khong phai "oracle" tuyet doi.

---

## TTC Deliberation Engine

Hybrid ABW cung cap `/abw-query-deep` cho cac cau hoi kho nhu:

- synthesis
- comparison
- RCA
- design tradeoff
- contradiction-heavy prompts

Luong TTC co 5 pass:

1. Decomposition
2. Evidence Assembly
3. Grounding
4. Self-Critique
5. Repair or Exit

Deliberation duoc chan bang:

- exit gate theo score
- circuit breaker
- query budget cho NotebookLM

---

## Fallback-first, khong fake success

Day la nguyen tac quan trong nhat cua repo nay.

Neu NotebookLM MCP chua san sang:

- `/abw-ingest` chi duoc tao `draft` hoac `pending_grounding`
- `/abw-query` tra loi theo wiki-first va log gap neu thieu bang chung
- `/abw-query-deep` van chay, nhung bo Pass 3 hoac dat budget = 0
- `/abw-lint` phai bao cao ro he thong dang trong fallback mode

Hybrid ABW uu tien trung thuc hon la nghe co ve thong minh.

---

## Quick Start

### 1. Cai installer

Windows:

```powershell
irm https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.ps1 | iex
```

macOS / Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.sh | sh
```

### 2. Cai NotebookLM CLI

```bash
uv tool install notebooklm-mcp-cli
```

### 3. Chay flow chinh

```text
/abw-init
/abw-setup
/abw-ingest
/abw-query
/abw-query-deep
/abw-lint
```

### 4. Quy trinh khuyen nghi

1. Tha tai lieu vao `raw/`
2. Chay `/abw-ingest`
3. Hoi nhanh bang `/abw-query`
4. Hoi kho bang `/abw-query-deep`
5. Bao tri bang `/abw-lint`

---

## Command Surface chinh

| Command | Muc dich |
|---------|----------|
| `/abw-init` | Khoi tao hoac repair cau truc Hybrid ABW |
| `/abw-setup` | Dang nhap va xac nhan NotebookLM MCP |
| `/abw-status` | Kiem tra MCP bridge va grounding queue |
| `/abw-ingest` | Xu ly raw source thanh manifest va wiki artifacts |
| `/abw-query` | Query nhanh theo wiki-first path |
| `/abw-query-deep` | Query kho voi TTC deliberation |
| `/abw-lint` | Audit wiki, grounding, contradictions, TTC health |

---

## Legacy AWF compatibility

Repo nay van giu mot so workflow AWF cu de compatibility va tham khao.

Nhung trong repo public nay, command surface chinh la `/abw-*`.
Khong nen doc repo nay nhu mot AWF installer thong thuong.

Neu ban muon full upstream AWF experience, hay cai upstream AWF rieng.

---

## Grounding principle

> Mot cau tra loi co citation tot hon mot cau tra loi tu tin.
> Mot knowledge gap duoc log tot hon mot fake answer.

Moi thay doi chinh trong `wiki/` nen truy nguoc duoc ve:

- raw source
- manifest line
- grounding outcome
- confidence status

---

## Tai lieu quan trong

- `AGENTS.md`: system architecture va invariants
- `skills/`: logic thuc thi cua ABW workflows
- `workflows/`: command wrappers cho IDE surface
- `wiki/_schemas/note.schema.md`: schema cho persistent knowledge

---

## Dong gop

Dong gop duoc hoan nghenh, nhat la o cac huong:

- TTC tuning
- better grounding bridges
- lint checks
- wiki schema evolution
- fallback honesty va reliability

Xem them `CONTRIBUTING.md`.