param(
    [string]$TaskName = "SistemaChamadosRotinas",
    [string]$StartTime = "23:30"
)

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ScriptPath = Join-Path $ProjectRoot "scripts\run_scheduled_tasks.ps1"

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`"" `
    -WorkingDirectory $ProjectRoot

$Trigger = New-ScheduledTaskTrigger -Daily -At $StartTime
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 4)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Executa varreduras de inventario, validacao diaria de status por ping e backup local do Sistema de Chamados." `
    -Force

Write-Host "Tarefa agendada criada/atualizada: $TaskName as $StartTime"
