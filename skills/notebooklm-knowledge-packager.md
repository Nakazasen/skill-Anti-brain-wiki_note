---
name: notebooklm-knowledge-packager
description: Quy trình hệ thống phân loại, gộp (compress) và kiểm định wiki notes để chuẩn bị đẩy lên NotebookLM mà không vượt qua source limit.
---

# Kỹ năng: ABW Knowledge Packager

## Mục tiêu
Dựng một gói tri thức đầu ra (Package Output) dựa trên `wiki/` note và `processed/manifest.jsonl` tuân thủ nguyên tắc giới hạn nguồn (source limit) của định dạng NotebookLM. 

## Quy tắc (Guiding Principles)
1. **Không can thiệp Ingest Path**: Tuyệt đối không thay thế `/abw-ingest`. Packager chỉ hoạt động ở giai đoạn cuối: chuyển từ nền tảng cục bộ sang gói nén (Package).
2. **Provenance (Truy vết)**: Mọi nội dung nén đều phải dẫn nguồn về `processed/manifest.jsonl#line-N` và tham chiếu tới thư mục `raw/` tương ứng.
3. **Phân loại rủi ro (Risk-based Classification)**:
   - **Critical Original**: Lõi kiến trúc cấu trúc, DB schema, flow thiết kế -> Cần giữ trọn vẹn tệp/hình ảnh.
   - **High**: Feature spec, quy trình kỹ thuật.
   - **Medium / Low**: Logs log hệ thống, README phụ, bản nháp thảo luận -> Bắt buộc Compress lại thành theo nhóm hệ thống (Domain Grouping).
4. **Không FAKE Grounding**: Nếu tài liệu Wiki đó vẫn mang cờ `status: draft` hay `pending_grounding`, TUYỆT ĐỐI không được gắn thành `grounded` trên bất kỳ file tổng hợp nào.
5. **No Sync Limit in Phase 1**: Kỹ năng này chỉ tạo Package Output để Review, cấm cấu hình Upload hay Sync qua API lúc này.

---

## Các Bước Thực Thi (Step-by-Step)

### Bước 1: Load Cấu Hình 
- Đọc `templates/notebook_pack_policy.example.json` để load `soft_warning_limit` (`45`), `hard_source_limit` (`50`), và danh sách `critical_keep_rules`, `force_keep`, v.v...
- Nếu có file cấu trúc thật ở `.brain/pack_policy.json`, lấy ưu tiên file thật.

### Bước 2: Load Đầu Vào (Inputs)
- Gọi đọc `processed/manifest.jsonl` và `wiki/index.md` để hiểu cây tri thức hệ thống.

### Bước 3: Phân Loại (Triage)
- Đưa tất cả documents vào 5 rổ: `Critical, High, Medium, Low, Deprecated`. 
- Bỏ qua các file ở nhóm `exclude` (hoặc `Deprecated`).

### Bước 4: Chạy Động Cơ Packager (Packager Engine)
LLM không tự parse text nén bằng tay. Trách nhiệm của bạn là gọi Terminal Script:
```bash
python ~/.gemini/antigravity/scripts/abw_pack.py --workspace . --policy <đường_dẫn_policy> --output notebooks/packages --package-id auto
```
*Script sẽ tự động thực thi Compaction Tất Định (Deterministic Compaction) và quét chéo rủi ro.*

### Bước 5: Giải Thích & Biên Dịch Báo Cáo (QA Explanation)
Sau khi Script chạy rớt STDOUT JSON và Exit Code (0, 1, 2, 3), bạn đóng vai trò là Người biên dịch:
- **Nếu Exit Code 0**: Báo gói thành công (READY FOR IMPORT).
- **Nếu Exit Code 2/3 (Needs Review / Fail)**: Đọc file `QA_REPORT.md` sinh ra trong thư mục output của Script. Giải thích cho người dùng bằng Tiếng Việt tại sao lỗi.
  - Ví dụ: Lỗi Mismatch (`Draft_Grounding_Check` = fail) -> Bạn giải thích *"Có sự chênh lệch trạng thái giữa Wiki Note và Manifest Line"*.
  - Lỗi Source Limit -> *"Bạn đang nhét nhồi quá 50 files"*.

### Bước 6: Phục Vụ Menu Hành Động (Action Menu)
Trình bày Menu Review cho Người điều hành chọn:
1. `approve package` -> Khóa package. 
2. `reject package` -> Chỉnh sửa thủ công `package_manifest.json` thành `"package_status": "rejected"`. Đừng xóa file.
3. `force keep <file>` / `force compress <file>` -> Bạn chủ động viết ngoại lệ vào `.brain/pack_policy.json` và chạy lệnh Script lại từ đầu. Lấy `templates/notebook_pack_policy.example.json` làm sườn nếu chưa có.
