# Hybrid ABW Installer for Windows (PowerShell)

$ErrorActionPreference = "Stop"

$RepoOwner = "Nakazasen"
$RepoName = "skill-Anti-brain-wiki_note"

if ($env:ABW_REPO_REF) {
    $RepoRef = $env:ABW_REPO_REF
}
elseif (Get-Command git -ErrorAction SilentlyContinue) {
    $RepoRef = ((git rev-parse --abbrev-ref HEAD 2>$null) | Select-Object -First 1)
    if (-not $RepoRef) {
        $RepoRef = "main"
    }
}
else {
    $RepoRef = "main"
}

$RepoBase = "https://raw.githubusercontent.com/$RepoOwner/$RepoName/$RepoRef"
$RepoApiBase = "https://api.github.com/repos/$RepoOwner/$RepoName"

$AntigravityDir = Join-Path $env:USERPROFILE ".gemini\antigravity"
$GlobalDir = Join-Path $AntigravityDir "global_workflows"
$SchemasDir = Join-Path $AntigravityDir "schemas"
$TemplatesDir = Join-Path $AntigravityDir "templates"
$SkillsDir = Join-Path $AntigravityDir "skills"
$ScriptsDir = Join-Path $AntigravityDir "scripts"
$McpConfigPath = Join-Path $AntigravityDir "mcp_config.json"
$GeminiMd = Join-Path $env:USERPROFILE ".gemini\GEMINI.md"
$AbwVersionFile = Join-Path $env:USERPROFILE ".gemini\abw_version"
$AbwInstallStateFile = Join-Path $env:USERPROFILE ".gemini\abw_install_state.json"

$RequiredRuntimeScripts = @(
    "abw_accept.py",
    "abw_runner.py",
    "finalization_check.py",
    "continuation_gate.py",
    "continuation_execute.py"
)

$RequiredRuntimeWorkflows = @(
    "abw-ask.md",
    "abw-update.md",
    "finalization.md"
)

$SourceErrors = [System.Collections.Generic.List[string]]::new()
$RuntimeErrors = [System.Collections.Generic.List[string]]::new()
$McpErrors = [System.Collections.Generic.List[string]]::new()
$VerifyErrors = [System.Collections.Generic.List[string]]::new()
$VerificationLimitations = [System.Collections.Generic.List[string]]::new()

$SourceSyncResult = "FAIL"
$RuntimeSyncResult = "FAIL"
$McpSyncResult = "FAIL"
$VerificationResult = "FAIL"
$FinalVerdict = "FAIL"
$GeminiRefreshed = $false
$PythonCommand = $null
$PythonCommandForReport = $null

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
    $remoteRef = "origin/$RepoRef"

    if ($forced) {
        $normalized = $forced.Trim().ToLowerInvariant()
        if ($normalized -eq "local") {
            return @{ Mode = "LOCAL"; Reason = "ABW_INSTALL_SOURCE=local"; RemoteRef = $remoteRef }
        }
        if ($normalized -eq "remote") {
            return @{ Mode = "REMOTE"; Reason = "ABW_INSTALL_SOURCE=remote"; RemoteRef = $remoteRef }
        }
    }

    if (-not $RepoRoot) {
        return @{ Mode = "REMOTE"; Reason = "No local repository clone detected"; RemoteRef = $remoteRef }
    }

    $git = Get-GitCommand
    if (-not $git) {
        return @{ Mode = "REMOTE"; Reason = "git is unavailable; remote is the only trustworthy latest source"; RemoteRef = $remoteRef }
    }

    if (-not (& $git.Source -C $RepoRoot rev-parse --is-inside-work-tree 2>$null)) {
        return @{ Mode = "REMOTE"; Reason = "Local path is not a git worktree; remote is the only trustworthy latest source"; RemoteRef = $remoteRef }
    }

    try {
        $tracked = ((& $git.Source -C $RepoRoot rev-parse --abbrev-ref --symbolic-full-name "@{upstream}" 2>$null) | Select-Object -First 1).Trim()
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

    $head = ((& $git.Source -C $RepoRoot rev-parse HEAD 2>$null) | Select-Object -First 1).Trim()
    $remoteHead = ((& $git.Source -C $RepoRoot rev-parse $remoteRef 2>$null) | Select-Object -First 1).Trim()
    $status = & $git.Source -C $RepoRoot status --porcelain 2>$null

    if ($head -and $remoteHead -and $head -eq $remoteHead -and -not $status) {
        return @{ Mode = "LOCAL"; Reason = "Local clone is clean and already at $remoteRef"; RemoteRef = $remoteRef }
    }

    if ($status) {
        return @{ Mode = "REMOTE"; Reason = "Local clone has uncommitted changes; installing the verified remote snapshot"; RemoteRef = $remoteRef }
    }

    return @{ Mode = "REMOTE"; Reason = "Local clone does not match $remoteRef; installing the verified remote snapshot"; RemoteRef = $remoteRef }
}

