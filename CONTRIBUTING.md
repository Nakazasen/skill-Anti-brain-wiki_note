# Đóng Góp cho Hybrid ABW

Cảm ơn bạn muốn đóng góp cho Hybrid ABW.

## Cách Đóng Góp

### Báo Lỗi
1. Kiểm tra [Issues](https://github.com/Nakazasen/skill-Anti-brain-wiki_note/issues) xem lỗi đã được báo chưa.
2. Tạo issue mới bằng template `Bug Report`.
3. Mô tả rõ bước tái hiện, kết quả mong đợi, và kết quả thực tế.

### Đề Xuất Tính Năng
1. Tạo issue mới bằng template `Feature Request`.
2. Giải thích vấn đề bạn đang gặp và cách tính năng mới sẽ giải quyết nó.

### Gửi Code
1. Fork repo này.
2. Tạo branch mới: `git checkout -b feature/ten-tinh-nang`
3. Code và test trên môi trường liên quan.
4. Commit với message rõ ràng, ví dụ: `feat: add reusable lesson checks`
5. Push branch và tạo pull request.

## Quy Tắc

- Giữ thay đổi nhỏ, rõ phạm vi, và có thể review độc lập.
- Dùng [Conventional Commits](https://www.conventionalcommits.org/) khi phù hợp.
- Test trên Windows nếu đụng `install.ps1`.
- Test trên macOS/Linux nếu đụng `install.sh`.
- Cập nhật README hoặc docs nếu public surface thay đổi.
- Không claim grounding, evaluation, hay compatibility nếu chưa verify.

## Cấu Trúc Thư Mục

```text
skill-Anti-brain-wiki_note/
|- workflows/        # Public command workflows
|- skills/           # Lower-level execution and reasoning rules
|- schemas/          # JSON schemas
|- templates/        # Example state and policy files
|- docs/             # Architecture and maintainer docs
|- examples/         # Minimal example workspaces
|- install.ps1       # Windows installer
`- install.sh        # macOS/Linux installer
```

## Cần Hỗ Trợ?

- Mở [Issues](https://github.com/Nakazasen/skill-Anti-brain-wiki_note/issues) nếu bạn gặp lỗi hoặc cần làm rõ hành vi.
- Nếu repo bật Discussions sau này, ưu tiên dùng Discussions cho câu hỏi mở và thảo luận thiết kế.

Mọi đóng góp tử tế đều có giá trị.
