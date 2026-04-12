# Hybrid ABW Rubric

Rubric này dùng để chấm Gemini Flash khi sửa bất kỳ phần nào trong Hybrid ABW.

Mục tiêu:
- ép model sửa đúng phạm vi
- ép model tự audit nghiêm túc
- tránh fake success
- giữ command model, router, grounding, session, và installer ở mức dễ vận hành

---

## Cách dùng nhanh

Dùng rubric này theo 3 vòng:

1. **Implement**
   - Chỉ cho Gemini Flash sửa.
   - Không cho tuyên bố PASS ngay.

2. **Self-audit**
   - Bắt Gemini Flash audit lại theo rubric này.
   - Yêu cầu evidence, residual risks, và verdict.

3. **Meta-audit**
   - Người review đọc lại artifact thật.
   - So sánh báo cáo của Gemini Flash với file thực tế.

---

## Nguyên tắc chấm chung

Mọi thay đổi trong Hybrid ABW phải được chấm theo 3 tầng:

1. **Artifact correctness**
   - file có thực sự được sửa đúng không
   - nội dung có đọc được không
   - command surface có đồng bộ không

2. **Behavior correctness**
   - router / workflow có định tuyến đúng ý định không
   - lane có rõ ràng không
   - user mới có biết nên gọi gì không

3. **Audit integrity**
   - Gemini Flash có chứng minh bằng file thật không
   - có nêu residual risks không
   - có tránh tự nhận PASS quá sớm không

Không chấp nhận các kết luận kiểu:
- "đã hoàn thành 100%"
- "đã sạch hoàn toàn"
- "không còn bất kỳ lỗi nào"

nếu không có bằng chứng từ artifact thật.

---

## Thang điểm chung

Mỗi hạng mục được chấm theo thang:

- `0` = fail rõ ràng
- `1` = có tiến triển nhưng yếu
- `2` = đạt mức dùng được, còn gap
- `3` = tốt, ổn định, dễ tin

Nếu một hạng mục không liên quan trực tiếp đến patch hiện tại, ghi:
- `Not targeted`

không được tự động chấm `3/3`.

---

## 1. Command Surface Clarity

### Mục tiêu
Người dùng nhìn hệ thống phải biết:
- bắt đầu từ đâu
- khi nào dùng `/abw-ask`
- khi nào dùng workflow discovery / knowledge / delivery / session

### Tiêu chí PASS
- Có command model rõ ràng, nhất quán
- `/abw-ask` được xác định là entrypoint mặc định
- Các lane được mô tả rõ:
  - Ask & Think
  - Build Knowledge
  - Build Product
  - Session & Memory
- `help.md`, `README.md`, `next.md`, `wiki/index.md` không mâu thuẫn nhau

### Dấu hiệu FAIL
- command list giữa các file không đồng bộ
- user vẫn phải tự đoán nên gọi gì
- `/abw-ask`, `/next`, `/help` chồng lấn không giải thích
- "legacy compatibility" còn làm người dùng hiểu đây là 2 hệ ghép tạm

### Cách audit
Đọc tối thiểu:
- `workflows/help.md`
- `workflows/README.md`
- `workflows/next.md`
- `wiki/index.md`

### Điểm
- `0` = rối, phân mảnh
- `1` = có mô hình nhưng mâu thuẫn
- `2` = tương đối rõ nhưng còn chỗ chồng lấn
- `3` = rõ và nhất quán

---

## 2. Router Behavior Quality

### Mục tiêu
`/abw-ask` phải route đúng intent, minh bạch, không thành hộp đen.

### Tiêu chí PASS
- Có logic phân biệt ít nhất:
  - Query vs Brainstorm
  - Recap vs Next
  - Ask vs Help
- Có mixed-intent handling:
  - chọn bước đầu tiên
  - ghi follow-up command
- Có routing log rõ ràng:
  - `[Router] Routing to ...`
- Có priority ladder hoặc equivalent decision order

### Dấu hiệu FAIL
- `/abw-ask` chỉ nói chung chung "smart router"
- mixed intent không có chiến lược
- confusion intent không route sang `/help`
- router mapping có nhưng không rõ tiebreak

### Cách audit
Đọc:
- `workflows/abw-ask.md`
- `skills/abw-router.md`

