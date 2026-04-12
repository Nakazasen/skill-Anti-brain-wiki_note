---
description: Tong quan va ban giao du an (legacy AWF compatibility workflow)
---
> LEGACY COMPATIBILITY WORKFLOW
> This file is kept for older AWF-style flows.
> Public ABW-first surface: `/abw-init`, `/abw-setup`, `/abw-ingest`, `/abw-query`, `/abw-query-deep`, `/abw-lint`.


# WORKFLOW: /review - The Project Scanner

B陂ｯ・｡n l・・｣ｰ **Antigravity Project Analyst**. Nhi逶ｻ纃・v逶ｻ・･: Qu・・ｽｩt to・・｣ｰn b逶ｻ繝ｻd逶ｻ・ｱ ・・ｽ｡n v・・｣ｰ t陂ｯ・｡o b・・ｽ｡o c・・ｽ｡o d逶ｻ繝ｻhi逶ｻ繝・・・ｻ幢ｽｻ繝ｻ
1. B陂ｯ・｡n (ho陂ｯ・ｷc ng・・ｽｰ逶ｻ諡ｱ kh・・ｽ｡c) c・・ｽｳ th逶ｻ繝ｻti陂ｯ・ｿp nh陂ｯ・ｭn d逶ｻ・ｱ ・・ｽ｡n nhanh ch・・ｽｳng
2. ・・撕・｡nh gi・・ｽ｡ "s逶ｻ・ｩc kh逶ｻ驫・ code hi逶ｻ繻ｻ t陂ｯ・｡i
3. L・・ｽｪn k陂ｯ・ｿ ho陂ｯ・｡ch n・・ｽ｢ng c陂ｯ・･p

---

## 﨟櫁ｭ・Non-Tech Mode (v4.0)

**・・妛・ｻ逧・preferences.json ・・ｻ幢ｽｻ繝ｻ・・ｨｴ逶ｻ縲・ch逶ｻ遨刺 ng・・ｽｴn ng逶ｻ・ｯ:**

```
if technical_level == "newbie":
    遶翫・陂ｯ・ｨn chi ti陂ｯ・ｿt k逶ｻ・ｹ thu陂ｯ・ｭt (dependencies, architecture)
    遶翫・Ch逶ｻ繝ｻhi逶ｻ繝・th逶ｻ繝ｻ "App l・・｣ｰm g・・ｽｬ", "C・・ｽ｡ch ch陂ｯ・｡y", "C・・ｽ｡ch s逶ｻ・ｭa ・・氈・｡n gi陂ｯ・｣n"
    遶翫・D・・ｽｹng ng・・ｽｴn ng逶ｻ・ｯ ・・ｻ幢ｽｻ諡ｱ th・・ｽｰ逶ｻ諡ｵg
```

### B・・ｽ｡o c・・ｽ｡o cho newbie:
```
隨ｶ繝ｻ・・妛・ｻ・ｪNG: "Architecture: Next.js App Router v逶ｻ螫・Server Components..."
隨ｨ繝ｻN・・汗:  "﨟槫ｰ・App qu陂ｯ・｣n l・・ｽｽ chi ti・・ｽｪu - Gi・・ｽｺp theo d・・ｽｵi ti逶ｻ・ｽ ra v・・｣ｰo h・・｣ｰng ng・・｣ｰy"
```

---

## Giai ・・曙陂ｯ・｡n 1: H逶ｻ豺・M逶ｻ・･c ・・撕・ｭch

```
"﨟槫翁 Anh mu逶ｻ蜑ｵ review d逶ｻ・ｱ ・・ｽ｡n ・・ｻ幢ｽｻ繝ｻl・・｣ｰm g・・ｽｬ?

1繝ｻ髷佩・**T逶ｻ・ｱ xem l陂ｯ・｡i** - Qu・・ｽｪn m陂ｯ・･t m・・ｽｬnh ・・鮪ng l・・｣ｰm g・・ｽｬ
2繝ｻ髷佩・**B・・｣ｰn giao** - Chuy逶ｻ繝・cho ng・・ｽｰ逶ｻ諡ｱ kh・・ｽ｡c ti陂ｯ・ｿp nh陂ｯ・ｭn  
3繝ｻ髷佩・**・・撕・｡nh gi・・ｽ｡** - Xem code c・・ｽｳ v陂ｯ・･n ・・ｻ幢ｽｻ繝ｻg・・ｽｬ kh・・ｽｴng
4繝ｻ髷佩・**L・・ｽｪn k陂ｯ・ｿ ho陂ｯ・｡ch n・・ｽ｢ng c陂ｯ・･p** - Chu陂ｯ・ｩn b逶ｻ繝ｻth・・ｽｪm t・・ｽｭnh n・・ワg m逶ｻ螫・

(Ho陂ｯ・ｷc n・・ｽｳi tr逶ｻ・ｱc ti陂ｯ・ｿp m逶ｻ・･c ・・ｦ･・ｭch c逶ｻ・ｧa anh)"
```

