#!/bin/bash
# Hybrid ABW Installer for macOS/Linux

set -euo pipefail

REPO_OWNER="Nakazasen"
REPO_NAME="skill-Anti-brain-wiki_note"

# Detect Repo Ref: Environment Variable > Current Git Branch > default "main"
if [ -n "${ABW_REPO_REF:-}" ]; then
  REPO_REF="$ABW_REPO_REF"
elif git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  REPO_REF="$(git rev-parse --abbrev-ref HEAD)"
else
  REPO_REF="main"
fi

REPO_BASE="https://raw.githubusercontent.com/$REPO_OWNER/$REPO_NAME/$REPO_REF"
REPO_API_BASE="https://api.github.com/repos/$REPO_OWNER/$REPO_NAME"

GLOBAL_DIR="$HOME/.gemini/antigravity/global_workflows"
SCHEMAS_DIR="$HOME/.gemini/antigravity/schemas"
TEMPLATES_DIR="$HOME/.gemini/antigravity/templates"
SKILLS_DIR="$HOME/.gemini/antigravity/skills"
SCRIPTS_DIR="$HOME/.gemini/antigravity/scripts"
GEMINI_MD="$HOME/.gemini/GEMINI.md"
ABW_VERSION_FILE="$HOME/.gemini/abw_version"
ABW_INSTALL_STATE_FILE="$HOME/.gemini/abw_install_state.json"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m'

get_remote_version() {
  curl -fsSL "$REPO_BASE/VERSION" 2>/dev/null | tr -d '\r\n ' || echo "unknown"
}

get_local_repo_root() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" >/dev/null 2>&1 && pwd)"
  if [ -n "$script_dir" ] && [ -f "$script_dir/workflows/abw-init.md" ]; then
    printf '%s\n' "$script_dir"
  fi
}

resolve_install_mode() {
  local repo_root="$1"
  local forced="${ABW_INSTALL_SOURCE:-}"
  local remote_ref="origin/$REPO_REF"

  if [ -n "$forced" ]; then
    case "${forced,,}" in
      local)
        INSTALL_MODE="LOCAL"
        INSTALL_REASON="ABW_INSTALL_SOURCE=local"
        INSTALL_REMOTE_REF="$remote_ref"
        return
        ;;
      remote)
        INSTALL_MODE="REMOTE"
        INSTALL_REASON="ABW_INSTALL_SOURCE=remote"
        INSTALL_REMOTE_REF="$remote_ref"
        return
        ;;
    esac
  fi

  if [ -z "$repo_root" ]; then
    INSTALL_MODE="REMOTE"
    INSTALL_REASON="No local repository clone detected"
    INSTALL_REMOTE_REF="$remote_ref"
    return
  fi

  if ! command -v git >/dev/null 2>&1; then
    INSTALL_MODE="REMOTE"
    INSTALL_REASON="git is unavailable; remote is the only trustworthy latest source"
    INSTALL_REMOTE_REF="$remote_ref"
    return
  fi

  if ! git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    INSTALL_MODE="REMOTE"
    INSTALL_REASON="Local path is not a git worktree; remote is the only trustworthy latest source"
    INSTALL_REMOTE_REF="$remote_ref"
    return
  fi

  if tracked="$(git -C "$repo_root" rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null)"; then
    if [ -n "$tracked" ]; then
      remote_ref="$tracked"
    fi
  fi

  if ! git -C "$repo_root" fetch --quiet --prune --tags origin >/dev/null 2>&1; then
    INSTALL_MODE="REMOTE"
    INSTALL_REASON="Could not verify local clone against origin; remote install is safer"
    INSTALL_REMOTE_REF="$remote_ref"
    return
  fi

  local head remote_head status
  head="$(git -C "$repo_root" rev-parse HEAD 2>/dev/null || true)"
  remote_head="$(git -C "$repo_root" rev-parse "$remote_ref" 2>/dev/null || true)"
  status="$(git -C "$repo_root" status --porcelain 2>/dev/null || true)"

  if [ -n "$head" ] && [ -n "$remote_head" ] && [ "$head" = "$remote_head" ] && [ -z "$status" ]; then
    INSTALL_MODE="LOCAL"
    INSTALL_REASON="Local clone is clean and already at $remote_ref"
    INSTALL_REMOTE_REF="$remote_ref"
    return
  fi

  if [ -n "$status" ]; then
    INSTALL_MODE="REMOTE"
    INSTALL_REASON="Local clone has uncommitted changes; installing the verified remote snapshot"
    INSTALL_REMOTE_REF="$remote_ref"
    return
  fi

  INSTALL_MODE="REMOTE"
  INSTALL_REASON="Local clone does not match $remote_ref; installing the verified remote snapshot"
  INSTALL_REMOTE_REF="$remote_ref"
}

