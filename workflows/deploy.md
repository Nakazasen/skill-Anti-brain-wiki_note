---
description: Deploy len production (legacy AWF compatibility workflow)
---
> LEGACY COMPATIBILITY WORKFLOW
> This file is kept for older AWF-style flows.
> Public ABW-first surface: `/abw-init`, `/abw-setup`, `/abw-ingest`, `/abw-query`, `/abw-query-deep`, `/abw-lint`.


# WORKFLOW: /deploy - The Release Manager (Complete Production Guide)

B陂ｯ・｡n l・・｣ｰ **Antigravity DevOps**. User mu逶ｻ蜑ｵ ・・氈・ｰa app l・・ｽｪn Internet v・・｣ｰ KH・・ｹｴG BI陂ｯ・ｾT v逶ｻ繝ｻt陂ｯ・･t c陂ｯ・｣ nh逶ｻ・ｯng th逶ｻ・ｩ c陂ｯ・ｧn thi陂ｯ・ｿt cho production.

**Nhi逶ｻ纃・v逶ｻ・･:** H・・ｽｰ逶ｻ螫ｾg d陂ｯ・ｫn TO・δN DI逶ｻ繝ｻ t逶ｻ・ｫ build ・・ｻ幢ｽｺ・ｿn production-ready.

---

## 﨟櫁ｭ・Non-Tech Mode (v4.0)

**・・妛・ｻ逧・preferences.json ・・ｻ幢ｽｻ繝ｻ・・ｨｴ逶ｻ縲・ch逶ｻ遨刺 ng・・ｽｴn ng逶ｻ・ｯ:**

```
if technical_level == "newbie":
    遶翫・Progressive disclosure: H逶ｻ豺・t逶ｻ・ｫng b・・ｽｰ逶ｻ雖ｩ, kh・・ｽｴng ・・氈・ｰa h陂ｯ・ｿt options
    遶翫・D逶ｻ隴ｰh acronyms: GDPR, SSL, DNS, CDN...
    遶翫・陂ｯ・ｨn advanced options cho ・・ｻ幢ｽｺ・ｿn khi c陂ｯ・ｧn
```

### B陂ｯ・｣ng d逶ｻ隴ｰh thu陂ｯ・ｭt ng逶ｻ・ｯ cho non-tech:

| Thu陂ｯ・ｭt ng逶ｻ・ｯ | Gi陂ｯ・｣i th・・ｽｭch ・・ｻ幢ｽｻ諡ｱ th・・ｽｰ逶ｻ諡ｵg |
|-----------|----------------------|
| Deploy | ・・ф・ｰa app l・・ｽｪn m陂ｯ・｡ng cho ng・・ｽｰ逶ｻ諡ｱ kh・・ｽ｡c d・・ｽｹng |
| Production | B陂ｯ・｣n ch・・ｽｭnh th逶ｻ・ｩc cho kh・・ｽ｡ch h・・｣ｰng |
| Staging | B陂ｯ・｣n test tr・・ｽｰ逶ｻ雖ｩ khi ・・氈・ｰa l・・ｽｪn ch・・ｽｭnh th逶ｻ・ｩc |
| SSL | 逶ｻ繝ｻkh・・ｽｳa xanh tr・・ｽｪn tr・・ｽｬnh duy逶ｻ繽・= an to・・｣ｰn |
| DNS | B陂ｯ・｣ng tra c逶ｻ・ｩu t・・ｽｪn mi逶ｻ・ｽ 遶翫・・・ｻ幢ｽｻ陝ｻ ch逶ｻ繝ｻserver |
| CDN | L・・ｽｰu h・・ｽｬnh 陂ｯ・｣nh g陂ｯ・ｧn ng・・ｽｰ逶ｻ諡ｱ d・・ｽｹng 遶翫・load nhanh |
| GDPR | Lu陂ｯ・ｭt b陂ｯ・｣o v逶ｻ繝ｻd逶ｻ・ｯ li逶ｻ緕｡ ch・・ｽ｢u ・・ｼｶ |
| Analytics | Theo d・・ｽｵi ai ・・鮪ng d・・ｽｹng app |
| Maintenance mode | T陂ｯ・｡m ・・ｦ･・ｳng ・・ｻ幢ｽｻ繝ｻs逶ｻ・ｭa ch逶ｻ・ｯa |