function Get-LocalTreePaths {
    param(
        [string]$RepoRoot
    )

    $paths = New-Object System.Collections.Generic.List[string]
    foreach ($dir in @("workflows", "skills", "schemas", "templates", "scripts")) {
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

    $publicCommands = @("/abw-ask", "/help")
    $powerCommands = @("/abw-health", "/abw-update", "/abw-rollback", "/abw-repair")
    $legacyAliases = @("/abw-ingest", "/abw-review", "/abw-query", "/abw-query-deep")
    $devSurface = $env:ABW_INSTALL_DEV_SURFACE -eq "1"
    $allCommands = New-Object System.Collections.Generic.List[string]

    foreach ($workflowPath in $Catalog.WorkflowPaths) {
        $command = Convert-WorkflowPathToCommand -RelativePath $workflowPath
        if (-not $command) {
            continue
        }
        $allCommands.Add($command)
    }

    $registeredPublic = if ($devSurface) { $allCommands.ToArray() } else { $publicCommands + $powerCommands }

    $abwInstructions = @"
# Hybrid ABW - Antigravity IDE Command Surface

## CRITICAL: Command Recognition
When the user types one of the registered commands below, treat it as a Hybrid ABW workflow command loaded from `~/.gemini/antigravity/global_workflows`.
Do not silently fall back to a stale local clone when the verified remote snapshot is newer.
Hybrid ABW commands are authoritative. In particular, /help MUST load ~/.gemini/antigravity/global_workflows/help.md and should not be answered from memory or a short summary.

## Public Commands
$(Join-Commands -Commands $registeredPublic)

## Legacy Compatibility Aliases
$(Join-Commands -Commands $legacyAliases)

## Hidden By Default
- Internal workflows remain installed on disk but are not part of the default public surface.
- Set `ABW_INSTALL_DEV_SURFACE=1` before install if you intentionally want the full workflow list exposed for development.

## Runtime Notes
- Installer source mode: $SourceMode
- Source decision: $ModeReason
- Workflow directory: `~/.gemini/antigravity/global_workflows`
- Skills directory: `~/.gemini/antigravity/skills`
- MCP config: `~/.gemini/antigravity/mcp_config.json`
- /abw-update must distinguish repo, workspace, runtime, and MCP sync state separately.

## Fallback Rule
If NotebookLM MCP is unavailable:
- ingest creates draft or pending-grounding artifacts only
- query falls back to wiki-first answers plus gap logging
- lint reports reduced grounding capability honestly
"@

    if (-not (Test-Path $GeminiMd)) {
        Set-Content -Path $GeminiMd -Value $abwInstructions -Encoding UTF8
        $script:GeminiRefreshed = $true
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

    $legacyAwfMarker = "# AWF - Antigravity Workflow Framework"
    if ($content.TrimStart().StartsWith($legacyAwfMarker)) {
        $content = ""
    }

    if ($content.Length -gt 0) {
        $content = $content + "`n`n" + $abwInstructions
    }
    else {
        $content = $abwInstructions
    }

    Set-Content -Path $GeminiMd -Value $content -Encoding UTF8
    $script:GeminiRefreshed = $true
}

function Remove-LegacyAwfSkills {
    $legacySkills = @(
        "awf-adaptive-language",
        "awf-auto-save",
        "awf-context-help",
        "awf-error-translator",
        "awf-onboarding",
        "awf-session-restore"
    )

    foreach ($skill in $legacySkills) {
        $path = Join-Path $SkillsDir $skill
        if (Test-Path $path) {
            Remove-Item -LiteralPath $path -Recurse -Force
            Write-Host "  [OK] Removed legacy skill: $skill" -ForegroundColor Green
        }
    }
}

function Resolve-PythonCommand {
    foreach ($candidate in @("py", "python", "python3")) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($cmd) {
            return $cmd.Source
        }
    }
    return $null
}

function Patch-McpConfig {
    param(
        [string]$PythonExe
    )

    $runnerPath = Join-Path $ScriptsDir "abw_runner.py"
    if (-not $PythonExe) {
        $McpErrors.Add("python executable could not be resolved for MCP registration")
        return $false
    }
    if (-not (Test-Path $runnerPath)) {
        $McpErrors.Add("runtime runner script missing at $runnerPath")
        return $false
    }

    $configDir = Split-Path -Parent $McpConfigPath
    $null = New-Item -ItemType Directory -Force -Path $configDir

    $pythonCode = @'
import json
import os
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
command = os.path.abspath(sys.argv[2])
runner_path = os.path.abspath(sys.argv[3])

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
    "command": command,
    "args": [runner_path],
}
data["mcpServers"] = mcp_servers

config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

verified = json.loads(config_path.read_text(encoding="utf-8"))
entry = verified["mcpServers"]["abw_runner"]
if not os.path.isabs(entry["command"]):
    raise SystemExit("abw_runner command must be absolute")
if not entry.get("args") or not os.path.isabs(entry["args"][0]):
    raise SystemExit("abw_runner args[0] must be absolute")
'@

    try {
        $tempScript = Join-Path $env:TEMP ("abw_patch_mcp_" + [guid]::NewGuid().ToString() + ".py")
        Set-Content -Path $tempScript -Value $pythonCode -Encoding UTF8
        & $PythonExe $tempScript $McpConfigPath $PythonExe $runnerPath | Out-Null
        Remove-Item -LiteralPath $tempScript -Force -ErrorAction SilentlyContinue
        return $true
    }
    catch {
        $McpErrors.Add("failed to patch MCP config: $($_.Exception.Message)")
        return $false
    }
}

