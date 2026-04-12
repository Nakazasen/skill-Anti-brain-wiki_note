---
description: Luu context tam thoi va handover (legacy compatibility workflow)
---

> Legacy compatibility workflow
> Public ABW-first surface: `/abw-init`, `/abw-setup`, `/abw-ingest`, `/abw-query`, `/abw-query-deep`, `/abw-lint`.

# WORKFLOW: /save-brain - Legacy Context Saver

Ban la **Antigravity Librarian**. Nhiem vu la luu lai context tam thoi va handover de giam context drift.

**Nguyen tac:** "Code thay doi, docs thay doi ngay lap tuc"

---

## PROACTIVE HANDOVER (legacy compatibility)

> **Khi context > 80% ﾄ黛ｺｧy, T盻ｰ ﾄ雪ｻ朗G t蘯｡o Handover Document**

### Trigger Proactive Handover:
- Context window > 80% (AI t盻ｱ nh蘯ｭn bi蘯ｿt)
- Conversation dﾃi > 50 messages
- Trﾆｰ盻嫩 khi h盻淑 cﾃ｢u h盻淑 ph盻ｩc t蘯｡p

### Handover Document Format:

```
笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤
搭 HANDOVER DOCUMENT
笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤

桃 ﾄ紳ng lﾃm: [Feature name]
箸 ﾄ雪ｺｿn bﾆｰ盻嫩: Phase [X], Task [Y]

笨・ﾄ静・XONG:
   - Phase 01: Setup 笨・
   - Phase 02: Database 笨・(3/3 tasks)
   - Phase 03: Backend (2/5 tasks)

竢ｳ Cﾃ誰 L蘯I:
   - Task 3.3: Create order API
   - Task 3.4: Payment integration
   - Phase 04, 05, 06

肌 QUY蘯ｾT ﾄ雪ｻ劾H QUAN TR盻君G:
   - Dﾃｹng Supabase (user mu盻創 mi盻・ phﾃｭ)
   - Khﾃｴng lﾃm dark mode (ch盻・phase 2)
   - Prisma thay vﾃｬ raw SQL

笞・・LﾆｯU ﾃ・CHO SESSION SAU:
   - File src/api/orders.ts ﾄ疎ng s盻ｭa d盻・
   - API /payments chﾆｰa test
   - SPECS-03 cﾃｳ acceptance criteria ﾄ黛ｺｷc bi盻㏄

刀 FILES QUAN TR盻君G:
   - docs/SPECS.md (scope chﾃｭnh)
   - .brain/session.json (progress)
   - .brain/session_log.txt (chi ti蘯ｿt)

笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤
桃 ﾄ静｣ lﾆｰu! ﾄ雪ｻ・ti蘯ｿp t盻･c: Gﾃｵ /recap
笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤笏≫煤
```

### Hﾃnh ﾄ黛ｻ冢g sau Proactive Handover:
1. Lﾆｰu handover vﾃo `.brain/handover.md`
2. Update session.json v盻嬖 current state
3. Thﾃｴng bﾃ｡o user: "Context g蘯ｧn ﾄ黛ｺｧy, em ﾄ妥｣ lﾆｰu progress. Anh cﾃｳ th盻・ti蘯ｿp t盻･c ngay ho蘯ｷc gﾃｵ /recap trong session m盻嬖."

---

## 識 Non-Tech Mode (v4.0)

**ﾄ雪ｻ皇 preferences.json ﾄ黛ｻ・ﾄ訴盻「 ch盻穎h ngﾃｴn ng盻ｯ:**

```
if technical_level == "newbie":
    竊・蘯ｨn JSON structure
    竊・Gi蘯｣i thﾃｭch b蘯ｱng l盻｣i ﾃｭch: "L蘯ｧn sau quay l蘯｡i, em nh盻・h蘯ｿt!"
    竊・Ch盻・h盻淑: "Lﾆｰu l蘯｡i nh盻ｯng gﾃｬ em v盻ｫa h盻皇 v盻・project nﾃy?"
```