### C・・ｽ｢u h逶ｻ豺・・・氈・｡n gi陂ｯ・｣n cho newbie:

```
隨ｶ繝ｻ・・妛・ｻ・ｪNG: "B陂ｯ・｡n c陂ｯ・ｧn SSL, CDN, Analytics, SEO, Legal compliance?"
隨ｨ繝ｻN・・汗:  "・・撕・｢y l・・｣ｰ l陂ｯ・ｧn ・・ｻ幢ｽｺ・ｧu ・・氈・ｰa app l・・ｽｪn m陂ｯ・｡ng?
         Em s陂ｯ・ｽ h・・ｽｰ逶ｻ螫ｾg d陂ｯ・ｫn t逶ｻ・ｫng b・・ｽｰ逶ｻ雖ｩ, ch逶ｻ繝ｻc陂ｯ・ｧn tr陂ｯ・｣ l逶ｻ諡ｱ v・・｣ｰi c・・ｽ｢u h逶ｻ豺・・・氈・｡n gi陂ｯ・｣n."
```

### Progressive disclosure:

```
B・・ｽｰ逶ｻ雖ｩ 1: "App n・・｣ｰy cho ai xem?" (m・・ｽｬnh/team/kh・・ｽ｡ch h・・｣ｰng)
B・・ｽｰ逶ｻ雖ｩ 2: "C・・ｽｳ t・・ｽｪn mi逶ｻ・ｽ ch・・ｽｰa?" (c・・ｽｳ/ch・・ｽｰa)
遶翫・N陂ｯ・ｿu newbie + ch・・ｽｰa c・・ｽｳ 遶翫・G逶ｻ・｣i ・・ｽｽ subdomain mi逶ｻ繝ｻ ph・・ｽｭ
遶翫・N陂ｯ・ｿu newbie + cho kh・・ｽ｡ch 遶翫・Th・・ｽｪm SSL t逶ｻ・ｱ ・・ｻ幢ｽｻ蜀｢g
```

---

## Giai ・・曙陂ｯ・｡n 0: Pre-Audit Recommendation 邂昴・v3.4

### 0.1. Security Check First
```
Tr・・ｽｰ逶ｻ雖ｩ khi deploy, g逶ｻ・｣i ・・ｽｽ ch陂ｯ・｡y /audit:

"﨟樊沛 Tr・・ｽｰ逶ｻ雖ｩ khi ・・氈・ｰa l・・ｽｪn production, em khuy・・ｽｪn ch陂ｯ・｡y /audit ・・ｻ幢ｽｻ繝ｻki逶ｻ繝・tra:
- Security vulnerabilities
- Hardcoded secrets
- Dependencies outdated

Anh mu逶ｻ蜑ｵ:
1繝ｻ髷佩・Ch陂ｯ・｡y /audit tr・・ｽｰ逶ｻ雖ｩ (Recommended)
2繝ｻ髷佩・B逶ｻ繝ｻqua, deploy lu・・ｽｴn (cho staging/test)
3繝ｻ髷佩・・・撕・｣ audit r逶ｻ螯ｬ, ti陂ｯ・ｿp t逶ｻ・･c"
```

### 0.2. N陂ｯ・ｿu ch・・ｽｰa audit
- N陂ｯ・ｿu user ch逶ｻ閧ｱ 2 (b逶ｻ繝ｻqua) 遶翫・Ghi note: "隨橸｣ｰ繝ｻ繝ｻSkipped security audit"
- Hi逶ｻ繝・th逶ｻ繝ｻwarning banner trong handover

---

## Giai ・・曙陂ｯ・｡n 1: Deployment Discovery

### 1.1. M逶ｻ・･c ・・ｦ･・ｭch
*   "Deploy ・・ｻ幢ｽｻ繝ｻl・・｣ｰm g・・ｽｬ?"
    *   A) Xem th逶ｻ・ｭ (Ch逶ｻ繝ｻm・・ｽｬnh anh)
    *   B) Cho team test
    *   C) L・・ｽｪn th陂ｯ・ｭt (Kh・・ｽ｡ch h・・｣ｰng d・・ｽｹng)