Yêu cầu Gemini Flash chạy behavior audit với ít nhất 12 prompt gồm:
- greenfield idea
- product discovery
- fast knowledge query
- deep knowledge query
- resume session
- save progress
- delivery planning
- implementation
- debugging
- "I don't know what command to use"
- "what should I do next"
- mixed request kiểu "summarize then plan"

### Điểm
- `0` = router mơ hồ
- `1` = router có mapping nhưng dễ lệch
- `2` = router tốt, còn vài ambiguity
- `3` = router rõ và có tiebreak minh bạch

---

## 3. Knowledge / Grounding Integrity

### Mục tiêu
ABW phải giữ được bản chất wiki-first, grounded, no fake success.

### Tiêu chí PASS
- `/abw-init`, `/abw-setup`, `/abw-status`, `/abw-ingest`, `/abw-lint` còn vai trò rõ
- docs vẫn phản ánh fallback-first
- không làm discovery / delivery lấn át knowledge lane
- `wiki/index.md` phản ánh đúng vai trò của knowledge layer

### Dấu hiệu FAIL
- sửa command model làm ABW mất bản sắc grounding
- `/abw-ask` route hết sang build flow mà quên knowledge checks
- docs không còn nhắc fallback / grounded / queue health

### Cách audit
Đọc:
- `wiki/index.md`
- `workflows/README.md`
- `workflows/help.md`

### Điểm
- `0` = đánh mất ABW identity
- `1` = vẫn còn nhưng mờ
- `2` = ổn
- `3` = rõ ràng và nhất quán

---

## 4. Session / Memory Continuity

### Mục tiêu
Người dùng phải hiểu khi nào dùng:
- `/save-brain`
- `/recap`
- `/next`

### Tiêu chí PASS
- `save-brain` có vai trò rõ: save / handover
- `recap` có vai trò rõ: restore / resume / past context
- `next` có vai trò rõ: next action recommendation
- 3 lệnh này không bị treo lơ lửng ngoài hệ thống

### Dấu hiệu FAIL
- `save-brain` / `recap` chỉ tồn tại trên giấy
- `next` bị lẫn với `/abw-ask`
- wording mơ hồ giữa past / future / recommendation

### Cách audit
Đọc:
- `workflows/save_brain.md`
- `workflows/recap.md`
- `workflows/next.md`
- `workflows/help.md`

### Điểm
- `0` = rời rạc
- `1` = tồn tại nhưng mơ hồ
- `2` = khá rõ
- `3` = rõ ràng và tự nhiên

---

## 5. Delivery Lane Coherence

### Mục tiêu
Nhóm `/plan`, `/design`, `/code`, `/run`, `/debug`, `/test`, `/deploy` phải sống trong hệ thống mới mà không còn "mồ côi".

### Tiêu chí PASS
- delivery lane được định vị rõ trong command model
- không còn wording làm user hiểu đây là luồng phụ
- router có thể handoff sang `/plan` hoặc `/debug` khi phù hợp

### Dấu hiệu FAIL
- các file delivery vẫn tự gọi mình là legacy
- docs chính không nhắc delivery lane
- router không biết route sang delivery

### Cách audit
Đọc:
- `workflows/plan.md`
- `workflows/design.md`
- `workflows/code.md`
- `workflows/debug.md`
- `workflows/help.md`

### Điểm
- `0` = delivery lane bị bỏ quên
- `1` = có nhắc nhưng vẫn gượng ép
- `2` = khá tốt
- `3` = tích hợp tự nhiên

---

## 6. Encoding / Rendering Integrity

### Mục tiêu
Không được kết luận sai giữa:
- file hỏng thật
- terminal hiển thị sai
- editor hiển thị đúng

### Tiêu chí PASS
- artifact đọc được trong editor / file view
- nếu terminal lỗi, phải gọi đúng tên: rendering / codepage issue
- không tuyên bố mojibake nếu chỉ có terminal fail
- không tuyên bố clean nếu file view vẫn hỏng

### Dấu hiệu FAIL
- kết luận encoding dựa trên 1 nguồn
- đổi verdict liên tục vì method kiểm tra không ổn định
- không phân biệt bytes / terminal / editor

### Cách audit
Bắt Gemini Flash báo theo 3 lớp:
1. file rendering
2. terminal rendering
3. final judgment

### Điểm
- `0` = audit encoding sai
- `1` = có kiểm tra nhưng kết luận yếu
- `2` = khá tốt
- `3` = phân biệt đúng 3 lớp

---

## 7. Installer / Runtime Robustness

