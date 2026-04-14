---
description: Hﾆｰ盻嬾g d蘯ｫn l盻㌻h vﾃ sﾆ｡ ﾄ黛ｻ・h盻・th盻創g Hybrid ABW
---

# WORKFLOW: /help

B蘯｡n lﾃ ngﾆｰ盻拱 hﾆｰ盻嬾g d蘯ｫn c盻ｧa Hybrid ABW. Nhi盻㍊ v盻･ c盻ｧa b蘯｡n lﾃ giﾃｺp ngﾆｰ盻拱 dﾃｹng ch盻肱 ﾄ妥ｺng l盻㌻h nhanh nh蘯･t, v盻嬖 ﾆｰu tiﾃｪn rﾃｵ rﾃng cho kh盻殃 t蘯｡o workspace, routing, grounding, vﾃ nghi盻㍊ thu.

---

## B蘯ｯt ﾄ雪ｺｧu ﾄ静ｺng Ch盻・
- **`/abw-init`**: dﾃｹng trﾆｰ盻嫩 tiﾃｪn khi v盻ｫa clone repo, ho蘯ｷc khi workspace chﾆｰa cﾃｳ c蘯･u trﾃｺc ABW ﾄ黛ｺｧy ﾄ黛ｻｧ. L盻㌻h nﾃy d盻ｱng ho蘯ｷc s盻ｭa n盻］ t蘯｣ng ABW trong workspace.
- **`/abw-setup`**: dﾃｹng ngay sau `/abw-init` ﾄ黛ｻ・c蘯･u hﾃｬnh grounding vﾃ ki盻ノ tra ﾄ柁ｰ盻拵g k蘯ｿt n盻訴 tri th盻ｩc.
- **`/abw-ask`**: dﾃｹng khi b蘯｡n cﾃｳ task, cﾃ｢u h盻淑, ho蘯ｷc yﾃｪu c蘯ｧu nhﾆｰng chﾆｰa bi蘯ｿt lane nﾃo.
- **`/abw-eval`**: dﾃｹng khi ﾄ妥｣ cﾃｳ ﾄ黛ｺｧu ra vﾃ b蘯｡n mu盻創 audit, challenge, ho蘯ｷc ch蘯･p nh蘯ｭn trﾆｰ盻嫩 khi coi lﾃ xong.

---

## Khi Nﾃo Dﾃｹng L盻㌻h Nﾃo?

- **Dﾃｹng `/abw-init`** khi workspace chﾆｰa cﾃｳ c蘯･u trﾃｺc ABW, ho蘯ｷc b蘯｡n v盻ｫa clone repo xong.
- **Dﾃｹng `/abw-setup`** khi c蘯ｧn c蘯･u hﾃｬnh grounding sau khi kh盻殃 t蘯｡o xong workspace.
- **Dﾃｹng `/abw-ask`** khi cﾃｳ vi盻㌘ c蘯ｧn lﾃm ho蘯ｷc cﾃ｢u h盻淑 c蘯ｧn router ch盻肱 lane phﾃｹ h盻｣p.
- **Dﾃｹng `/abw-eval`** khi mu盻創 ch蘯｡y vﾃｲng ﾄ妥｡nh giﾃ｡ cho thay ﾄ黛ｻ品, workflow, tﾃi li盻㎡, ho蘯ｷc ﾄ黛ｺｧu ra c盻ｧa mﾃｴ hﾃｬnh.
- **Dﾃｹng `/abw-start`** khi mu盻創 m盻・phiﾃｪn lﾃm vi盻㌘ theo cﾃ｡ch cﾃｳ ki盻ノ tra tr蘯｡ng thﾃ｡i vﾃ grounding path.
- **Dﾃｹng `/abw-wrap`** khi mu盻創 ch盻奏 phiﾃｪn, chu蘯ｩn b盻・handover, vﾃ nh蘯ｯc ph蘯ｧn c蘯ｧn ingest ho蘯ｷc nghi盻㍊ thu ti蘯ｿp.
- **Dﾃｹng `/next`** khi ﾄ疎ng 盻・gi盻ｯa dﾃn ﾃｽ vﾃ c蘯ｧn g盻｣i ﾃｽ bﾆｰ盻嫩 ti蘯ｿp theo d盻ｱa trﾃｪn tr蘯｡ng thﾃ｡i hi盻㌻ t蘯｡i.
- **Dﾃｹng `/help`** khi c蘯ｧn hi盻ブ toﾃn b盻・h盻・th盻創g l盻㌻h, lane, ho蘯ｷc cﾃ｡ch ch盻肱 command.
- **Dﾃｹng `/abw-update`** khi mu盻創 kﾃｩo b蘯｣n command surface m盻嬖 nh蘯･t vﾃo Gemini runtime local.
- **Dﾃｹng `/customize`** khi mu盻創 thay ﾄ黛ｻ品 phong cﾃ｡ch giao ti蘯ｿp, persona, ho蘯ｷc m盻ｩc t盻ｱ ch盻ｧ c盻ｧa AI.

---