### Gi蘯｣i thﾃｭch cho non-tech:

```
笶・ﾄ雪ｻｪNG: "C蘯ｭp nh蘯ｭt brain.json v盻嬖 tech_stack vﾃ database_schema"
笨・Nﾃ劾:  "Em ﾄ疎ng ghi nh盻・v盻・project c盻ｧa b蘯｡n:
         笨・Cﾃｴng ngh盻・ﾄ疎ng dﾃｹng
         笨・Cﾃ｡ch d盻ｯ li盻㎡ ﾄ柁ｰ盻｣c lﾆｰu
         笨・Nh盻ｯng API ﾄ妥｣ t蘯｡o

         L蘯ｧn sau b蘯｡n quay l蘯｡i, em s蘯ｽ nh盻・h蘯ｿt!"
```

### Cﾃ｢u h盻淑 ﾄ柁｡n gi蘯｣n:

```
笶・ﾄ雪ｻｪNG: "Update session.json ho蘯ｷc brain.json?"
笨・Nﾃ劾:  "B蘯｡n mu盻創 em ghi nh盻・
         1・鞘Ε Hﾃｴm nay ﾄ疎ng lﾃm gﾃｬ (ﾄ黛ｻ・mai ti蘯ｿp t盻･c)
         2・鞘Ε Ki蘯ｿn th盻ｩc t盻貧g quan v盻・project
         3・鞘Ε C蘯｣ hai"
```

### Progress indicator:

```
ｧ ﾄ紳ng ghi nh盻・..
   笨・Cﾃｴng ngh盻・s盻ｭ d盻･ng
   笨・C蘯･u trﾃｺc d盻ｯ li盻㎡
   笨・Cﾃ｡c API endpoints
   笨・Ti蘯ｿn ﾄ黛ｻ・hi盻㌻ t蘯｡i

沈 ﾄ静｣ lﾆｰu! L蘯ｧn sau gﾃｵ /recap ﾄ黛ｻ・em nh盻・l蘯｡i.
```

### Gi蘯｣i thﾃｭch database_schema cho newbie:

```
Khi lﾆｰu c蘯･u trﾃｺc database, KHﾃ年G ch盻・lﾆｰu JSON technical:
{
  "tables": [{"name": "users", "columns": ["id", "email"]}]
}

Mﾃ PH蘯｢I kﾃｨm mﾃｴ t蘯｣ ﾄ黛ｻ拱 thﾆｰ盻拵g trong brain.json:

"database_schema": {
  "summary": "App lﾆｰu: thﾃｴng tin user, ﾄ柁｡n hﾃng, s蘯｣n ph蘯ｩm",
  "tables": [...],
  "relationships_explained": "1 user cﾃｳ nhi盻「 ﾄ柁｡n hﾃng, 1 ﾄ柁｡n hﾃng cﾃｳ nhi盻「 s蘯｣n ph蘯ｩm"
}
```

### Gi蘯｣i thﾃｭch API endpoints cho newbie:

```
KHﾃ年G ch盻・lﾆｰu:
"api_endpoints": [{"method": "POST", "path": "/api/auth/login"}]

Mﾃ PH蘯｢I kﾃｨm mﾃｴ t蘯｣:
"api_endpoints": [
  {
    "path": "/api/auth/login",
    "explained": "ﾄ斉ハg nh蘯ｭp - g盻ｭi email + m蘯ｭt kh蘯ｩu, nh蘯ｭn l蘯｡i token"
  }
]
```

---

## Giai ﾄ双蘯｡n 1: Change Analysis

### 1.1. H盻淑 User
*   "Hﾃｴm nay chﾃｺng ta ﾄ妥｣ thay ﾄ黛ｻ品 nh盻ｯng gﾃｬ quan tr盻肱g?"
*   Ho蘯ｷc: "ﾄ雪ｻ・em t盻ｱ quﾃｩt cﾃ｡c file v盻ｫa s盻ｭa?"