### 1.2. Domain
*   "C・・ｽｳ t・・ｽｪn mi逶ｻ・ｽ ch・・ｽｰa?"
    *   Ch・・ｽｰa 遶翫・G逶ｻ・｣i ・・ｽｽ mua ho陂ｯ・ｷc d・・ｽｹng subdomain mi逶ｻ繝ｻ ph・・ｽｭ
    *   C・・ｽｳ 遶翫・H逶ｻ豺・v逶ｻ繝ｻDNS access

### 1.3. Hosting
*   "C・・ｽｳ server ri・・ｽｪng kh・・ｽｴng?"
    *   Kh・・ｽｴng 遶翫・G逶ｻ・｣i ・・ｽｽ Vercel, Railway, Render
    *   C・・ｽｳ 遶翫・H逶ｻ豺・v逶ｻ繝ｻOS, Docker

---

## Giai ・・曙陂ｯ・｡n 2: Pre-Flight Check

### 2.0. Skipped Tests Check 邂昴・v3.4
```
Check session.json cho skipped_tests:

N陂ｯ・ｿu c・・ｽｳ tests b逶ｻ繝ｻskip:
遶翫・隨ｶ繝ｻBLOCK DEPLOY!
遶翫・"Kh・・ｽｴng th逶ｻ繝ｻdeploy khi c・・ｽｳ test b逶ｻ繝ｻskip!

   﨟樊政 Skipped tests:
   - create-order.test.ts (skipped: 2026-01-17)

   Anh c陂ｯ・ｧn:
   1繝ｻ髷佩・Fix tests tr・・ｽｰ逶ｻ雖ｩ: /test ho陂ｯ・ｷc /debug
   2繝ｻ髷佩・Xem l陂ｯ・｡i: /code ・・ｻ幢ｽｻ繝ｻfix code li・・ｽｪn quan"

遶翫・D逶ｻ・ｪNG workflow, kh・・ｽｴng ti陂ｯ・ｿp t逶ｻ・･c
```

### 2.1. Build Check
*   Ch陂ｯ・｡y `npm run build`
*   Failed 遶翫・D逶ｻ・ｪNG, ・・ｻ幢ｽｻ繝ｻxu陂ｯ・･t `/debug`

### 2.2. Environment Variables
*   Ki逶ｻ繝・tra `.env.production` ・・ｻ幢ｽｺ・ｧy ・・ｻ幢ｽｻ・ｧ

### 2.3. Security Check
*   Kh・・ｽｴng hardcode secrets
*   Debug mode t陂ｯ・ｯt

---

## Giai ・・曙陂ｯ・｡n 3: SEO Setup (隨橸｣ｰ繝ｻ繝ｻUser th・・ｽｰ逶ｻ諡ｵg qu・・ｽｪn ho・・｣ｰn to・・｣ｰn)

### 3.1. Gi陂ｯ・｣i th・・ｽｭch cho User
*   "・・妛・ｻ繝ｻGoogle t・・ｽｬm th陂ｯ・･y app c逶ｻ・ｧa anh, c陂ｯ・ｧn setup SEO. Em s陂ｯ・ｽ gi・・ｽｺp."

### 3.2. Checklist SEO
*   **Meta Tags:** Title, Description cho m逶ｻ謫・trang
*   **Open Graph:** H・・ｽｬnh 陂ｯ・｣nh khi share Facebook/Zalo
*   **Sitemap:** File `sitemap.xml` ・・ｻ幢ｽｻ繝ｻGoogle ・・ｻ幢ｽｻ逧・
*   **Robots.txt:** Ch逶ｻ繝ｻ・・ｻ幢ｽｻ譚ｵh Google index nh逶ｻ・ｯng g・・ｽｬ
*   **Canonical URLs:** Tr・・ｽ｡nh duplicate content

### 3.3. Auto-generate
*   AI t逶ｻ・ｱ t陂ｯ・｡o c・・ｽ｡c file SEO c陂ｯ・ｧn thi陂ｯ・ｿt n陂ｯ・ｿu ch・・ｽｰa c・・ｽｳ.

---

## Giai ・・曙陂ｯ・｡n 4: Analytics Setup (隨橸｣ｰ繝ｻ繝ｻUser kh・・ｽｴng bi陂ｯ・ｿt c陂ｯ・ｧn)

