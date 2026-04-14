# Hybrid ABW Installer for Windows (PowerShell)

$ErrorActionPreference = "Stop"

$RepoOwner = "Nakazasen"
$RepoName = "skill-Anti-brain-wiki_note"
$RepoRef = "main"
$RepoBase = "https://raw.githubusercontent.com/$RepoOwner/$RepoName/$RepoRef"
$RepoApiBase = "https://api.github.com/repos/$RepoOwner/$RepoName"

$GlobalDir = "$env:USERPROFILE\.gemini\antigravity\global_workflows"
$SchemasDir = "$env:USERPROFILE\.gemini\antigravity\schemas"
$TemplatesDir = "$env:USERPROFILE\.gemini\antigravity\templates"
$SkillsDir = "$env:USERPROFILE\.gemini\antigravity\skills"
$ScriptsDir = "$env:USERPROFILE\.gemini\antigravity\scripts"
$GeminiMd = "$env:USERPROFILE\.gemini\GEMINI.md"
$AbwVersionFile = "$env:USERPROFILE\.gemini\abw_version"
$AbwInstallStateFile = "$env:USERPROFILE\.gemini\abw_install_state.json"

function Get-RemoteVersion {
    try {
        return (Invoke-WebRequest -Uri "$RepoBase/VERSION" -UseBasicParsing).Content.Trim()
    }
    catch {
        return "unknown"
    }
}

function Get-LocalRepoRoot {
    if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "workflows\abw-init.md"))) {
        return $PSScriptRoot
    }

    if (-not $MyInvocation.MyCommand.Path) {
        return $null
    }

    $possibleRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    if (Test-Path (Join-Path $possibleRoot "workflows\abw-init.md")) {
        return $possibleRoot
    }

    return $null
}

function Get-GitCommand {
    return Get-Command git -ErrorAction SilentlyContinue
}

function Resolve-InstallMode {
    param(
        [string]$RepoRoot
    )

    $forced = $env:ABW_INSTALL_SOURCE
    if ($forced) {
        $normalized = $forced.Trim().ToLowerInvariant()
        if ($normalized -eq "local") {
            return @{ Mode = "LOCAL"; Reason = "ABW_INSTALL_SOURCE=local"; RemoteRef = "origin/$RepoRef" }
        }
        if ($normalized -eq "remote") {
            return @{ Mode = "REMOTE"; Reason = "ABW_INSTALL_SOURCE=remote"; RemoteRef = "origin/$RepoRef" }
        }
    }

    if (-not $RepoRoot) {
        return @{ Mode = "REMOTE"; Reason = "No local repository clone detected"; RemoteRef = "origin/$RepoRef" }
    }

    $git = Get-GitCommand
    if (-not $git) {
        return @{ Mode = "REMOTE"; Reason = "git is unavailable; remote is the only trustworthy latest source"; RemoteRef = "origin/$RepoRef" }
    }

    try {
        $null = & $git.Source -C $RepoRoot rev-parse --is-inside-work-tree 2>$null
    }
    catch {
        return @{ Mode = "REMOTE"; Reason = "Local path is not a git worktree; remote is the only trustworthy latest source"; RemoteRef = "origin/$RepoRef" }
    }

    $remoteRef = "origin/$RepoRef"
    try {
        $tracked = (& $git.Source -C $RepoRoot rev-parse --abbrev-ref --symbolic-full-name "@{upstream}" 2>$null | Select-Object -First 1).Trim()
        if ($tracked) {
            $remoteRef = $tracked
        }
    }
    catch {
    }

    try {
        & $git.Source -C $RepoRoot fetch --quiet --prune --tags origin 2>$null | Out-Null
    }
    catch {
        return @{ Mode = "REMOTE"; Reason = "Could not verify local clone against origin; remote install is safer"; RemoteRef = $remoteRef }
    }

    try {
        $head = (& $git.Source -C $RepoRoot rev-parse HEAD 2>$null | Select-Object -First 1).Trim()
        $remoteHead = (& $git.Source -C $RepoRoot rev-parse $remoteRef 2>$null | Select-Object -First 1).Trim()
        $status = & $git.Source -C $RepoRoot status --porcelain 2>$null

        if ($head -and $remoteHead -and $head -eq $remoteHead -and -not $status) {
            return @{ Mode = "LOCAL"; Reason = "Local clone is clean and already at $remoteRef"; RemoteRef = $remoteRef }
        }

        if ($status) {
            return @{ Mode = "REMOTE"; Reason = "Local clone has uncommitted changes; installing the verified remote snapshot"; RemoteRef = $remoteRef }
        }

        return @{ Mode = "REMOTE"; Reason = "Local clone does not match $remoteRef; installing the verified remote snapshot"; RemoteRef = $remoteRef }
    }
    catch {
        return @{ Mode = "REMOTE"; Reason = "Could not compare local HEAD with $remoteRef; remote install is safer"; RemoteRef = $remoteRef }
    }
}