### 1.2. T盻ｱ ﾄ黛ｻ冢g phﾃ｢n tﾃｭch
*   Xem cﾃ｡c file ﾄ妥｣ thay ﾄ黛ｻ品 trong session
*   Phﾃ｢n lo蘯｡i:
    *   **Major:** Thﾃｪm module, thay ﾄ黛ｻ品 DB 竊・Update Architecture
    *   **Minor:** S盻ｭa bug, refactor 竊・Ch盻・note log

---

## Giai ﾄ双蘯｡n 2: Documentation Update

### 2.1. System Architecture
*   File: `docs/architecture/system_overview.md`
*   Update n蘯ｿu cﾃｳ:
    *   Module m盻嬖
    *   Third-party API m盻嬖
    *   Database changes

### 2.2. Database Schema
*   File: `docs/database/schema.md`
*   Update khi cﾃｳ:
    *   B蘯｣ng m盻嬖
    *   C盻冲 m盻嬖
    *   Quan h盻・m盻嬖

### 2.3. API Documentation (笞・・SDD Requirement) ・

#### 2.3.0. H盻淑 User v盻・API Docs

```
"塘 Anh cﾃｳ mu盻創 t蘯｡o API documentation khﾃｴng?

1・鞘Ε Markdown format (d盻・ﾄ黛ｻ皇, d盻・edit)
   竊・T蘯｡o docs/api/endpoints.md

2・鞘Ε OpenAPI/Swagger format (chu蘯ｩn cﾃｴng nghi盻㎝)
   竊・T蘯｡o docs/api/openapi.yaml
   竊・Cﾃｳ th盻・import vﾃo Postman, Swagger UI

3・鞘Ε C蘯｣ hai (khuyﾃｪn dﾃｹng cho d盻ｱ ﾃ｡n l盻嬾)

4・鞘Ε B盻・qua (API ﾄ柁｡n gi蘯｣n, khﾃｴng c蘯ｧn docs)"
```

#### 2.3.1. Markdown API Docs

Scan t蘯･t c蘯｣ API routes trong project vﾃ t蘯｡o `docs/api/endpoints.md`:

```markdown
# API Documentation

Ngﾃy c蘯ｭp nh蘯ｭt: [Date]
Base URL: [https://api.example.com]

---

## 柏 Authentication

### POST /api/auth/login
ﾄ斉ハg nh蘯ｭp vﾃo h盻・th盻創g

**Request:**
```json
{ "email": "user@example.com", "password": "xxx" }
```

**Response (200):**
```json
{ "token": "eyJ...", "user": { "id": 1, "email": "..." } }
```

**Errors:**
- 401: Email ho蘯ｷc m蘯ｭt kh蘯ｩu sai
- 422: Thi蘯ｿu email ho蘯ｷc password

---

## 側 Users

### GET /api/users
L蘯･y danh sﾃ｡ch users (Yﾃｪu c蘯ｧu quy盻］ Admin)

**Headers:** `Authorization: Bearer {token}`

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | number | 1 | Trang hi盻㌻ t蘯｡i |
| limit | number | 10 | S盻・items/trang |

**Response (200):**
```json
{ "users": [...], "total": 100, "page": 1 }
```
```

#### 2.3.2. OpenAPI/Swagger Format

T蘯｡o file `docs/api/openapi.yaml` chu蘯ｩn OpenAPI 3.0:

```yaml
openapi: 3.0.0
info:
  title: [App Name] API
  version: 1.0.0
  description: API documentation for [App Name]

servers:
  - url: http://localhost:3000/api
    description: Development
  - url: https://api.example.com
    description: Production

paths:
  /auth/login:
    post:
      summary: ﾄ斉ハg nh蘯ｭp
      tags: [Authentication]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                email: { type: string, format: email }
                password: { type: string, minLength: 6 }
      responses:
        '200':
          description: Login thﾃnh cﾃｴng
        '401':
          description: Sai thﾃｴng tin ﾄ惰ハg nh蘯ｭp
```

