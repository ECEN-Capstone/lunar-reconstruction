$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
$linuxPath = (& wsl -d Ubuntu -- wslpath -a -u "$repoPath").Trim()
if ($LASTEXITCODE -ne 0) { throw 'Unable to locate this repository in Ubuntu.' }
Write-Host 'Lunar labeler: http://localhost:7860 (Ctrl+C to stop)'
& wsl -d Ubuntu --cd "$linuxPath" -- /home/alejo/.venvs/lunar-sam2/bin/python -m reconstruction.annotate @args