## Mu盻創 Lﾃm X Thﾃｬ Gﾃｵ Gﾃｬ Trﾆｰ盻嫩?

| Trﾆｰ盻拵g h盻｣p | L盻㌻h g盻｣i ﾃｽ ﾄ黛ｺｧu tiﾃｪn |
|---|---|
| V盻ｫa clone repo, c蘯ｧn t蘯｡o c蘯･u trﾃｺc ABW | `/abw-init` |
| Chﾆｰa bi蘯ｿt nﾃｪn b蘯ｯt ﾄ黛ｺｧu t盻ｫ ﾄ妥｢u | `/abw-ask` |
| Cﾃｳ cﾃ｢u h盻淑 d盻ｱ ﾃ｡n nhﾆｰng chﾆｰa rﾃｵ nﾃｪn tra c盻ｩu hay brainstorm | `/abw-ask` |
| C蘯ｧn tra c盻ｩu nhanh m盻冲 fact ﾄ妥｣ cﾃｳ trong wiki | `/abw-query` |
| C蘯ｧn phﾃ｢n tﾃｭch sﾃ｢u, so sﾃ｡nh, RCA, tradeoff | `/abw-query-deep` |
| D盻ｱ ﾃ｡n greenfield, chﾆｰa cﾃｳ raw/wiki | `/abw-bootstrap` |
| Mu盻創 ch盻奏 brief s蘯｣n ph蘯ｩm ho蘯ｷc scope | `/brainstorm` |
| Mu盻創 d盻ｱng n盻］ tri th盻ｩc t盻ｫ tﾃi li盻㎡ ngu盻渡 | `/abw-ingest` |
| Mu盻創 ﾄ妥ｳng gﾃｳi tri th盻ｩc cho NotebookLM | `/abw-pack` |
| Mu盻創 dry-run ho蘯ｷc sync package ﾄ妥｣ duy盻㏄ lﾃｪn NotebookLM | `/abw-sync` |
| Mu盻創 ki盻ノ tra s盻ｩc kh盻銃 wiki, grounding, manifest | `/abw-lint` |
| Mu盻創 ki盻ノ tra MCP ho蘯ｷc tr蘯｡ng thﾃ｡i hﾃng ﾄ黛ｻ｣i | `/abw-status` |
| Mu盻創 l蘯ｭp k蘯ｿ ho蘯｡ch th盻ｱc thi ho蘯ｷc chia task | `/plan` |
| Mu盻創 thi蘯ｿt k蘯ｿ k盻ｹ thu蘯ｭt ho蘯ｷc DB | `/design` |
| Mu盻創 mockup UI/UX ho蘯ｷc screen spec | `/visualize` |
| Mu盻創 b蘯ｯt tay vﾃo code | `/code` |
| Mu盻創 ch蘯｡y app c盻･c b盻・| `/run` |
| Mu盻創 s盻ｭa bug | `/debug` |
| Mu盻創 ki盻ノ tra b蘯ｱng test | `/test` |
| Mu盻創 tri盻ハ khai lﾃｪn mﾃｴi trﾆｰ盻拵g ﾄ妥ｭch | `/deploy` |
| Mu盻創 refactor khi ﾄ妥｣ rﾃｵ ph蘯｡m vi | `/refactor` |
| Mu盻創 review code ho蘯ｷc tr蘯｡ng thﾃ｡i d盻ｱ ﾃ｡n trﾆｰ盻嫩 audit sﾃ｢u hﾆ｡n | `/abw-review` |
| Mu盻創 audit code, s蘯｣n ph蘯ｩm, ho蘯ｷc b蘯｣o m蘯ｭt trong vﾃｲng delivery | `/audit` |
| Mu盻創 audit thay ﾄ黛ｻ品 ho蘯ｷc artifact theo ABW rubric | `/abw-audit` |
| Mu盻創 quay v盻・tr蘯｡ng thﾃ｡i an toﾃn sau thay ﾄ黛ｻ品 l盻擁 | `/abw-rollback` |
| Mu盻創 ch盻奏 pass/fail cu盻訴 cﾃｹng | `/abw-accept` |
| Mu盻創 ch蘯｡y toﾃn b盻・chain evaluation | `/abw-eval` |
| Mu盻創 lﾆｰu ti蘯ｿn ﾄ黛ｻ・vﾃ chu蘯ｩn b盻・handover | `/save-brain` |
| Mu盻創 khﾃｴi ph盻･c b盻訴 c蘯｣nh phiﾃｪn trﾆｰ盻嫩 | `/recap` |
| Mu盻創 bi蘯ｿt bﾆｰ盻嫩 ti蘯ｿp theo nﾃｪn lﾃm gﾃｬ | `/next` |
| Mu盻創 c蘯ｭp nh蘯ｭt command surface ABW | `/abw-update` |

---

## Mﾃｴ Hﾃｬnh 6 Lane

### 1. Khﾃ｡m phﾃ｡ vﾃ tﾆｰ duy