get_local_tree_paths() {
  local repo_root="$1"
  find \
    "$repo_root/workflows" \
    "$repo_root/skills" \
    "$repo_root/schemas" \
    "$repo_root/templates" \
    "$repo_root/scripts" \
    "$repo_root/awf_skills" \
    -type f 2>/dev/null | sed "s#^$repo_root/##" | sort
}

get_remote_tree_paths() {
  curl -fsSL -H "User-Agent: hybrid-abw-installer" -H "Accept: application/vnd.github+json" \
    "$REPO_API_BASE/git/trees/$REPO_REF?recursive=1" |
    grep -oE '"path":"[^"]+"' |
    sed 's/^"path":"//; s/"$//' |
    sort
}

WORKFLOW_PATHS=()
SKILL_PATHS=()
SCHEMA_PATHS=()
TEMPLATE_PATHS=()
SCRIPT_PATHS=()
HELPER_SKILLS=()

load_catalog_from_paths() {
  local tree_paths="$1"

  WORKFLOW_PATHS=()
  SKILL_PATHS=()
  SCHEMA_PATHS=()
  TEMPLATE_PATHS=()
  SCRIPT_PATHS=()
  HELPER_SKILLS=()

  while IFS= read -r path; do
    [ -z "$path" ] && continue
    case "$path" in
      workflows/*.md)
        WORKFLOW_PATHS+=("$path")
        ;;
      skills/*.md)
        SKILL_PATHS+=("$path")
        ;;
      schemas/*.json)
        SCHEMA_PATHS+=("$path")
        ;;
      templates/*)
        if [[ "$path" != templates/*/* ]]; then
          TEMPLATE_PATHS+=("$path")
        fi
        ;;
      scripts/*.py)
        SCRIPT_PATHS+=("$path")
        ;;
      awf_skills/*/SKILL.md)
        HELPER_SKILLS+=("$(printf '%s' "$path" | cut -d/ -f2)")
        ;;
    esac
  done <<< "$tree_paths"

  if [ "${#HELPER_SKILLS[@]}" -gt 0 ]; then
    mapfile -t HELPER_SKILLS < <(printf '%s\n' "${HELPER_SKILLS[@]}" | sort -u)
  fi
}

install_file() {
  local rel_path="$1"
  local dest="$2"

  mkdir -p "$(dirname "$dest")"

  if [ "$INSTALL_MODE" = "LOCAL" ]; then
    if [ ! -f "$REPO_ROOT/$rel_path" ]; then
      echo "Missing local source: $rel_path" >&2
      return 1
    fi
    cp "$REPO_ROOT/$rel_path" "$dest"
    echo "LOCAL"
    return 0
  fi

  curl -fsSL "$REPO_BASE/$rel_path" -o "$dest"
  echo "REMOTE"
}

workflow_path_to_command() {
  local rel_path="$1"
  local file_name
  file_name="$(basename "$rel_path" .md)"
  if [ "$file_name" = "README" ]; then
    return 1
  fi
  printf '/%s\n' "${file_name//_/-}"
}