---

## Giai ・・曙陂ｯ・｡n 2: Qu・・ｽｩt D逶ｻ・ｱ ・・ｼｽ T逶ｻ・ｱ ・・妛・ｻ蜀｢g

AI t逶ｻ・ｱ ・・ｻ幢ｽｻ蜀｢g th逶ｻ・ｱc hi逶ｻ繻ｻ:

### 2.1. ・・妛・ｻ逧・c陂ｯ・･u tr・・ｽｺc th・・ｽｰ m逶ｻ・･c
```bash
# Li逶ｻ繽・k・・ｽｪ c・・ｽ｡c file/folder ch・・ｽｭnh
# ・・妛・ｺ・ｿm s逶ｻ繝ｻfile code
# Ph・・ｽ｡t hi逶ｻ繻ｻ framework ・・鮪ng d・・ｽｹng
```

### 2.2. ・・妛・ｻ逧・package.json (n陂ｯ・ｿu c・・ｽｳ)
```bash
# X・・ｽ｡c ・・ｻ幢ｽｻ譚ｵh tech stack
# Version c・・ｽ｡c th・・ｽｰ vi逶ｻ繻ｻ
# Scripts c・・ｽｳ s陂ｯ・ｵn
```

### 2.3. ・・妛・ｻ逧・README, docs/ (n陂ｯ・ｿu c・・ｽｳ)
```bash
# M・・ｽｴ t陂ｯ・｣ d逶ｻ・ｱ ・・ｽ｡n
# H・・ｽｰ逶ｻ螫ｾg d陂ｯ・ｫn c・・｣ｰi ・・ｻ幢ｽｺ・ｷt
```

### 2.4. ・・妛・ｻ逧・.brain/ (n陂ｯ・ｿu c・・ｽｳ)
```bash
# Session g陂ｯ・ｧn nh陂ｯ・･t
# Context ・・鮪ng l・・｣ｰm vi逶ｻ繻・
```

---

## Giai ・・曙陂ｯ・｡n 3: T陂ｯ・｡o B・・ｽ｡o C・・ｽ｡o

### 3.1. B・・ｽ｡o c・・ｽ｡o cho m逶ｻ・･c ・・ｦ･・ｭch "T逶ｻ・ｱ xem l陂ｯ・｡i" ho陂ｯ・ｷc "B・・｣ｰn giao"

```markdown
# 﨟樊兜 B・・ｼｾ C・・ｼｾ D逶ｻ・ｰ ・δｨ: [T・・ｽｪn]

## 﨟櫁ｭ・App n・・｣ｰy l・・｣ｰm g・・ｽｬ?
[M・・ｽｴ t陂ｯ・｣ 2-3 c・・ｽ｢u, ng・・ｽｴn ng逶ｻ・ｯ ・・ｻ幢ｽｻ諡ｱ th・・ｽｰ逶ｻ諡ｵg]

## 﨟槫・ C陂ｯ・･u tr・・ｽｺc ch・・ｽｭnh
```
[Folder tree ・・氈・｡n gi陂ｯ・｣n, ch逶ｻ繝ｻc・・ｽ｡c folder quan tr逶ｻ閧ｱg]
```

## 﨟槫ｱ上・繝ｻC・・ｽｴng ngh逶ｻ繝ｻs逶ｻ・ｭ d逶ｻ・･ng
| Th・・｣ｰnh ph陂ｯ・ｧn | C・・ｽｴng ngh逶ｻ繝ｻ|
|------------|-----------|
| Framework | [Next.js 14] |
| Giao di逶ｻ繻ｻ | [TailwindCSS] |
| Database | [Supabase] |

## 﨟槫勠 C・・ｽ｡ch ch陂ｯ・｡y
```bash
npm install
npm run dev
# M逶ｻ繝ｻhttp://localhost:3000
```

## 﨟樊｡・・・ｴｳng l・・｣ｰm d逶ｻ繝ｻg・・ｽｬ?
[・・妛・ｻ逧・t逶ｻ・ｫ session.json n陂ｯ・ｿu c・・ｽｳ]
- T・・ｽｭnh n・・ワg: [...]
- Task ti陂ｯ・ｿp theo: [...]

## 﨟樒ｵｱ C・・ｽ｡c file quan tr逶ｻ閧ｱg c陂ｯ・ｧn bi陂ｯ・ｿt
| File | Ch逶ｻ・ｩc n・・ワg |
|------|-----------|
| `app/page.tsx` | Trang ch逶ｻ・ｧ |
| `components/...` | C・・ｽ｡c component UI |
| `lib/...` | Logic x逶ｻ・ｭ l・・ｽｽ |

## 隨橸｣ｰ繝ｻ繝ｻL・・ｽｰu ・・ｽｽ khi ti陂ｯ・ｿp nh陂ｯ・ｭn
- [・・ｲ逶ｻ縲・1]
- [・・ｲ逶ｻ縲・2]
```

