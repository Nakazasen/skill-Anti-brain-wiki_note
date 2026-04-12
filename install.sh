#!/bin/bash
# Hybrid ABW Installer for macOS/Linux

set -euo pipefail

REPO_BASE="https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main"
GLOBAL_DIR="$HOME/.gemini/antigravity/global_workflows"
SCHEMAS_DIR="$HOME/.gemini/antigravity/schemas"
TEMPLATES_DIR="$HOME/.gemini/antigravity/templates"
SKILLS_DIR="$HOME/.gemini/antigravity/skills"
GEMINI_MD="$HOME/.gemini/GEMINI.md"
ABW_VERSION_FILE="$HOME/.gemini/abw_version"

WORKFLOW_FILES=(
  "abw-init.md"
  "abw-setup.md"
  "abw-status.md"
  "abw-ingest.md"
  "abw-query.md"
  "abw-query-deep.md"
  "abw-lint.md"
  "help.md"
  "next.md"
  "README.md"
  "awf-update.md"
)

SCHEMA_FILES=(
  "brain.schema.json"
  "session.schema.json"
  "preferences.schema.json"
)

TEMPLATE_FILES=(
  "brain.example.json"
  "session.example.json"
  "preferences.example.json"
  "manifest.example.jsonl"
  "grounding_queue.example.json"
  "knowledge_gaps.example.json"
  "exit_gate_policy.example.json"
  "circuit_breaker.example.json"
  "ingest_exit_gate_policy.json"
  "ingest_circuit_breaker.json"
)

AWF_HELPER_SKILLS=(
  "awf-session-restore"
  "awf-auto-save"
  "awf-adaptive-language"
  "awf-error-translator"
  "awf-context-help"
  "awf-onboarding"
)

ABW_SKILLS=(
  "abw-init.md"
  "abw-setup.md"
  "abw-status.md"
  "ingest-wiki.md"
  "ingest-wiki-deliberative.md"
  "query-wiki.md"
  "query-wiki-deliberative.md"
  "lint-wiki.md"
  "notebooklm-mcp-bridge.md"
)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m'

CURRENT_VERSION=$(curl -fsSL "$REPO_BASE/VERSION" 2>/dev/null || echo "1.1.1")
CURRENT_VERSION=$(echo "$CURRENT_VERSION" | tr -d '\r\n ')

mkdir -p "$GLOBAL_DIR" "$SCHEMAS_DIR" "$TEMPLATES_DIR" "$SKILLS_DIR" "$HOME/.gemini"

fetch_file() {
  local url="$1"
  local dest="$2"
  curl -fsSL "$url" -o "$dest"
}

echo ""
echo -e "${CYAN}===============================================${NC}"
echo -e "${CYAN}Hybrid ABW Installer v$CURRENT_VERSION${NC}"
echo -e "${CYAN}===============================================${NC}"
echo ""

success=0

echo -e "${CYAN}Installing ABW workflows...${NC}"
for wf in "${WORKFLOW_FILES[@]}"; do
  if fetch_file "$REPO_BASE/workflows/$wf" "$GLOBAL_DIR/$wf"; then
    echo -e "  ${GREEN}[OK]${NC} $wf"
    success=$((success + 1))
  else
    echo -e "  ${RED}[X]${NC} $wf"
  fi
done

echo -e "${CYAN}Installing schemas...${NC}"
for schema in "${SCHEMA_FILES[@]}"; do
  if fetch_file "$REPO_BASE/schemas/$schema" "$SCHEMAS_DIR/$schema"; then
    echo -e "  ${GREEN}[OK]${NC} $schema"
    success=$((success + 1))
  else
    echo -e "  ${RED}[X]${NC} $schema"
  fi
done

echo -e "${CYAN}Installing templates...${NC}"
for template in "${TEMPLATE_FILES[@]}"; do
  if fetch_file "$REPO_BASE/templates/$template" "$TEMPLATES_DIR/$template"; then
    echo -e "  ${GREEN}[OK]${NC} $template"
    success=$((success + 1))
  else
    echo -e "  ${RED}[X]${NC} $template"
  fi
