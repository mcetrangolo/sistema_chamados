param(
    [string]$ServerUrl = "",
    [string]$Token = "sistema-chamados-agent-local",
    [string]$NumeroSerieManual = "",
    [int]$IntervalHours = 6
)

$ErrorActionPreference = "Stop"

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Quote-Arg([string]$value) {
    return '"' + ($value -replace '"', '\"') + '"'
}

function Show-Message {
    param(
        [string]$Message,
        [string]$Title = "Sistema Chamados Agent"
    )
    try {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show(
            $Message,
            $Title,
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Information
        ) | Out-Null
    } catch {
        Write-Host $Message
    }
}

$installScript = Join-Path $PSScriptRoot "install.ps1"
if (-not (Test-Path $installScript)) {
    try {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show(
            "Arquivo install.ps1 nao encontrado junto do instalador.",
            "Sistema Chamados Agent",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        ) | Out-Null
    } catch {
        Write-Host "Arquivo install.ps1 nao encontrado junto do instalador."
    }
    exit 1
}

$argsList = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-WindowStyle", "Hidden",
    "-File", (Quote-Arg $installScript),
    "-Token", (Quote-Arg $Token),
    "-IntervalHours", $IntervalHours
)

if ($ServerUrl) {
    $argsList += @("-ServerUrl", (Quote-Arg $ServerUrl))
}
if ($NumeroSerieManual) {
    $argsList += @("-NumeroSerieManual", (Quote-Arg $NumeroSerieManual))
}

if (-not (Test-Admin)) {
    Show-Message "O Windows vai solicitar permissao de Administrador para instalar o agente.`n`nDepois de confirmar o UAC, aguarde as proximas telas de configuracao."
    Start-Process -FilePath "powershell.exe" -ArgumentList $argsList -Verb RunAs -WindowStyle Hidden
    exit 0
}

$process = Start-Process -FilePath "powershell.exe" -ArgumentList $argsList -WindowStyle Hidden -Wait -PassThru
exit $process.ExitCode
