# Install the orchestrate skill, agents and Cursor rules into your user profile (Windows).
# Works with Windows PowerShell 5.1 and PowerShell 7+.
# Default: copy (symlinks need Developer Mode or an admin shell). Use -Link to symlink instead.
#
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 [-Link] [-NoCursor] [-WithClaudeMd] [-DryRun]

[CmdletBinding()]
param(
    [switch]$Link,
    [switch]$NoCursor,
    [switch]$WithClaudeMd,
    [switch]$DryRun,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Write-Host @'
Usage: .\install.ps1 [-Link] [-NoCursor] [-WithClaudeMd] [-DryRun]

  -Link          symlink instead of copy (needs Developer Mode or an admin shell; falls back to copy)
  -NoCursor      skip the Cursor rule and agents (~\.cursor)
  -WithClaudeMd  append the "Orchestrate big tasks" rule to ~\.claude\CLAUDE.md
  -DryRun        print what would happen, change nothing

Existing files are backed up as <file>.bak-<timestamp> before being replaced.
'@
    exit 0
}

$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$HomeDir = if ($env:USERPROFILE) { $env:USERPROFILE } else { $HOME }
$ClaudeDir = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $HomeDir '.claude' }
$CursorDir = Join-Path $HomeDir '.cursor'
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false

function Get-LinkTarget([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    if ($item -and $item.LinkType -eq 'SymbolicLink') { return @($item.Target)[0] }
    return $null
}

function Install-File([string]$Src, [string]$Dst) {
    $dir = Split-Path -Parent $Dst
    if (-not (Test-Path -LiteralPath $dir)) {
        if ($DryRun) { Write-Host "  [dry-run] create $dir" } else { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    }

    $exists = Test-Path -LiteralPath $Dst
    $target = Get-LinkTarget $Dst
    if ($Link -and $target -eq $Src) {
        Write-Host "  ok       $Dst (already linked)"
        return
    }
    if (-not $Link -and $exists -and -not $target) {
        if ((Get-FileHash -LiteralPath $Src).Hash -eq (Get-FileHash -LiteralPath $Dst).Hash) {
            Write-Host "  ok       $Dst (already up to date)"
            return
        }
    }

    if ($exists -or $target) {
        $backup = "$Dst.bak-$Stamp"
        if ($DryRun) { Write-Host "  [dry-run] move $Dst -> $backup" } else { Move-Item -LiteralPath $Dst -Destination $backup }
        Write-Host "  backup   $backup"
    }

    if ($DryRun) {
        $verb = if ($Link) { 'link' } else { 'copy' }
        Write-Host "  [dry-run] $verb $Src -> $Dst"
        return
    }

    if ($Link) {
        try {
            New-Item -ItemType SymbolicLink -Path $Dst -Target $Src | Out-Null
            Write-Host "  link     $Dst"
            return
        } catch {
            Write-Host "  note     symlink not allowed here (enable Developer Mode or use an admin shell); copying instead"
        }
    }
    Copy-Item -LiteralPath $Src -Destination $Dst
    Write-Host "  copy     $Dst"
}

Write-Host "Claude Code ($ClaudeDir)"
Install-File (Join-Path $Repo 'claude\skills\orchestrate\SKILL.md') (Join-Path $ClaudeDir 'skills\orchestrate\SKILL.md')
foreach ($agent in @('explorer', 'implementer', 'verifier')) {
    Install-File (Join-Path $Repo "claude\agents\$agent.md") (Join-Path $ClaudeDir "agents\$agent.md")
}

if ($WithClaudeMd) {
    $claudeMd = Join-Path $ClaudeDir 'CLAUDE.md'
    $hasRule = (Test-Path -LiteralPath $claudeMd) -and (Select-String -LiteralPath $claudeMd -Pattern '^## Orchestrate big tasks' -Quiet)
    if ($hasRule) {
        Write-Host "  ok       $claudeMd already has the rule"
    } elseif ($DryRun) {
        Write-Host "  [dry-run] append claude\CLAUDE.snippet.md to $claudeMd"
    } else {
        $snippet = [System.IO.File]::ReadAllText((Join-Path $Repo 'claude\CLAUDE.snippet.md'), $Utf8NoBom)
        if ((Test-Path -LiteralPath $claudeMd) -and (Get-Item -LiteralPath $claudeMd).Length -gt 0) { $snippet = [Environment]::NewLine + $snippet }
        [System.IO.File]::AppendAllText($claudeMd, $snippet, $Utf8NoBom)
        Write-Host "  append   $claudeMd"
    }
}

if ($NoCursor -or -not (Test-Path -LiteralPath $CursorDir)) {
    Write-Host 'Cursor: skipped'
} else {
    Write-Host "Cursor ($CursorDir)"
    Install-File (Join-Path $Repo 'cursor\rules\orchestrate.mdc') (Join-Path $CursorDir 'rules\orchestrate.mdc')
    foreach ($agent in @('explorer', 'verifier')) {
        Install-File (Join-Path $Repo "cursor\agents\$agent.md") (Join-Path $CursorDir "agents\$agent.md")
    }
}

Write-Host ''
Write-Host 'Done. Next steps:'
Write-Host '  1. Restart Claude Code / Cursor so they pick up the new skill and agents.'
Write-Host '  2. Optional: copy examples\project-skills\* into <your-project>\.claude\skills\ and adapt them.'
if (-not $WithClaudeMd) {
    Write-Host '  3. Optional: rerun with -WithClaudeMd so big tasks trigger orchestration automatically.'
}
