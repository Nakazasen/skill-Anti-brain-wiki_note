# Hybrid ABW Meta-Audit Prompt

Copy prompt này vào Gemini Flash khi muốn nó audit lại chính báo cáo audit trước đó của nó.

```text
Bạn đang làm META-AUDIT cho chính báo cáo audit trước đó của mình trong Hybrid ABW.

Mục tiêu:
- không audit lại từ đầu một cách mù quáng
- kiểm tra xem báo cáo audit trước có trung thực, có đủ bằng chứng, và có chấm đúng hay không
- phát hiện chỗ nào bạn đã kết luận quá tay, thiếu evidence, hoặc nhầm giữa fact và inference

Bối cảnh:
- đã có một patch trước đó
- đã có một báo cáo audit trước đó
- bây giờ bạn phải audit lại CHÍNH báo cáo audit đó

Yêu cầu bắt buộc:
1. Đọc lại:
   - báo cáo audit trước đó của chính bạn
   - các file thực tế liên quan đến patch
2. So sánh:
   - bạn đã claim điều gì
   - file thực tế chứng minh được gì
3. Không được tự bảo vệ báo cáo cũ
4. Nếu báo cáo trước kết luận quá mạnh, phải nói rõ
5. Nếu báo cáo trước thiếu evidence, phải nói rõ
6. Nếu báo cáo trước đúng, phải nói vì sao đúng

Báo cáo theo format này:

1. Audit Report Under Review
- tóm tắt ngắn báo cáo audit cũ đã kết luận gì

2. Meta-Findings
- liệt kê các điểm trong báo cáo cũ bị:
  - overclaim
  - under-evidenced
  - fact/inference confusion
  - scope drift
  - đúng và có căn cứ

3. Evidence Check
- với mỗi claim quan trọng, ghi:
  - claim cũ
  - file/artefact liên quan
  - verdict:
    - supported
    - partially supported
    - unsupported

4. Scoring Review
- chấm lại các mục liên quan trong Hybrid ABW Rubric
- nếu báo cáo cũ chấm quá cao, phải hạ xuống
- nếu báo cáo cũ chấm đúng, giữ nguyên

5. Corrected Verdict
Chỉ chọn một:
- FAIL
- PASS WITH CRITICAL GAPS
- PASS WITH MINOR GAPS
- PASS

6. What Should Happen Next
- nếu báo cáo cũ quá lạc quan: nêu patch/audit tiếp theo cần làm
- nếu báo cáo cũ đủ tốt: nói rõ vì sao có thể chốt

Quy tắc:
- không được viết lại audit cũ theo kiểu marketing
- không được bỏ qua mâu thuẫn giữa báo cáo và artifact thật
- phải phân biệt rõ:
  - fact = điều được chứng minh từ file / command / output
  - inference = suy luận hợp lý nhưng chưa được chứng minh trực tiếp
- nếu chưa đủ bằng chứng, không được giữ verdict mạnh
```

