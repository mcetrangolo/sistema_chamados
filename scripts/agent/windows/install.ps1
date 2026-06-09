param(
    [string]$ServerUrl = "",
    [string]$Token = "sistema-chamados-agent-local",
    [string]$NumeroSerieManual = "",
    [int]$IntervalHours = 6
)

$ErrorActionPreference = "Stop"

function Assert-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Execute este instalador como Administrador."
    }
}

function Show-Message {
    param(
        [string]$Message,
        [string]$Title = "Sistema Chamados Agent"
    )
    try {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show($Message, $Title, [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null
    } catch {
        Write-Host $Message
    }
}

function Read-Input {
    param(
        [string]$Prompt,
        [string]$Title = "Sistema Chamados Agent",
        [string]$Default = ""
    )
    try {
        Add-Type -AssemblyName Microsoft.VisualBasic
        return [Microsoft.VisualBasic.Interaction]::InputBox($Prompt, $Title, $Default)
    } catch {
        return Read-Host $Prompt
    }
}

function Normalize-ServerUrl([string]$value) {
    $value = $value.Trim()
    if (-not $value) {
        throw "Informe o IP, porta ou URL do servidor."
    }
    if ($value -notmatch "^https?://") {
        $value = "http://$value"
    }
    return $value.TrimEnd("/")
}

function JsonEscape([string]$value) {
    if ($null -eq $value) { return "" }
    return $value.Replace("\", "\\").Replace('"', '\"').Replace("`r", "\r").Replace("`n", "\n")
}

function Write-ConfigJson {
    param(
        [string]$Path,
        [string]$ServerUrl,
        [string]$Token,
        [string]$NumeroSerieManual,
        [int]$IntervalHours
    )

    $json = @"
{
  "server_url": "$(JsonEscape $ServerUrl)",
  "token": "$(JsonEscape $Token)",
  "numero_serie_manual": "$(JsonEscape $NumeroSerieManual)",
  "installed_at": "$(Get-Date -Format o)",
  "interval_hours": $IntervalHours
}
"@
    $json | Out-File -FilePath $Path -Encoding utf8 -Force
}

function Register-AgentTask {
    param(
        [string]$TaskName,
        [string]$Schedule,
        [string]$Modifier,
        [string]$Command
    )

    & schtasks.exe /Delete /TN $TaskName /F 2>$null | Out-Null
    if ($Schedule -eq "ONSTART") {
        & schtasks.exe /Create /TN $TaskName /SC ONSTART /RU SYSTEM /RL HIGHEST /TR $Command /F | Out-Null
    } else {
        & schtasks.exe /Create /TN $TaskName /SC HOURLY /MO $Modifier /RU SYSTEM /RL HIGHEST /TR $Command /F | Out-Null
    }
}

function Register-UninstallEntry {
    param(
        [string]$InstallDir,
        [string]$UninstallScript
    )

    $keyPaths = @("HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\SistemaChamadosAgent")
    if ([Environment]::Is64BitOperatingSystem) {
        $keyPaths += "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\SistemaChamadosAgent"
    }

    foreach ($keyPath in $keyPaths) {
        New-Item -Path $keyPath -Force | Out-Null
        New-ItemProperty -Path $keyPath -Name "DisplayName" -Value "Sistema Chamados Agent" -PropertyType String -Force | Out-Null
        New-ItemProperty -Path $keyPath -Name "DisplayVersion" -Value "1.0.1" -PropertyType String -Force | Out-Null
        New-ItemProperty -Path $keyPath -Name "Publisher" -Value "Sistema de Chamados" -PropertyType String -Force | Out-Null
        New-ItemProperty -Path $keyPath -Name "InstallLocation" -Value $InstallDir -PropertyType String -Force | Out-Null
        New-ItemProperty -Path $keyPath -Name "DisplayIcon" -Value "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -PropertyType String -Force | Out-Null
        New-ItemProperty -Path $keyPath -Name "UninstallString" -Value "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$UninstallScript`"" -PropertyType String -Force | Out-Null
        New-ItemProperty -Path $keyPath -Name "QuietUninstallString" -Value "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$UninstallScript`" -Silent" -PropertyType String -Force | Out-Null
        New-ItemProperty -Path $keyPath -Name "InstallDate" -Value (Get-Date -Format "yyyyMMdd") -PropertyType String -Force | Out-Null
        New-ItemProperty -Path $keyPath -Name "EstimatedSize" -Value 1024 -PropertyType DWord -Force | Out-Null
        New-ItemProperty -Path $keyPath -Name "SystemComponent" -Value 0 -PropertyType DWord -Force | Out-Null
        New-ItemProperty -Path $keyPath -Name "NoModify" -Value 1 -PropertyType DWord -Force | Out-Null
        New-ItemProperty -Path $keyPath -Name "NoRepair" -Value 1 -PropertyType DWord -Force | Out-Null
    }
}

Assert-Admin

Show-Message "Bem-vindo ao instalador do Agente de Inventario do Sistema de Chamados.`n`nEste assistente vai configurar o servidor, instalar o agente e criar as tarefas de coleta automatica."

if (-not $ServerUrl) {
    $ServerUrl = Read-Input -Prompt "Informe o IP:porta ou URL do servidor.`nExemplos: 192.168.0.10:8000 ou https://chamados.local" -Default "http://"
}

if (-not $NumeroSerieManual) {
    $NumeroSerieManual = Read-Input -Prompt "Numero de serie manual/patrimonio, se houver.`nDeixe em branco para usar o serial da BIOS."
}

$ServerUrl = Normalize-ServerUrl $ServerUrl
if (-not $Token.Trim()) {
    throw "Token do agente nao foi configurado no instalador."
}
if ($IntervalHours -lt 1) {
    $IntervalHours = 6
}

$installDir = Join-Path $env:ProgramData "SistemaChamadosAgent"
$agentSource = Join-Path $PSScriptRoot "agent.ps1"
$uninstallSource = Join-Path $PSScriptRoot "uninstall.ps1"
$agentTarget = Join-Path $installDir "agent.ps1"
$uninstallTarget = Join-Path $installDir "uninstall.ps1"
$configPath = Join-Path $installDir "config.json"

if (-not (Test-Path $agentSource)) {
    throw "agent.ps1 nao encontrado junto do instalador."
}
if (-not (Test-Path $uninstallSource)) {
    throw "uninstall.ps1 nao encontrado junto do instalador."
}

New-Item -ItemType Directory -Path $installDir -Force | Out-Null
Copy-Item -Path $agentSource -Destination $agentTarget -Force
Copy-Item -Path $uninstallSource -Destination $uninstallTarget -Force
Write-ConfigJson -Path $configPath -ServerUrl $ServerUrl -Token $Token.Trim() -NumeroSerieManual $NumeroSerieManual.Trim() -IntervalHours $IntervalHours

$psCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$agentTarget`" -ConfigPath `"$configPath`""
Register-AgentTask -TaskName "SistemaChamadosAgentStartup" -Schedule "ONSTART" -Modifier 1 -Command $psCommand
Register-AgentTask -TaskName "SistemaChamadosAgentInterval" -Schedule "HOURLY" -Modifier $IntervalHours -Command $psCommand
Register-UninstallEntry -InstallDir $installDir -UninstallScript $uninstallTarget

Write-Host ""
Write-Host "Agente instalado com sucesso." -ForegroundColor Green
Write-Host "Servidor: $ServerUrl"
if ($NumeroSerieManual.Trim()) {
    Write-Host "Numero de serie manual: $($NumeroSerieManual.Trim())"
}
Write-Host "Pasta: $installDir"
Write-Host "Tarefas agendadas: SistemaChamadosAgentStartup e SistemaChamadosAgentInterval"
Write-Host ""
Write-Host "Executando primeira coleta..."
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $agentTarget -ConfigPath $configPath
Write-Host "Primeira coleta concluida."

Show-Message "Agente instalado com sucesso.`n`nServidor: $ServerUrl`nPasta: $installDir`n`nEle agora aparece no Painel de Controle para desinstalacao."
