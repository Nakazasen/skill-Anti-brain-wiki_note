# Hybrid ABW Installer for Windows (PowerShell)

$RepoBase = "https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main"
$GlobalDir = "$env:USERPROFILE\.gemini\antigravity\global_workflows"
$SchemasDir = "$env:USERPROFILE\.gemini\antigravity\schemas"
$TemplatesDir = "$env:USERPROFILE\.gemini\antigravity\templates"
$SkillsDir = "$env:USERPROFILE\.gemini\antigravity\skills"
$GeminiMd = "$env:USERPROFILE\.gemini\GEMINI.md"
$AbwVersionFile = "$env:USERPROFILE\.gemini\abw_version"

$WorkflowFiles = @(
    "abw-init.md",
    "abw-setup.md",
    "abw-status.md",
    "abw-ingest.md",
    "abw-query.md",
    "abw-query-deep.md",
    "abw-lint.md",
    "help.md",
    "next.md",
    "README.md",
    "awf-update.md"
)

$SchemaFiles = @(
    "brain.schema.json",
    "session.schema.json",
    "preferences.schema.json"
)

$TemplateFiles = @(
    "brain.example.json",
    "session.example.json",
    "preferences.example.json",
    "manifest.example.jsonl",
    "grounding_queue.example.json",
    "knowledge_gaps.example.json",
    "exit_gate_policy.example.json",
    "circuit_breaker.example.json",
    "ingest_exit_gate_policy.json",
    "ingest_circuit_breaker.json"
)

$AwfHelperSkills = @(
    "awf-session-restore",
    "awf-auto-save",
    "awf-adaptive-language",
    "awf-error-translator",
    "awf-context-help",
    "awf-onboarding"
)

$AbwSkills = @(
    "abw-init.md",
    "abw-setup.md",
    "abw-status.md",
    "ingest-wiki.md",
    "ingest-wiki-deliberative.md",
    "query-wiki.md",
    "query-wiki-deliberative.md",
    "lint-wiki.md",
    "notebooklm-mcp-bridge.md"
)

try {
    $CurrentVersion = (Invoke-WebRequest -Uri "$RepoBase/VERSION" -UseBasicParsing).Content.Trim()
} catch {
    $CurrentVersion = "1.1.1"
}

$Null = New-Item -ItemType Directory -Force -Path $GlobalDir, $SchemasDir, $TemplatesDir, $SkillsDir, "$env:USERPROFILE\.gemini"

function Download-File {
    param(
        [string]$Url,
        [string]$Destination
    )
    Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing -ErrorAction Stop
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "Hybrid ABW Installer v$CurrentVersion" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

$success = 0

Write-Host "Installing ABW workflows..." -ForegroundColor Cyan
foreach ($wf in $WorkflowFiles) {
    try {
        Download-File -Url "$RepoBase/workflows/$wf" -Destination "$GlobalDir\$wf"
        Write-Host "  [OK] $wf" -ForegroundColor Green
        $success++
    } catch {
        Write-Host "  [X] $wf" -ForegroundColor Red
    }
}

Write-Host "Installing schemas..." -ForegroundColor Cyan
foreach ($schema in $SchemaFiles) {
    try {
        Download-File -Url "$RepoBase/schemas/$schema" -Destination "$SchemasDir\$schema"
        Write-Host "  [OK] $schema" -ForegroundColor Green
        $success++
    } catch {
        Write-Host "  [X] $schema" -ForegroundColor Red
    }
}

Write-Host "Installing templates..." -ForegroundColor Cyan
foreach ($template in $TemplateFiles) {
    try {
        Download-File -Url "$RepoBase/templates/$template" -Destination "$TemplatesDir\$template"
        Write-Host "  [OK] $template" -ForegroundColor Green
        $success++
    } catch {
        Write-Host "  [X] $template" -ForegroundColor Red
    }
}

Write-Host "Installing ABW skills..." -ForegroundColor Cyan
foreach ($skill in $AbwSkills) {
    try {
        Download-File -Url "$RepoBase/skills/$skill" -Destination "$SkillsDir\$skill"
        Write-Host "  [OK] $skill" -ForegroundColor Green
        $success++
    } catch {
        Write-Host "  [X] $skill" -ForegroundColor Red
    }
}

Write-Host "Installing compatibility helper skills..." -ForegroundColor Cyan
foreach ($skill in $AwfHelperSkills) {
    $skillDir = "$SkillsDir\$skill"
    $Null = New-Item -ItemType Directory -Force -Path $skillDir
    try {
        Download-File -Url "$RepoBase/awf_skills/$skill/SKILL.md" -Destination "$skillDir\SKILL.md"
        Write-Host "  [OK] $skill" -ForegroundColor Green
        $success++
    } catch {
        Write-Host "  [X] $skill" -ForegroundColor Red
    }
}

Set-Content -Path $AbwVersionFile -Value $CurrentVersion -Encoding UTF8

$abwInstructions = @"
# Hybrid ABW - Antigravity IDE Command Surface

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
"@

if (-not (Test-Path $GeminiMd)) {
    Set-Content -Path $GeminiMd -Value $abwInstructions -Encoding UTF8
} else {
    $content = Get-Content $GeminiMd -Raw -ErrorAction SilentlyContinue
    if ($null -eq $content) { $content = "" }
    $abwMarker = "# Hybrid ABW - Antigravity IDE Command Surface"
    $oldAwfMarker = "# AWF - Antigravity Workflow Framework"
    $abwIndex = $content.IndexOf($abwMarker)
    if ($abwIndex -ge 0) { $content = $content.Substring(0, $abwIndex).TrimEnd() }
    $oldAwfIndex = $content.IndexOf($oldAwfMarker)
    if ($oldAwfIndex -ge 0) { $content = $content.Substring(0, $oldAwfIndex).TrimEnd() }
    if ($content.Length -gt 0) {
        $content = $content + "`n`n" + $abwInstructions
    } else {
        $content = $abwInstructions
    }
    Set-Content -Path $GeminiMd -Value $content -Encoding UTF8
}

Write-Host ""
Write-Host "Installed $success files." -ForegroundColor Yellow
Write-Host "ABW version file: $AbwVersionFile" -ForegroundColor DarkGray
Write-Host "Workflows: $GlobalDir" -ForegroundColor DarkGray
Write-Host "Skills: $SkillsDir" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Run /abw-init" -ForegroundColor White
Write-Host "  2. Run /abw-setup" -ForegroundColor White
Write-Host "  3. Run /abw-ingest after dropping sources into raw/" -ForegroundColor White
Write-Host ""