### Mục tiêu
Người clone repo từ GitHub rồi setup không bị rơi vào trạng thái half-installed.

### Tiêu chí PASS
- installers có fail-closed cho phần critical
- có verify sau install
- local clone mode hoạt động
- `GEMINI.md` merge an toàn
- verify đủ workflow ABW và skills ABW

### Dấu hiệu FAIL
- cài đặt xong nhưng thiếu workflow
- block ABW mất khỏi `GEMINI.md`
- script nuốt lỗi rồi báo thành công

### Cách audit
Đọc:
- `install.ps1`
- `install.sh`

Kiểm:
- workflow verify
- skills verify
- `GEMINI.md` verify
- fail-closed behavior

### Điểm
- `0` = nguy hiểm
- `1` = có sửa nhưng chưa kín
- `2` = đủ tốt
- `3` = robust

---

## 8. Scope Discipline

### Mục tiêu
Gemini Flash phải sửa đúng phạm vi được yêu cầu.

### Tiêu chí PASS
- sửa đúng file cần thiết
- không làm phồng phạm vi
- không biến patch nhỏ thành refactor lớn

### Dấu hiệu FAIL
- user yêu cầu patch hẹp nhưng nó sửa nửa repo
- thêm "tiện tay" feature mới
- audit không đúng phạm vi

### Cách audit
So sánh:
- yêu cầu đầu bài
- file changed
- final report

### Điểm
- `0` = trôi scope nặng
- `1` = hơi trôi
- `2` = chấp nhận được
- `3` = rất kỷ luật

---

## 9. Audit Integrity

### Mục tiêu
Gemini Flash phải biết tự audit tử tế.

### Tiêu chí PASS
- có `Findings`
- có `Evidence`
- có `Residual Risks`
- có `Verdict`
- nếu có gap thì nhận gap
- không tự nhận PASS sớm khi artifact chưa sạch

### Dấu hiệu FAIL
- chỉ viết success summary
- không có bằng chứng
- nói "no issues" khi artifact còn lỗi
- không phân biệt fact và inference

### Cách audit
Chấm chính báo cáo của Gemini Flash.

### Điểm
- `0` = audit giả
- `1` = audit hời hợt
- `2` = audit khá
- `3` = audit tốt, có tự sửa sai

---

## 10. Overall Verdict Scale

Sau khi chấm từng mục, tổng kết theo 1 trong 4 mức:

- **FAIL**
  - có blocker rõ
  - artifact hoặc behavior chưa dùng được

- **PASS WITH CRITICAL GAPS**
  - hướng đi đúng
  - nhưng còn lỗi lớn chưa được phép đóng

- **PASS WITH MINOR GAPS**
  - phần chính ổn
  - còn vài điểm nhỏ cần dọn

- **PASS**
  - artifact, behavior, audit đều đủ tốt để chốt

---

## 11. Mẫu Prompt Audit Chuẩn

Copy prompt này vào Gemini Flash sau mỗi lần sửa:

```text
Hãy tự audit thay đổi vừa rồi theo Hybrid ABW Rubric.

Bắt buộc báo cáo theo các mục:
1. Files changed
2. Findings
3. Evidence
4. Residual risks
5. Rubric scoring
   - Command Surface Clarity
   - Router Behavior Quality
   - Knowledge / Grounding Integrity
   - Session / Memory Continuity
   - Delivery Lane Coherence
   - Encoding / Rendering Integrity
   - Installer / Runtime Robustness
   - Scope Discipline
   - Audit Integrity
6. Final verdict

Quy tắc:
- Không được chỉ viết summary thành công
- Nếu một hạng mục không liên quan đến patch hiện tại, ghi "Not targeted" chứ không được tự chấm 3/3
- Nếu artifact thực tế chưa sạch, không được chấm PASS
- Phải phân biệt rõ fact và inference
```

---

## 12. Khuyến nghị quy trình dùng

Dùng 3 vòng cố định:

### Vòng 1: Implement
- chỉ cho Gemini Flash sửa

### Vòng 2: Self-audit
- bắt nó audit theo rubric

### Vòng 3: Meta-audit
- người review đọc lại artifact thật
- chỉ ra:
  - nó chấm sai ở đâu
  - nó "nổ" ở đâu
  - nó bỏ sót bằng chứng ở đâu

Đây là vòng giúp Gemini Flash thông minh hơn theo thời gian.
