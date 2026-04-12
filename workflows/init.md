---
description: Khoi tao du an moi (legacy AWF compatibility workflow)
---
> LEGACY COMPATIBILITY WORKFLOW
> This file is kept for older AWF-style flows.
> Public ABW-first surface: `/abw-init`, `/abw-setup`, `/abw-ingest`, `/abw-query`, `/abw-query-deep`, `/abw-lint`.

# WORKFLOW: /init - Khoi tao du an

**Vai tro:** Project Initializer
**Muc tieu:** Thu thap y tuong va tao workspace co ban. Khong cai packages, khong setup database.**

**Ngon ngu:** Luon tra loi bang tieng Viet.**

---

## Flow Position

```
[/init] 驕ｶ鄙ｫ繝ｻB髯ゑｽｯ繝ｻ・ｰN 繝ｻ繝ｻ・､蠎ｷG 騾ｶ・ｻ郢晢ｽｻ繝ｻ繝ｻ謦慕ｹ晢ｽｻ
   驕ｶ鄙ｫ繝ｻ
/brainstorm (n髯ゑｽｯ繝ｻ・ｿu ch繝ｻ繝ｻ・ｽ・ｰa r繝ｻ繝ｻ・ｽ・ｵ 繝ｻ繝ｻ・ｽ・ｽ t繝ｻ繝ｻ・ｽ・ｰ騾ｶ・ｻ隹ｿ・､g)
   驕ｶ鄙ｫ繝ｻ
/plan (l繝ｻ繝ｻ・ｽ・ｪn k髯ゑｽｯ繝ｻ・ｿ ho髯ゑｽｯ繝ｻ・｡ch features)
   驕ｶ鄙ｫ繝ｻ
/design (thi髯ゑｽｯ繝ｻ・ｿt k髯ゑｽｯ繝ｻ・ｿ k騾ｶ・ｻ繝ｻ・ｹ thu髯ゑｽｯ繝ｻ・ｭt)
   驕ｶ鄙ｫ繝ｻ
/code (vi髯ゑｽｯ繝ｻ・ｿt code)
```

---

## Stage 1: Capture Vision (H騾ｶ・ｻ鬲・・NG髯ゑｽｯ繝ｻ・ｮN G騾ｶ・ｻ陷ｷ繝ｻ

### 1.1. T繝ｻ繝ｻ・ｽ・ｪn d騾ｶ・ｻ繝ｻ・ｱ 繝ｻ繝ｻ・ｽ・｡n
"T繝ｻ繝ｻ・ｽ・ｪn d騾ｶ・ｻ繝ｻ・ｱ 繝ｻ繝ｻ・ｽ・｡n l繝ｻ繝ｻ・｣・ｰ g繝ｻ繝ｻ・ｽ・ｬ? (VD: my-coffee-app)"

### 1.2. M繝ｻ繝ｻ・ｽ・ｴ t髯ゑｽｯ繝ｻ・｣ 1 c繝ｻ繝ｻ・ｽ・｢u
"M繝ｻ繝ｻ・ｽ・ｴ t髯ゑｽｯ繝ｻ・｣ ng髯ゑｽｯ繝ｻ・ｯn g騾ｶ・ｻ髢ｧ・ｱ app l繝ｻ繝ｻ・｣・ｰm g繝ｻ繝ｻ・ｽ・ｬ? (1-2 c繝ｻ繝ｻ・ｽ・｢u)"

### 1.3. V騾ｶ・ｻ郢晢ｽｻtr繝ｻ繝ｻ・ｽ・ｭ
"T髯ゑｽｯ繝ｻ・｡o 騾ｶ・ｻ郢晢ｽｻth繝ｻ繝ｻ・ｽ・ｰ m騾ｶ・ｻ繝ｻ・･c hi騾ｶ・ｻ郢ｻ・ｻ t髯ゑｽｯ繝ｻ・｡i hay ch騾ｶ・ｻ郢晢ｽｻkh繝ｻ繝ｻ・ｽ・｡c?"

**XONG. Kh繝ｻ繝ｻ・ｽ・ｴng h騾ｶ・ｻ雎ｺ繝ｻth繝ｻ繝ｻ・ｽ・ｪm.**

---

## Stage 2: T髯ゑｽｯ繝ｻ・｡o Workspace (CH騾ｶ・ｻ郢晢ｽｻT髯ゑｽｯ繝ｻ・ｰO FOLDER)

Ch騾ｶ・ｻ郢晢ｽｻt髯ゑｽｯ繝ｻ・｡o c髯ゑｽｯ繝ｻ・･u tr繝ｻ繝ｻ・ｽ・ｺc folder c繝ｻ繝ｻ・ｽ・｡ b髯ゑｽｯ繝ｻ・｣n:

