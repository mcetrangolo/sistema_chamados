param(
    [string]$ServerUrl = "",
    [string]$Token = "",
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

Assert-Admin

if (-not $ServerUrl) {
    $ServerUrl = Read-Host "Informe o IP:porta ou URL do servidor (ex: 192.168.0.10:8000 ou https://chamados.local)"
}

if (-not $Token) {
    $Token = Read-Host "Informe o token do agente configurado no servidor"
}

if (-not $NumeroSerieManual) {
    $NumeroSerieManual = Read-Host "Numero de serie manual/patrimonio (opcional, Enter para usar o serial da BIOS)"
}

$ServerUrl = Normalize-ServerUrl $ServerUrl
if (-not $Token.Trim()) {
    throw "Token do agente e obrigatorio."
}
if ($IntervalHours -lt 1) {
    $IntervalHours = 6
}

$installDir = Join-Path $env:ProgramData "SistemaChamadosAgent"
$agentSource = Join-Path $PSScriptRoot "agent.ps1"
$agentTarget = Join-Path $installDir "agent.ps1"
$configPath = Join-Path $installDir "config.json"

if (-not (Test-Path $agentSource)) {
    throw "agent.ps1 nao encontrado junto do instalador."
}

New-Item -ItemType Directory -Path $installDir -Force | Out-Null
Copy-Item -Path $agentSource -Destination $agentTarget -Force
Write-ConfigJson -Path $configPath -ServerUrl $ServerUrl -Token $Token.Trim() -NumeroSerieManual $NumeroSerieManual.Trim() -IntervalHours $IntervalHours

$psCommand = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$agentTarget`" -ConfigPath `"$configPath`""
Register-AgentTask -TaskName "SistemaChamadosAgentStartup" -Schedule "ONSTART" -Modifier 1 -Command $psCommand
Register-AgentTask -TaskName "SistemaChamadosAgentInterval" -Schedule "HOURLY" -Modifier $IntervalHours -Command $psCommand

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
