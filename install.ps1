# Hybrid ABW Installer for Windows (PowerShell)

$RepoBase = "https://raw.githubusercontent.com/Nakazasen/skill-Anti-brain-wiki_note/main"
$GlobalDir = "$env:USERPROFILE\.gemini\antigravity\global_workflows"
$SchemasDir = "$env:USERPROFILE\.gemini\antigravity\schemas"
$TemplatesDir = "$env:USERPROFILE\.gemini\antigravity\templates"
$SkillsDir = "$env:USERPROFILE\.gemini\antigravity\skills"
$ScriptsDir = "$env:USERPROFILE\.gemini\antigravity\scripts"
$GeminiMd = "$env:USERPROFILE\.gemini\GEMINI.md"
$AbwVersionFile = "$env:USERPROFILE\.gemini\abw_version"

$WorkflowFiles = @(
    "abw-init.md",
    "abw-setup.md",
    "abw-status.md",
    "abw-ingest.md",
    "abw-pack.md",
    "abw-sync.md",
    "abw-query.md",
    "abw-query-deep.md",
    "abw-lint.md",
    "abw-bootstrap.md",
    "abw-ask.md",
    "abw-audit.md",
    "abw-meta-audit.md",
    "abw-accept.md",
    "abw-eval.md",
    "abw-start.md",
    "abw-wrap.md",
    "abw-review.md",
    "abw-rollback.md",

    "brainstorm.md",
    "plan.md",
    "design.md",
    "visualize.md",
    "code.md",
    "run.md",
    "debug.md",
    "test.md",
    "deploy.md",
    "refactor.md",
    "audit.md",
    "save_brain.md",
    "recap.md",
    "help.md",
    "next.md",
    "README.md",
    "abw-update.md"
)

$SchemaFiles = @(
    "brain.schema.json",
    "session.schema.json",
    "preferences.schema.json",
    "notebook_package_manifest.schema.json"
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
    "deliberation_run.example.json",
    "assumptions.example.json",
    "hypotheses.example.json",
    "decision_log.example.jsonl",
    "validation_backlog.example.json",
    "notebook_pack_policy.example.json",
    "notebook_package_manifest.example.json"
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
    "abw-audit.md",
    "abw-meta-audit.md",
    "abw-accept.md",
    "abw-eval.md",
    "abw-start.md",
    "abw-wrap.md",
    "abw-review.md",
    "abw-rollback.md",
    "ingest-wiki.md",
    "notebooklm-knowledge-packager.md",
    "notebooklm-sync.md",
    "query-wiki.md",
    "query-wiki-deliberative.md",
    "lint-wiki.md",
    "notebooklm-mcp-bridge.md",
    "abw-bootstrap.md",
    "abw-router.md"
)

try {
    $CurrentVersion = (Invoke-WebRequest -Uri "$RepoBase/VERSION" -UseBasicParsing).Content.Trim()
}
catch {
    $CurrentVersion = "1.2.0"
}

$Null = New-Item -ItemType Directory -Force -Path $GlobalDir, $SchemasDir, $TemplatesDir, $SkillsDir, "$env:USERPROFILE\.gemini"

# Local clone detection
$isLocalRepo = $false
$RepoRoot = ""
if ($MyInvocation.MyCommand.Path) {
    # If run as a script file, check if it's inside the actual repo
    $possibleRoot = Split-Path $MyInvocation.MyCommand.Path
    if (Test-Path (Join-Path $possibleRoot "workflows\abw-init.md")) {
        $isLocalRepo = $true
        $RepoRoot = $possibleRoot
    }
}

