param(
    [switch]$Silent
)

$ErrorActionPreference = "Stop"

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
$uninstallKeys = @("HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\SistemaChamadosAgent")
if ([Environment]::Is64BitOperatingSystem) {
    $uninstallKeys += "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\SistemaChamadosAgent"
}

foreach ($taskName in @("SistemaChamadosAgentStartup", "SistemaChamadosAgentInterval", "SistemaChamadosAgent")) {
    & schtasks.exe /Delete /TN $taskName /F 2>$null | Out-Null
}

foreach ($uninstallKey in $uninstallKeys) {
    if (Test-Path $uninstallKey) {
        Remove-Item -Path $uninstallKey -Recurse -Force
    }
}

if (Test-Path $installDir) {
    Remove-Item -Path $installDir -Recurse -Force
}

Show-Message "Agente de inventario removido com sucesso."
