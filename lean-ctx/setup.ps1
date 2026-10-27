# Wire lean-ctx into Claude Code (and Cursor) with the hardened shell policy used by this repo (Windows).
# Works with Windows PowerShell 5.1 and PowerShell 7+. Requires lean-ctx on PATH: see lean-ctx\README.md.
#
#   powershell -ExecutionPolicy Bypass -File .\lean-ctx\setup.ps1 [-Privacy] [-DryRun]

# Interactive setup: console status lines, so Write-Host is intended.
[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSAvoidUsingWriteHost', '')]
[CmdletBinding()]
param(
    [switch]$Privacy,
    [switch]$DryRun,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
    Write-Host @'
Usage: .\lean-ctx\setup.ps1 [-Privacy] [-DryRun]

  -Privacy   also turn lean-ctx telemetry off and limit file access to project folders
  -DryRun    print what would happen, change nothing

Steps: lean-ctx wrap claude (and cursor if ~\.cursor exists), shell_hook_mode=deny,
merge lean-ctx\claude-permissions.json into your Claude Code settings.json (backed up first).
'@
    exit 0
}

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$HomeDir = if ($env:USERPROFILE) { $env:USERPROFILE } else { $HOME }
$ClaudeDir = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $HomeDir '.claude' }
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false

function Invoke-Step([string[]]$Cmd) {
    Write-Host ("  > " + ($Cmd -join ' '))
    if (-not $DryRun) {
        & $Cmd[0] $Cmd[1..($Cmd.Length - 1)]
        if ($LASTEXITCODE -ne 0) { throw "Command failed: $($Cmd -join ' ')" }
    }
}

function Add-Unique($List, [string[]]$Items, [string]$Key, $Changes) {
    foreach ($item in $Items) {
        if ($List -notcontains $item) { $List.Add($item) | Out-Null; $Changes.Add("+ ${Key}: $item") | Out-Null }
    }
}

if (-not (Get-Command lean-ctx -ErrorAction SilentlyContinue)) {
    Write-Host 'lean-ctx is not installed. On Windows, use WSL or build it with cargo (see lean-ctx\README.md).'
    exit 1
}

Write-Host ('lean-ctx: ' + (& lean-ctx --version | Select-Object -First 1))
Write-Host 'Connect agents'
Invoke-Step @('lean-ctx', 'wrap', 'claude')
if (Test-Path -LiteralPath (Join-Path $HomeDir '.cursor')) { Invoke-Step @('lean-ctx', 'wrap', 'cursor') }

Write-Host 'Shell policy: every command goes through ctx_shell and its allowlist'
Invoke-Step @('lean-ctx', 'config', 'set', 'shell_hook_mode', 'deny')

if ($Privacy) {
    Write-Host 'Privacy'
    Invoke-Step @('lean-ctx', 'telemetry', 'off')
    Invoke-Step @('lean-ctx', 'config', 'set', 'path_jail_scope', 'projects')
}

$settingsPath = Join-Path $ClaudeDir 'settings.json'
Write-Host "Claude Code permissions ($settingsPath)"
$wanted = ([System.IO.File]::ReadAllText((Join-Path $Here 'claude-permissions.json'), $Utf8NoBom) | ConvertFrom-Json).permissions

$settings = New-Object PSObject
if (Test-Path -LiteralPath $settingsPath) {
    $raw = [System.IO.File]::ReadAllText($settingsPath, $Utf8NoBom)
    if ($raw.Trim()) { $settings = $raw | ConvertFrom-Json }
}
if (-not $settings.PSObject.Properties['permissions']) { $settings | Add-Member -NotePropertyName permissions -NotePropertyValue (New-Object PSObject) }
$perms = $settings.permissions

$changes = New-Object System.Collections.ArrayList
$lists = @{}
foreach ($key in @('allow', 'ask', 'deny')) {
    $list = New-Object System.Collections.ArrayList
    if ($perms.PSObject.Properties[$key]) { foreach ($e in @($perms.$key)) { $list.Add([string]$e) | Out-Null } }
    if ($wanted.PSObject.Properties[$key]) { Add-Unique $list @($wanted.$key) $key $changes }
    $lists[$key] = $list
}
foreach ($e in @($wanted.ask)) {
    if ($lists['allow'] -contains $e) { $lists['allow'].Remove($e); $changes.Add("- allow: $e (now ask)") | Out-Null }
}

if ($changes.Count -eq 0) {
    Write-Host "  ok       $settingsPath already has the lean-ctx permissions"
} else {
    foreach ($c in $changes) { Write-Host "  $c" }
    if ($DryRun) {
        Write-Host "  [dry-run] would update $settingsPath"
    } else {
        foreach ($key in @('allow', 'ask', 'deny')) {
            $value = [object[]]$lists[$key].ToArray()
            if ($perms.PSObject.Properties[$key]) { $perms.$key = $value } else { $perms | Add-Member -NotePropertyName $key -NotePropertyValue $value }
        }
        if (-not (Test-Path -LiteralPath $ClaudeDir)) { New-Item -ItemType Directory -Path $ClaudeDir -Force | Out-Null }
        if (Test-Path -LiteralPath $settingsPath) {
            $backup = "$settingsPath.bak-" + (Get-Date -Format 'yyyyMMdd-HHmmss')
            Copy-Item -LiteralPath $settingsPath -Destination $backup
            Write-Host "  backup   $backup"
        }
        [System.IO.File]::WriteAllText($settingsPath, ($settings | ConvertTo-Json -Depth 32) + "`n", $Utf8NoBom)
        Write-Host "  updated  $settingsPath"
    }
}

$config = (& lean-ctx config path 2>$null | Select-Object -First 1)
if ($config -and (Test-Path -LiteralPath $config) -and (Select-String -LiteralPath $config -Pattern '"sudo"' -Quiet)) {
    Write-Host "Warning: 'sudo' is in your lean-ctx allowlist ($config). Remove it from shell_allowlist_extra."
}

Write-Host ''
Write-Host 'Done. Next steps:'
Write-Host '  1. Restart Claude Code / Cursor so the MCP server and hooks reload.'
Write-Host '  2. Run `lean-ctx doctor` and fix anything it flags.'
Write-Host '  3. Allow the build and test commands your projects need, one by one: `lean-ctx allow <cmd>`.'
