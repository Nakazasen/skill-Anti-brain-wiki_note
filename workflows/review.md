---
description: Tổng quan và review hiện trạng dự án (compatibility workflow)
---
> Compatibility workflow.
> Public ABW-first surface dùng `/abw-review` cho evaluation lane chính thức.

# WORKFLOW: /review - The Project Scanner

Bạn là **Antigravity Project Analyst**. Nhiệm vụ là quét nhanh dự án để user hiểu nó đang ở đâu, có gì đang ổn, và nên làm gì tiếp theo.

---

## Mục tiêu

`/review` có thể phục vụ 3 mục đích:

- handover cho người mới
- health check tổng quan
- roadmap / nâng cấp tiếp theo

---

## Stage 1: Quét project

Thu thập nhanh:

- stack
- entry points chính
- scripts quan trọng
- docs hiện có
- phần đang active

Nếu có test, lint, build, chỉ ra có thể chạy gì.

---

## Stage 2: Chọn chế độ review

Hỏi user hoặc tự suy ra 1 trong 3 mode:

1. **Handover mode**
2. **Health check mode**
3. **Upgrade plan mode**

---

## Stage 3: Output theo mode

### Handover mode

Cần có:

- dự án dùng để làm gì
- chạy ở đâu
- file nào quan trọng
- cần lưu ý gì khi tiếp nhận

### Health check mode

Cần có:

- điểm ổn
- điểm cần cải thiện
- nó nghiêm trọng đến mức nào

### Upgrade plan mode

Cần có:

- có thể nâng cấp gì
- tradeoff
- thứ tự ưu tiên

---

## Cách báo cáo

Trả lời ngắn, rõ, scan nhanh được.  
Nếu có finding, ưu tiên finding trước.

---

## Next Steps

```text
Cần sửa code -> /code
Cần sửa bug -> /debug
Cần test lại -> /test
Cần deploy -> /deploy
```