### 3.2. B・・ｽ｡o c・・ｽ｡o cho m逶ｻ・･c ・・ｦ･・ｭch "・・撕・｡nh gi・・ｽ｡"

```markdown
# 﨟槫罰 ・・撕ﾂｨH GI・・・S逶ｻ・ｨC KH逶ｻ谿ｺ CODE: [T・・ｽｪn]

## 﨟樊兜 T逶ｻ雋ｧg quan
| Ch逶ｻ繝ｻs逶ｻ繝ｻ| K陂ｯ・ｿt qu陂ｯ・｣ | ・・撕・｡nh gi・・ｽ｡ |
|--------|---------|----------|
| Build | 隨ｨ繝ｻTh・・｣ｰnh c・・ｽｴng / 隨ｶ繝ｻL逶ｻ謫・| [T逶ｻ螂・C陂ｯ・ｧn s逶ｻ・ｭa] |
| Lint | X warnings | [T逶ｻ螂・C陂ｯ・ｧn c陂ｯ・｣i thi逶ｻ繻ｻ] |
| TypeScript | X errors | [T逶ｻ螂・C陂ｯ・ｧn s逶ｻ・ｭa] |

## 隨ｨ繝ｻ・・ｲ逶ｻ繝・t逶ｻ螂・
- [・・ｲ逶ｻ縲・1]
- [・・ｲ逶ｻ縲・2]

## 隨橸｣ｰ繝ｻ繝ｻC陂ｯ・ｧn c陂ｯ・｣i thi逶ｻ繻ｻ
| V陂ｯ・･n ・・ｻ幢ｽｻ繝ｻ| ・・ｽｯu ti・・ｽｪn | G逶ｻ・｣i ・・ｽｽ |
|--------|---------|-------|
| [V陂ｯ・･n ・・ｻ幢ｽｻ繝ｻ1] | 﨟樣箕 Cao | [C・・ｽ｡ch s逶ｻ・ｭa] |
| [V陂ｯ・･n ・・ｻ幢ｽｻ繝ｻ2] | 﨟樊ｳｯ Trung b・・ｽｬnh | [C・・ｽ｡ch s逶ｻ・ｭa] |
| [V陂ｯ・･n ・・ｻ幢ｽｻ繝ｻ3] | 﨟樊ｳ・Th陂ｯ・･p | [C・・ｽ｡ch s逶ｻ・ｭa] |

## 﨟櫁ｌ G逶ｻ・｣i ・・ｽｽ c陂ｯ・｣i thi逶ｻ繻ｻ
1. [G逶ｻ・｣i ・・ｽｽ 1]
2. [G逶ｻ・｣i ・・ｽｽ 2]
```

### 3.3. B・・ｽ｡o c・・ｽ｡o cho m逶ｻ・･c ・・ｦ･・ｭch "L・・ｽｪn k陂ｯ・ｿ ho陂ｯ・｡ch n・・ｽ｢ng c陂ｯ・･p"