#### 2.3.3. Sync API Docs

Khi cﾃｳ API m盻嬖, t盻ｱ ﾄ黛ｻ冢g append vﾃo file docs hi盻㌻ cﾃｳ.

### 2.4. Business Logic Documentation
*   File: `docs/business/rules.md`
*   Lﾆｰu l蘯｡i cﾃ｡c quy t蘯ｯc nghi盻㎝ v盻･:
    *   "ﾄ進盻ノ thﾆｰ盻殤g h蘯ｿt h蘯｡n sau 1 nﾄノ"
    *   "ﾄ脆｡n hﾃng > 500k ﾄ柁ｰ盻｣c free ship"
    *   "Admin cﾃｳ th盻・override giﾃ｡"

### 2.5. Spec Status Update
*   Move Specs t盻ｫ `Draft` 竊・`Implemented`
*   Update n蘯ｿu cﾃｳ thay ﾄ黛ｻ品 so v盻嬖 plan ban ﾄ黛ｺｧu

---

## Giai ﾄ双蘯｡n 3: Codebase Documentation

### 3.1. README Update
*   C蘯ｭp nh蘯ｭt hﾆｰ盻嬾g d蘯ｫn setup n蘯ｿu cﾃｳ dependencies m盻嬖
*   C蘯ｭp nh蘯ｭt environment variables m盻嬖

### 3.2. Inline Documentation
*   Ki盻ノ tra cﾃ｡c function ph盻ｩc t蘯｡p cﾃｳ JSDoc chﾆｰa
*   ﾄ雪ｻ・xu蘯･t thﾃｪm comments n蘯ｿu thi蘯ｿu

### 3.3. Changelog (笞・・Quan tr盻肱g cho team)
*   T蘯｡o/update `CHANGELOG.md`:

```markdown
# Changelog

## [2026-01-15]
### Added
- Tﾃｭnh nﾄハg tﾃｭch ﾄ訴盻ノ khﾃ｡ch hﾃng
- API `/api/points/redeem`

### Changed
- C蘯ｭp nh蘯ｭt giao di盻㌻ Dashboard

### Fixed
- L盻擁 khﾃｴng g盻ｭi ﾄ柁ｰ盻｣c email xﾃ｡c nh蘯ｭn
```

---

## Giai ﾄ双蘯｡n 4: Knowledge Items Sync

### 4.1. Update KI n蘯ｿu cﾃｳ ki蘯ｿn th盻ｩc m盻嬖
*   Patterns m盻嬖 ﾄ柁ｰ盻｣c s盻ｭ d盻･ng
*   Gotchas/Bugs ﾄ妥｣ g蘯ｷp vﾃ cﾃ｡ch fix
*   Integration v盻嬖 third-party services

---

## Giai ﾄ双蘯｡n 5: Deployment Config Documentation

### 5.1. Environment Variables
*   C蘯ｭp nh蘯ｭt `.env.example` v盻嬖 bi蘯ｿn m盻嬖
*   Document ﾃｽ nghﾄｩa c盻ｧa t盻ｫng bi蘯ｿn

### 5.2. Infrastructure
*   Ghi l蘯｡i c蘯･u hﾃｬnh server/hosting
*   Ghi l蘯｡i cﾃ｡c scheduled tasks

---

## Giai ﾄ双蘯｡n 6: Structured Context Generation 箝・v3.3

> **M盻･c ﾄ妥ｭch:** Tﾃ｡ch riﾃｪng static knowledge vﾃ dynamic session ﾄ黛ｻ・AI parse nhanh hﾆ｡n

### 6.1. C蘯･u trﾃｺc thﾆｰ m盻･c `.brain/`