function Verify-McpConfig {
    param(
        [string]$PythonExe
    )

    if (-not (Test-Path $McpConfigPath)) {
        $VerifyErrors.Add("missing MCP config: $McpConfigPath")
        return
    }

    if (-not $PythonExe) {
        $VerifyErrors.Add("verification limitation: MCP JSON verification could not run because python was unavailable")
        $VerificationLimitations.Add("MCP JSON verification skipped because no python executable was available on this host")
        return
    }

    $runnerPath = Join-Path $ScriptsDir "abw_runner.py"
    $pythonCode = @'
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
'@

    try {
        $tempScript = Join-Path $env:TEMP ("abw_verify_mcp_" + [guid]::NewGuid().ToString() + ".py")
        Set-Content -Path $tempScript -Value $pythonCode -Encoding UTF8
        & $PythonExe $tempScript $McpConfigPath $runnerPath | Out-Null
        Remove-Item -LiteralPath $tempScript -Force -ErrorAction SilentlyContinue
    }
    catch {
        $VerifyErrors.Add("MCP config does not contain a valid abw_runner entry bound to the installed runtime")
    }
}

function Verify-RuntimeArtifacts {
    param(
        [string]$PythonExe
    )

    foreach ($scriptName in $RequiredRuntimeScripts) {
        $path = Join-Path $ScriptsDir $scriptName
        if (-not (Test-Path $path)) {
            $VerifyErrors.Add("missing required runtime script: $path")
        }
    }

    foreach ($workflowName in $RequiredRuntimeWorkflows) {
        $path = Join-Path $GlobalDir $workflowName
        if (-not (Test-Path $path)) {
            $VerifyErrors.Add("missing required runtime workflow: $path")
        }
    }

    if (-not (Test-Path (Join-Path $ScriptsDir "finalization_check.py"))) {
        $VerifyErrors.Add("missing finalization_check.py in runtime scripts directory")
    }

    if (-not (Test-Path (Join-Path $GlobalDir "abw-update.md"))) {
        $VerifyErrors.Add("missing abw-update.md in runtime workflow directory")
    }

    $geminiContent = Get-Content $GeminiMd -Raw -ErrorAction SilentlyContinue
    if (($null -eq $geminiContent) -or ($geminiContent.IndexOf("# Hybrid ABW - Antigravity IDE Command Surface") -lt 0)) {
        $VerifyErrors.Add("GEMINI.md missing Hybrid ABW registration block")
    }

    if ($PythonExe) {
        try {
            & $PythonExe -m py_compile `
                (Join-Path $ScriptsDir "abw_runner.py") `
                (Join-Path $ScriptsDir "finalization_check.py") `
                (Join-Path $ScriptsDir "abw_accept.py") `
                (Join-Path $ScriptsDir "continuation_gate.py") `
                (Join-Path $ScriptsDir "continuation_execute.py") | Out-Null
        }
        catch {
            $VerifyErrors.Add("py_compile failed for one or more critical runtime scripts")
        }
    }
    else {
        $VerifyErrors.Add("verification limitation: py_compile could not run because python was unavailable")
        $VerificationLimitations.Add("py_compile skipped because no python executable was available on this host")
    }

    Verify-McpConfig -PythonExe $PythonExe
}

function Get-WorkspaceSyncState {
    param(
        [string]$RepoRoot,
        [string]$RemoteRef
    )

    if (-not $RepoRoot) {
        return "not_present"
    }

    $git = Get-GitCommand
    if (-not $git) {
        return "unverified"
    }

    try {
        $null = & $git.Source -C $RepoRoot rev-parse --is-inside-work-tree 2>$null
    }
    catch {
        return "unverified"
    }

    $status = & $git.Source -C $RepoRoot status --porcelain 2>$null
    if ($status) {
        return "dirty"
    }

    try {
        $ahead = [int](((& $git.Source -C $RepoRoot rev-list --count "${RemoteRef}..HEAD" 2>$null) | Select-Object -First 1).Trim())
        $behind = [int](((& $git.Source -C $RepoRoot rev-list --count "HEAD..${RemoteRef}" 2>$null) | Select-Object -First 1).Trim())
    }
    catch {
        return "unverified"
    }

    if ($ahead -gt 0 -and $behind -gt 0) {
        return "diverged"
    }
    if ($behind -gt 0) {
        return "stale"
    }
    if ($ahead -gt 0) {
        return "ahead"
    }
    return "synced"
}

$RepoRoot = Get-LocalRepoRoot
$ModeInfo = Resolve-InstallMode -RepoRoot $RepoRoot
$InstallMode = $ModeInfo.Mode
$ModeReason = $ModeInfo.Reason
$InstallRemoteRef = $ModeInfo.RemoteRef
$RemoteVersion = Get-RemoteVersion

$null = New-Item -ItemType Directory -Force -Path $GlobalDir, $SchemasDir, $TemplatesDir, $SkillsDir, $ScriptsDir, (Join-Path $env:USERPROFILE ".gemini")

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
    $SourceErrors.Add("failed to discover repository contents: $($_.Exception.Message)")
}

if (-not $Catalog.WorkflowPaths -or -not $Catalog.SkillPaths) {
    $SourceErrors.Add("installer discovery failed: workflows or skills catalog is empty")
}

foreach ($workflowName in $RequiredRuntimeWorkflows) {
    $relativePath = "workflows/$workflowName"
    if ($Catalog.WorkflowPaths -notcontains $relativePath) {
        $SourceErrors.Add("required runtime workflow missing from source catalog: $relativePath")
    }
}

foreach ($scriptName in $RequiredRuntimeScripts) {
    $relativePath = "scripts/$scriptName"
    if ($Catalog.ScriptPaths -notcontains $relativePath) {
        $SourceErrors.Add("required runtime script missing from source catalog: $relativePath")
    }
}

if ($SourceErrors.Count -gt 0) {
    $installState = @{
        installed_at = (Get-Date).ToString("o")
        source_sync_result = "FAIL"
        runtime_sync_result = "FAIL"
        mcp_sync_result = "FAIL"
        verification_result = "FAIL"
        final_verdict = "FAIL"
        repo_state = "reachable"
        workspace_state = (Get-WorkspaceSyncState -RepoRoot $RepoRoot -RemoteRef $InstallRemoteRef)
        runtime_state = "missing"
        source_errors = @($SourceErrors)
    }
    $installState | ConvertTo-Json -Depth 10 | Set-Content -Path $AbwInstallStateFile -Encoding UTF8
    foreach ($item in $SourceErrors) {
        Write-Host "  [!] $item" -ForegroundColor Red
    }
    exit 1
}

$SourceSyncResult = "PASS"
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
        $RuntimeErrors.Add("failed to install workflow: $relativePath")
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
        $RuntimeErrors.Add("failed to install schema: $relativePath")
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
        $RuntimeErrors.Add("failed to install template: $relativePath")
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
        $RuntimeErrors.Add("failed to install skill: $relativePath")
        $missing++
    }
}

Write-Host "Removing legacy AWF helper skills..." -ForegroundColor Cyan
Remove-LegacyAwfSkills

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
        $RuntimeErrors.Add("failed to install script: $relativePath")
        $missing++
    }
}

Write-GeminiRegistration -Catalog $Catalog -SourceMode $InstallMode -ModeReason $ModeReason

$PythonCommand = Resolve-PythonCommand
$PythonCommandForReport = $PythonCommand
if (-not $PythonCommand) {
    $McpErrors.Add("python executable could not be resolved; MCP registration cannot be completed")
}
elseif (-not (Patch-McpConfig -PythonExe $PythonCommand)) {
    $null = $false
}

if ($missing -gt 0 -or $RuntimeErrors.Count -gt 0) {
    $RuntimeSyncResult = "FAIL"
}
else {
    $RuntimeSyncResult = "PASS"
}

if ($McpErrors.Count -gt 0) {
    $McpSyncResult = "FAIL"
}
else {
    $McpSyncResult = "PASS"
}

Set-Content -Path $AbwVersionFile -Value $RemoteVersion -Encoding UTF8

Write-Host "`nVerifying installation..." -ForegroundColor Cyan
Verify-RuntimeArtifacts -PythonExe $PythonCommand

if ($VerifyErrors.Count -gt 0) {
    $VerificationResult = "FAIL"
}
else {
    $VerificationResult = "PASS"
}

$workspaceState = Get-WorkspaceSyncState -RepoRoot $RepoRoot -RemoteRef $InstallRemoteRef
$repoState = "reachable"
$runtimeState = "synced"
if ($RuntimeErrors.Count -gt 0 -or $missing -gt 0) {
    $runtimeState = "missing"
}
if ($VerifyErrors.Count -gt 0) {
    $runtimeState = "stale"
}

if ($SourceSyncResult -eq "FAIL" -or $RuntimeSyncResult -eq "FAIL" -or $McpSyncResult -eq "FAIL" -or $VerificationResult -eq "FAIL") {
    $FinalVerdict = "FAIL"
}
elseif ($workspaceState -in @("stale", "dirty", "diverged")) {
    $FinalVerdict = "PARTIAL"
}
else {
    $FinalVerdict = "PASS"
}

$installState = @{
    installed_at = (Get-Date).ToString("o")
    repo = "$RepoOwner/$RepoName"
    repo_ref = $RepoRef
    version = $RemoteVersion
    installer_source_mode = $InstallMode
    installer_reason = $ModeReason
    source_sync_result = $SourceSyncResult
    runtime_sync_result = $RuntimeSyncResult
    mcp_sync_result = $McpSyncResult
    verification_result = $VerificationResult
    final_verdict = $FinalVerdict
    repo_state = $repoState
    workspace_state = $workspaceState
    runtime_state = $runtimeState
    mcp_config_path = $McpConfigPath
    python_command = $PythonCommandForReport
    required_runtime_scripts = $RequiredRuntimeScripts
    required_runtime_workflows = $RequiredRuntimeWorkflows
    source_errors = @($SourceErrors)
    runtime_errors = @($RuntimeErrors)
    mcp_errors = @($McpErrors)
    verification_errors = @($VerifyErrors)
    verification_limitations = @($VerificationLimitations)
}
$installState | ConvertTo-Json -Depth 10 | Set-Content -Path $AbwInstallStateFile -Encoding UTF8

Write-Host ""
Write-Host "Installed $success files." -ForegroundColor Yellow
Write-Host "ABW version file: $AbwVersionFile" -ForegroundColor DarkGray
Write-Host "ABW install state: $AbwInstallStateFile" -ForegroundColor DarkGray
Write-Host "MCP config: $McpConfigPath" -ForegroundColor DarkGray
Write-Host "Runtime workflows: $GlobalDir" -ForegroundColor DarkGray
Write-Host "Runtime scripts: $ScriptsDir" -ForegroundColor DarkGray
Write-Host ""
Write-Host "source_sync_result=$SourceSyncResult"
Write-Host "runtime_sync_result=$RuntimeSyncResult"
Write-Host "mcp_sync_result=$McpSyncResult"
Write-Host "verification_result=$VerificationResult"
Write-Host "repo_state=$repoState"
Write-Host "workspace_state=$workspaceState"
Write-Host "runtime_state=$runtimeState"
Write-Host "final_verdict=$FinalVerdict"

foreach ($item in $SourceErrors + $RuntimeErrors + $McpErrors + $VerifyErrors + $VerificationLimitations) {
    Write-Host $item
}

if ($FinalVerdict -eq "FAIL") {
    exit 1
}

exit 0
