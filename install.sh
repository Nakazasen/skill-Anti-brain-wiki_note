#!/bin/bash
# Hybrid ABW Installer for macOS/Linux

set -euo pipefail

REPO_OWNER="Nakazasen"
REPO_NAME="skill-Anti-brain-wiki_note"

if [ -n "${ABW_REPO_REF:-}" ]; then
  REPO_REF="$ABW_REPO_REF"
elif git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  REPO_REF="$(git rev-parse --abbrev-ref HEAD)"
else
  REPO_REF="main"
fi

REPO_BASE="https://raw.githubusercontent.com/$REPO_OWNER/$REPO_NAME/$REPO_REF"
REPO_API_BASE="https://api.github.com/repos/$REPO_OWNER/$REPO_NAME"

ANTIGRAVITY_DIR="$HOME/.gemini/antigravity"
GLOBAL_DIR="$ANTIGRAVITY_DIR/global_workflows"
SCHEMAS_DIR="$ANTIGRAVITY_DIR/schemas"
TEMPLATES_DIR="$ANTIGRAVITY_DIR/templates"
SKILLS_DIR="$ANTIGRAVITY_DIR/skills"
SCRIPTS_DIR="$ANTIGRAVITY_DIR/scripts"
MCP_CONFIG_PATH="$ANTIGRAVITY_DIR/mcp_config.json"
GEMINI_MD="$HOME/.gemini/GEMINI.md"
ABW_VERSION_FILE="$HOME/.gemini/abw_version"
ABW_INSTALL_STATE_FILE="$HOME/.gemini/abw_install_state.json"

REQUIRED_RUNTIME_SCRIPTS=(
  "abw_accept.py"
  "abw_runner.py"
  "finalization_check.py"
  "continuation_gate.py"
  "continuation_execute.py"
)

REQUIRED_RUNTIME_WORKFLOWS=(
  "abw-ask.md"
  "abw-update.md"
  "finalization.md"
)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m'

WORKFLOW_PATHS=()
SKILL_PATHS=()
SCHEMA_PATHS=()
TEMPLATE_PATHS=()
SCRIPT_PATHS=()

SOURCE_SYNC_RESULT="FAIL"
RUNTIME_SYNC_RESULT="FAIL"
MCP_SYNC_RESULT="FAIL"
VERIFICATION_RESULT="FAIL"
FINAL_VERDICT="FAIL"
VERIFICATION_LIMITATIONS=()
SOURCE_ERRORS=()
RUNTIME_ERRORS=()
MCP_ERRORS=()
VERIFY_ERRORS=()

INSTALL_MODE="REMOTE"
INSTALL_REASON=""
INSTALL_REMOTE_REF="origin/$REPO_REF"
REMOTE_VERSION="unknown"
PYTHON_CMD=""
PYTHON_FOR_MCP=""
PYTHON_FOR_REPORT=""
GEMINI_REFRESHED="false"
INSTALLER_RAN="false"

json_escape() {
  local raw="${1:-}"
  raw="${raw//\\/\\\\}"
  raw="${raw//\"/\\\"}"
  raw="${raw//$'\n'/\\n}"
  raw="${raw//$'\r'/\\r}"
  raw="${raw//$'\t'/\\t}"
  printf '%s' "$raw"
}

append_error() {
  local array_name="$1"
  shift
  local value="$*"
  eval "$array_name+=(\"\$value\")"
}

array_to_json() {
  local array_name="$1"
  eval "local items=(\"\${${array_name}[@]}\")"
  local first=1
  printf '['
  for item in "${items[@]}"; do
    if [ "$first" -eq 0 ]; then
      printf ', '
    fi
    first=0
    printf '"%s"' "$(json_escape "$item")"
  done
  printf ']'
}

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
    -type f 2>/dev/null | sed "s#^$repo_root/##" | sort
}

get_remote_tree_paths() {
  curl -fsSL -H "User-Agent: hybrid-abw-installer" -H "Accept: application/vnd.github+json" \
    "$REPO_API_BASE/git/trees/$REPO_REF?recursive=1" |
    grep -oE '"path":"[^"]+"' |
    sed 's/^"path":"//; s/"$//' |
    sort
}

