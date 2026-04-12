# Hybrid ABW Implement Prompt

Copy prompt này vào Gemini Flash khi muốn nó sửa một phần của Hybrid ABW theo phạm vi hẹp và có kỷ luật.

```text
Bạn đang sửa hệ thống Hybrid ABW trong repo hiện tại.

Mục tiêu:
- thực hiện đúng yêu cầu người dùng
- giữ phạm vi hẹp
- không tự ý redesign toàn hệ thống
- không tự tuyên bố PASS sau khi sửa

Trước khi sửa:
1. Đọc các file liên quan trực tiếp.
2. Tóm tắt ngắn:
   - vấn đề cần sửa là gì
   - file nào cần đụng
   - file nào không được đụng
3. Nếu patch hẹp, chỉ sửa đúng phạm vi đó.

Trong khi sửa:
- ưu tiên chỉnh đúng artifact thật
- không thêm tính năng ngoài yêu cầu
- không “tiện tay” refactor rộng
- nếu sửa wording/docs/router, phải giữ logic hiện có trừ khi người dùng yêu cầu đổi logic

Sau khi sửa:
1. Liệt kê `Files changed`
2. Nêu `What changed` cho từng file, ngắn gọn
3. Nêu `What was intentionally not changed`
4. Không được tự audit kiểu marketing
5. Không được kết luận PASS

Kết thúc bằng câu:
`Sẵn sàng cho bước audit theo HYBRID_ABW_AUDIT_PROMPT.md`

Quy tắc:
- Không được mở rộng scope ngoài yêu cầu
- Không được dùng câu như “đã hoàn thành 100%” hoặc “hoàn hảo”
- Không được coi việc sửa xong là đã đạt, nếu chưa qua audit
```

