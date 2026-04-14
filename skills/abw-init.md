# Skill: abw-init

> **Version:** 1.0.0  
> **Trigger:** User says "/abw-init" or requests to "install ABW", "setup wiki architecture"  
> **Source:** `templates/` inside the global skill folder  
> **Targets:** Current workspace root  

---

## Purpose

Initialize or upgrade the Hybrid Anti-Brain-Wiki (ABW) architecture in any project. Ensure consistent directory structure, schemas, and policy templates to enable all other ABW commands.

---

## Initialization Pipeline

### STAGE 1: Environment Audit
1. Identify the current workspace root directory.
2. Check for existence of the following folders:
   - `wiki/`
   - `wiki/_schemas/`
   - `wiki/entities/`, `wiki/concepts/`, `wiki/timelines/`, `wiki/sources/`
   - `processed/`
   - `raw/`
   - `.brain/`
3. Check for existence of core configuration files in `.brain/`:
   - `exit_gate_policy.json`
   - `circuit_breaker.json`
   - `lessons_learned.jsonl`

### STAGE 2: Scaffold Structure
1. **Create Missing Folders**: Run `mkdir` or equivalent for all missing folders identified in Stage 1.
2. **Setup .gitignore**: If not present, append the following to the project's `.gitignore`:
   ```text
   # Hybrid ABW Runtime State
   raw/*
   processed/*
   .brain/grounding_queue.json
   .brain/knowledge_gaps.json
   .brain/deliberation_runs.jsonl
   .brain/lessons_learned.jsonl
   .brain/cache/
   ```

### STAGE 3: Provision Templates
Copy the following files from the global skill `templates/` directory to the workspace (only if missing, do NOT overwrite user-modified files unless asked):

| Template Source | Workspace Destination | Purpose |
|-----------------|-----------------------|---------|
| `note_schema.example.md` | `wiki/_schemas/note.schema.md` | Enforcement of wiki structure |
| `wiki_index.example.md` | `wiki/index.md` | Knowledge root index |
| `exit_gate_policy.example.json` | `.brain/exit_gate_policy.json` | TTC Deliberation scoring |
| `circuit_breaker.example.json` | `.brain/circuit_breaker.json` | Loop safety control |
| `lessons_learned.example.jsonl` | `.brain/lessons_learned.jsonl` | Active user corrections and project-specific lessons |

### STAGE 4: Finalize & Welcome
1. Verify all files are in place.
2. Log a summary of created/updated items.
3. Inform the user:
   - "Hybrid ABW architecture initialized successfully."
   - "Next Step: Run `/abw-setup` to configure NotebookLM and exit Fallback Mode."
   - "Ready to ingest: Drop your first source into `/raw` and run `/abw-ingest`."

---

## Implementation Details for AI

When executing this skill, use `run_command` with PowerShell to ensure directory creation and file copying works reliably on Windows.

**Template Path Retrieval**: 
The templates are located in the `templates/` directory inside the global skill folder.
ALWAYS refer to the current skill directory to find the source for the bootstrap copy operation.

---

## Usage Examples

### Fresh Project
"Install ABW here" -> AI creates all 7 folders + 4 template files + updates gitignore.

### Existing Project (Upgrade)
"I want to add the wiki system to this repo" -> AI detects existing folders, only adds `wiki/_schemas` and configuration templates.
