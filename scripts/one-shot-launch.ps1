# Final launch remaster: Phase D + UL App Bridge + wine-wolf-bridge
param(
    [switch]$SkipRemaster,
    [switch]$SkipEval,
    [string]$BaseIso = "",
    [string]$Tag = "12.20.0-wolf-os"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Payload = if ($env:COGOS_ROOT) { $env:COGOS_ROOT } else { Join-Path $Root "AI OS Trixie Build\payload\opt\cogos" }
$env:COGOS_ROOT = $Payload
$Py = if ($env:COGOS_PYTHON) { $env:COGOS_PYTHON } else { "E:\project-infi\AAIS-main\.runtime\python312-store-copy\python.exe" }

function ConvertTo-WslPath {
    param([Parameter(Mandatory=$true)][string]$Path)
    $resolved = [System.IO.Path]::GetFullPath($Path)
    if ($resolved -notmatch '^([A-Za-z]):\\(.*)$') {
        throw "Cannot convert non-drive path to WSL path: $resolved"
    }
    $drive = $matches[1].ToLowerInvariant()
    $rest = $matches[2].Replace('\', '/')
    return "/mnt/$drive/$rest"
}

Write-Host "== Wolf CoG OS LAUNCH remaster ($Tag) =="
& $Py (Join-Path $Payload "runtime\mesh_physical_smoke.py")
& $Py (Join-Path $Payload "runtime\ul_app_bridge_smoke.py")
& $Py (Join-Path $Payload "runtime\wine_wolf_bridge_smoke.py")
& $Py (Join-Path $Payload "runtime\win_launcher_smoke.py")

if (-not $SkipEval) {
    & $Py (Join-Path $Payload "bin\cogos_manifest.py") sign (Join-Path $Payload "config\release_manifest.json")
    & $Py (Join-Path $Payload "bin\cogos_ship.py") preflight
    & $Py (Join-Path $Payload "bin\cogos_eval.py") run
}

if (-not $SkipRemaster) {
    if (-not $BaseIso) { $BaseIso = Join-Path $Root "debian-live-13.4.0-amd64-cinnamon.iso" }
    if (-not (Test-Path $BaseIso)) { throw "Base ISO not found: $BaseIso" }
    $env:COGOS_TAG = $Tag
    $OutIso = Join-Path $Root "AI OS Debian Build\output\project-infi-cogos-$Tag.iso"
    $wslPayload = ConvertTo-WslPath $Payload
    $wslIso = ConvertTo-WslPath $BaseIso
    $wslOut = ConvertTo-WslPath $OutIso
    $wslScript = ConvertTo-WslPath (Join-Path $Root "AI OS Debian Build\scripts\build_debian_cogos.sh")
    $work = "/tmp/cogos-build-wolf-os"
    Write-Host "== Remaster $Tag (final) =="
    wsl -e bash -lc "export COGOS_TAG='$Tag'; export COGOS_ROOT='$wslPayload'; export COGOS_OUT='$wslOut'; export COGOS_WORK='$work'; bash '$wslScript' '$wslIso'"
    if (Test-Path $OutIso) {
        certutil -hashfile $OutIso SHA256 | Out-File "$OutIso.sha256" -Encoding ascii
        Write-Host "LAUNCH ISO ready: $OutIso"
    } else {
        Write-Host "WARN: ISO not found at $OutIso"
    }
}

Write-Host "Launch one-shot: complete"