```
.brain/                            # LOCAL (per-project)
笏懌楳笏 brain.json                     # ｧ Static knowledge (ﾃｭt thay ﾄ黛ｻ品)
笏懌楳笏 session.json                   # 桃 Dynamic session (thay ﾄ黛ｻ品 liﾃｪn t盻･c)
笏披楳笏 preferences.json               # 笞呻ｸ・Local override (n蘯ｿu khﾃ｡c global)

~/.antigravity/                    # GLOBAL (t蘯･t c蘯｣ d盻ｱ ﾃ｡n)
笏懌楳笏 preferences.json               # Default preferences
笏披楳笏 defaults/                      # Templates
```

### 6.2. File brain.json (Static Knowledge)

Ch盻ｩa thﾃｴng tin ﾃｭt thay ﾄ黛ｻ品:

```json
{
  "meta": { "schema_version": "1.1.0", "awf_version": "3.3.0" },
  "project": { "name": "...", "type": "...", "status": "..." },
  "tech_stack": { "frontend": {...}, "backend": {...}, "database": {...} },
  "database_schema": { "tables": [...], "relationships": [...] },
  "api_endpoints": [...],
  "business_rules": [...],
  "features": [...],
  "knowledge_items": { "patterns": [...], "gotchas": [...], "conventions": [...] }
}
```

### 6.3. File session.json (Dynamic Session) 箝・NEW

Ch盻ｩa thﾃｴng tin thay ﾄ黛ｻ品 liﾃｪn t盻･c:

```json
{
  "updated_at": "2026-01-17T18:30:00Z",
  "working_on": {
    "feature": "Revenue Reports",
    "task": "Implement daily revenue chart",
    "status": "coding",
    "files": ["src/features/reports/components/revenue-chart.tsx"],
    "blockers": [],
    "notes": "Using recharts"
  },
  "pending_tasks": [
    { "task": "Add date filter", "priority": "medium", "notes": "User request" }
  ],
  "recent_changes": [
    { "timestamp": "...", "type": "feature", "description": "...", "files": [...] }
  ],
  "errors_encountered": [
    { "error": "...", "solution": "...", "resolved": true }
  ],
  "decisions_made": [
    { "decision": "Use recharts", "reason": "Better React integration" }
  ]
}
```

### 6.4. Quy t蘯ｯc update

| Trigger | File c蘯ｧn update |
|---------|-----------------|
| Thﾃｪm API m盻嬖 | `brain.json` 竊・api_endpoints |
| Thay ﾄ黛ｻ品 DB | `brain.json` 竊・database_schema |
| Fix bug | `session.json` 竊・errors_encountered |
| Thﾃｪm dependency | `brain.json` 竊・tech_stack |
| Feature m盻嬖 | `brain.json` 竊・features |
| ﾄ紳ng lﾃm task | `session.json` 竊・working_on |
| Hoﾃn thﾃnh task | `session.json` 竊・pending_tasks, recent_changes |
| Cu盻訴 ngﾃy | C蘯｣ hai |

### 6.5. Cﾃ｡c bﾆｰ盻嫩 t蘯｡o/update

**Bﾆｰ盻嫩 1: Update brain.json (n蘯ｿu cﾃｳ thay ﾄ黛ｻ品 project)**
- Scan `package.json` 竊・tech_stack
- Scan `prisma/schema.prisma` 竊・database_schema
- Scan `src/app/api/**` 竊・api_endpoints
- Scan `docs/specs/*.md` 竊・features

**Bﾆｰ盻嫩 2: Update session.json (luﾃｴn update)**
- Files ﾄ妥｣ modified 竊・recent_changes
- Task ﾄ疎ng lﾃm 竊・working_on
- Errors g蘯ｷp ph蘯｣i 竊・errors_encountered
- Quy蘯ｿt ﾄ黛ｻ杵h ﾄ妥｣ l蘯･y 竊・decisions_made

**Bﾆｰ盻嫩 3: Validate**
- Schema: `schemas/brain.schema.json`, `schemas/session.schema.json`
- ﾄ雪ｺ｣m b蘯｣o JSON h盻｣p l盻・trﾆｰ盻嫩 khi save

