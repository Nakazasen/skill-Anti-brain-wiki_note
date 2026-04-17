---
description: Hướng dẫn lệnh và sơ đồ hệ thống Hybrid ABW
---

# WORKFLOW: /help

Bạn là người hướng dẫn của Hybrid ABW. Nhiệm vụ của bạn là giúp người dùng chọn đúng lệnh nhanh nhất, với ưu tiên rõ ràng cho khởi tạo workspace, routing, grounding, dự án tiếp diễn (continuation), và nghiệm thu.

---

## Bắt Đầu Đúng Chỗ

| Tình huống | Gõ |
|---|---|
| Vừa clone repo, chưa có cấu trúc ABW | `/abw-init` |
| Có việc cần làm nhưng chưa biết gõ gì | `/abw-ask` |
| Dự án đang dở, bị ngắt quãng giữa chừng | `/abw-resume` |
| Có kết quả, muốn nghiệm thu trước khi bàn giao | `/abw-eval` |

---

## Hệ Thống 6 Lane — Tham Khảo Đầy Đủ

### Lane 1: Khám phá và Tư duy (Ask & Think)

#### `/abw-ask` — Master Router
Entrypoint mặc định. Nhận ý định của bạn, tự động chọn lane phù hợp rồi chuyển tiếp. Bạn không cần nhớ hết tên lệnh — chỉ cần mô tả việc cần làm.

```text
/abw-ask tôi muốn thêm tính năng export PDF
→ [Router] Routing to /plan for feature_planning.
```

#### `/abw-query` — Tra cứu nhanh Wiki
Tìm câu trả lời nhanh từ dữ liệu đã có trong `wiki/`. Một lần đọc, không suy luận phức tạp. Nếu wiki chưa có dữ liệu, ghi vào `knowledge_gaps.json` thay vì bịa.

```text
/abw-query API endpoint nào xử lý đơn hàng?
→ Trả lời dựa trên wiki/api-routes.md, kèm trích dẫn nguồn.
```

#### `/abw-query-deep` — Suy luận Sâu (TTC Engine)
Dùng cho câu hỏi cần phân tích nhiều chiều: so sánh kiến trúc, tradeoff, RCA (Root Cause Analysis), hoặc giải quyết mâu thuẫn giữa các nguồn. Chạy 3–5 vòng suy luận có kiểm soát.

```text
/abw-query-deep nên dùng PostgreSQL hay MongoDB cho module inventory?
→ Phân tích đa chiều qua 5 pass: Decompose → Evidence → Ground → Critique → Repair.
```

#### `/abw-bootstrap` — Tư duy Greenfield
Dự án mới hoàn toàn, chưa có `raw/` hay `wiki/`. Thay vì bịa kiến thức, lệnh này tạo ra bộ reasoning state gồm: giả định, giả thuyết, nhật ký quyết định, và danh sách thí nghiệm rẻ nhất để xác minh.

```text
/abw-bootstrap tôi muốn làm app quản lý sức khỏe cho thú cưng
→ Tạo .brain/bootstrap/assumptions.json, hypotheses.json, validation_backlog.json
```

#### `/brainstorm` — Hội thảo Ý tưởng
Biến ý tưởng mờ nhạt thành bản brief rõ ràng: Problem → Users → MVP Features → Risks → Next Step. Dùng trước `/plan`.

```text
/brainstorm tôi muốn làm marketplace cho freelancer Việt Nam
→ Output: brief có Problem, Users, MVP feature list, risks, next step.
```

---

### Lane 2: Dựng nền Tri thức (Build Knowledge)

#### `/abw-init` — Khởi tạo Workspace
Tạo hoặc sửa cấu trúc ABW: các thư mục `raw/`, `processed/`, `wiki/`, `.brain/`, template, và file cấu hình. **Chạy đầu tiên sau khi clone repo.**

```text
/abw-init
→ Tạo cấu trúc thư mục, copy template vào .brain/, báo cáo kết quả.
```

#### `/abw-setup` — Cấu hình Grounding
Wizard hướng dẫn cài `nlm` CLI, đăng nhập NotebookLM, và xác nhận MCP bridge hoạt động. Nếu MCP không khả dụng, kích hoạt fallback mode.

