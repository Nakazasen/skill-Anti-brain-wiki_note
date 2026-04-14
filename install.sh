#!/bin/bash
# Hybrid ABW Installer for macOS/Linux

set -euo pipefail

REPO_BASE="https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main"
GLOBAL_DIR="$HOME/.gemini/antigravity/global_workflows"
SCHEMAS_DIR="$HOME/.gemini/antigravity/schemas"
TEMPLATES_DIR="$HOME/.gemini/antigravity/templates"
SKILLS_DIR="$HOME/.gemini/antigravity/skills"
SCRIPTS_DIR="$HOME/.gemini/antigravity/scripts"
GEMINI_MD="$HOME/.gemini/GEMINI.md"
ABW_VERSION_FILE="$HOME/.gemini/abw_version"

WORKFLOW_FILES=(
  "abw-init.md"
  "abw-setup.md"
  "abw-status.md"
  "abw-ingest.md"
  "abw-pack.md"
  "abw-sync.md"
  "abw-query.md"
  "abw-query-deep.md"
  "abw-lint.md"
  "abw-bootstrap.md"
  "abw-ask.md"
  "abw-audit.md"
  "abw-meta-audit.md"
  "abw-accept.md"
  "abw-eval.md"
  "abw-start.md"
  "abw-learn.md"
  "abw-wrap.md"
  "abw-review.md"
  "abw-rollback.md"

  "brainstorm.md"
  "plan.md"
  "design.md"
  "visualize.md"
  "code.md"
  "run.md"
  "debug.md"
  "test.md"
  "deploy.md"
  "refactor.md"
  "audit.md"
  "save_brain.md"
  "recap.md"
  "help.md"
  "next.md"
  "README.md"
  "abw-update.md"
)

SCHEMA_FILES=(
  "brain.schema.json"
  "session.schema.json"
  "preferences.schema.json"
  "notebook_package_manifest.schema.json"
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
  "deliberation_run.example.json"
  "assumptions.example.json"
  "hypotheses.example.json"
  "decision_log.example.jsonl"
  "validation_backlog.example.json"
  "notebook_pack_policy.example.json"
  "notebook_package_manifest.example.json"
  "lessons_learned.example.jsonl"
  "note_schema.example.md"
  "wiki_index.example.md"
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
  "abw-audit.md"
  "abw-meta-audit.md"
  "abw-accept.md"
  "abw-eval.md"
  "abw-start.md"
  "abw-wrap.md"
  "abw-review.md"
  "abw-rollback.md"
  "ingest-wiki.md"
  "notebooklm-knowledge-packager.md"
  "notebooklm-sync.md"
  "query-wiki.md"
  "query-wiki-deliberative.md"
  "lint-wiki.md"
  "notebooklm-mcp-bridge.md"
  "abw-bootstrap.md"
  "abw-router.md"
)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m'

# Local clone detection
IS_LOCAL=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" &>/dev/null && pwd)"
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/workflows/abw-init.md" ]; then
  IS_LOCAL=1
  REPO_ROOT="$SCRIPT_DIR"
fi

install_file() {
  local rel_path="$1"
  local dest="$2"
  
  if [ "$IS_LOCAL" -eq 1 ] && [ -f "$REPO_ROOT/$rel_path" ]; then
    cp "$REPO_ROOT/$rel_path" "$dest"
    echo "LOCAL"
    return 0
  fi
  
  local url="$REPO_BASE/$rel_path"
  if curl -fsSL "$url" -o "$dest"; then
    echo "REMOTE"
    return 0
  else
    return 1
  fi
}

CURRENT_VERSION=$(curl -fsSL "$REPO_BASE/VERSION" 2>/dev/null || echo "1.2.0")
CURRENT_VERSION=$(echo "$CURRENT_VERSION" | tr -d '\r\n ')

mkdir -p "$GLOBAL_DIR" "$SCHEMAS_DIR" "$TEMPLATES_DIR" "$SKILLS_DIR" "$HOME/.gemini"

