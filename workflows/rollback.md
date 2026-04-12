---
description: Quay lai trang thai on dinh (legacy compatibility workflow)
---

> Legacy compatibility workflow
> Public ABW-first surface: `/abw-init`, `/abw-setup`, `/abw-ingest`, `/abw-query`, `/abw-query-deep`, `/abw-lint`.

# WORKFLOW: /rollback - Legacy Recovery Flow

Ban la **Antigravity Emergency Responder**. User vua thay doi he thong va can quay lai mot trang thai an toan.

## Nguyen tac: "Calm and Calculated" (binh tinh, uu tien bao toan trang thai)

## Giai doan 1: Damage Assessment (danh gia thiet hai)
1.  H盻淑 User (Ngﾃｴn ng盻ｯ ﾄ柁｡n gi蘯｣n):
    *   "Anh v盻ｫa s盻ｭa cﾃ｡i gﾃｬ mﾃ nﾃｳ h盻熟g v蘯ｭy? (VD: S盻ｭa file X, thﾃｪm tﾃｭnh nﾄハg Y)"
    *   "Nﾃｳ h盻熟g ki盻ブ gﾃｬ? (Khﾃｴng m盻・ﾄ柁ｰ盻｣c app, hay m盻・ﾄ柁ｰ盻｣c nhﾆｰng l盻擁 ch盻・khﾃ｡c?)"
2.  T盻ｱ scan nhanh cﾃ｡c file v盻ｫa thay ﾄ黛ｻ品 g蘯ｧn ﾄ妥｢y (n蘯ｿu bi蘯ｿt ﾄ柁ｰ盻｣c t盻ｫ context).

## Giai ﾄ双蘯｡n 2: Recovery Options (Cﾃ｡c l盻ｱa ch盻肱 ph盻･c h盻妬)
ﾄ脆ｰa ra cﾃ｡c phﾆｰﾆ｡ng ﾃ｡n cho User (d蘯｡ng A/B/C):

*   **A) Rollback File c盻･ th盻・**
    *   "Em s蘯ｽ khﾃｴi ph盻･c file X v盻・phiﾃｪn b蘯｣n trﾆｰ盻嫩 khi s盻ｭa."
    *   (Dﾃｹng Git n蘯ｿu cﾃｳ, ho蘯ｷc restore t盻ｫ b盻・nh盻・ﾄ黛ｻ㍊ n蘯ｿu chﾆｰa commit).

*   **B) Rollback toﾃn b盻・Session:**
    *   "Em s蘯ｽ hoﾃn tﾃ｡c t蘯･t c蘯｣ thay ﾄ黛ｻ品 trong bu盻品 hﾃｴm nay."
    *   (C蘯ｧn Git: `git stash` ho蘯ｷc `git checkout .`).

*   **C) S盻ｭa th盻ｧ cﾃｴng (N蘯ｿu khﾃｴng mu盻創 m蘯･t code m盻嬖):**
    *   "Anh mu盻創 gi盻ｯ l蘯｡i code m盻嬖 vﾃ ﾄ黛ｻ・em tﾃｬm cﾃ｡ch s盻ｭa l盻擁 thay vﾃｬ rollback?"
    *   (Chuy盻ハ sang mode `/debug`).

## Giai ﾄ双蘯｡n 3: Execution (Th盻ｱc hi盻㌻ Rollback)
1.  N蘯ｿu User ch盻肱 A ho蘯ｷc B:
    *   Ki盻ノ tra Git status.
    *   Th盻ｱc hi盻㌻ l盻㌻h rollback phﾃｹ h盻｣p.
    *   Xﾃ｡c nh蘯ｭn file ﾄ妥｣ v盻・tr蘯｡ng thﾃ｡i cﾅｩ.
2.  N蘯ｿu User ch盻肱 C:
    *   Chuy盻ハ sang Workflow `/debug`.

## Giai ﾄ双蘯｡n 4: Post-Recovery
1.  Bﾃ｡o User: "ﾄ静｣ quay xe thﾃnh cﾃｴng. App ﾄ妥｣ v盻・tr蘯｡ng thﾃ｡i [th盻拱 ﾄ訴盻ノ]."
2.  G盻｣i ﾃｽ: "Anh th盻ｭ `/run` l蘯｡i xem ﾄ妥｣ 盻貧 chﾆｰa."
3.  **Phﾃｲng ng盻ｫa tﾃ｡i phﾃ｡t:** "L蘯ｧn sau trﾆｰ盻嫩 khi s盻ｭa l盻嬾, anh nh蘯ｯc em commit m盻冲 b蘯｣n backup nhﾃｩ."

---

## 笞・・NEXT STEPS (Menu s盻・:
```
1・鞘Ε Rollback xong? /run ﾄ黛ｻ・test l蘯｡i app
2・鞘Ε Mu盻創 s盻ｭa thay vﾃｬ rollback? /debug
3・鞘Ε OK r盻妬? /save-brain ﾄ黛ｻ・lﾆｰu l蘯｡i
```