```text
/abw-setup
→ Kiểm tra nlm CLI → đăng nhập NotebookLM → xác nhận kết nối MCP.
```

#### `/abw-status` — Health Check
Kiểm tra nhanh: MCP bridge có sống không, grounding queue có item nào pending không, hệ thống đang active hay fallback.

```text
/abw-status
→ MCP: active | Grounding queue: 3 pending | Mode: grounded
```

#### `/abw-ingest` — Nạp Tri thức
Đọc tài liệu trong `raw/`, trích xuất bằng chứng, cập nhật `processed/manifest.jsonl`, biên soạn thành note trong `wiki/`, và đưa vào grounding queue nếu cần.

```text
/abw-ingest
→ Xử lý raw/api-spec.pdf → tạo wiki/api-spec.md → cập nhật manifest.
```

#### `/abw-pack` — Đóng gói Tri thức
Gộp các note trong `wiki/` thành package gọn để upload lên NotebookLM (giải quyết giới hạn source). Chạy script Python, trình bày menu phê duyệt cho user.

```text
/abw-pack
→ Tạo notebooks/packages/<id>/ với package_manifest.json → chờ user approve.
```

#### `/abw-sync` — Đồng bộ lên NotebookLM
Dry-run (mặc định) hoặc upload thật package đã được duyệt lên NotebookLM. Không xóa source có sẵn, không upload nếu chưa xác nhận.

```text
/abw-sync
→ Dry-run: 5 sources sẽ upload → chờ user xác nhận → upload thật.
```

#### `/abw-lint` — Kiểm tra Tính nhất quán
Audit cấu trúc wiki, link integrity, mâu thuẫn nội dung, grounding health, và TTC signals.

```text
/abw-lint
→ 2 broken links, 1 contradicting claim between wiki/auth.md and wiki/api.md.
```

---

### Lane 3: Triển khai Sản phẩm (Build Product)

#### `/plan` — Lập kế hoạch
Biến yêu cầu tính năng thành kế hoạch thực thi: scope, feature list, phases, risks, và next step. Đưa ra 2–3 option (nhẹ / cân bằng / đầy đủ).

```text
/plan thêm tính năng export báo cáo PDF
→ Output: Problem, Users, Scope, MVP features, 3 phases, next step.
```

#### `/design` — Thiết kế Kỹ thuật
Thiết kế chi tiết: schema DB, API endpoints, data flow, system diagram. Dùng sau `/plan`, trước `/code`.

```text
/design thiết kế DB cho module quản lý đơn hàng
→ Output: ERD, API routes, data flow diagram.
```

#### `/visualize` — Mockup UI/UX
Dựng mockup giao diện, layout, wireframe, hoặc đặc tả màn hình. Không viết code thật.

```text
/visualize trang dashboard cho admin
→ Output: mockup image + screen spec.
```

#### `/code` — Viết Code
Cài đặt tính năng theo plan và design đã duyệt. Tuân thủ coding convention của dự án.

```text
/code implement API endpoint POST /orders theo design đã duyệt
→ Tạo/sửa file, chạy lint, báo cáo kết quả.
```

#### `/run` — Chạy Ứng dụng
Khởi động ứng dụng cục bộ, xác nhận app chạy được, báo cáo port và URL.

```text
/run
→ npm run dev → http://localhost:3000 → OK.
```

#### `/debug` — Sửa Lỗi
Tìm và sửa bug có hệ thống: reproduce → isolate → fix → verify.

```text
/debug API /orders trả về 500 khi quantity = 0
→ Reproduce → tìm root cause → fix → verify bằng test.
```

#### `/test` — Kiểm thử
Chạy test suite và kiểm tra chất lượng: unit test, integration test, hoặc manual verification.

```text
/test chạy test cho module orders
→ pytest tests/orders/ → 12 passed, 0 failed.
```

#### `/deploy` — Triển khai
Deploy lên môi trường đích (staging / production). Kiểm tra pre-deploy checklist.

```text
/deploy lên staging
→ Build → push → verify health check → báo cáo URL.
```

#### `/refactor` — Tối ưu Code
Dọn dẹp, tái cấu trúc code **sau khi đã hiểu rõ hành vi**. Không thay đổi hành vi bên ngoài.