done

echo -e "${CYAN}Installing ABW skills...${NC}"
for skill in "${ABW_SKILLS[@]}"; do
  if fetch_file "$REPO_BASE/skills/$skill" "$SKILLS_DIR/$skill"; then
    echo -e "  ${GREEN}[OK]${NC} $skill"
    success=$((success + 1))
  else
    echo -e "  ${RED}[X]${NC} $skill"
  fi
done

echo -e "${CYAN}Installing AWF helper skills...${NC}"
for skill in "${AWF_HELPER_SKILLS[@]}"; do
  skill_dir="$SKILLS_DIR/$skill"
  mkdir -p "$skill_dir"
  if fetch_file "$REPO_BASE/awf_skills/$skill/SKILL.md" "$skill_dir/SKILL.md"; then
    echo -e "  ${GREEN}[OK]${NC} $skill"
    success=$((success + 1))
  else
    echo -e "  ${RED}[X]${NC} $skill"
  fi
done

echo "$CURRENT_VERSION" > "$ABW_VERSION_FILE"

ABW_INSTRUCTIONS='''# Hybrid ABW - Antigravity IDE Command Surface

## CRITICAL: Command Recognition
When the user types one of the commands below, treat it as a Hybrid ABW workflow command.
Do not route users to the legacy AWF flow by default.

## Primary Commands
| Command | Workflow File | Purpose |
|---------|---------------|---------|
| `/abw-init` | abw-init.md | Bootstrap or repair the Hybrid ABW structure |
| `/abw-setup` | abw-setup.md | Authenticate NotebookLM MCP and verify bridge status |
| `/abw-status` | abw-status.md | Check MCP health and grounding queue state |
| `/abw-ingest` | abw-ingest.md | Process raw sources into manifest and wiki artifacts |
| `/abw-query` | abw-query.md | Fast wiki-first query path |
| `/abw-query-deep` | abw-query-deep.md | TTC deliberation path for complex questions |
| `/abw-lint` | abw-lint.md | Audit wiki, grounding, and deliberation health |

## Recommended Flow
`/abw-init` -> `/abw-setup` -> `/abw-ingest` -> `/abw-query` -> `/abw-query-deep` -> `/abw-lint`

## Fallback Rule
If NotebookLM MCP is unavailable:
- ingest creates draft or pending-grounding artifacts only
- query falls back to wiki-first answers plus gap logging
- lint reports reduced grounding capability honestly

## Legacy Compatibility
Legacy AWF workflows may still exist in the repo for compatibility.
They are not the primary public surface of this install.
'''

if [ ! -f "$GEMINI_MD" ]; then
  printf "%s\n" "$ABW_INSTRUCTIONS" > "$GEMINI_MD"
else
  tmp_file=$(mktemp)
  if grep -q "# Hybrid ABW - Antigravity IDE Command Surface" "$GEMINI_MD" 2>/dev/null; then
    sed '/# Hybrid ABW - Antigravity IDE Command Surface/,$d' "$GEMINI_MD" > "$tmp_file"
  elif grep -q "# AWF - Antigravity Workflow Framework" "$GEMINI_MD" 2>/dev/null; then
    sed '/# AWF - Antigravity Workflow Framework/,$d' "$GEMINI_MD" > "$tmp_file"
  else
    cat "$GEMINI_MD" > "$tmp_file"
  fi
  printf "\n%s\n" "$ABW_INSTRUCTIONS" >> "$tmp_file"
  mv "$tmp_file" "$GEMINI_MD"
fi

echo ""
echo -e "${YELLOW}Installed $success files.${NC}"
echo -e "${GRAY}ABW version file: $ABW_VERSION_FILE${NC}"
echo -e "${GRAY}Workflows: $GLOBAL_DIR${NC}"
echo -e "${GRAY}Skills: $SKILLS_DIR${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo -e "  1. Run /abw-init"
echo -e "  2. Run /abw-setup"
echo -e "  3. Run /abw-ingest after dropping sources into raw/"
echo ""