```
{project-name}/
髫ｨ荵励飴隶鯉ｽｳ髫ｨ貂可 .brain/
髫ｨ荳翫・  髫ｨ荵怜繭隶鯉ｽｳ髫ｨ貂可 brain.json      # Project context (empty template)
髫ｨ荵励飴隶鯉ｽｳ髫ｨ貂可 docs/
髫ｨ荳翫・  髫ｨ荵怜繭隶鯉ｽｳ髫ｨ貂可 ideas.md        # Ghi 繝ｻ繝ｻ・ｽ・ｽ t繝ｻ繝ｻ・ｽ・ｰ騾ｶ・ｻ隹ｿ・､g
髫ｨ荵怜繭隶鯉ｽｳ髫ｨ貂可 README.md           # T繝ｻ繝ｻ・ｽ・ｪn + m繝ｻ繝ｻ・ｽ・ｴ t髯ゑｽｯ繝ｻ・｣
```

### brain.json template:
```json
{
  "project": {
    "name": "{project-name}",
    "description": "{m繝ｻ繝ｻ・ｽ・ｴ t髯ゑｽｯ繝ｻ・｣}",
    "created_at": "{timestamp}"
  },
  "tech_stack": [],
  "features": [],
  "decisions": []
}
```

### README.md template:
```markdown
# {Project Name}

{M繝ｻ繝ｻ・ｽ・ｴ t髯ゑｽｯ繝ｻ・｣ 1 c繝ｻ繝ｻ・ｽ・｢u}

## Status: ・滓ｧｫ諠｡ Planning

D騾ｶ・ｻ繝ｻ・ｱ 繝ｻ繝ｻ・ｽ・｡n 繝ｻ繝ｻ魄ｪng trong giai 繝ｻ繝ｻ譖咎凾・ｯ繝ｻ・｡n l繝ｻ繝ｻ・ｽ・ｪn 繝ｻ繝ｻ・ｽ・ｽ t繝ｻ繝ｻ・ｽ・ｰ騾ｶ・ｻ隹ｿ・､g.

## Next Steps

1. G繝ｻ繝ｻ・ｽ・ｵ `/brainstorm` 繝ｻ繝ｻ・ｻ蟷｢・ｽ・ｻ郢晢ｽｻexplore 繝ｻ繝ｻ・ｽ・ｽ t繝ｻ繝ｻ・ｽ・ｰ騾ｶ・ｻ隹ｿ・､g
2. Ho髯ゑｽｯ繝ｻ・ｷc `/plan` n髯ゑｽｯ繝ｻ・ｿu 繝ｻ繝ｻ・ｦ・･繝ｻ・｣ r繝ｻ繝ｻ・ｽ・ｵ mu騾ｶ・ｻ陷托ｽｵ l繝ｻ繝ｻ・｣・ｰm g繝ｻ繝ｻ・ｽ・ｬ
```

---

## Stage 3: X繝ｻ繝ｻ・ｽ・｡c nh髯ゑｽｯ繝ｻ・ｭn & H繝ｻ繝ｻ・ｽ・ｰ騾ｶ・ｻ陞ｫ・ｾg d髯ゑｽｯ繝ｻ・ｫn

```
髫ｨ・ｨ郢晢ｽｻ繝ｻ繝ｻ謦輔・・｣ t髯ゑｽｯ繝ｻ・｡o workspace cho "{project-name}"!

・滓ｧｫ繝ｻ V騾ｶ・ｻ郢晢ｽｻtr繝ｻ繝ｻ・ｽ・ｭ: {path}

・滓ｧｫ蜍 B繝ｻ繝ｻ・ｽ・ｯ騾ｶ・ｻ陷･・ｾ TI髯ゑｽｯ繝ｻ・ｾP THEO:

Ch騾ｶ・ｻ髢ｧ・ｱ 1 trong 2:

1郢晢ｽｻ鬮ｷ菴ｩ繝ｻ/brainstorm - N髯ゑｽｯ繝ｻ・ｿu ch繝ｻ繝ｻ・ｽ・ｰa r繝ｻ繝ｻ・ｽ・ｵ mu騾ｶ・ｻ陷托ｽｵ l繝ｻ繝ｻ・｣・ｰm g繝ｻ繝ｻ・ｽ・ｬ, c髯ゑｽｯ繝ｻ・ｧn explore 繝ｻ繝ｻ・ｽ・ｽ t繝ｻ繝ｻ・ｽ・ｰ騾ｶ・ｻ隹ｿ・､g
2郢晢ｽｻ鬮ｷ菴ｩ繝ｻ/plan - N髯ゑｽｯ繝ｻ・ｿu 繝ｻ繝ｻ・ｦ・･繝ｻ・｣ bi髯ゑｽｯ繝ｻ・ｿt r繝ｻ繝ｻ・ｽ・ｵ features c髯ゑｽｯ繝ｻ・ｧn l繝ｻ繝ｻ・｣・ｰm

・滓ｧｫ・ｺ繝ｻTip: Newbie n繝ｻ繝ｻ・ｽ・ｪn ch騾ｶ・ｻ髢ｧ・ｱ /brainstorm tr繝ｻ繝ｻ・ｽ・ｰ騾ｶ・ｻ髮厄ｽｩ!
```

---

## QUAN TR騾ｶ・ｻ陷ｷ蟋・- KH繝ｻ繝ｻ・ｹ・ｴG L繝ｻﾎｴﾂM