load_catalog_from_paths() {
  local tree_paths="$1"

  WORKFLOW_PATHS=()
  SKILL_PATHS=()
  SCHEMA_PATHS=()
  TEMPLATE_PATHS=()
  SCRIPT_PATHS=()

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
    esac
  done <<< "$tree_paths"
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
  local public_commands=("/abw-ask" "/abw-review" "/abw-doctor" "/abw-version" "/abw-migrate")
  local power_commands=("/abw-update" "/abw-rollback" "/abw-repair")
  local legacy_aliases=("/abw-health" "/abw-status" "/abw-ingest" "/abw-query" "/abw-query-deep")
  local all_commands=()
  local registered_public=()
  local dev_surface="${ABW_INSTALL_DEV_SURFACE:-0}"
  local workflow_path command tmp_file

  for workflow_path in "${WORKFLOW_PATHS[@]}"; do
    if command="$(workflow_path_to_command "$workflow_path" 2>/dev/null)"; then
      all_commands+=("$command")
    fi
  done

  if [ "$dev_surface" = "1" ]; then
    mapfile -t registered_public < <(printf '%s\n' "${all_commands[@]}" | sort -u)
  else
    mapfile -t registered_public < <(printf '%s\n' "${public_commands[@]}" "${power_commands[@]}" | sort -u)
  fi

  read -r -d '' ABW_INSTRUCTIONS <<EOF || true
# Hybrid ABW - Antigravity IDE Command Surface

## CRITICAL: Command Recognition
ABW is explicit-invocation only. Normal prompts, plain chat, and non-ABW slash workflows must bypass ABW.

Invoke ABW only when the user explicitly types \`/abw...\` or runs an \`abw\` CLI command.

When the user types one of the registered \`/abw...\` commands below, treat it as a Hybrid ABW workflow command loaded from \`~/.gemini/antigravity/global_workflows\`.
Do not silently fall back to a stale local clone when the verified remote snapshot is newer.
Hybrid ABW commands are authoritative only for \`/abw...\` inputs.

## Public Commands
$(join_commands "${registered_public[@]}")

## Legacy Compatibility Aliases
$(join_commands "${legacy_aliases[@]}")

## Hidden By Default
- Internal workflows remain installed on disk but are not part of the default public surface.
- Set \`ABW_INSTALL_DEV_SURFACE=1\` before install if you intentionally want the full workflow list exposed for development.

## Runtime Notes
- Installer source mode: $INSTALL_MODE
- Source decision: $INSTALL_REASON
- Workflow directory: \`~/.gemini/antigravity/global_workflows\`
- Skills directory: \`~/.gemini/antigravity/skills\`
- MCP config: \`~/.gemini/antigravity/mcp_config.json\`
- /abw-update must distinguish repo, workspace, runtime, and MCP sync state separately.

## Fallback Rule
If NotebookLM MCP is unavailable:
- ingest creates draft or pending-grounding artifacts only
- query falls back to wiki-first answers plus gap logging
- lint reports reduced grounding capability honestly
EOF

  mkdir -p "$(dirname "$GEMINI_MD")"
  if [ ! -f "$GEMINI_MD" ]; then
    printf '%s\n' "$ABW_INSTRUCTIONS" > "$GEMINI_MD"
    GEMINI_REFRESHED="true"
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
  GEMINI_REFRESHED="true"
}

remove_legacy_awf_skills() {
  local legacy_skills=(
    awf-adaptive-language
    awf-auto-save
    awf-context-help
    awf-error-translator
    awf-onboarding
    awf-session-restore
  )

  for skill in "${legacy_skills[@]}"; do
    if [ -e "$SKILLS_DIR/$skill" ]; then
      rm -rf "$SKILLS_DIR/$skill"
      echo -e "  ${GREEN}[OK]${NC} Removed legacy skill: $skill"
    fi
  done
}

ensure_required_artifacts_in_catalog() {
  local missing=0
  local workflow_name script_name rel_path found catalog_path

  for workflow_name in "${REQUIRED_RUNTIME_WORKFLOWS[@]}"; do
    rel_path="workflows/$workflow_name"
    found=0
    for catalog_path in "${WORKFLOW_PATHS[@]}"; do
      if [ "$catalog_path" = "$rel_path" ]; then
        found=1
        break
      fi
    done
    if [ "$found" -eq 0 ]; then
      append_error SOURCE_ERRORS "required runtime workflow missing from source catalog: $rel_path"
      missing=$((missing + 1))
    fi
  done

  for script_name in "${REQUIRED_RUNTIME_SCRIPTS[@]}"; do
    rel_path="scripts/$script_name"
    found=0
    for catalog_path in "${SCRIPT_PATHS[@]}"; do
      if [ "$catalog_path" = "$rel_path" ]; then
        found=1
        break
      fi
    done
    if [ "$found" -eq 0 ]; then
      append_error SOURCE_ERRORS "required runtime script missing from source catalog: $rel_path"
      missing=$((missing + 1))
    fi
  done

  return "$missing"
}

resolve_python_command() {
  local candidate
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYTHON_CMD="$(command -v "$candidate")"
      PYTHON_FOR_MCP="$PYTHON_CMD"
      PYTHON_FOR_REPORT="$PYTHON_CMD"
      return 0
    fi
  done
  return 1
}

patch_mcp_config() {
  local runner_path="$SCRIPTS_DIR/abw_runner.py"

  if [ -z "$PYTHON_CMD" ]; then
    append_error MCP_ERRORS "python executable could not be resolved for MCP registration"
    return 1
  fi

  if [ ! -f "$runner_path" ]; then
    append_error MCP_ERRORS "runtime runner script missing at $runner_path"
    return 1
  fi

  mkdir -p "$(dirname "$MCP_CONFIG_PATH")"
  "$PYTHON_CMD" - "$MCP_CONFIG_PATH" "$PYTHON_FOR_MCP" "$runner_path" <<'PY'
import json
import os
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
command = sys.argv[2]
runner_path = sys.argv[3]

if config_path.exists():
    raw = config_path.read_text(encoding="utf-8")
    data = json.loads(raw) if raw.strip() else {}
else:
    data = {}

if not isinstance(data, dict):
    raise SystemExit("mcp_config root must be a JSON object")

mcp_servers = data.get("mcpServers")
if mcp_servers is None:
    mcp_servers = {}
elif not isinstance(mcp_servers, dict):
    raise SystemExit("mcpServers must be a JSON object")

mcp_servers["abw_runner"] = {
    "command": os.path.abspath(command),
    "args": [os.path.abspath(runner_path)],
}
data["mcpServers"] = mcp_servers

config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

verified = json.loads(config_path.read_text(encoding="utf-8"))
entry = verified["mcpServers"]["abw_runner"]
if not os.path.isabs(entry["command"]):
    raise SystemExit("abw_runner command must be absolute")
if not entry.get("args") or not os.path.isabs(entry["args"][0]):
    raise SystemExit("abw_runner args[0] must be absolute")
PY
}

remove_abw_mcp_config() {
  if [ ! -f "$MCP_CONFIG_PATH" ]; then
    return 0
  fi
  if [ -z "$PYTHON_CMD" ]; then
    return 0
  fi
  "$PYTHON_CMD" - "$MCP_CONFIG_PATH" <<'PY'
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
raw = config_path.read_text(encoding="utf-8")
data = json.loads(raw) if raw.strip() else {}
if isinstance(data, dict) and isinstance(data.get("mcpServers"), dict):
    data["mcpServers"].pop("abw_runner", None)
config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
}

verify_runtime_artifacts() {
  local script_name workflow_name rel_path

  for script_name in "${REQUIRED_RUNTIME_SCRIPTS[@]}"; do
    if [ ! -f "$SCRIPTS_DIR/$script_name" ]; then
      append_error VERIFY_ERRORS "missing required runtime script: $SCRIPTS_DIR/$script_name"
    fi
  done

  for workflow_name in "${REQUIRED_RUNTIME_WORKFLOWS[@]}"; do
    if [ ! -f "$GLOBAL_DIR/$workflow_name" ]; then
      append_error VERIFY_ERRORS "missing required runtime workflow: $GLOBAL_DIR/$workflow_name"
    fi
  done

  if [ ! -f "$SCRIPTS_DIR/finalization_check.py" ]; then
    append_error VERIFY_ERRORS "missing finalization_check.py in runtime scripts directory"
  fi

  if [ ! -f "$GLOBAL_DIR/abw-update.md" ]; then
    append_error VERIFY_ERRORS "missing abw-update.md in runtime workflow directory"
  fi

  if [ "$GEMINI_REFRESHED" != "true" ] && ! grep -q "# Hybrid ABW - Antigravity IDE Command Surface" "$GEMINI_MD" 2>/dev/null; then
    append_error VERIFY_ERRORS "GEMINI.md missing Hybrid ABW registration block"
  fi

  if [ -n "$PYTHON_CMD" ]; then
    if ! "$PYTHON_CMD" -m py_compile \
      "$SCRIPTS_DIR/abw_runner.py" \
      "$SCRIPTS_DIR/finalization_check.py" \
      "$SCRIPTS_DIR/abw_accept.py" \
      "$SCRIPTS_DIR/continuation_gate.py" \
      "$SCRIPTS_DIR/continuation_execute.py" >/dev/null 2>&1; then
      append_error VERIFY_ERRORS "py_compile failed for one or more critical runtime scripts"
    fi
  else
    VERIFICATION_LIMITATIONS+=("py_compile skipped because no python executable was available on this host")
    append_error VERIFY_ERRORS "verification limitation: py_compile could not run because python was unavailable"
  fi

  if [ "${ABW_INSTALL_MCP:-0}" = "1" ] && [ ! -f "$MCP_CONFIG_PATH" ]; then
    append_error VERIFY_ERRORS "missing MCP config: $MCP_CONFIG_PATH"
  elif [ "${ABW_INSTALL_MCP:-0}" = "1" ] && [ -n "$PYTHON_CMD" ]; then
    if ! "$PYTHON_CMD" - "$MCP_CONFIG_PATH" "$SCRIPTS_DIR/abw_runner.py" <<'PY'
import json
import os
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
runner_path = os.path.abspath(sys.argv[2])
data = json.loads(config_path.read_text(encoding="utf-8"))
if not isinstance(data, dict):
    raise SystemExit(1)
mcp_servers = data.get("mcpServers")
if not isinstance(mcp_servers, dict):
    raise SystemExit(2)
entry = mcp_servers.get("abw_runner")
if not isinstance(entry, dict):
    raise SystemExit(3)
command = entry.get("command")
args = entry.get("args")
if not isinstance(command, str) or not command or not os.path.isabs(command):
    raise SystemExit(4)
if not isinstance(args, list) or not args or not isinstance(args[0], str) or not os.path.isabs(args[0]):
    raise SystemExit(5)
if os.path.abspath(args[0]) != runner_path:
    raise SystemExit(6)
if not Path(args[0]).exists():
    raise SystemExit(7)
PY
    then
      append_error VERIFY_ERRORS "MCP config does not contain a valid abw_runner entry bound to the installed runtime"
    fi
  fi
}

workspace_sync_state() {
  local repo_root="$1"
  local remote_ref="$2"
  if [ -z "$repo_root" ]; then
    printf 'not_present'
    return
  fi
  if ! command -v git >/dev/null 2>&1; then
    printf 'unverified'
    return
  fi
  if ! git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    printf 'unverified'
    return
  fi

  local status ahead behind
  status="$(git -C "$repo_root" status --porcelain 2>/dev/null || true)"
  if [ -n "$status" ]; then
    printf 'dirty'
    return
  fi

  ahead="$(git -C "$repo_root" rev-list --count "${remote_ref}..HEAD" 2>/dev/null || echo "")"
  behind="$(git -C "$repo_root" rev-list --count "HEAD..${remote_ref}" 2>/dev/null || echo "")"
  if [ -z "$ahead" ] || [ -z "$behind" ]; then
    printf 'unverified'
    return
  fi
  if [ "$behind" -gt 0 ] && [ "$ahead" -gt 0 ]; then
    printf 'diverged'
    return
  fi
  if [ "$behind" -gt 0 ]; then
    printf 'stale'
    return
  fi
  if [ "$ahead" -gt 0 ]; then
    printf 'ahead'
    return
  fi
  printf 'synced'
}

write_install_state() {
  local workspace_state="$1"
  local runtime_state="$2"
  local repo_state="$3"

  cat > "$ABW_INSTALL_STATE_FILE" <<EOF
{
  "installed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "repo": "$REPO_OWNER/$REPO_NAME",
  "repo_ref": "$(json_escape "$REPO_REF")",
  "version": "$(json_escape "$REMOTE_VERSION")",
  "installer_source_mode": "$(json_escape "$INSTALL_MODE")",
  "installer_reason": "$(json_escape "$INSTALL_REASON")",
  "source_sync_result": "$SOURCE_SYNC_RESULT",
  "runtime_sync_result": "$RUNTIME_SYNC_RESULT",
  "mcp_sync_result": "$MCP_SYNC_RESULT",
  "verification_result": "$VERIFICATION_RESULT",
  "final_verdict": "$FINAL_VERDICT",
  "repo_state": "$repo_state",
  "workspace_state": "$workspace_state",
  "runtime_state": "$runtime_state",
  "mcp_config_path": "$(json_escape "$MCP_CONFIG_PATH")",
  "python_command": "$(json_escape "$PYTHON_FOR_MCP")",
  "required_runtime_scripts": $(array_to_json REQUIRED_RUNTIME_SCRIPTS),
  "required_runtime_workflows": $(array_to_json REQUIRED_RUNTIME_WORKFLOWS),
  "source_errors": $(array_to_json SOURCE_ERRORS),
  "runtime_errors": $(array_to_json RUNTIME_ERRORS),
  "mcp_errors": $(array_to_json MCP_ERRORS),
  "verification_errors": $(array_to_json VERIFY_ERRORS),
  "verification_limitations": $(array_to_json VERIFICATION_LIMITATIONS)
}
EOF
}

REPO_ROOT="$(get_local_repo_root || true)"
resolve_install_mode "$REPO_ROOT"
REMOTE_VERSION="$(get_remote_version)"

mkdir -p "$GLOBAL_DIR" "$SCHEMAS_DIR" "$TEMPLATES_DIR" "$SKILLS_DIR" "$SCRIPTS_DIR" "$HOME/.gemini"

echo ""
echo -e "${CYAN}===============================================${NC}"
echo -e "${CYAN}Hybrid ABW Installer v$REMOTE_VERSION${NC}"
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
  append_error SOURCE_ERRORS "installer discovery failed: workflows or skills catalog is empty"
fi

if ! ensure_required_artifacts_in_catalog; then
  :
fi

if [ "${#SOURCE_ERRORS[@]}" -gt 0 ]; then
  SOURCE_SYNC_RESULT="FAIL"
  echo -e "${RED}Installer discovery failed.${NC}"
  for item in "${SOURCE_ERRORS[@]}"; do
    echo -e "  ${RED}[!]${NC} $item"
  done
  write_install_state "$(workspace_sync_state "$REPO_ROOT" "$INSTALL_REMOTE_REF")" "missing" "reachable"
  exit 1
fi

SOURCE_SYNC_RESULT="PASS"
INSTALLER_RAN="true"
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
    append_error RUNTIME_ERRORS "failed to install workflow: $rel_path"
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
    append_error RUNTIME_ERRORS "failed to install schema: $rel_path"
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
    append_error RUNTIME_ERRORS "failed to install template: $rel_path"
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
    append_error RUNTIME_ERRORS "failed to install skill: $rel_path"
    missing=$((missing + 1))
  fi
done

echo -e "${CYAN}Removing legacy AWF helper skills...${NC}"
remove_legacy_awf_skills

echo -e "${CYAN}Installing runtime scripts...${NC}"
for rel_path in "${SCRIPT_PATHS[@]}"; do
  leaf="$(basename "$rel_path")"
  if source_type="$(install_file "$rel_path" "$SCRIPTS_DIR/$leaf")"; then
    echo -e "  ${GREEN}[OK]${NC} $leaf ($source_type)"
    success=$((success + 1))
  else
    echo -e "  ${RED}[X]${NC} FAILED: $leaf"
    append_error RUNTIME_ERRORS "failed to install script: $rel_path"
    missing=$((missing + 1))
  fi
done

write_gemini_registration

if ! resolve_python_command; then
  if [ "${ABW_INSTALL_MCP:-0}" = "1" ]; then
    append_error MCP_ERRORS "python executable could not be resolved; MCP registration cannot be completed"
  fi
elif [ "${ABW_INSTALL_MCP:-0}" = "1" ]; then
  if ! patch_mcp_config; then
    :
  fi
else
  remove_abw_mcp_config
fi

if [ "$missing" -gt 0 ]; then
  RUNTIME_SYNC_RESULT="FAIL"
else
  RUNTIME_SYNC_RESULT="PASS"
fi

if [ "${ABW_INSTALL_MCP:-0}" != "1" ]; then
  MCP_SYNC_RESULT="SKIPPED"
elif [ "${#MCP_ERRORS[@]}" -gt 0 ]; then
  MCP_SYNC_RESULT="FAIL"
else
  MCP_SYNC_RESULT="PASS"
fi

printf '%s\n' "$REMOTE_VERSION" > "$ABW_VERSION_FILE"

echo -e "\n${CYAN}Verifying installation...${NC}"
verify_runtime_artifacts

if [ "${#VERIFY_ERRORS[@]}" -gt 0 ]; then
  VERIFICATION_RESULT="FAIL"
else
  VERIFICATION_RESULT="PASS"
fi

workspace_state="$(workspace_sync_state "$REPO_ROOT" "$INSTALL_REMOTE_REF")"
repo_state="reachable"
runtime_state="synced"

if [ "${#RUNTIME_ERRORS[@]}" -gt 0 ] || [ "$missing" -gt 0 ]; then
  runtime_state="missing"
fi
if [ "${#VERIFY_ERRORS[@]}" -gt 0 ]; then
  runtime_state="stale"
fi

if [ "$SOURCE_SYNC_RESULT" = "FAIL" ] || [ "$RUNTIME_SYNC_RESULT" = "FAIL" ] || [ "$MCP_SYNC_RESULT" = "FAIL" ] || [ "$VERIFICATION_RESULT" = "FAIL" ]; then
  FINAL_VERDICT="FAIL"
elif [ "$workspace_state" = "stale" ] || [ "$workspace_state" = "dirty" ] || [ "$workspace_state" = "diverged" ]; then
  FINAL_VERDICT="PARTIAL"
else
  FINAL_VERDICT="PASS"
fi

write_install_state "$workspace_state" "$runtime_state" "$repo_state"

echo ""
echo -e "${YELLOW}Installed $success files.${NC}"
echo -e "${GRAY}ABW version file: $ABW_VERSION_FILE${NC}"
echo -e "${GRAY}ABW install state: $ABW_INSTALL_STATE_FILE${NC}"
echo -e "${GRAY}MCP config: $MCP_CONFIG_PATH${NC}"
echo -e "${GRAY}Runtime workflows: $GLOBAL_DIR${NC}"
echo -e "${GRAY}Runtime scripts: $SCRIPTS_DIR${NC}"
echo ""
echo "source_sync_result=$SOURCE_SYNC_RESULT"
echo "runtime_sync_result=$RUNTIME_SYNC_RESULT"
echo "mcp_sync_result=$MCP_SYNC_RESULT"
echo "verification_result=$VERIFICATION_RESULT"
echo "repo_state=$repo_state"
echo "workspace_state=$workspace_state"
echo "runtime_state=$runtime_state"
echo "final_verdict=$FINAL_VERDICT"

if [ "${#SOURCE_ERRORS[@]}" -gt 0 ]; then
  printf '%s\n' "${SOURCE_ERRORS[@]}"
fi
if [ "${#RUNTIME_ERRORS[@]}" -gt 0 ]; then
  printf '%s\n' "${RUNTIME_ERRORS[@]}"
fi
if [ "${#MCP_ERRORS[@]}" -gt 0 ]; then
  printf '%s\n' "${MCP_ERRORS[@]}"
fi
if [ "${#VERIFY_ERRORS[@]}" -gt 0 ]; then
  printf '%s\n' "${VERIFY_ERRORS[@]}"
fi
if [ "${#VERIFICATION_LIMITATIONS[@]}" -gt 0 ]; then
  printf '%s\n' "${VERIFICATION_LIMITATIONS[@]}"
fi

if [ "$FINAL_VERDICT" = "FAIL" ]; then
  exit 1
fi

exit 0