echo ""
echo -e "${CYAN}===============================================${NC}"
echo -e "${CYAN}Hybrid ABW Installer v$CURRENT_VERSION${NC}"
if [ "$IS_LOCAL" -eq 1 ]; then
  echo -e "${YELLOW}(Local installation mode detected)${NC}"
fi
echo -e "${CYAN}===============================================${NC}"
echo ""

success=0
CRITICAL_FAIL=0

echo -e "${CYAN}Installing ABW workflows...${NC}"
for wf in "${WORKFLOW_FILES[@]}"; do
  if source_type=$(install_file "workflows/$wf" "$GLOBAL_DIR/$wf"); then
    echo -e "  ${GREEN}[OK]${NC} $wf ($source_type)"
    success=$((success + 1))
  else
    echo -e "  ${RED}[X] FAILED to install critical workflow: $wf${NC}"
    CRITICAL_FAIL=1
  fi
done

if [ "$CRITICAL_FAIL" -eq 1 ]; then
  echo -e "\n${RED}CRITICAL ERROR: Failed to install one or more required ABW workflows. Aborting installation.${NC}"
  exit 1
fi

echo -e "${CYAN}Installing schemas...${NC}"
for schema in "${SCHEMA_FILES[@]}"; do
  if source_type=$(install_file "schemas/$schema" "$SCHEMAS_DIR/$schema"); then
    echo -e "  ${GREEN}[OK]${NC} $schema ($source_type)"
    success=$((success + 1))
  else
    echo -e "  ${RED}[X] FAILED: $schema${NC}"
  fi
done

echo -e "${CYAN}Installing templates...${NC}"
for template in "${TEMPLATE_FILES[@]}"; do
  if source_type=$(install_file "templates/$template" "$TEMPLATES_DIR/$template"); then
    echo -e "  ${GREEN}[OK]${NC} $template ($source_type)"
    success=$((success + 1))
  else
    echo -e "  ${RED}[X] FAILED: $template${NC}"
  fi
done

CRITICAL_FAIL=0
echo -e "${CYAN}Installing ABW skills...${NC}"
for skill in "${ABW_SKILLS[@]}"; do
  if source_type=$(install_file "skills/$skill" "$SKILLS_DIR/$skill"); then
    echo -e "  ${GREEN}[OK]${NC} $skill ($source_type)"
    success=$((success + 1))
  else
    echo -e "  ${RED}[X] FAILED: $skill${NC}"
    CRITICAL_FAIL=1
  fi
done

if [ "$CRITICAL_FAIL" -eq 1 ]; then
  echo -e "\n${RED}CRITICAL ERROR: Failed to install one or more required ABW skills. Aborting installation.${NC}"
  exit 1
fi

echo -e "${CYAN}Installing compatibility helper skills...${NC}"
for skill in "${AWF_HELPER_SKILLS[@]}"; do
  skill_dir="$SKILLS_DIR/$skill"
  mkdir -p "$skill_dir"
  if source_type=$(install_file "awf_skills/$skill/SKILL.md" "$skill_dir/SKILL.md"); then
    echo -e "  ${GREEN}[OK]${NC} $skill ($source_type)"
    success=$((success + 1))
  else
    echo -e "  ${RED}[X] FAILED: $skill${NC}"
  fi
done

echo -e "${CYAN}Installing runtime scripts...${NC}"
if [ "$IS_LOCAL" -eq 1 ] && [ -f "$REPO_ROOT/scripts/abw_pack.py" ] && [ -f "$REPO_ROOT/scripts/abw_sync.py" ]; then
  mkdir -p "$SCRIPTS_DIR"
  if cp "$REPO_ROOT/scripts/abw_pack.py" "$SCRIPTS_DIR/abw_pack.py"; then
    cp "$REPO_ROOT/scripts/abw_sync.py" "$SCRIPTS_DIR/abw_sync.py"
    echo -e "  ${GREEN}[OK]${NC} Copied runtime scripts ($REPO_ROOT/scripts)"
    success=$((success + 1))
  else
    echo -e "  ${RED}[X] FAILED: Could not copy runtime scripts${NC}"
  fi
