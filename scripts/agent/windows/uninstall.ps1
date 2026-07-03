param(
    [switch]$Silent
)

$ErrorActionPreference = "Stop"

function Test-Is64BitOperatingSystem {
    try {
        return [Environment]::Is64BitOperatingSystem
    } catch {
        return ($env:PROCESSOR_ARCHITECTURE -eq "AMD64" -or $env:PROCESSOR_ARCHITEW6432 -eq "AMD64")
    }
}

function Show-Message {
    param([string]$Message, [string]$Title = "Sistema Chamados Agent")
    if ($Silent) { return }
    try {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show($Message, $Title, [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null
    } catch {
        Write-Host $Message
    }
}

$installDir = Join-Path $env:ProgramData "SistemaChamadosAgent"
$programsDir = Join-Path $env:ProgramData "Microsoft\Windows\Start Menu\Programs"
$menuDir = Join-Path $programsDir "Sistema Chamados Agent"
$userProgramsDir = [Environment]::GetFolderPath("Programs")
$userMenuDir = if ($userProgramsDir) { Join-Path $userProgramsDir "Sistema Chamados Agent" } else { "" }
$startupDir = Join-Path $env:ProgramData "Microsoft\Windows\Start Menu\Programs\Startup"
$startupShortcut = if ($startupDir) { Join-Path $startupDir "Sistema Chamados Agent.lnk" } else { "" }
$uninstallKeys = @("HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\SistemaChamadosAgent")
if (Test-Is64BitOperatingSystem) {
    $uninstallKeys += "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\SistemaChamadosAgent"
}

foreach ($taskName in @("SistemaChamadosAgentStartup", "SistemaChamadosAgentInterval", "SistemaChamadosAgentSolicitacoes", "SistemaChamadosAgent")) {
    & schtasks.exe /Delete /TN $taskName /F 2>$null | Out-Null
}

Stop-Process -Name "SistemaChamadosAgentTray" -Force -ErrorAction SilentlyContinue

foreach ($uninstallKey in $uninstallKeys) {
    if (Test-Path $uninstallKey) {
        Remove-Item -Path $uninstallKey -Recurse -Force
    }
}

if (Test-Path $menuDir) {
    Remove-Item -Path $menuDir -Recurse -Force
}

if ($userMenuDir -and (Test-Path $userMenuDir)) {
    Remove-Item -Path $userMenuDir -Recurse -Force
}

if ($startupShortcut -and (Test-Path $startupShortcut)) {
    Remove-Item -LiteralPath $startupShortcut -Force
}

if (Test-Path $installDir) {
    Remove-Item -Path $installDir -Recurse -Force
}

Show-Message "Agente de inventario removido com sucesso."
