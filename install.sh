#!/bin/bash
# AWF Installer for macOS/Linux
# Tự động detect Antigravity Global Workflows

REPO_BASE="https://raw.githubusercontent.com/TUAN130294/awf/main"
REPO_URL="$REPO_BASE/workflows"

# Full workflow list (v4.0.2) - Ordered by flow
WORKFLOWS=(
    # Core Flow: init → brainstorm → plan → design → visualize → code → run
    "init.md" "brainstorm.md" "plan.md" "design.md"
    "visualize.md" "code.md" "run.md"
    # Quality: debug → test → audit
    "debug.md" "test.md" "audit.md"
    # Deploy & Maintain
    "deploy.md" "refactor.md" "rollback.md"
    # Support workflows
    "next.md" "recap.md" "help.md" "customize.md"
    "save_brain.md" "review.md"
    # System
    "awf-update.md" "cloudflare-tunnel.md" "README.md"
)

# Schemas and Templates (v3.3+)
SCHEMAS=(
    "brain.schema.json" "session.schema.json" "preferences.schema.json"
)
TEMPLATES=(
    "brain.example.json" "session.example.json" "preferences.example.json"
)

# AWF Skills (v4.1+)
AWF_SKILLS=(
    "awf-session-restore"
    "awf-auto-save"
    "awf-adaptive-language"
    "awf-error-translator"
    "awf-context-help"
    "awf-onboarding"
)

# Detect Antigravity Global Path
ANTIGRAVITY_GLOBAL="$HOME/.gemini/antigravity/global_workflows"
SCHEMAS_DIR="$HOME/.gemini/antigravity/schemas"
TEMPLATES_DIR="$HOME/.gemini/antigravity/templates"
SKILLS_DIR="$HOME/.gemini/antigravity/skills"
GEMINI_MD="$HOME/.gemini/GEMINI.md"
AWF_VERSION_FILE="$HOME/.gemini/awf_version"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# Get version from repo
CURRENT_VERSION=$(curl -fsSL "$REPO_BASE/VERSION" 2>/dev/null || echo "4.1.0")
CURRENT_VERSION=$(echo "$CURRENT_VERSION" | tr -d '\r\n ')

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     🚀 AWF - Antigravity Workflow Framework v$CURRENT_VERSION        ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if updating
if [ -f "$AWF_VERSION_FILE" ]; then
    OLD_VERSION=$(cat "$AWF_VERSION_FILE")
    echo -e "${YELLOW}📦 Phiên bản hiện tại: $OLD_VERSION${NC}"
    echo -e "${GREEN}📦 Phiên bản mới: $CURRENT_VERSION${NC}"
    echo ""
fi

# 1. Cài Global Workflows
if [ ! -d "$ANTIGRAVITY_GLOBAL" ]; then
    mkdir -p "$ANTIGRAVITY_GLOBAL"
    echo -e "${GREEN}📂 Đã tạo thư mục Global: $ANTIGRAVITY_GLOBAL${NC}"
else
    echo -e "${GREEN}✅ Tìm thấy Antigravity Global: $ANTIGRAVITY_GLOBAL${NC}"
fi

echo -e "${CYAN}⏳ Đang tải workflows...${NC}"
success=0
for wf in "${WORKFLOWS[@]}"; do
    if curl -fsSL "$REPO_URL/$wf" -o "$ANTIGRAVITY_GLOBAL/$wf" 2>/dev/null; then
        echo -e "   ${GREEN}✅ $wf${NC}"
        ((success++))
    else
        echo -e "   ${RED}❌ $wf${NC}"
    fi
done

# 2. Download Schemas (v3.3+)
mkdir -p "$SCHEMAS_DIR"
echo -e "${CYAN}⏳ Đang tải schemas...${NC}"
for schema in "${SCHEMAS[@]}"; do
    if curl -fsSL "$REPO_BASE/schemas/$schema" -o "$SCHEMAS_DIR/$schema" 2>/dev/null; then
        echo -e "   ${GREEN}✅ $schema${NC}"
        ((success++))
    else
        echo -e "   ${RED}❌ $schema${NC}"
    fi
done

# 3. Download Templates (v3.3+)
mkdir -p "$TEMPLATES_DIR"
echo -e "${CYAN}⏳ Đang tải templates...${NC}"
for template in "${TEMPLATES[@]}"; do
    if curl -fsSL "$REPO_BASE/templates/$template" -o "$TEMPLATES_DIR/$template" 2>/dev/null; then
        echo -e "   ${GREEN}✅ $template${NC}"
        ((success++))
    else
        echo -e "   ${RED}❌ $template${NC}"
    fi
done

# 4. Download AWF Skills (v4.0+)
echo -e "${CYAN}⏳ Đang tải skills (v4.0+)...${NC}"
for skill in "${AWF_SKILLS[@]}"; do
    skill_dir="$SKILLS_DIR/$skill"
    mkdir -p "$skill_dir"
    if curl -fsSL "$REPO_BASE/awf_skills/$skill/SKILL.md" -o "$skill_dir/SKILL.md" 2>/dev/null; then
        echo -e "   ${GREEN}✅ $skill${NC}"
        ((success++))
    else
        echo -e "   ${RED}❌ $skill${NC}"
    fi
done

# 5. Save version
mkdir -p "$HOME/.gemini"
echo "$CURRENT_VERSION" > "$AWF_VERSION_FILE"
echo -e "${GREEN}✅ Đã lưu version: $CURRENT_VERSION${NC}"

# 6. Update Global Rules (GEMINI.md)
AWF_INSTRUCTIONS='
# AWF - Antigravity Workflow Framework