elif [ "$IS_LOCAL" -eq 0 ]; then
  mkdir -p "$SCRIPTS_DIR"
  if curl -fsSL "$REPO_BASE/scripts/abw_pack.py" -o "$SCRIPTS_DIR/abw_pack.py" && \
     curl -fsSL "$REPO_BASE/scripts/abw_sync.py" -o "$SCRIPTS_DIR/abw_sync.py"; then
    echo -e "  ${GREEN}[OK]${NC} Downloaded runtime scripts"
    success=$((success + 1))
  else
    echo -e "  ${RED}[X] FAILED: Could not download runtime scripts${NC}"
  fi
fi

echo "$CURRENT_VERSION" > "$ABW_VERSION_FILE"

ABW_INSTRUCTIONS='''# Hybrid ABW - Antigravity IDE Command Surface

## CRITICAL: Command Recognition
When the user types one of the commands below, treat it as a Hybrid ABW workflow command.
Do not route users to the legacy AWF flow by default.

### Primary Commands
| Command | Workflow File | Purpose |
|---------|---------------|---------|
| /abw-init | abw-init.md | Bootstrap or repair the Hybrid ABW structure |
| /abw-setup | abw-setup.md | Authenticate NotebookLM MCP and verify bridge status |
| /abw-status | abw-status.md | Check MCP health and grounding queue state |
| /abw-ingest | abw-ingest.md | Process raw sources into manifest and wiki artifacts |
| /abw-pack | abw-pack.md | Package wiki into compressed files for NotebookLM limits |
| /abw-sync | abw-sync.md | Dry-run or execute NotebookLM sync for an approved package |
| /abw-ask | abw-ask.md | Smart default router: auto-selects fast, deep, or bootstrap path |
| /customize | customize.md | Configure AI style, persona, and autonomy |

| /abw-query | abw-query.md | Fast wiki-first query path |
| /abw-query-deep | abw-query-deep.md | TTC deliberation path for complex questions |
| /abw-lint | abw-lint.md | Audit wiki, grounding, and deliberation health |
| /abw-bootstrap | abw-bootstrap.md | System 2 reasoning for greenfield ideas (no raw/wiki data yet) |
| /abw-audit | abw-audit.md | Self-audit a change, workflow, doc, or output |
| /abw-meta-audit | abw-meta-audit.md | Audit the audit report itself |
| /abw-accept | abw-accept.md | Run the final acceptance gate |
| /abw-eval | abw-eval.md | Run the full evaluation chain |
| /abw-start | abw-start.md | Start a session with state, grounding, and next-step checks |
| /abw-learn | abw-learn.md | Record a reusable behavioral lesson into lessons_learned |
| /abw-wrap | abw-wrap.md | Wrap a session with handover and follow-up guidance |
| /abw-review | abw-review.md | Review code, changes, or current project state |
| /abw-rollback | abw-rollback.md | Recover a safe state after a bad change |

## Command Model (6 Lanes)
- Ask & Think: /abw-ask, /abw-query, /abw-query-deep, /abw-bootstrap, /brainstorm
- Build Knowledge: /abw-setup, /abw-status, /abw-ingest, /abw-pack, /abw-sync, /abw-lint
- Build Product: /plan, /design, /visualize, /code, /run, /debug, /test, /deploy, /refactor
- Session & Memory: /abw-start, /abw-learn, /save-brain, /recap, /next, /abw-wrap
- Evaluation & Acceptance: /abw-audit, /abw-meta-audit, /abw-accept, /abw-eval, /abw-review, /abw-rollback
- Utility & Customization: /customize, /help, /abw-update

## Extended Workflows
| Command | Workflow File | Purpose |
|---------|---------------|---------|
| `/brainstorm` | brainstorm.md | Product discovery, scoping, and MVP framing |
| `/plan` | plan.md | Delivery planning and task breakdown |
| `/design` | design.md | Technical and data design |
| `/visualize` | visualize.md | UI/UX mockup and screen specification |
| `/code` | code.md | Feature implementation |
| `/run` | run.md | Local execution |
| `/debug` | debug.md | Bug investigation and repair |
| `/test` | test.md | Test and quality loop |
| `/deploy` | deploy.md | Delivery to target environment |
| `/refactor` | refactor.md | Safe cleanup after behavior is understood |
| `/audit` | audit.md | Product/code/security review in the delivery loop |
| `/save-brain` | save_brain.md | Save session progress and handover |
| `/recap` | recap.md | Restore last-session context |
| `/next` | next.md | Suggest the best next move |

## Command Model (6 Lanes)
- Ask & Think: `/abw-ask`, `/abw-query`, `/abw-query-deep`, `/abw-bootstrap`, `/brainstorm`
- Build Knowledge: `/abw-init`, `/abw-setup`, `/abw-status`, `/abw-ingest`, `/abw-pack`, `/abw-sync`, `/abw-lint`
- Build Product: `/plan`, `/design`, `/visualize`, `/code`, `/run`, `/debug`, `/test`, `/deploy`, `/refactor`, `/audit`
- Session & Memory: `/abw-start`, `/abw-learn`, `/save-brain`, `/recap`, `/next`, `/abw-wrap`
- Evaluation & Acceptance: `/abw-audit`, `/abw-meta-audit`, `/abw-accept`, `/abw-eval`, `/abw-review`, `/abw-rollback`

## Recommended Flow
`/abw-init` -> `/abw-setup` -> `/abw-ingest` -> `/abw-ask` -> `/abw-lint` -> `/abw-eval`

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
  else
    cat "$GEMINI_MD" > "$tmp_file"
  fi
  printf "\n%s\n" "$ABW_INSTRUCTIONS" >> "$tmp_file"
  mv "$tmp_file" "$GEMINI_MD"
fi

echo -e "\n${CYAN}Verifying installation...${NC}"
MISSING_FILES=0
REQUIRED_WFS=(
  "abw-init.md" "abw-setup.md" "abw-status.md" "abw-ingest.md" "abw-pack.md" "abw-sync.md"
  "abw-ask.md" "abw-query.md" "abw-query-deep.md" "abw-bootstrap.md" "abw-lint.md"
  "abw-audit.md" "abw-meta-audit.md" "abw-accept.md" "abw-eval.md"
  "abw-start.md" "abw-learn.md" "abw-wrap.md" "abw-review.md" "abw-rollback.md"
  "brainstorm.md" "plan.md" "design.md" "visualize.md" "code.md" "run.md"
  "debug.md" "test.md" "deploy.md" "refactor.md" "audit.md" "save_brain.md"
  "recap.md" "next.md" "help.md" "README.md" "abw-update.md"
)

for wf in "${REQUIRED_WFS[@]}"; do
  if [ ! -f "$GLOBAL_DIR/$wf" ]; then
    echo -e "  ${RED}[!] Missing: $wf${NC}"
    MISSING_FILES=$((MISSING_FILES + 1))
  else
    echo -e "  ${GRAY}[OK] Verified: $wf${NC}"
  fi
done

for skill in "${ABW_SKILLS[@]}"; do
  if [ ! -f "$SKILLS_DIR/$skill" ]; then
    echo -e "  ${RED}[!] Missing Skill: $skill${NC}"
    MISSING_FILES=$((MISSING_FILES + 1))
  else
    echo -e "  ${GRAY}[OK] Verified Skill: $skill${NC}"
  fi
done

if ! grep -q "# Hybrid ABW - Antigravity IDE Command Surface" "$GEMINI_MD" 2>/dev/null; then
  echo -e "  ${RED}[!] GEMINI.md missing ABW block.${NC}"
  MISSING_FILES=$((MISSING_FILES + 1))
else
  echo -e "  ${GRAY}[OK] GEMINI.md ABW registration verified.${NC}"
fi

if [ "$MISSING_FILES" -gt 0 ]; then
  echo -e "\n${RED}Installation FAILED verification. Missing $MISSING_FILES required components.${NC}"
  exit 1
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
echo -e "  3. Run /abw-ingest to build project knowledge"
echo -e "  4. Run /abw-ask when you have a task or question and want the router to choose the lane"
echo -e "  5. Run /abw-eval when you want an evaluation pass before accepting a change or output"
echo ""
