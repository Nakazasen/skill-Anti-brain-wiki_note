# 🧠 Hybrid Anti-Brain-Wiki (Hybrid ABW)

> **Version:** 1.1.0  
> **Tagline:** Đưa trí tuệ nhân tạo từ "Phản hồi tức thì" sang "Tư duy đa tầng" rành mạch.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![TTC: Enabled](https://img.shields.io/badge/Test--Time%20Compute-Active-brightgreen)](https://github.com/Nakazasen/skill-Anti-brain-wiki_note)

**Hybrid ABW** là một kiến trúc quản lý tri thức và tư duy cho AI Agent, được thiết kế để giải quyết vấn đề lớn nhất của các mô hình ngôn ngữ hiện nay: **Sự thiếu hụt bộ nhớ dài hạn tin cậy và sự hời hợt trong lập luận**.

---

## ✨ Tại sao lại là Hybrid ABW?

Thay vì để AI tự do "phóng tác" câu trả lời, Hybrid ABW ép AI phải đi qua một bộ khung tư duy nghiêm ngặt, đối chiếu mọi tuyên bố với các nguồn bằng chứng xác thực (Grounding).

### 1. Kiến trúc Bộ nhớ 4 Lớp (The 4-Layer Memory)
Hệ thống phân tách tri thức thành các tầng riêng biệt để tối ưu hóa việc truy xuất:
- **Layer 1: Operation Memory** (`.brain/`): Ghi nhớ bối cảnh phiên làm việc hiện tại, các task đang dở dang và blockers.
- **Layer 2: Persistent Knowledge** (`wiki/`): Kho tri thức đã được biên soạn, trích dẫn và xác thực. Đây là "Bộ não vĩnh cửu" của bạn.
- **Layer 3: Grounding Engine** (NotebookLM): Kết nối với dữ liệu tư nhân sâu để đối chiếu chéo (cross-check) thông tin.
- **Layer 4: Logic Gap Logging** (`knowledge_gaps.json`): Trung thực ghi lại những gì AI chưa biết thay vì trả lời bừa bãi.

### 2. Test-Time Compute (TTC) Deliberation Engine
Được lấy cảm hứng từ các kỹ thuật suy luận hiện đại, Hybrid ABW cung cấp lệnh `/abw-query-deep` – kích hoạt một vòng lặp suy nghĩ (deliberation loop) 5 bước:
1. **Decomposition**: Chia nhỏ vấn đề.
2. **Evidence Assembly**: Gom bằng chứng từ Wiki.
3. **Grounding**: Xác thực qua NotebookLM.
4. **Self-Critique**: Tự chấm điểm lập luận (Exit Gate).
5. **Repair**: Sửa lỗi logic trước khi trả lời.

---

## 🛠️ Cài đặt & Sử dụng (Quick Start)

Dự án được thiết kế dưới dạng **Global Skill** (Kỹ năng Toàn cầu) cho Antigravity IDE, cho phép bạn mang bộ não này theo mọi Project.

### 1. Cài đặt MCP Bridge
Bạn cần cài đặt bộ công cụ CLI hỗ trợ NotebookLM:
```powershell
uv tool install notebooklm-mcp-cli
```

### 2. Khởi tạo & Đăng nhập
Trong IDE, thực hiện 2 lệnh đơn giản:
- `/abw-init`: Khởi tạo cấu trúc folder chuẩn (wiki, raw, .brain).
- `/abw-setup`: Wizard hướng dẫn đăng nhập NotebookLM và kiểm tra kết nối.

### 3. Quy trình làm việc chuẩn
1. Thả tài liệu vào thư mục `raw/`.
2. Chạy `/abw-ingest` để AI đọc, trích xuất và lưu vào Wiki (grounded status).
3. Hỏi đáp bằng `/abw-query` (nhanh) hoặc `/abw-query-deep` (suy luận sâu).

---

## 🛡️ Nguyên tắc "Grounding"
> **"Một câu trả lời có trích dẫn đáng giá hơn một phỏng đoán tự tin. Một lỗ hổng được ghi lại đáng giá hơn một câu trả lời giả."**

Hệ thống tuân thủ nghiêm ngặt **AGENTS.md** Spec – đảm bảo mọi thông tin trong Wiki đều có nguồn gốc (provenance chain) rõ ràng.

---

## 🤝 Đóng góp
Chúng tôi hoan nghênh mọi đóng góp để hoàn thiện Deliberation Engine và các bộ Schema tri thức. Hãy xem [CONTRIBUTING.md](CONTRIBUTING.md).

---
**Phát triển bởi Đội ngũ Advanced Agentic Coding - Google DeepMind.**
*(Lưu ý: Đây là một dự án nghiên cứu và phát triển mã nguồn mở).*
