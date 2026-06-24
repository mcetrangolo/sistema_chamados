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
$sourcePackageDir = Join-Path $outputDirFull "SistemaChamadosAgentSource"
$exePath = Join-Path $outputDirFull $OutputName
$zipPath = Join-Path $outputDirFull "SistemaChamadosAgentSource.zip"
$releaseDir = Join-Path $projectDir "releases\agents\windows"
$releaseExePath = Join-Path $releaseDir $OutputName
$releaseZipPath = Join-Path $releaseDir "SistemaChamadosAgentSource.zip"
$releaseTrayPath = Join-Path $releaseDir "SistemaChamadosAgentTray.exe"

if (Test-Path $packageDir) {
    Remove-Item -Path $packageDir -Recurse -Force
}
if (Test-Path $sourcePackageDir) {
    Remove-Item -Path $sourcePackageDir -Recurse -Force
}
New-Item -ItemType Directory -Path $packageDir -Force | Out-Null
New-Item -ItemType Directory -Path $sourcePackageDir -Force | Out-Null

$csc = @(
    (Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe"),
    (Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"),
    (Join-Path $env:WINDIR "Microsoft.NET\Framework\v3.5\csc.exe")
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $csc) {
    throw "Compilador C# do .NET Framework nao encontrado. Nao foi possivel gerar o instalador grafico."
}

$traySourcePath = Join-Path $baseDir "AgentTray.cs"
$trayExePath = Join-Path $packageDir "SistemaChamadosAgentTray.exe"
& $csc /nologo /target:winexe /out:$trayExePath /reference:System.Windows.Forms.dll /reference:System.Drawing.dll $traySourcePath
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

foreach ($file in @("agent.ps1", "install.ps1", "install_gui.ps1", "uninstall.ps1", "README.md")) {
    $sourceFile = Join-Path $baseDir $file
    $targetFile = Join-Path $sourcePackageDir $file
    if ($file -in @("install.ps1", "install_gui.ps1")) {
        $content = Get-Content $sourceFile -Raw
        $escapedToken = $AgentToken.Replace("\", "\\").Replace('"', '\"')
        $content = $content.Replace('[string]$Token = "sistema-chamados-agent-local"', "[string]`$Token = `"$escapedToken`"")
        $content | Out-File -FilePath $targetFile -Encoding UTF8 -Force
    } else {
        Copy-Item -LiteralPath $sourceFile -Destination $targetFile -Force
    }
}
Copy-Item -LiteralPath $trayExePath -Destination (Join-Path $sourcePackageDir "SistemaChamadosAgentTray.exe") -Force

@"
@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_gui.ps1"
pause
"@ | Out-File -FilePath (Join-Path $sourcePackageDir "InstalarAgente.cmd") -Encoding ascii -Force

if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path (Join-Path $sourcePackageDir "*") -DestinationPath $zipPath -Force

& $csc /nologo /target:winexe /out:$exePath /reference:System.Windows.Forms.dll $generatedSource

if (Test-Path $exePath) {
    New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
    Copy-Item -LiteralPath $exePath -Destination $releaseExePath -Force
    Copy-Item -LiteralPath $zipPath -Destination $releaseZipPath -Force
    Copy-Item -LiteralPath $trayExePath -Destination $releaseTrayPath -Force
    Write-Host "Instalador standalone criado: $exePath" -ForegroundColor Green
    Write-Host "Pacote ZIP criado: $zipPath" -ForegroundColor Green
    Write-Host "Copia versionada atualizada: $releaseExePath" -ForegroundColor Green
    Write-Host "Copia ZIP versionada atualizada: $releaseZipPath" -ForegroundColor Green
    Write-Host "Aplicativo da bandeja atualizado: $releaseTrayPath" -ForegroundColor Green
} else {
    throw "Compilacao executou, mas o EXE nao foi encontrado: $exePath"
}