- `/abw-ask`: router chﾃｭnh theo intent
- `/abw-query`: tra c盻ｩu nhanh trﾃｪn wiki
- `/abw-query-deep`: suy lu蘯ｭn sﾃ｢u, RCA, tradeoff
- `/abw-bootstrap`: tﾆｰ duy cho bﾃi toﾃ｡n greenfield
- `/brainstorm`: ch盻奏 brief vﾃ scope MVP

### 2. D盻ｱng n盻］ tri th盻ｩc

- `/abw-init`: d盻ｱng ho蘯ｷc s盻ｭa c蘯･u trﾃｺc ABW
- `/abw-setup`: c蘯･u hﾃｬnh NotebookLM MCP
- `/abw-status`: ki盻ノ tra MCP vﾃ queue
- `/abw-ingest`: x盻ｭ lﾃｽ raw thﾃnh wiki
- `/abw-pack`: ﾄ妥ｳng gﾃｳi tri th盻ｩc thﾃnh package
- `/abw-sync`: dry-run ho蘯ｷc sync package lﾃｪn NotebookLM
- `/abw-lint`: audit s盻ｩc kh盻銃 wiki, grounding, manifest

### 3. Tri盻ハ khai s蘯｣n ph蘯ｩm

- `/plan`: l蘯ｭp k蘯ｿ ho蘯｡ch th盻ｱc thi
- `/design`: thi蘯ｿt k蘯ｿ k盻ｹ thu蘯ｭt vﾃ data
- `/visualize`: mockup UI/UX vﾃ layout
- `/code`: cﾃi ﾄ黛ｺｷt tﾃｭnh nﾄハg
- `/run`: ch蘯｡y 盻ｩng d盻･ng c盻･c b盻・- `/debug`: s盻ｭa l盻擁 hﾃnh vi ho蘯ｷc runtime
- `/test`: ki盻ノ tra ch蘯･t lﾆｰ盻｣ng b蘯ｱng test
- `/deploy`: tri盻ハ khai lﾃｪn mﾃｴi trﾆｰ盻拵g ﾄ妥ｭch
- `/refactor`: d盻肱 code an toﾃn khi ﾄ妥｣ rﾃｵ hﾃnh vi
- `/audit`: review code, s蘯｣n ph蘯ｩm, ho蘯ｷc b蘯｣o m蘯ｭt trong delivery loop

### 4. Phiﾃｪn lﾃm vi盻㌘ vﾃ ghi nh盻・
- `/abw-start`: m盻・phiﾃｪn lﾃm vi盻㌘ vﾃ ki盻ノ tra tr蘯｡ng thﾃ｡i
- `/save-brain`: lﾆｰu ti蘯ｿn ﾄ黛ｻ・ handover, vﾃ lessons learned
- `/recap`: khﾃｴi ph盻･c b盻訴 c蘯｣nh phiﾃｪn trﾆｰ盻嫩
- `/next`: g盻｣i ﾃｽ bﾆｰ盻嫩 ti蘯ｿp theo
- `/abw-wrap`: ch盻奏 phiﾃｪn vﾃ chu蘯ｩn b盻・quay l蘯｡i

### 5. ﾄ静｡nh giﾃ｡ vﾃ nghi盻㍊ thu

- `/abw-review`: review code ho蘯ｷc tr蘯｡ng thﾃ｡i d盻ｱ ﾃ｡n
- `/abw-audit`: audit workflow, tﾃi li盻㎡, thay ﾄ黛ｻ品, ho蘯ｷc ﾄ黛ｺｧu ra
- `/abw-meta-audit`: audit l蘯｡i bﾃ｡o cﾃ｡o audit
- `/abw-rollback`: quay v盻・tr蘯｡ng thﾃ｡i an toﾃn
- `/abw-accept`: ch盻奏 pass/fail cu盻訴 cﾃｹng
- `/abw-eval`: ch蘯｡y full evaluation chain

### 6. Ti盻㌻ ﾃｭch vﾃ C蘯･u hﾃｬnh

- `/customize`: ch盻穎h phong cﾃ｡ch giao ti蘯ｿp, persona, vﾃ autonomy
- `/help`: xem b蘯｣n ﾄ黛ｻ・l盻㌻h vﾃ quy蘯ｿt ﾄ黛ｻ杵h nhanh
- `/abw-update`: c蘯ｭp nh蘯ｭt command surface ABW vﾃo Gemini runtime local

---

## Ghi Nh盻・Nhanh

- N蘯ｿu b蘯｡n v盻ｫa clone repo, gﾃｵ `/abw-init` trﾆｰ盻嫩.
- N蘯ｿu workspace ﾄ妥｣ cﾃｳ c蘯･u trﾃｺc r盻妬, gﾃｵ `/abw-setup` ﾄ黛ｻ・n盻訴 grounding.
- N蘯ｿu b蘯｡n chﾆｰa bi蘯ｿt lane, gﾃｵ `/abw-ask`.
- N蘯ｿu b蘯｡n mu盻創 ch盻奏 ﾄ黛ｺｧu ra, gﾃｵ `/abw-eval`.
- N蘯ｿu b蘯｡n mu盻創 s盻ｭa code an toﾃn sau khi hi盻ブ rﾃｵ, gﾃｵ `/refactor`.