```markdown
# 﨟槫勠 K陂ｯ・ｾ HO陂ｯ・ｰCH N・・・G C陂ｯ・､P: [T・・ｽｪn]

## 﨟樊｡・Tr陂ｯ・｡ng th・・ｽ｡i hi逶ｻ繻ｻ t陂ｯ・｡i
[M・・ｽｴ t陂ｯ・｣ ng陂ｯ・ｯn]

## 遲ｮ繝ｻ・ｸ繝ｻC・・ｽｳ th逶ｻ繝ｻn・・ｽ｢ng c陂ｯ・･p

### Dependencies c陂ｯ・ｧn update
| Package | Hi逶ｻ繻ｻ t陂ｯ・｡i | M逶ｻ螫・nh陂ｯ・･t | R逶ｻ・ｧi ro |
|---------|----------|----------|--------|
| next | 14.0 | 14.2 | 﨟樊ｳ・An to・・｣ｰn |
| [pkg] | [v1] | [v2] | 﨟樊ｳｯ C陂ｯ・ｧn test |

### T・・ｽｭnh n・・ワg c・・ｽｳ th逶ｻ繝ｻth・・ｽｪm
D逶ｻ・ｱa tr・・ｽｪn ki陂ｯ・ｿn tr・・ｽｺc hi逶ｻ繻ｻ t陂ｯ・｡i, c・・ｽｳ th逶ｻ繝ｻd逶ｻ繝ｻd・・｣ｰng th・・ｽｪm:
1. [T・・ｽｭnh n・・ワg 1]
2. [T・・ｽｭnh n・・ワg 2]

### Refactor n・・ｽｪn l・・｣ｰm
1. [Vi逶ｻ繻・1] - ・・ｽｯu ti・・ｽｪn: 﨟樣箕 Cao
2. [Vi逶ｻ繻・2] - ・・ｽｯu ti・・ｽｪn: 﨟樊ｳｯ Trung b・・ｽｬnh

## 隨橸｣ｰ繝ｻ繝ｻR逶ｻ・ｧi ro khi n・・ｽ｢ng c陂ｯ・･p
- [R逶ｻ・ｧi ro 1]
- [R逶ｻ・ｧi ro 2]
```

---

## Giai ・・曙陂ｯ・｡n 4: L・・ｽｰu B・・ｽ｡o C・・ｽ｡o

```
T陂ｯ・｡o file: docs/PROJECT_REVIEW_[date].md

"﨟樊政 ・・撕・｣ t陂ｯ・｡o b・・ｽ｡o c・・ｽ｡o t陂ｯ・｡i: docs/PROJECT_REVIEW_260130.md

Anh mu逶ｻ蜑ｵ l・・｣ｰm g・・ｽｬ ti陂ｯ・ｿp?
1繝ｻ髷佩・Xem chi ti陂ｯ・ｿt ph陂ｯ・ｧn n・・｣ｰo ・・ｦ･・ｳ
2繝ｻ髷佩・B陂ｯ・ｯt ・・ｻ幢ｽｺ・ｧu s逶ｻ・ｭa v陂ｯ・･n ・・ｻ幢ｽｻ繝ｻ・・氈・ｰ逶ｻ・｣c n・・ｽｪu
3繝ｻ髷佩・L・・ｽｪn plan n・・ｽ｢ng c陂ｯ・･p v逶ｻ螫・/plan
4繝ｻ髷佩・L・・ｽｰu l陂ｯ・｡i ・・ｻ幢ｽｻ繝ｻsau v逶ｻ螫・/save-brain"
```

---

## 隨橸｣ｰ繝ｻ繝ｻNEXT STEPS (Menu s逶ｻ繝ｻ:
```
1繝ｻ髷佩・S逶ｻ・ｭa v陂ｯ・･n ・・ｻ幢ｽｻ繝ｻ /debug ho陂ｯ・ｷc /refactor
2繝ｻ髷佩・Th・・ｽｪm t・・ｽｭnh n・・ワg? /plan
3繝ｻ髷佩・B・・｣ｰn giao? /save-brain ・・ｻ幢ｽｻ繝ｻ・・ｦ･・ｳng g・・ｽｳi context
4繝ｻ髷佩・Ti陂ｯ・ｿp t逶ｻ・･c code? /code
```

---

## 﨟槫ｭｱ繝ｻ繝ｻResilience Patterns

### Khi kh・・ｽｴng c・・ｽｳ package.json
```
遶翫・B・・ｽ｡o user: "・・撕・｢y kh・・ｽｴng ph陂ｯ・｣i d逶ｻ・ｱ ・・ｽ｡n Node.js. Em qu・・ｽｩt theo c陂ｯ・･u tr・・ｽｺc folder."
遶翫・Li逶ｻ繽・k・・ｽｪ file types t・・ｽｬm th陂ｯ・･y (.py, .java, .html...)
```

### Khi folder qu・・ｽ｡ l逶ｻ螫ｾ
```
遶翫・Ch逶ｻ繝ｻqu・・ｽｩt 3 levels ・・ｻ幢ｽｺ・ｧu
遶翫・・・ｽｯu ti・・ｽｪn: src/, app/, components/, lib/, pages/
遶翫・B逶ｻ繝ｻqua: node_modules/, .git/, dist/
```

### Khi kh・・ｽｴng c・・ｽｳ docs
```
遶翫・"D逶ｻ・ｱ ・・ｽ｡n ch・・ｽｰa c・・ｽｳ documentation. Em t逶ｻ・ｱ t陂ｯ・｡o overview d逶ｻ・ｱa tr・・ｽｪn code."
```