```text
/refactor tách logic validation ra khỏi controller
→ Extract → move → verify tests vẫn pass.
```

#### `/audit` — Kiểm tra Chất lượng (Delivery Loop)
Review thực tế về code, sản phẩm, hoặc bảo mật trong quá trình phát triển. **Không phải** cổng nghiệm thu cuối — dùng `/abw-eval` cho việc đó.

```text
/audit review security cho module authentication
→ Delivery Audit Report: Findings, Verification Gaps, Recommended Next Action.
```

---

### Lane 4: Phiên làm việc và Ghi nhớ (Session & Memory)

#### `/abw-start` — Mở Phiên Làm việc
Bắt đầu phiên làm việc có kiểm tra trạng thái, có định hướng, có fallback rõ ràng.

```text
/abw-start
→ Load .brain/ state → kiểm tra grounding → gợi ý bước đầu tiên.
```

#### `/abw-resume` — Khôi phục Dự án (Continuation Kernel)
Dùng khi dự án bị ngắt quãng (hết quota, mất context, đổi model). Đọc `.brain/` state, chạy Continuation Gate, chọn **đúng 1 bước an toàn** tiếp theo. **Không tự động thực thi** — luôn hỏi user trước.

```text
/abw-resume
→ [Resume] Project: ecommerce | Phase: backend
→ Next safe step: step-003 "Add order validation" (safety_score: 91.2)
→ Execute this step? (yes / no / show alternatives)
```

#### `/abw-execute` — Thực thi Có Giám sát
Chạy **đúng 1 bước** đã được `/abw-resume` phê duyệt, trong phạm vi file đã khóa. Ghi log append-only vào `.brain/step_history.jsonl`. Nếu cần mở rộng scope, dừng lại và quay về `/abw-resume`.

```text
/abw-execute
→ Prepare step-003 → edit 2 files → run tests → record outcome: success.
```

#### `/abw-learn` — Ghi Bài học Hành vi
Biến một correction của user thành record tái sử dụng trong `.brain/lessons_learned.jsonl`. Chỉ ghi lesson có giá trị lâu dài, không ghi note một lần.

```text
/abw-learn "Đừng dùng regex để parse HTML; dùng parser phù hợp."
→ Đã ghi: scope=backend, priority=high, expires_at=null.
```

#### `/save-brain` — Lưu Tiến độ
Snapshot toàn bộ trạng thái phiên làm việc: thay đổi, quyết định, lessons learned, và tạo điểm handover cho phiên sau. File đích: `.brain/session.json`, `.brain/brain.json`, `.brain/handover.md`.

```text
/save-brain
→ Đã lưu: 3 file changed, 1 lesson learned, handover.md updated.
```

#### `/recap` — Khôi phục Bối cảnh
Đọc `.brain/handover.md`, `session.json`, `brain.json` và tóm tắt: dự án đang ở đâu, task cuối là gì, bước tiếp theo nên làm gì.

```text
/recap
→ Dự án: ecommerce | Task cuối: implement cart API | Next: /test
```

#### `/next` — Gợi ý Bước Tiếp theo
Phân tích trạng thái hiện tại của repo và gợi ý **1 lệnh** nên gõ tiếp. Khác `/abw-resume` ở chỗ: `/next` là gợi ý nhẹ, `/abw-resume` chạy Continuation Kernel governance.

```text
/next
→ CURRENT STATE: plan done, design done, no code yet.
→ NEXT STEP: /code
→ WHY: Plan và design đã sẵn sàng, chưa có implementation.
```

#### `/abw-wrap` — Đóng Phiên
Kết thúc phiên làm việc: lưu tiến độ, tạo handover, nhắc những thay đổi cần ingest hoặc nghiệm thu.

```text
/abw-wrap
→ Saved state → 2 files need /abw-ingest → 1 change needs /abw-eval.
```

---

### Lane 5: Đánh giá và Nghiệm thu (Evaluation & Acceptance)

*Tất cả lệnh trong lane này hoạt động theo cơ chế Gated Execution — phải có bằng chứng mới được pass.*