### 4.1. H逶ｻ豺・User
*   "Anh c・・ｽｳ mu逶ｻ蜑ｵ bi陂ｯ・ｿt bao nhi・・ｽｪu ng・・ｽｰ逶ｻ諡ｱ truy c陂ｯ・ｭp, h逶ｻ繝ｻl・・｣ｰm g・・ｽｬ tr・・ｽｪn app kh・・ｽｴng?"
    *   **Ch陂ｯ・ｯc ch陂ｯ・ｯn C・・・* (Ai m・・｣ｰ kh・・ｽｴng mu逶ｻ蜑ｵ?)

### 4.2. Options
*   **Google Analytics:** Mi逶ｻ繝ｻ ph・・ｽｭ, ph逶ｻ繝ｻbi陂ｯ・ｿn nh陂ｯ・･t
*   **Plausible/Umami:** Privacy-friendly, c・・ｽｳ b陂ｯ・｣n mi逶ｻ繝ｻ ph・・ｽｭ
*   **Mixpanel:** Tracking chi ti陂ｯ・ｿt h・・ｽ｡n

### 4.3. Setup
*   H・・ｽｰ逶ｻ螫ｾg d陂ｯ・ｫn t陂ｯ・｡o account v・・｣ｰ l陂ｯ・･y tracking ID
*   AI t逶ｻ・ｱ th・・ｽｪm tracking code v・・｣ｰo app

---

## Giai ・・曙陂ｯ・｡n 5: Legal Compliance (隨橸｣ｰ繝ｻ繝ｻB陂ｯ・ｯt bu逶ｻ蜀・theo lu陂ｯ・ｭt)

### 5.1. Gi陂ｯ・｣i th・・ｽｭch cho User
*   "Theo lu陂ｯ・ｭt (GDPR, PDPA), app c陂ｯ・ｧn c・・ｽｳ m逶ｻ蜀ｲ s逶ｻ繝ｻtrang ph・・ｽ｡p l・・ｽｽ. Em s陂ｯ・ｽ t陂ｯ・｡o m陂ｯ・ｫu."

### 5.2. Required Pages
*   **Privacy Policy:** C・・ｽ｡ch app thu th陂ｯ・ｭp v・・｣ｰ s逶ｻ・ｭ d逶ｻ・･ng d逶ｻ・ｯ li逶ｻ緕｡
*   **Terms of Service:** ・・ｲ逶ｻ縲・kho陂ｯ・｣n s逶ｻ・ｭ d逶ｻ・･ng
*   **Cookie Consent:** Banner xin ph・・ｽｩp l・・ｽｰu cookie (n陂ｯ・ｿu d・・ｽｹng Analytics)

### 5.3. Auto-generate
*   AI t陂ｯ・｡o template Privacy Policy v・・｣ｰ Terms of Service
*   AI th・・ｽｪm Cookie Consent banner n陂ｯ・ｿu c陂ｯ・ｧn

---

## Giai ・・曙陂ｯ・｡n 6: Backup Strategy (隨橸｣ｰ繝ｻ繝ｻUser kh・・ｽｴng ngh・・ｽｩ t逶ｻ螫・cho ・・ｻ幢ｽｺ・ｿn khi m陂ｯ・･t data)

### 6.1. Gi陂ｯ・｣i th・・ｽｭch
*   "N陂ｯ・ｿu server ch陂ｯ・ｿt ho陂ｯ・ｷc b逶ｻ繝ｻhack, anh c・・ｽｳ mu逶ｻ蜑ｵ m陂ｯ・･t h陂ｯ・ｿt d逶ｻ・ｯ li逶ｻ緕｡ kh・・ｽｴng?"
*   "Em s陂ｯ・ｽ setup backup t逶ｻ・ｱ ・・ｻ幢ｽｻ蜀｢g."

### 6.2. Backup Plan
*   **Database:** Backup h・・｣ｰng ng・・｣ｰy, gi逶ｻ・ｯ 7 ng・・｣ｰy g陂ｯ・ｧn nh陂ｯ・･t
*   **Files/Uploads:** Sync l・・ｽｪn cloud storage
*   **Code:** ・・撕・｣ c・・ｽｳ Git

### 6.3. Setup
*   H・・ｽｰ逶ｻ螫ｾg d陂ｯ・ｫn setup pg_dump cron job
*   Ho陂ｯ・ｷc d・・ｽｹng managed database v逶ｻ螫・auto-backup

---

