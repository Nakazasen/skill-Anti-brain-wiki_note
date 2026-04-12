# Hybrid ABW Audit Prompt

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