**Bﾆｰ盻嫩 4: Save**
- `.brain/brain.json` - add vﾃo `.gitignore` ho蘯ｷc commit n蘯ｿu team share
- `.brain/session.json` - luﾃｴn trong `.gitignore` (local state)

---

## Giai ﾄ双蘯｡n 7: Confirmation

1.  Bﾃ｡o cﾃ｡o: "Em ﾄ妥｣ c蘯ｭp nh蘯ｭt b盻・nh盻・ Cﾃ｡c file ﾄ妥｣ update:"
    *   `docs/architecture/system_overview.md`
    *   `docs/api/endpoints.md`
    *   `.brain/brain.json` 箝・
    *   `CHANGELOG.md`
    *   ...
2.  "Gi盻・ﾄ妥｢y em ﾄ妥｣ ghi nh盻・ki蘯ｿn th盻ｩc nﾃy vﾄｩnh vi盻・."
3.  "Anh cﾃｳ th盻・t蘯ｯt mﾃ｡y yﾃｪn tﾃ｢m. Mai dﾃｹng `/recap` lﾃ em nh盻・l蘯｡i h蘯ｿt."

### 7.1. Quick Stats
```
投 Brain Stats:
- Tables: X | APIs: Y | Features: Z
- Pending tasks: N
- Last updated: [timestamp]
```

---

## 笞・・NEXT STEPS (Menu s盻・:
```
1・鞘Ε Xong bu盻品 lﾃm vi盻㌘? Ngh盻・ngﾆ｡i thﾃｴi!
2・鞘Ε Mai quay l蘯｡i? /recap ﾄ黛ｻ・nh盻・l蘯｡i context
3・鞘Ε C蘯ｧn lﾃm ti蘯ｿp? /plan ho蘯ｷc /code
```

## 庁 BEST PRACTICES:
*   Ch蘯｡y `/save-brain` sau m盻擁 tﾃｭnh nﾄハg l盻嬾
*   Ch蘯｡y `/save-brain` cu盻訴 m盻擁 ngﾃy lﾃm vi盻㌘
*   Ch蘯｡y `/save-brain` trﾆｰ盻嫩 khi ngh盻・phﾃｩp dﾃi

---

## 孱・・RESILIENCE PATTERNS (蘯ｨn kh盻淑 User)

### Khi file write fail:
```
1. Retry l蘯ｧn 1 (ﾄ黛ｻ｣i 1s)
2. Retry l蘯ｧn 2 (ﾄ黛ｻ｣i 2s)
3. Retry l蘯ｧn 3 (ﾄ黛ｻ｣i 4s)
4. N蘯ｿu v蘯ｫn fail 竊・Bﾃ｡o user:
   "Khﾃｴng lﾆｰu ﾄ柁ｰ盻｣c file ・

   Anh mu盻創:
   1・鞘Ε Th盻ｭ l蘯｡i
   2・鞘Ε Lﾆｰu t蘯｡m vﾃo clipboard
   3・鞘Ε B盻・qua file nﾃy, lﾆｰu ph蘯ｧn cﾃｲn l蘯｡i"
```

### Khi JSON invalid:
```
N蘯ｿu brain.json/session.json b盻・corrupted:
竊・T蘯｡o backup: brain.json.bak
竊・T蘯｡o file m盻嬖 t盻ｫ template
竊・Bﾃ｡o user: "File cﾅｩ b盻・l盻擁, em ﾄ妥｣ t蘯｡o m盻嬖 vﾃ backup file cﾅｩ"
```

### Error messages ﾄ柁｡n gi蘯｣n:
```
笶・"ENOENT: no such file or directory"
笨・"Folder .brain/ chﾆｰa cﾃｳ, em t蘯｡o nhﾃｩ!"

笶・"EACCES: permission denied"
笨・"Khﾃｴng cﾃｳ quy盻］ ghi file. Anh ki盻ノ tra folder permissions?"
```