function Install-File {
    param(
        [string]$RelativePath,
        [string]$Destination
    )
    if ($isLocalRepo) {
        $LocalPath = Join-Path $RepoRoot $RelativePath
        if (Test-Path $LocalPath) {
            Copy-Item -Path $LocalPath -Destination $Destination -Force -ErrorAction Stop
            return "LOCAL"
        }
    }
    
    $Url = "$RepoBase/$RelativePath"
    if ($Url -match '\\') {
        $Url = $Url.Replace('\', '/')
    }
    Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing -ErrorAction Stop
    return "REMOTE"
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "Hybrid ABW Installer v$CurrentVersion" -ForegroundColor Cyan
if ($isLocalRepo) {
    Write-Host "(Local installation mode detected)" -ForegroundColor Yellow
}
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

$success = 0
$criticalFail = $false

Write-Host "Installing ABW workflows..." -ForegroundColor Cyan
foreach ($wf in $WorkflowFiles) {
    try {
        $source = Install-File -RelativePath "workflows/$wf" -Destination "$GlobalDir\$wf"
        Write-Host "  [OK] $wf ($source)" -ForegroundColor Green
        $success++
    }
    catch {
        Write-Host "  [X] FAILED: $wf" -ForegroundColor Red
        $criticalFail = $true
    }
}

if ($criticalFail) {
    Write-Host "`nCRITICAL ERROR: Failed to install one or more required ABW workflows. Aborting installation." -ForegroundColor Red
    exit 1
}

Write-Host "Installing schemas..." -ForegroundColor Cyan
foreach ($schema in $SchemaFiles) {
    try {
        $source = Install-File -RelativePath "schemas/$schema" -Destination "$SchemasDir\$schema"
        Write-Host "  [OK] $schema ($source)" -ForegroundColor Green
        $success++
    }
    catch {
        Write-Host "  [X] FAILED: $schema" -ForegroundColor Red
    }
}

Write-Host "Installing templates..." -ForegroundColor Cyan
foreach ($template in $TemplateFiles) {
    try {
        $source = Install-File -RelativePath "templates/$template" -Destination "$TemplatesDir\$template"
        Write-Host "  [OK] $template ($source)" -ForegroundColor Green
        $success++
    }
    catch {
        Write-Host "  [X] FAILED: $template" -ForegroundColor Red
    }
}

$criticalFail = $false
Write-Host "Installing ABW skills..." -ForegroundColor Cyan
foreach ($skill in $AbwSkills) {
    try {
        $source = Install-File -RelativePath "skills/$skill" -Destination "$SkillsDir\$skill"
        Write-Host "  [OK] $skill ($source)" -ForegroundColor Green
        $success++
    }
    catch {
        Write-Host "  [X] FAILED: $skill" -ForegroundColor Red
        $criticalFail = $true
    }
}

if ($criticalFail) {
    Write-Host "`nCRITICAL ERROR: Failed to install one or more required ABW skills. Aborting installation." -ForegroundColor Red
    exit 1
}

Write-Host "Installing compatibility helper skills..." -ForegroundColor Cyan
foreach ($skill in $AwfHelperSkills) {
    $skillDir = "$SkillsDir\$skill"
    $Null = New-Item -ItemType Directory -Force -Path $skillDir
    try {
        $source = Install-File -RelativePath "awf_skills/$skill/SKILL.md" -Destination "$skillDir\SKILL.md"
        Write-Host "  [OK] $skill ($source)" -ForegroundColor Green
        $success++
    }
    catch {
        Write-Host "  [X] FAILED: $skill" -ForegroundColor Red
    }
}

Write-Host "Installing runtime scripts..." -ForegroundColor Cyan
# Runtime scripts are copied explicitly to avoid publishing __pycache__ artifacts.
$sourceScriptDir = if ($isLocalRepo) { Join-Path $PSScriptRoot "scripts" } else { $null }
if ($isLocalRepo -and (Test-Path "$sourceScriptDir\abw_pack.py") -and (Test-Path "$sourceScriptDir\abw_sync.py")) {
    $Null = New-Item -ItemType Directory -Force -Path $ScriptsDir
    try {
        Copy-Item -Path "$sourceScriptDir\abw_pack.py" -Destination "$ScriptsDir\abw_pack.py" -Force
        Copy-Item -Path "$sourceScriptDir\abw_sync.py" -Destination "$ScriptsDir\abw_sync.py" -Force
        Write-Host "  [OK] Copied runtime scripts ($sourceScriptDir)" -ForegroundColor Green
        $success++
    }
    catch {
        Write-Host "  [X] FAILED: Could not copy runtime scripts" -ForegroundColor Red
    }
} elseif (-not $isLocalRepo) {
    $Null = New-Item -ItemType Directory -Force -Path $ScriptsDir
    try {
        Invoke-WebRequest -Uri "$RepoBase/scripts/abw_pack.py" -OutFile "$ScriptsDir\abw_pack.py" -UseBasicParsing
        Invoke-WebRequest -Uri "$RepoBase/scripts/abw_sync.py" -OutFile "$ScriptsDir\abw_sync.py" -UseBasicParsing
        Write-Host "  [OK] Downloaded runtime scripts" -ForegroundColor Green
        $success++
    } catch {
        Write-Host "  [X] FAILED: Could download runtime scripts" -ForegroundColor Red
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
| `/abw-pack` | abw-pack.md | Package wiki into compressed files for NotebookLM limits |
| `/abw-sync` | abw-sync.md | Dry-run or execute NotebookLM sync for an approved package |
| `/abw-ask` | abw-ask.md | Smart default router: auto-selects fast, deep, or bootstrap path |

| `/abw-query` | abw-query.md | Fast wiki-first query path |
| `/abw-query-deep` | abw-query-deep.md | TTC deliberation path for complex questions |
| `/abw-lint` | abw-lint.md | Audit wiki, grounding, and deliberation health |
| `/abw-bootstrap` | abw-bootstrap.md | System 2 reasoning for greenfield ideas (no raw/wiki data yet) |
| `/abw-audit` | abw-audit.md | Self-audit a change, workflow, doc, or output |
| `/abw-meta-audit` | abw-meta-audit.md | Audit the audit report itself |
| `/abw-accept` | abw-accept.md | Run the final acceptance gate |
| `/abw-eval` | abw-eval.md | Run the full evaluation chain |
| `/abw-start` | abw-start.md | Start a session with state, grounding, and next-step checks |
| `/abw-wrap` | abw-wrap.md | Wrap a session with handover and follow-up guidance |
| `/abw-review` | abw-review.md | Review code, changes, or current project state |
| `/abw-rollback` | abw-rollback.md | Recover a safe state after a bad change |

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

## Command Model (5 Lanes)
- Ask & Think: `/abw-ask`, `/abw-query`, `/abw-query-deep`, `/abw-bootstrap`, `/brainstorm`
- Build Knowledge: `/abw-init`, `/abw-setup`, `/abw-status`, `/abw-ingest`, `/abw-pack`, `/abw-sync`, `/abw-lint`
- Build Product: `/plan`, `/design`, `/visualize`, `/code`, `/run`, `/debug`, `/test`, `/deploy`, `/refactor`, `/audit`
- Session & Memory: `/abw-start`, `/save-brain`, `/recap`, `/next`, `/abw-wrap`
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
"@

if (-not (Test-Path $GeminiMd)) {
    Set-Content -Path $GeminiMd -Value $abwInstructions -Encoding UTF8
}
else {
    $content = Get-Content $GeminiMd -Raw -ErrorAction SilentlyContinue
    if ($null -eq $content) { $content = "" }
    $abwMarker = "# Hybrid ABW - Antigravity IDE Command Surface"
    $abwIndex = $content.IndexOf($abwMarker)
    if ($abwIndex -ge 0) { $content = $content.Substring(0, $abwIndex).TrimEnd() }
    if ($content.Length -gt 0) {
        $content = $content + "`n`n" + $abwInstructions
    }
    else {
        $content = $abwInstructions
    }
    Set-Content -Path $GeminiMd -Value $content -Encoding UTF8
}

Write-Host "`nVerifying installation..." -ForegroundColor Cyan
$missingFiles = 0
$requiredWorkflows = @(
    "abw-init.md", "abw-setup.md", "abw-status.md", "abw-ingest.md", "abw-pack.md", "abw-sync.md", "abw-ask.md",
    "abw-query.md", "abw-query-deep.md", "abw-bootstrap.md", "abw-lint.md",
    "abw-audit.md", "abw-meta-audit.md", "abw-accept.md", "abw-eval.md",
    "abw-start.md", "abw-wrap.md", "abw-review.md", "abw-rollback.md",
    "brainstorm.md", "plan.md", "design.md", "visualize.md", "code.md", "run.md",
    "debug.md", "test.md", "deploy.md", "refactor.md", "audit.md", "save_brain.md",
    "recap.md", "next.md", "help.md", "README.md", "abw-update.md"
)

foreach ($wf in $requiredWorkflows) {
    if (-not (Test-Path "$GlobalDir\$wf")) {
        Write-Host "  [!] Missing: $wf" -ForegroundColor Red
        $missingFiles++
    } else {
        Write-Host "  [OK] Verified: $wf" -ForegroundColor DarkGray
    }
}

foreach ($skill in $AbwSkills) {
    if (-not (Test-Path "$SkillsDir\$skill")) {
        Write-Host "  [!] Missing Skill: $skill" -ForegroundColor Red
        $missingFiles++
    } else {
        Write-Host "  [OK] Verified Skill: $skill" -ForegroundColor DarkGray
    }
}

$geminiContent = Get-Content $GeminiMd -Raw -ErrorAction SilentlyContinue
if (($null -eq $geminiContent) -or ($geminiContent.IndexOf("# Hybrid ABW - Antigravity IDE Command Surface") -lt 0)) {
    Write-Host "  [!] GEMINI.md missing ABW block." -ForegroundColor Red
    $missingFiles++
} else {
    Write-Host "  [OK] GEMINI.md ABW registration verified." -ForegroundColor DarkGray
}

if ($missingFiles -gt 0) {
    Write-Host "`nInstallation FAILED verification. Missing $missingFiles required components." -ForegroundColor Red
    exit 1
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
Write-Host "  3. Run /abw-ingest to build project knowledge" -ForegroundColor White
Write-Host "  4. Run /abw-ask when you have a task or question and want the router to choose the lane" -ForegroundColor White
Write-Host "  5. Run /abw-eval when you want an evaluation pass before accepting a change or output" -ForegroundColor White
Write-Host ""