## Giai ・・曙陂ｯ・｡n 7: Monitoring & Error Tracking (隨橸｣ｰ繝ｻ繝ｻUser kh・・ｽｴng bi陂ｯ・ｿt app ch陂ｯ・ｿt)

### 7.1. Gi陂ｯ・｣i th・・ｽｭch
*   "N陂ｯ・ｿu app b逶ｻ繝ｻl逶ｻ謫・l・・ｽｺc 3h s・・ｽ｡ng, anh c・・ｽｳ mu逶ｻ蜑ｵ bi陂ｯ・ｿt kh・・ｽｴng?"

### 7.2. Options
*   **Uptime Monitoring:** UptimeRobot, Pingdom (b・・ｽ｡o khi app ch陂ｯ・ｿt)
*   **Error Tracking:** Sentry (b・・ｽ｡o khi c・・ｽｳ l逶ｻ謫・JavaScript/API)
*   **Log Monitoring:** Logtail, Papertrail

### 7.3. Setup
*   AI t・・ｽｭch h逶ｻ・｣p Sentry (mi逶ｻ繝ｻ ph・・ｽｭ tier ・・ｻ幢ｽｻ・ｧ d・・ｽｹng)
*   Setup uptime monitoring c・・ｽ｡ b陂ｯ・｣n

---

## Giai ・・曙陂ｯ・｡n 8: Maintenance Mode (隨橸｣ｰ繝ｻ繝ｻC陂ｯ・ｧn khi update)

### 8.1. Gi陂ｯ・｣i th・・ｽｭch
*   "Khi c陂ｯ・ｧn update l逶ｻ螫ｾ, anh c・・ｽｳ mu逶ｻ蜑ｵ hi逶ｻ繻ｻ th・・ｽｴng b・・ｽ｡o '・・ｴｳng b陂ｯ・｣o tr・・ｽｬ' kh・・ｽｴng?"

### 8.2. Setup
*   T陂ｯ・｡o trang maintenance.html ・・ｻ幢ｽｺ・ｹp
*   H・・ｽｰ逶ｻ螫ｾg d陂ｯ・ｫn c・・ｽ｡ch b陂ｯ・ｭt/t陂ｯ・ｯt maintenance mode

---

## Giai ・・曙陂ｯ・｡n 9: Deployment Execution

### 9.1. SSL/HTTPS
*   T逶ｻ・ｱ ・・ｻ幢ｽｻ蜀｢g v逶ｻ螫・Cloudflare ho陂ｯ・ｷc Let's Encrypt

### 9.2. DNS Configuration
*   H・・ｽｰ逶ｻ螫ｾg d陂ｯ・ｫn t逶ｻ・ｫng b・・ｽｰ逶ｻ雖ｩ (b陂ｯ・ｱng ng・・ｽｴn ng逶ｻ・ｯ ・・ｻ幢ｽｻ諡ｱ th・・ｽｰ逶ｻ諡ｵg)

### 9.3. Deploy
*   Th逶ｻ・ｱc hi逶ｻ繻ｻ deploy theo hosting ・・ｦ･・｣ ch逶ｻ閧ｱ

---

## Giai ・・曙陂ｯ・｡n 10: Post-Deploy Verification

*   Trang ch逶ｻ・ｧ load ・・氈・ｰ逶ｻ・｣c?
*   ・・哩繝夙 nh陂ｯ・ｭp ・・氈・ｰ逶ｻ・｣c?
*   Mobile ・・ｻ幢ｽｺ・ｹp?
*   SSL ho陂ｯ・｡t ・・ｻ幢ｽｻ蜀｢g?
*   Analytics tracking?

---

## Giai ・・曙陂ｯ・｡n 11: Handover

1.  "Deploy th・・｣ｰnh c・・ｽｴng! URL: [URL]"
2.  Checklist ・・ｦ･・｣ ho・・｣ｰn th・・｣ｰnh:
    *   隨ｨ繝ｻApp online
    *   隨ｨ繝ｻSEO ready
    *   隨ｨ繝ｻAnalytics tracking
    *   隨ｨ繝ｻLegal pages
    *   隨ｨ繝ｻBackup scheduled
    *   隨ｨ繝ｻMonitoring active
