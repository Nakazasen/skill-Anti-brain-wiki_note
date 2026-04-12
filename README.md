# Hybrid Anti-Brain-Wiki (Hybrid ABW)

> Version: 1.2.0
> Tagline: Biến AI từ trạng thái trả lời nhanh thành một hệ thống tri thức có grounding (neo dữ liệu thực tế), có bộ nhớ, và có suy luận ranh giới (bounded deliberation).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![TTC: Enabled](https://img.shields.io/badge/Test--Time%20Compute-Active-brightgreen)](https://github.com/Nakazasen/skill-Anti-brain-wiki_note)

Hybrid ABW là một kiến trúc quản lý tri thức và suy luận dành cho AI Agent. Mục tiêu của nó là giải quyết 2 điểm yếu phổ biến nhất của LLM:

- Thiếu bộ nhớ dài hạn đáng tin cậy.
- Trả lời nghe có vẻ hợp lý (plausible) nhưng không có nguồn gốc rõ ràng (provenance).

---

## Tại sao lại là Hybrid ABW?

Thay vì để AI trả lời theo kiểu "single-pass" (nghĩ một lần rồi nói luôn), Hybrid ABW buộc mô hình phải đi qua một khung làm việc rõ ràng và chặt chẽ:

1. Đọc context vận hành trong `.brain/`.
2. Tìm tri thức đã được biên soạn trong thư mục `wiki/`.
3. Nếu cần thiết, thực hiện grounding qua NotebookLM để lấy chứng cứ.
4. Nếu chưa đủ bằng chứng, hệ thống bắt buộc phải "log gap" (ghi nhận lỗ hổng kiến thức) thay vì "fake success" (giả vờ biết và bịa ra câu trả lời).

## Kiến trúc 4 lớp

- `raw/`: Nguồn gốc tài liệu thô, chưa qua xử lý.
- `processed/`: Lớp lưu trữ bằng chứng và nguồn gốc (provenance).
- `wiki/`: Tri thức bền vững, tuân thủ schema và có trích dẫn (citation) rõ ràng.
- `.brain/`: Trạng thái vận hành, bao gồm các hàng đợi (queue), lịch sử lỗ hổng kiến thức (gap log), và nhật ký suy luận (deliberation log).

\* *Lưu ý: NotebookLM được sử dụng như một cỗ máy neo dữ liệu (deep grounding engine), hoàn toàn không phải là "thần thánh hóa" hay "oracle" tuyệt đối.*

---

## Hệ thống suy luận TTC (Test-Time Compute Deliberation Engine)

Hybrid ABW cung cấp đường dẫn lệnh `/abw-query-deep` dành cho các câu hỏi cực khó như:

- Tổng hợp thông tin (Synthesis)
- So sánh (Comparison)
- Phân tích nguyên nhân gốc rễ (Root Cause Analysis - RCA)
- Đánh đổi trong thiết kế (Design tradeoff)
- Các prompt có nhiều yếu tố mâu thuẫn (Contradiction-heavy prompts)

Luồng TTC trải qua 5 bước (passes):

1. **Decomposition:** Chia nhỏ vấn đề.
2. **Evidence Assembly:** Tập hợp bằng chứng.
3. **Grounding:** Neo dữ liệu thực tế với NotebookLM.
4. **Self-Critique:** Tự đánh giá và phản biện nội bộ.
5. **Repair or Exit:** Sửa chữa phản hồi hoặc thoát vòng lặp.

Quá trình suy luận (Deliberation) được chặn lại an toàn bằng:

- Cổng thoát (exit gate) dựa trên mức điểm đánh giá (score).
- Cầu dao tự động ngắt (circuit breaker) nếu bị kẹt trong vòng lặp.
- Ngân sách truy vấn (query budget) dành cho NotebookLM để tiết kiệm token/thời gian.

---

## Fallback-first, Không bao giờ Fake Success

Đây là **nguyên tắc quan trọng nhất** của repository này.

Nếu NotebookLM MCP chưa sẵn sàng hoặc gặp lỗi:

- Lệnh `/abw-ingest` chỉ được phép tạo artifact ở dạng `draft` hoặc `pending_grounding`.
- Lệnh `/abw-query` sẽ trả lời theo ưu tiên từ `wiki/` (wiki-first) và tạo log gap nếu thiếu bằng chứng.
- Lệnh `/abw-query-deep` vẫn chạy, nhưng sẽ chủ động bỏ qua Bước 3 (Grounding) hoặc đặt budget = 0 để hệ thống không treo chờ.
- Lệnh `/abw-lint` phải cảnh báo rõ ràng rằng hệ thống đang trong trạng thái fallback mode (thiếu khả năng grounding sâu).

**Hybrid ABW luôn ưu tiên sự trung thực hơn là những câu trả lời "nghe có vẻ thông minh nhưng sáo rỗng".**

---

## Quick Start (Bắt đầu nhanh)

### 1. Cài đặt các Installer / Workflows

Trên Windows:

```powershell
irm https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.ps1 | iex
```

Trên macOS / Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main/install.sh | sh
```

### 2. Cài đặt cầu nối NotebookLM CLI

```bash
uv tool install notebooklm-mcp-cli
```

### 3. Khởi chạy luồng quy trình chính

```text
/abw-init
   -> /abw-setup
   -> /abw-status
   -> /abw-ingest
   -> /abw-ask 
        |-> (Tier 1) /abw-query
        |-> (Tier 2) /abw-query-deep
        |-> (Tier 3) /abw-bootstrap
   -> /abw-lint
```

### 4. Quy trình làm việc khuyến nghị

1. Chép tài liệu thô vào `raw/`.
2. Chạy `/abw-ingest`.
3. Thay vì phải "bắt bệnh", bạn hãy sử dụng `/abw-ask` cho bất kỳ câu hỏi nào. Hệ thống Smart Router sẽ tự động phân loại và định tuyến câu hỏi sang luồng tư duy nhanh (Fast path), sâu (Deep path), hoặc khởi tạo ý tưởng mới (Bootstrap path).
4. Thường xuyên bảo trì dự án bằng `/abw-lint`.

---

## Bảng lệnh hệ thống (Command Surface)

| Command | Mục đích |
|---------|----------|
| `/abw-init` | Khởi tạo hoặc sửa chữa cấu trúc thư mục Hybrid ABW. |
| `/abw-setup` | Đăng nhập và xác nhận kết nối NotebookLM MCP. |
| `/abw-status` | Kiểm tra tình trạng MCP bridge và grounding queue. |
| `/abw-ingest` | Xử lý tài liệu raw để tạo manifest và wiki artifacts. |
| `/abw-ask` | **Smart Router: Tự động phân luồng (định tuyến) sang query nhanh, suy luận sâu hoặc bootstrap ý tưởng mới!** |

**Các nhánh phía sau Router:**
| Lệnh nội bộ / Mở rộng | Mục đích |
|---------|----------|
| `/abw-query` | Trả lời nhanh dựa vào đường dẫn wiki-first (Tier 1). |
| `/abw-query-deep` | Trả lời cho các câu hỏi khó, yêu cầu TTC deliberation (Tier 2). |
| `/abw-lint` | Audit kiểm tra chuẩn wiki, quá trình grounding, mâu thuẫn và mức độ khỏe của TTC. |
| `/abw-bootstrap` | Kích hoạt hệ thống suy luận ý tưởng mới (Tier 3), tạo quản lý giả định (assumptions) & tập lệnh xác nhận giả định (validation). |

---

## Tương thích với di sản AWF (Legacy AWF compatibility)

Repository này vẫn giữ một số quy trình/workflow từ AWF đời cũ để tái cấu trúc tương thích ngược và phục vụ tham khảo.

Tuy nhiên, trong một dự án Hybrid ABW thuần túy, bộ lệnh cốt lõi trực tiếp luôn bắt đầu với tiền tố `/abw-*`. Xin đừng nhầm lẫn repository này như một bản cài đặt AWF thông thường.

Nếu bạn muốn có một trải nghiệm AWF bản tiêu chuẩn theo phiên bản gốc (upstream), vui lòng cài đặt AWF upstream riêng.

---

## Nguyên tắc neo dữ liệu thực tế (Grounding Principle)

> "Một câu trả lời có trích dẫn nguồn vẫn tốt hơn là một câu đoán mò chắp vá và tự tin."
> 
> "Chủ động ghi log lại sự thiếu hụt kiến thức (knowledge gap) vẫn tốt hơn là trả lời sai sự thật (fake answer)."

Mọi thay đổi chính trong nhóm thư mục kiến thức chung `wiki/` phải luôn luôn truy xuất ngược lại được về:

- Nguồn tài gốc (raw source).
- Dòng mô tả trong manifest (manifest line).
- Tình trạng xử lý dữ liệu (grounding outcome).
- Mức độ tự tin của dữ liệu (confidence status).

---

## Các tài liệu quan trọng khác

- `AGENTS.md`: Tóm lược kiến thức hệ thống và các bất biến (invariants) bắt buộc phải có.
- Thư mục `skills/`: Chứa các logic thực thi quan trọng của workflow.
- Thư mục `workflows/`: Chứa các lệnh wrapper bọc ngoài (chạy trực tiếp trên IDE).
- `wiki/_schemas/note.schema.md`: Khuôn rập chuẩn (schema) quy định khung lưu trữ của từng Note Kiến thức lâu dài.

---

## Đóng góp (Contributing)

Hoan nghênh mọi đóng góp, đặc biệt trong các lĩnh vực sau:

- Tinh chỉnh thông số giới hạn (TTC tuning).
- Nâng cao chất lượng cho cầu nối neo dữ liệu (grounding bridge).
- Tăng độ phủ toàn diện cho bộ tự động kiểm tra `lint`.
- Nâng cấp phiên bản tiến hóa cho hệ thống `wiki schema`.
- Cải thiện mức độ trung thực và tính khả dụng của quy trình dự phòng fallback.

Chi tiết có thể xem trong file `CONTRIBUTING.md`.