function Get-LocalTreePaths {
    param(
        [string]$RepoRoot
    )

    $paths = New-Object System.Collections.Generic.List[string]

    foreach ($dir in @("workflows", "skills", "schemas", "templates", "scripts", "awf_skills")) {
        $target = Join-Path $RepoRoot $dir
        if (-not (Test-Path $target)) {
            continue
        }

        Get-ChildItem -Path $target -Recurse -File | ForEach-Object {
            $relative = $_.FullName.Substring($RepoRoot.Length + 1).Replace("\", "/")
            $paths.Add($relative)
        }
    }

    return $paths
}

function Get-RemoteTreePaths {
    $headers = @{
        "User-Agent" = "hybrid-abw-installer"
        "Accept" = "application/vnd.github+json"
    }
    $tree = Invoke-RestMethod -Uri "${RepoApiBase}/git/trees/${RepoRef}?recursive=1" -Headers $headers
    return $tree.tree | Where-Object { $_.type -eq "blob" } | ForEach-Object { $_.path }
}

function New-RepoCatalog {
    param(
        [string[]]$Paths
    )

    return @{
        WorkflowPaths = $Paths | Where-Object { $_ -like "workflows/*.md" } | Sort-Object -Unique
        SkillPaths = $Paths | Where-Object { $_ -like "skills/*.md" } | Sort-Object -Unique
        SchemaPaths = $Paths | Where-Object { $_ -like "schemas/*.json" } | Sort-Object -Unique
        TemplatePaths = $Paths | Where-Object { $_ -like "templates/*" -and $_ -notlike "templates/*/*" } | Sort-Object -Unique
        ScriptPaths = $Paths | Where-Object { $_ -like "scripts/*.py" } | Sort-Object -Unique
        HelperSkills = $Paths |
            Where-Object { $_ -like "awf_skills/*/SKILL.md" } |
            ForEach-Object { ($_ -split "/")[1] } |
            Sort-Object -Unique
    }
}

function Install-File {
    param(
        [string]$RelativePath,
        [string]$Destination,
        [string]$SourceMode,
        [string]$RepoRoot
    )

    $parent = Split-Path -Parent $Destination
    if ($parent) {
        $null = New-Item -ItemType Directory -Force -Path $parent
    }

    if ($SourceMode -eq "LOCAL") {
        $localPath = Join-Path $RepoRoot $RelativePath
        if (-not (Test-Path $localPath)) {
            throw "Missing local source: $RelativePath"
        }

        Copy-Item -Path $localPath -Destination $Destination -Force
        return "LOCAL"
    }

    $url = "$RepoBase/$RelativePath".Replace("\", "/")
    Invoke-WebRequest -Uri $url -OutFile $Destination -UseBasicParsing
    return "REMOTE"
}

function Convert-WorkflowPathToCommand {
    param(
        [string]$RelativePath
    )

    $leaf = [System.IO.Path]::GetFileNameWithoutExtension($RelativePath)
    if ($leaf -eq "README") {
        return $null
    }

    return "/" + $leaf.Replace("_", "-")
}

function Join-Commands {
    param(
        [string[]]$Commands
    )

    if (-not $Commands -or $Commands.Count -eq 0) {
        return "(none)"
    }

    return ($Commands | Sort-Object -Unique) -join ", "
}

function Write-GeminiRegistration {
    param(
        [hashtable]$Catalog,
        [string]$SourceMode,
        [string]$ModeReason
    )

    $abwCommands = New-Object System.Collections.Generic.List[string]
    $extendedCommands = New-Object System.Collections.Generic.List[string]

    foreach ($workflowPath in $Catalog.WorkflowPaths) {
        $command = Convert-WorkflowPathToCommand -RelativePath $workflowPath
        if (-not $command) {
            continue
        }

        if ($command.StartsWith("/abw-")) {
            $abwCommands.Add($command)
        }
        else {
            $extendedCommands.Add($command)
        }
    }

    $abwInstructions = @"
# Hybrid ABW - Antigravity IDE Command Surface

## CRITICAL: Command Recognition
When the user types one of the registered commands below, treat it as a Hybrid ABW workflow command loaded from `~/.gemini/antigravity/global_workflows`.
Do not silently fall back to a stale local clone when the verified remote snapshot is newer.

## Registered ABW Commands
$(Join-Commands -Commands $abwCommands.ToArray())

## Registered Extended Commands
$(Join-Commands -Commands $extendedCommands.ToArray())

## Runtime Notes
- Installer source mode: $SourceMode
- Source decision: $ModeReason
- Workflow directory: `~/.gemini/antigravity/global_workflows`
- Skills directory: `~/.gemini/antigravity/skills`

## Fallback Rule
If NotebookLM MCP is unavailable:
- ingest creates draft or pending-grounding artifacts only
- query falls back to wiki-first answers plus gap logging
- lint reports reduced grounding capability honestly
"@

    if (-not (Test-Path $GeminiMd)) {
        Set-Content -Path $GeminiMd -Value $abwInstructions -Encoding UTF8
        return
    }

    $content = Get-Content $GeminiMd -Raw -ErrorAction SilentlyContinue
    if ($null -eq $content) {
        $content = ""
    }

    $marker = "# Hybrid ABW - Antigravity IDE Command Surface"
    $markerIndex = $content.IndexOf($marker)
    if ($markerIndex -ge 0) {
        $content = $content.Substring(0, $markerIndex).TrimEnd()
    }

    if ($content.Length -gt 0) {
        $content = $content + "`n`n" + $abwInstructions
    }
    else {
        $content = $abwInstructions
    }

    Set-Content -Path $GeminiMd -Value $content -Encoding UTF8
}

$RepoRoot = Get-LocalRepoRoot
$ModeInfo = Resolve-InstallMode -RepoRoot $RepoRoot
$InstallMode = $ModeInfo.Mode
$ModeReason = $ModeInfo.Reason
$RemoteVersion = Get-RemoteVersion

$null = New-Item -ItemType Directory -Force -Path $GlobalDir, $SchemasDir, $TemplatesDir, $SkillsDir, $ScriptsDir, "$env:USERPROFILE\.gemini"

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "Hybrid ABW Installer v$RemoteVersion" -ForegroundColor Cyan
Write-Host "Source mode: $InstallMode" -ForegroundColor Yellow
Write-Host "Reason: $ModeReason" -ForegroundColor DarkGray
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

try {
    $treePaths = if ($InstallMode -eq "LOCAL") { Get-LocalTreePaths -RepoRoot $RepoRoot } else { Get-RemoteTreePaths }
    $Catalog = New-RepoCatalog -Paths $treePaths
}
catch {
    Write-Host "Failed to discover repository contents for installation: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

if (-not $Catalog.WorkflowPaths -or -not $Catalog.SkillPaths) {
    Write-Host "Installer discovery failed: workflows or skills catalog is empty." -ForegroundColor Red
    exit 1
}

$success = 0
$missing = 0

Write-Host "Installing ABW workflows..." -ForegroundColor Cyan
foreach ($relativePath in $Catalog.WorkflowPaths) {
    $leaf = Split-Path -Leaf $relativePath
    try {
        $source = Install-File -RelativePath $relativePath -Destination (Join-Path $GlobalDir $leaf) -SourceMode $InstallMode -RepoRoot $RepoRoot
        Write-Host "  [OK] $leaf ($source)" -ForegroundColor Green
        $success++
    }
    catch {
        Write-Host "  [X] FAILED: $leaf" -ForegroundColor Red
        $missing++
    }
}

Write-Host "Installing schemas..." -ForegroundColor Cyan
foreach ($relativePath in $Catalog.SchemaPaths) {
    $leaf = Split-Path -Leaf $relativePath
    try {
        $source = Install-File -RelativePath $relativePath -Destination (Join-Path $SchemasDir $leaf) -SourceMode $InstallMode -RepoRoot $RepoRoot
        Write-Host "  [OK] $leaf ($source)" -ForegroundColor Green
        $success++
    }
    catch {
        Write-Host "  [X] FAILED: $leaf" -ForegroundColor Red
        $missing++
    }
}

Write-Host "Installing templates..." -ForegroundColor Cyan
foreach ($relativePath in $Catalog.TemplatePaths) {
    $leaf = Split-Path -Leaf $relativePath
    try {
        $source = Install-File -RelativePath $relativePath -Destination (Join-Path $TemplatesDir $leaf) -SourceMode $InstallMode -RepoRoot $RepoRoot
        Write-Host "  [OK] $leaf ($source)" -ForegroundColor Green
        $success++
    }
    catch {
        Write-Host "  [X] FAILED: $leaf" -ForegroundColor Red
        $missing++
    }
}

Write-Host "Installing ABW skills..." -ForegroundColor Cyan
foreach ($relativePath in $Catalog.SkillPaths) {
    $leaf = Split-Path -Leaf $relativePath
    try {
        $source = Install-File -RelativePath $relativePath -Destination (Join-Path $SkillsDir $leaf) -SourceMode $InstallMode -RepoRoot $RepoRoot
        Write-Host "  [OK] $leaf ($source)" -ForegroundColor Green
        $success++
    }
    catch {
        Write-Host "  [X] FAILED: $leaf" -ForegroundColor Red
        $missing++
    }
}

Write-Host "Installing compatibility helper skills..." -ForegroundColor Cyan
foreach ($skill in $Catalog.HelperSkills) {
    $skillDir = Join-Path $SkillsDir $skill
    $null = New-Item -ItemType Directory -Force -Path $skillDir
    try {
        $source = Install-File -RelativePath "awf_skills/$skill/SKILL.md" -Destination (Join-Path $skillDir "SKILL.md") -SourceMode $InstallMode -RepoRoot $RepoRoot
        Write-Host "  [OK] $skill ($source)" -ForegroundColor Green
        $success++
    }
    catch {
        Write-Host "  [X] FAILED: $skill" -ForegroundColor Red
        $missing++
    }
}

Write-Host "Installing runtime scripts..." -ForegroundColor Cyan
foreach ($relativePath in $Catalog.ScriptPaths) {
    $leaf = Split-Path -Leaf $relativePath
    try {
        $source = Install-File -RelativePath $relativePath -Destination (Join-Path $ScriptsDir $leaf) -SourceMode $InstallMode -RepoRoot $RepoRoot
        Write-Host "  [OK] $leaf ($source)" -ForegroundColor Green
        $success++
    }
    catch {
        Write-Host "  [X] FAILED: $leaf" -ForegroundColor Red
        $missing++
    }
}

if ($missing -gt 0) {
    Write-Host "`nInstallation failed while copying $missing components." -ForegroundColor Red
    exit 1
}

Set-Content -Path $AbwVersionFile -Value $RemoteVersion -Encoding UTF8

$installState = @{
    installed_at = (Get-Date).ToString("o")
    installer_source_mode = $InstallMode
    installer_reason = $ModeReason
    repo = "$RepoOwner/$RepoName"
    repo_ref = $RepoRef
    version = $RemoteVersion
    workflow_count = $Catalog.WorkflowPaths.Count
    skill_count = $Catalog.SkillPaths.Count
    schema_count = $Catalog.SchemaPaths.Count
    template_count = $Catalog.TemplatePaths.Count
    script_count = $Catalog.ScriptPaths.Count
    helper_skill_count = $Catalog.HelperSkills.Count
}
$installState | ConvertTo-Json | Set-Content -Path $AbwInstallStateFile -Encoding UTF8

Write-GeminiRegistration -Catalog $Catalog -SourceMode $InstallMode -ModeReason $ModeReason

Write-Host "`nVerifying installation..." -ForegroundColor Cyan
$verificationErrors = 0

foreach ($relativePath in $Catalog.WorkflowPaths) {
    if (-not (Test-Path (Join-Path $GlobalDir (Split-Path -Leaf $relativePath)))) {
        Write-Host "  [!] Missing workflow: $(Split-Path -Leaf $relativePath)" -ForegroundColor Red
        $verificationErrors++
    }
}

foreach ($relativePath in $Catalog.SkillPaths) {
    if (-not (Test-Path (Join-Path $SkillsDir (Split-Path -Leaf $relativePath)))) {
        Write-Host "  [!] Missing skill: $(Split-Path -Leaf $relativePath)" -ForegroundColor Red
        $verificationErrors++
    }
}

foreach ($relativePath in $Catalog.SchemaPaths) {
    if (-not (Test-Path (Join-Path $SchemasDir (Split-Path -Leaf $relativePath)))) {
        Write-Host "  [!] Missing schema: $(Split-Path -Leaf $relativePath)" -ForegroundColor Red
        $verificationErrors++
    }
}

foreach ($relativePath in $Catalog.TemplatePaths) {
    if (-not (Test-Path (Join-Path $TemplatesDir (Split-Path -Leaf $relativePath)))) {
        Write-Host "  [!] Missing template: $(Split-Path -Leaf $relativePath)" -ForegroundColor Red
        $verificationErrors++
    }
}

foreach ($relativePath in $Catalog.ScriptPaths) {
    if (-not (Test-Path (Join-Path $ScriptsDir (Split-Path -Leaf $relativePath)))) {
        Write-Host "  [!] Missing script: $(Split-Path -Leaf $relativePath)" -ForegroundColor Red
        $verificationErrors++
    }
}

foreach ($skill in $Catalog.HelperSkills) {
    if (-not (Test-Path (Join-Path (Join-Path $SkillsDir $skill) "SKILL.md"))) {
        Write-Host "  [!] Missing helper skill: $skill" -ForegroundColor Red
        $verificationErrors++
    }
}

$geminiContent = Get-Content $GeminiMd -Raw -ErrorAction SilentlyContinue
if (($null -eq $geminiContent) -or ($geminiContent.IndexOf("# Hybrid ABW - Antigravity IDE Command Surface") -lt 0)) {
    Write-Host "  [!] GEMINI.md missing ABW block." -ForegroundColor Red
    $verificationErrors++
}

if ($verificationErrors -gt 0) {
    Write-Host "`nInstallation failed verification. Missing $verificationErrors required components." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Installed $success files." -ForegroundColor Yellow
Write-Host "ABW version file: $AbwVersionFile" -ForegroundColor DarkGray
Write-Host "ABW install state: $AbwInstallStateFile" -ForegroundColor DarkGray
Write-Host "Workflows: $GlobalDir" -ForegroundColor DarkGray
Write-Host "Skills: $SkillsDir" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Reload Gemini or your IDE slash-command surface if it still shows stale commands." -ForegroundColor White
Write-Host "  2. Run /help or /abw to confirm the command list refreshed." -ForegroundColor White
Write-Host "  3. Use /abw-learn or /audit to validate the newly installed workflows." -ForegroundColor White
Write-Host ""