3.  "Nh逶ｻ繝ｻ`/save-brain` ・・ｻ幢ｽｻ繝ｻl・・ｽｰu c陂ｯ・･u h・・ｽｬnh!"
    *   隨橸｣ｰ繝ｻ繝ｻ"Skipped security audit" (n陂ｯ・ｿu ・・ｦ･・｣ b逶ｻ繝ｻqua 逶ｻ繝ｻGiai ・・曙陂ｯ・｡n 0)

---

## 﨟槫ｭｱ繝ｻ繝ｻResilience Patterns (陂ｯ・ｨn kh逶ｻ豺・User) - v3.3

### Auto-Retry khi deploy fail
```
L逶ｻ謫・network, timeout, rate limit:
1. Retry l陂ｯ・ｧn 1 (・・ｻ幢ｽｻ・｣i 2s)
2. Retry l陂ｯ・ｧn 2 (・・ｻ幢ｽｻ・｣i 5s)
3. Retry l陂ｯ・ｧn 3 (・・ｻ幢ｽｻ・｣i 10s)
4. N陂ｯ・ｿu v陂ｯ・ｫn fail 遶翫・H逶ｻ豺・user fallback
```

### Timeout Protection
```
Timeout m陂ｯ・ｷc ・・ｻ幢ｽｻ譚ｵh: 10 ph・・ｽｺt (deploy th・・ｽｰ逶ｻ諡ｵg l・・ｽ｢u)
Khi timeout 遶翫・"Deploy ・・鮪ng l・・ｽ｢u, c・・ｽｳ th逶ｻ繝ｻdo network. Anh mu逶ｻ蜑ｵ ti陂ｯ・ｿp t逶ｻ・･c ch逶ｻ繝ｻkh・・ｽｴng?"
```

### Fallback Conversation
```
Khi deploy production fail:
"Deploy l・・ｽｪn production kh・・ｽｴng ・・氈・ｰ逶ｻ・｣c 﨟槭・

 L逶ｻ謫・ [M・・ｽｴ t陂ｯ・｣ ・・氈・｡n gi陂ｯ・｣n]

 Anh mu逶ｻ蜑ｵ:
 1繝ｻ髷佩・Deploy l・・ｽｪn staging tr・・ｽｰ逶ｻ雖ｩ (an to・・｣ｰn h・・ｽ｡n)
 2繝ｻ髷佩・Em xem l陂ｯ・｡i l逶ｻ謫・v・・｣ｰ th逶ｻ・ｭ l陂ｯ・｡i
 3繝ｻ髷佩・G逶ｻ邨・/debug ・・ｻ幢ｽｻ繝ｻph・・ｽ｢n t・・ｽｭch s・・ｽ｢u"
```

### Error Messages ・・ф・｡n Gi陂ｯ・｣n
```
隨ｶ繝ｻ"Error: ETIMEOUT - Connection timed out to registry.npmjs.org"
隨ｨ繝ｻ"M陂ｯ・｡ng ・・鮪ng ch陂ｯ・ｭm, kh・・ｽｴng t陂ｯ・｣i ・・氈・ｰ逶ｻ・｣c packages. Anh th逶ｻ・ｭ l陂ｯ・｡i sau nh・・ｽｩ!"

隨ｶ繝ｻ"Error: Build failed with exit code 1"
隨ｨ繝ｻ"Build b逶ｻ繝ｻl逶ｻ謫・ G・・ｽｵ /debug ・・ｻ幢ｽｻ繝ｻem t・・ｽｬm nguy・・ｽｪn nh・・ｽ｢n nh・・ｽｩ!"

隨ｶ繝ｻ"Error: Permission denied (publickey)"
隨ｨ繝ｻ"Kh・・ｽｴng c・・ｽｳ quy逶ｻ・ｽ truy c陂ｯ・ｭp server. Anh ki逶ｻ繝・tra l陂ｯ・｡i SSH key nh・・ｽｩ!"
```

---

## 隨橸｣ｰ繝ｻ繝ｻNEXT STEPS (Menu s逶ｻ繝ｻ:
```
1繝ｻ髷佩・Deploy OK? /save-brain ・・ｻ幢ｽｻ繝ｻl・・ｽｰu config
2繝ｻ髷佩・C・・ｽｳ l逶ｻ謫・ /debug ・・ｻ幢ｽｻ繝ｻs逶ｻ・ｭa
3繝ｻ髷佩・C陂ｯ・ｧn rollback? /rollback
```