#### `/abw-review` — Đánh giá Tổng thể
Review code, thay đổi, hoặc hiện trạng dự án. Đọc hiểu, nhận xét, chỉ ra bước tiếp theo. Nhẹ hơn `/abw-audit`.

```text
/abw-review xem lại module authentication
→ Nhận xét: thiếu rate limiting, JWT expiry quá dài. → Gợi ý: /debug hoặc /code.
```

#### `/abw-audit` — Tự Audit theo Rubric ABW
Audit chi tiết thay đổi hoặc artifact theo Hybrid ABW Rubric: findings, evidence, residual risks, và verdict.

```text
/abw-audit kiểm tra thay đổi vừa push
→ Findings: 2 medium, 1 low | Evidence: file diffs, test output | Verdict: needs_fix.
```

#### `/abw-meta-audit` — Audit báo cáo Audit
Kiểm tra lại chính báo cáo audit trước đó: có overclaim không, bằng chứng đủ chưa, verdict có quá lạc quan không.

```text
/abw-meta-audit
→ Audit report overclaims PASS but test coverage is only 40%. Revised: needs_fix.
```

#### `/abw-rollback` — Quay lại Trạng thái An toàn
Phục hồi hệ thống khi thay đổi vừa rồi gây lỗi hoặc đi sai hướng.

```text
/abw-rollback
→ Reverted 3 files to last safe commit → verified app runs.
```

#### `/abw-accept` — Cổng Nghiệm thu Cuối cùng
Chạy Evaluation Kernel v1. Quyết định artifact có đủ bằng chứng để chấp nhận hay không. Nếu thiếu test hoặc evidence, **reject** và yêu cầu sửa.

```text
/abw-accept
→ Verdict: PASS | Evidence: tests green, audit clean, no open gaps.
```

hoặc:

```text
/abw-accept
→ Verdict: REJECTED | Reason: unit tests missing, no verification evidence.
```

#### `/abw-eval` — Chạy Full Evaluation Chain
Orchestrate toàn bộ chuỗi: `/abw-audit` → `/abw-meta-audit` → rubric scoring → `/abw-accept`. Dùng khi muốn nghiệm thu end-to-end.

```text
/abw-eval
→ Audit: 2 findings → Meta-audit: no overclaim → Score: 8.5/10 → Verdict: PASS.
```

#### `/finalization` — Kiểm tra Trạng thái Kết thúc
Áp dụng finalization profile và chạy `scripts/finalization_check.py` trên finalization block trước khi trả lời cuối.

```text
/finalization
→ current_state: verified | evidence: direct runtime trace | verdict: pass.
```

---

### Lane 6: Tiện ích và Cấu hình (Utility & Config)

#### `/customize` — Cá nhân hóa AI
Thay đổi phong cách giao tiếp, persona, mức độ tự quyết (autonomy), và ngôn ngữ ưu tiên. Lưu vào `.brain/preferences.json`.

```text
/customize ngôn ngữ tiếng Việt, giải thích đơn giản
→ Saved: language=vi, technical_level=basic.
```

#### `/help` — Tài liệu này
Hiển thị bản đồ lệnh, mô tả chi tiết, và ví dụ sử dụng cho toàn bộ hệ thống.

#### `/abw-update` — Cập nhật Command Surface
Chạy lại installer để đăng ký command surface ABW mới nhất từ repo vào Gemini runtime local. Sau khi chạy, cần reload IDE.

```text
/abw-update
→ Installer chạy → 110 files installed → reload IDE để thấy lệnh mới.
```

---

## Lưu ý kỹ thuật

**Alias:** Lệnh `/save-brain` trong slash menu tương ứng với file `save_brain.md` trong repo (dấu gạch ngang vs gạch dưới). Đây là alias có chủ đích, không phải lỗi.

**Luồng chuẩn cho dự án mới:**
```text
/abw-init → /abw-setup → /brainstorm → /plan → /design → /code → /test → /abw-eval
```

**Luồng tiếp tục dự án đang dở:**
```text
/recap (hoặc /abw-resume) → /abw-execute → /abw-eval
```

**Luồng nạp tri thức:**
```text
/abw-ingest → /abw-lint → /abw-pack → /abw-sync
```
