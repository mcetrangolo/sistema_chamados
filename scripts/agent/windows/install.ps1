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
        throw "Informe o IP ou URL do servidor."
    }
    if ($value -notmatch "^https?://") {
        $value = "http://$value"
    }
    return $value.TrimEnd("/")
}

Assert-Admin

if (-not $ServerUrl) {
    $ServerUrl = Read-Host "Informe o IP ou URL do servidor (ex: 192.168.0.10:8000 ou https://chamados.local)"
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

$installDir = Join-Path $env:ProgramData "SistemaChamadosAgent"
$agentSource = Join-Path $PSScriptRoot "agent.ps1"
$agentTarget = Join-Path $installDir "agent.ps1"
$configPath = Join-Path $installDir "config.json"

if (-not (Test-Path $agentSource)) {
    throw "agent.ps1 nao encontrado junto do instalador."
}

New-Item -ItemType Directory -Path $installDir -Force | Out-Null
Copy-Item -Path $agentSource -Destination $agentTarget -Force

$config = @{
    server_url = $ServerUrl
    token = $Token.Trim()
    numero_serie_manual = $NumeroSerieManual.Trim()
    installed_at = (Get-Date).ToString("o")
    interval_hours = $IntervalHours
}

$config | ConvertTo-Json -Depth 3 | Out-File -FilePath $configPath -Encoding utf8 -Force

$taskName = "SistemaChamadosAgent"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$agentTarget`" -ConfigPath `"$configPath`""
$triggerStartup = New-ScheduledTaskTrigger -AtStartup
$triggerInterval = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Hours $IntervalHours)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($triggerStartup, $triggerInterval) -Principal $principal -Settings $settings -Force | Out-Null

Write-Host ""
Write-Host "Agente instalado com sucesso." -ForegroundColor Green
Write-Host "Servidor: $ServerUrl"
if ($NumeroSerieManual.Trim()) {
    Write-Host "Numero de serie manual: $($NumeroSerieManual.Trim())"
}
Write-Host "Pasta: $installDir"
Write-Host "Tarefa agendada: $taskName"
Write-Host ""
Write-Host "Executando primeira coleta..."
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $agentTarget -ConfigPath $configPath
Write-Host "Primeira coleta concluida."
