param(
    [string]$OutputDir = ".\dist",
    [string]$OutputName = "SistemaChamadosAgentSetup.exe",
    [string]$AgentToken = ""
)

$ErrorActionPreference = "Stop"
$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Resolve-Path (Join-Path $baseDir "..\..\..")
$outputDirFull = (New-Item -ItemType Directory -Path $OutputDir -Force).FullName
$packageDir = Join-Path $outputDirFull "SistemaChamadosAgentPackage"
$exePath = Join-Path $outputDirFull $OutputName
$releaseDir = Join-Path $projectDir "releases\agents\windows"
$releaseExePath = Join-Path $releaseDir $OutputName
$releaseTrayPath = Join-Path $releaseDir "SistemaChamadosAgentTray.exe"
$releaseIconPath = Join-Path $releaseDir "SistemaChamadosAgent.ico"

if (Test-Path $packageDir) {
    Remove-Item -Path $packageDir -Recurse -Force
}
New-Item -ItemType Directory -Path $packageDir -Force | Out-Null

$csc = @(
    (Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe"),
    (Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"),
    (Join-Path $env:WINDIR "Microsoft.NET\Framework\v3.5\csc.exe")
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $csc) {
    throw "Compilador C# do .NET Framework nao encontrado. Nao foi possivel gerar o instalador grafico."
}

$iconGeneratorSource = Join-Path $baseDir "AgentIconGenerator.cs"
$iconGeneratorExe = Join-Path $packageDir "AgentIconGenerator.exe"
$iconPath = Join-Path $packageDir "SistemaChamadosAgent.ico"
& $csc /nologo /target:exe /out:$iconGeneratorExe /reference:System.Drawing.dll $iconGeneratorSource
if (-not (Test-Path $iconGeneratorExe)) {
    throw "Nao foi possivel compilar o gerador do icone."
}
& $iconGeneratorExe $iconPath
if (-not (Test-Path $iconPath)) {
    throw "O icone do agente nao foi gerado."
}

$traySourcePath = Join-Path $baseDir "AgentTray.cs"
$trayExePath = Join-Path $packageDir "SistemaChamadosAgentTray.exe"
& $csc /nologo /target:winexe /out:$trayExePath /win32icon:$iconPath /reference:System.Windows.Forms.dll /reference:System.Drawing.dll $traySourcePath
if (-not (Test-Path $trayExePath)) {
    throw "Nao foi possivel compilar o aplicativo da bandeja."
}

if (-not $AgentToken) {
    $envPath = Join-Path $projectDir ".env"
    if (Test-Path $envPath) {
        $tokenLine = Get-Content $envPath | Where-Object { $_ -match "^INVENTARIO_AGENT_TOKEN=" } | Select-Object -First 1
        if ($tokenLine) {
            $AgentToken = ($tokenLine -replace "^INVENTARIO_AGENT_TOKEN=", "").Trim().Trim('"').Trim("'")
        }
    }
}
if (-not $AgentToken) {
    $AgentToken = "sistema-chamados-agent-local"
}

function Convert-ToBase64Utf8([string]$Path) {
    $text = Get-Content $Path -Raw
    return [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($text))
}

$agentScript = Convert-ToBase64Utf8 (Join-Path $baseDir "agent.ps1")
$uninstallScript = Convert-ToBase64Utf8 (Join-Path $baseDir "uninstall.ps1")
$trayExecutable = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($trayExePath))
$templatePath = Join-Path $baseDir "AgentStandaloneInstaller.template.cs"
$generatedSource = Join-Path $packageDir "AgentStandaloneInstaller.cs"

$source = Get-Content $templatePath -Raw
$source = $source.Replace("__AGENT_TOKEN__", $AgentToken.Replace("\", "\\").Replace('"', '\"'))
$source = $source.Replace("__AGENT_SCRIPT_BASE64__", $agentScript)
$source = $source.Replace("__UNINSTALL_SCRIPT_BASE64__", $uninstallScript)
$source = $source.Replace("__TRAY_EXECUTABLE_BASE64__", $trayExecutable)
$source | Out-File -FilePath $generatedSource -Encoding UTF8 -Force

& $csc /nologo /target:winexe /out:$exePath /win32icon:$iconPath /reference:System.Windows.Forms.dll $generatedSource

if (Test-Path $exePath) {
    New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
    Copy-Item -LiteralPath $exePath -Destination $releaseExePath -Force
    Copy-Item -LiteralPath $trayExePath -Destination $releaseTrayPath -Force
    Copy-Item -LiteralPath $iconPath -Destination $releaseIconPath -Force
    Write-Host "Instalador standalone criado: $exePath" -ForegroundColor Green
    Write-Host "Copia versionada atualizada: $releaseExePath" -ForegroundColor Green
    Write-Host "Aplicativo da bandeja atualizado: $releaseTrayPath" -ForegroundColor Green
    Write-Host "Icone do agente atualizado: $releaseIconPath" -ForegroundColor Green
} else {
    throw "Compilacao executou, mas o EXE nao foi encontrado: $exePath"
}