## CRITICAL: Command Recognition
Khi user gõ các lệnh bắt đầu bằng `/` dưới đây, đây là AWF WORKFLOW COMMANDS (không phải file path).
Bạn PHẢI đọc file workflow tương ứng và thực hiện theo hướng dẫn trong đó.

## Command Mapping (v4.0.2 - Full Flow):
| Command | Workflow File | Mô tả |
|---------|--------------|-------|
| `/init` | init.md | ✨ Khởi tạo dự án mới |
| `/brainstorm` | brainstorm.md | 💡 Bàn ý tưởng, research |
| `/plan` | plan.md | 📋 Lên kế hoạch tính năng |
| `/design` | design.md | 🎨 Thiết kế kỹ thuật (DB, API, Flow) |
| `/visualize` | visualize.md | 🖼️ Thiết kế UI/UX mockup |
| `/code` | code.md | 💻 Viết code |
| `/run` | run.md | ▶️ Chạy ứng dụng |
| `/debug` | debug.md | 🐛 Sửa lỗi |
| `/test` | test.md | 🧪 Kiểm thử |
| `/audit` | audit.md | 🔒 Kiểm tra bảo mật |
| `/deploy` | deploy.md | 🚀 Deploy production |
| `/next` | next.md | ➡️ Gợi ý bước tiếp theo |
| `/recap` | recap.md | 📖 Khôi phục ngữ cảnh |
| `/help` | help.md | ❓ Trợ giúp & Hướng dẫn |
| `/customize` | customize.md | ⚙️ Cá nhân hóa AI |
| `/refactor` | refactor.md | 🔧 Tái cấu trúc code |
| `/review` | review.md | 👀 Review code |
| `/save-brain` | save_brain.md | 🧠 Lưu kiến thức |
| `/rollback` | rollback.md | ⏪ Rollback deployment |
| `/awf-update` | awf-update.md | 📦 Cập nhật AWF |
| `/cloudflare-tunnel` | cloudflare-tunnel.md | 🌐 Quản lý tunnel |

## Flow Chuẩn (v4.0.2):
`/init` → `/plan` → `/design` → `/code` → `/run` → `/test` → `/deploy`

## Resource Locations (v4.0+):
- Schemas: ~/.gemini/antigravity/schemas/
- Templates: ~/.gemini/antigravity/templates/
- Skills: ~/.gemini/antigravity/skills/

## AWF Skills (v4.0 - Auto-activate):
Skills là helper ẩn, tự động kích hoạt khi cần. User KHÔNG cần gọi trực tiếp.

| Skill | Trigger | Chức năng |
|-------|---------|-----------|
| awf-session-restore | Đầu mỗi session | Tự động khôi phục context (lazy loading) |
| awf-auto-save | Workflow end, user leaving, decisions | Eternal Context - auto-save để không mất data |
| awf-adaptive-language | Đầu mỗi session | Điều chỉnh ngôn ngữ theo trình độ user |
| awf-error-translator | Khi có lỗi | Dịch lỗi kỹ thuật sang tiếng đời thường |
| awf-onboarding | /init lần đầu | Hướng dẫn user mới |
| awf-context-help | /help hoặc ? | Trợ giúp thông minh theo context |

**Cách hoạt động:**
1. Đọc ~/.brain/preferences.json để lấy technical_level (newbie/basic/technical)
2. Điều chỉnh ngôn ngữ trong workflows theo level
3. Skills tự động trigger, user không cần biết

## Hướng dẫn thực hiện:
1. Khi user gõ một trong các commands trên, ĐỌC FILE WORKFLOW tương ứng
2. Thực hiện TỪNG GIAI ĐOẠN trong workflow
3. KHÔNG tự ý bỏ qua bước nào
4. Kết thúc bằng NEXT STEPS menu như trong workflow

## Update Check:
- AWF version được lưu tại: ~/.gemini/awf_version
- Để kiểm tra và cập nhật AWF, user gõ: /awf-update
- Thỉnh thoảng (1 lần/tuần) nhắc user kiểm tra update nếu họ dùng AWF thường xuyên
'

if [ ! -f "$GEMINI_MD" ]; then
    echo "$AWF_INSTRUCTIONS" > "$GEMINI_MD"
    echo -e "${GREEN}✅ Đã tạo Global Rules (GEMINI.md)${NC}"
else
    # Remove old AWF section and append new one
    AWF_MARKER="# AWF - Antigravity Workflow Framework"
    if grep -q "$AWF_MARKER" "$GEMINI_MD" 2>/dev/null; then
        # Remove from marker to end of file
        sed -i.bak "/$AWF_MARKER/,\$d" "$GEMINI_MD" 2>/dev/null || sed -i '' "/$AWF_MARKER/,\$d" "$GEMINI_MD"
        rm -f "$GEMINI_MD.bak"
    fi
    echo "$AWF_INSTRUCTIONS" >> "$GEMINI_MD"
    echo -e "${GREEN}✅ Đã cập nhật Global Rules (GEMINI.md)${NC}"
fi

echo ""
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}🎉 HOÀN TẤT! Đã cài $success files vào hệ thống.${NC}"
echo -e "${CYAN}📦 Version: $CURRENT_VERSION${NC}"
echo ""
echo -e "${GRAY}📂 Workflows: $ANTIGRAVITY_GLOBAL${NC}"
echo -e "${GRAY}📂 Schemas:   $SCHEMAS_DIR${NC}"
echo -e "${GRAY}📂 Templates: $TEMPLATES_DIR${NC}"
echo -e "${GRAY}📂 Skills:    $SKILLS_DIR${NC}"
echo ""
echo -e "${CYAN}👉 Bạn có thể dùng AWF ở BẤT KỲ project nào ngay lập tức!${NC}"
echo -e "👉 Thử gõ '/plan' để kiểm tra."
echo -e "👉 Kiểm tra update: '/awf-update'"
echo ""
