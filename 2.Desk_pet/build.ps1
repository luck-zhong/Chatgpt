param(
    [switch]$InstallPyInstaller
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (-not (Test-Path -LiteralPath ".\photo")) {
    throw "Cannot find .\photo. Keep the action PNG strips next to desktop_pet.py."
}

$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& python -m PyInstaller --version *> $null
$pyInstallerExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorActionPreference

if ($pyInstallerExitCode -ne 0) {
    if ($InstallPyInstaller) {
        python -m pip install pyinstaller
    } else {
        throw "PyInstaller is not installed. Run .\build.ps1 -InstallPyInstaller or install it with: python -m pip install pyinstaller"
    }
}

python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name DeskPet `
    --add-data "codex-pet;codex-pet" `
    desktop_pet.py

Write-Host "Built dist\DeskPet\DeskPet.exe"