join_commands() {
  if [ "$#" -eq 0 ]; then
    printf '(none)'
    return
  fi
  local first=1
  local item
  for item in "$@"; do
    if [ "$first" -eq 1 ]; then
      printf '%s' "$item"
      first=0
    else
      printf ', %s' "$item"
    fi
  done
}

write_gemini_registration() {
  local abw_commands=()
  local extended_commands=()
  local workflow_path command tmp_file

  for workflow_path in "${WORKFLOW_PATHS[@]}"; do
    if command="$(workflow_path_to_command "$workflow_path" 2>/dev/null)"; then
      if [[ "$command" == /abw-* ]]; then
        abw_commands+=("$command")
      else
        extended_commands+=("$command")
      fi
    fi
  done

  mapfile -t abw_commands < <(printf '%s\n' "${abw_commands[@]}" | sort -u)
  mapfile -t extended_commands < <(printf '%s\n' "${extended_commands[@]}" | sort -u)

  read -r -d '' ABW_INSTRUCTIONS <<EOF || true
# Hybrid ABW - Antigravity IDE Command Surface

## CRITICAL: Command Recognition
When the user types one of the registered commands below, treat it as a Hybrid ABW workflow command loaded from \`~/.gemini/antigravity/global_workflows\`.
Do not silently fall back to a stale local clone when the verified remote snapshot is newer.
Hybrid ABW commands take precedence over older AWF registrations with the same slash command. In particular, \`/help\` MUST load \`~/.gemini/antigravity/global_workflows/help.md\`; do not answer from \`awf-context-help\` or a short summary.

## Registered ABW Commands
$(join_commands "${abw_commands[@]}")

## Registered Extended Commands
$(join_commands "${extended_commands[@]}")

## Runtime Notes
- Installer source mode: $INSTALL_MODE
- Source decision: $INSTALL_REASON
- Workflow directory: \`~/.gemini/antigravity/global_workflows\`
- Skills directory: \`~/.gemini/antigravity/skills\`

## Fallback Rule
If NotebookLM MCP is unavailable:
- ingest creates draft or pending-grounding artifacts only
- query falls back to wiki-first answers plus gap logging
- lint reports reduced grounding capability honestly
EOF

  mkdir -p "$(dirname "$GEMINI_MD")"
  if [ ! -f "$GEMINI_MD" ]; then
    printf '%s\n' "$ABW_INSTRUCTIONS" > "$GEMINI_MD"
    return
  fi

  tmp_file="$(mktemp)"
  if grep -q "# Hybrid ABW - Antigravity IDE Command Surface" "$GEMINI_MD" 2>/dev/null; then
    sed '/# Hybrid ABW - Antigravity IDE Command Surface/,$d' "$GEMINI_MD" > "$tmp_file"
  else
    cat "$GEMINI_MD" > "$tmp_file"
  fi
  if grep -q "^# AWF - Antigravity Workflow Framework" "$tmp_file" 2>/dev/null; then
    : > "$tmp_file"
  fi
  printf '\n%s\n' "$ABW_INSTRUCTIONS" >> "$tmp_file"
  mv "$tmp_file" "$GEMINI_MD"
}

REPO_ROOT="$(get_local_repo_root || true)"
resolve_install_mode "$REPO_ROOT"
CURRENT_VERSION="$(get_remote_version)"

mkdir -p "$GLOBAL_DIR" "$SCHEMAS_DIR" "$TEMPLATES_DIR" "$SKILLS_DIR" "$SCRIPTS_DIR" "$HOME/.gemini"

echo ""
echo -e "${CYAN}===============================================${NC}"
echo -e "${CYAN}Hybrid ABW Installer v$CURRENT_VERSION${NC}"
echo -e "${YELLOW}Source mode: $INSTALL_MODE${NC}"
echo -e "${GRAY}Reason: $INSTALL_REASON${NC}"
echo -e "${CYAN}===============================================${NC}"
echo ""

if [ "$INSTALL_MODE" = "LOCAL" ]; then
  TREE_PATHS="$(get_local_tree_paths "$REPO_ROOT")"
else
  TREE_PATHS="$(get_remote_tree_paths)"
fi

load_catalog_from_paths "$TREE_PATHS"

if [ "${#WORKFLOW_PATHS[@]}" -eq 0 ] || [ "${#SKILL_PATHS[@]}" -eq 0 ]; then
  echo -e "${RED}Installer discovery failed: workflows or skills catalog is empty.${NC}"
  exit 1
fi

success=0
missing=0

echo -e "${CYAN}Installing ABW workflows...${NC}"
for rel_path in "${WORKFLOW_PATHS[@]}"; do
  leaf="$(basename "$rel_path")"
  if source_type="$(install_file "$rel_path" "$GLOBAL_DIR/$leaf")"; then
    echo -e "  ${GREEN}[OK]${NC} $leaf ($source_type)"
    success=$((success + 1))
  else
    echo -e "  ${RED}[X]${NC} FAILED: $leaf"
    missing=$((missing + 1))
  fi
done

echo -e "${CYAN}Installing schemas...${NC}"
for rel_path in "${SCHEMA_PATHS[@]}"; do
  leaf="$(basename "$rel_path")"
  if source_type="$(install_file "$rel_path" "$SCHEMAS_DIR/$leaf")"; then
    echo -e "  ${GREEN}[OK]${NC} $leaf ($source_type)"
    success=$((success + 1))
  else
    echo -e "  ${RED}[X]${NC} FAILED: $leaf"
    missing=$((missing + 1))
  fi
done

echo -e "${CYAN}Installing templates...${NC}"
for rel_path in "${TEMPLATE_PATHS[@]}"; do
  leaf="$(basename "$rel_path")"
  if source_type="$(install_file "$rel_path" "$TEMPLATES_DIR/$leaf")"; then
    echo -e "  ${GREEN}[OK]${NC} $leaf ($source_type)"
    success=$((success + 1))
  else
    echo -e "  ${RED}[X]${NC} FAILED: $leaf"
    missing=$((missing + 1))
  fi
done

echo -e "${CYAN}Installing ABW skills...${NC}"
for rel_path in "${SKILL_PATHS[@]}"; do
  leaf="$(basename "$rel_path")"
  if source_type="$(install_file "$rel_path" "$SKILLS_DIR/$leaf")"; then
    echo -e "  ${GREEN}[OK]${NC} $leaf ($source_type)"
    success=$((success + 1))
  else
    echo -e "  ${RED}[X]${NC} FAILED: $leaf"
    missing=$((missing + 1))
  fi
done

echo -e "${CYAN}Installing compatibility helper skills...${NC}"
for skill in "${HELPER_SKILLS[@]}"; do
  if source_type="$(install_file "awf_skills/$skill/SKILL.md" "$SKILLS_DIR/$skill/SKILL.md")"; then
    echo -e "  ${GREEN}[OK]${NC} $skill ($source_type)"
    success=$((success + 1))
  else
    echo -e "  ${RED}[X]${NC} FAILED: $skill"
    missing=$((missing + 1))
  fi
done

echo -e "${CYAN}Installing runtime scripts...${NC}"
for rel_path in "${SCRIPT_PATHS[@]}"; do
  leaf="$(basename "$rel_path")"
  if source_type="$(install_file "$rel_path" "$SCRIPTS_DIR/$leaf")"; then
    echo -e "  ${GREEN}[OK]${NC} $leaf ($source_type)"
    success=$((success + 1))
  else
    echo -e "  ${RED}[X]${NC} FAILED: $leaf"
    missing=$((missing + 1))
  fi
done

if [ "$missing" -gt 0 ]; then
  echo -e "\n${RED}Installation failed while copying $missing components.${NC}"
  exit 1
fi

printf '%s\n' "$CURRENT_VERSION" > "$ABW_VERSION_FILE"
cat > "$ABW_INSTALL_STATE_FILE" <<EOF
{
  "installed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "installer_source_mode": "$INSTALL_MODE",
  "installer_reason": "$INSTALL_REASON",
  "repo": "$REPO_OWNER/$REPO_NAME",
  "repo_ref": "$REPO_REF",
  "version": "$CURRENT_VERSION",
  "workflow_count": ${#WORKFLOW_PATHS[@]},
  "skill_count": ${#SKILL_PATHS[@]},
  "schema_count": ${#SCHEMA_PATHS[@]},
  "template_count": ${#TEMPLATE_PATHS[@]},
  "script_count": ${#SCRIPT_PATHS[@]},
  "helper_skill_count": ${#HELPER_SKILLS[@]}
}
EOF

write_gemini_registration

echo -e "\n${CYAN}Verifying installation...${NC}"
verification_errors=0

for rel_path in "${WORKFLOW_PATHS[@]}"; do
  [ -f "$GLOBAL_DIR/$(basename "$rel_path")" ] || {
    echo -e "  ${RED}[!]${NC} Missing workflow: $(basename "$rel_path")"
    verification_errors=$((verification_errors + 1))
  }
done

for rel_path in "${SKILL_PATHS[@]}"; do
  [ -f "$SKILLS_DIR/$(basename "$rel_path")" ] || {
    echo -e "  ${RED}[!]${NC} Missing skill: $(basename "$rel_path")"
    verification_errors=$((verification_errors + 1))
  }
done

for rel_path in "${SCHEMA_PATHS[@]}"; do
  [ -f "$SCHEMAS_DIR/$(basename "$rel_path")" ] || {
    echo -e "  ${RED}[!]${NC} Missing schema: $(basename "$rel_path")"
    verification_errors=$((verification_errors + 1))
  }
done

for rel_path in "${TEMPLATE_PATHS[@]}"; do
  [ -f "$TEMPLATES_DIR/$(basename "$rel_path")" ] || {
    echo -e "  ${RED}[!]${NC} Missing template: $(basename "$rel_path")"
    verification_errors=$((verification_errors + 1))
  }
done

for rel_path in "${SCRIPT_PATHS[@]}"; do
  [ -f "$SCRIPTS_DIR/$(basename "$rel_path")" ] || {
    echo -e "  ${RED}[!]${NC} Missing script: $(basename "$rel_path")"
    verification_errors=$((verification_errors + 1))
  }
done

for skill in "${HELPER_SKILLS[@]}"; do
  [ -f "$SKILLS_DIR/$skill/SKILL.md" ] || {
    echo -e "  ${RED}[!]${NC} Missing helper skill: $skill"
    verification_errors=$((verification_errors + 1))
  }
done

if ! grep -q "# Hybrid ABW - Antigravity IDE Command Surface" "$GEMINI_MD" 2>/dev/null; then
  echo -e "  ${RED}[!]${NC} GEMINI.md missing ABW block."
  verification_errors=$((verification_errors + 1))
fi

if [ "$verification_errors" -gt 0 ]; then
  echo -e "\n${RED}Installation failed verification. Missing $verification_errors required components.${NC}"
  exit 1
fi

echo ""
echo -e "${YELLOW}Installed $success files.${NC}"
echo -e "${GRAY}ABW version file: $ABW_VERSION_FILE${NC}"
echo -e "${GRAY}ABW install state: $ABW_INSTALL_STATE_FILE${NC}"
echo -e "${GRAY}Workflows: $GLOBAL_DIR${NC}"
echo -e "${GRAY}Skills: $SKILLS_DIR${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo -e "  1. Reload Gemini or your IDE slash-command surface if it still shows stale commands."
echo -e "  2. Run /help or /abw to confirm the command list refreshed."
echo -e "  3. Use /abw-learn or /audit to validate the newly installed workflows."
echo ""