髫ｨ・ｶ郢晢ｽｻKH繝ｻ繝ｻ・ｹ・ｴG install packages (繝ｻ繝ｻ・ｻ蟷｢・ｽ・ｻ郢晢ｽｻ/code l繝ｻ繝ｻ・｣・ｰm)
髫ｨ・ｶ郢晢ｽｻKH繝ｻ繝ｻ・ｹ・ｴG setup database (繝ｻ繝ｻ・ｻ蟷｢・ｽ・ｻ郢晢ｽｻ/design l繝ｻ繝ｻ・｣・ｰm)
髫ｨ・ｶ郢晢ｽｻKH繝ｻ繝ｻ・ｹ・ｴG t髯ゑｽｯ繝ｻ・｡o code files (繝ｻ繝ｻ・ｻ蟷｢・ｽ・ｻ郢晢ｽｻ/code l繝ｻ繝ｻ・｣・ｰm)
髫ｨ・ｶ郢晢ｽｻKH繝ｻ繝ｻ・ｹ・ｴG ch髯ゑｽｯ繝ｻ・｡y npm/yarn/pnpm
髫ｨ・ｶ郢晢ｽｻKH繝ｻ繝ｻ・ｹ・ｴG h騾ｶ・ｻ雎ｺ繝ｻv騾ｶ・ｻ郢晢ｽｻtech stack (AI s髯ゑｽｯ繝ｻ・ｽ t騾ｶ・ｻ繝ｻ・ｱ quy髯ゑｽｯ繝ｻ・ｿt sau)

---

## First-time User

N髯ゑｽｯ繝ｻ・ｿu ch繝ｻ繝ｻ・ｽ・ｰa c繝ｻ繝ｻ・ｽ・ｳ `.brain/preferences.json`:

```
・滓ｨ抵ｽｪ繝ｻCh繝ｻ繝ｻ・｣・ｰo m騾ｶ・ｻ繝ｻ・ｫng b髯ゑｽｯ繝ｻ・｡n 繝ｻ繝ｻ・ｻ蟷｢・ｽ・ｺ繝ｻ・ｿn v騾ｶ・ｻ陞ｫ繝ｻAWF!

繝ｻ繝ｻ謦輔・・｢y l繝ｻ繝ｻ・｣・ｰ l髯ゑｽｯ繝ｻ・ｧn 繝ｻ繝ｻ・ｻ蟷｢・ｽ・ｺ繝ｻ・ｧu d繝ｻ繝ｻ・ｽ・ｹng. B髯ゑｽｯ繝ｻ・｡n mu騾ｶ・ｻ陷托ｽｵ:
1郢晢ｽｻ鬮ｷ菴ｩ繝ｻD繝ｻ繝ｻ・ｽ・ｹng m髯ゑｽｯ繝ｻ・ｷc 繝ｻ繝ｻ・ｻ蟷｢・ｽ・ｻ隴夲ｽｵh (Recommended)
2郢晢ｽｻ鬮ｷ菴ｩ繝ｻT繝ｻ繝ｻ・ｽ・ｹy ch騾ｶ・ｻ驕ｨ蛻ｺ (/customize)
```

---

## Error Handling

### Folder 繝ｻ繝ｻ・ｦ・･繝ｻ・｣ t騾ｶ・ｻ雋ゑｽ｡ t髯ゑｽｯ繝ｻ・｡i:
```
髫ｨ讖ｸ・｣・ｰ郢晢ｽｻ郢晢ｽｻFolder "{name}" 繝ｻ繝ｻ・ｦ・･繝ｻ・｣ c繝ｻ繝ｻ・ｽ・ｳ r騾ｶ・ｻ陞ｯ・ｬ.
1郢晢ｽｻ鬮ｷ菴ｩ繝ｻD繝ｻ繝ｻ・ｽ・ｹng folder n繝ｻ繝ｻ・｣・ｰy (c繝ｻ繝ｻ・ｽ・ｳ th騾ｶ・ｻ郢晢ｽｻghi 繝ｻ繝ｻ・ｦ・･繝ｻ・ｨ)
2郢晢ｽｻ鬮ｷ菴ｩ繝ｻ繝ｻ繝ｻ螯帙・・ｻ陷ｩ繝ｻt繝ｻ繝ｻ・ｽ・ｪn kh繝ｻ繝ｻ・ｽ・｡c
```

### Kh繝ｻ繝ｻ・ｽ・ｴng c繝ｻ繝ｻ・ｽ・ｳ quy騾ｶ・ｻ繝ｻ・ｽ t髯ゑｽｯ繝ｻ・｡o folder:
```
髫ｨ・ｶ郢晢ｽｻKh繝ｻ繝ｻ・ｽ・ｴng t髯ゑｽｯ繝ｻ・｡o 繝ｻ繝ｻ豌医・・ｰ騾ｶ・ｻ繝ｻ・｣c folder. Ki騾ｶ・ｻ郢昴・tra quy騾ｶ・ｻ繝ｻ・ｽ write nh繝ｻ繝ｻ・ｽ・ｩ!
```
