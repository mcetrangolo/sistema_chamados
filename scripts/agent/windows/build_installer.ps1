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

if (Test-Path $packageDir) {
    Remove-Item -Path $packageDir -Recurse -Force
}
New-Item -ItemType Directory -Path $packageDir -Force | Out-Null

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
$templatePath = Join-Path $baseDir "AgentStandaloneInstaller.template.cs"
$generatedSource = Join-Path $packageDir "AgentStandaloneInstaller.cs"

$source = Get-Content $templatePath -Raw
$source = $source.Replace("__AGENT_TOKEN__", $AgentToken.Replace("\", "\\").Replace('"', '\"'))
$source = $source.Replace("__AGENT_SCRIPT_BASE64__", $agentScript)
$source = $source.Replace("__UNINSTALL_SCRIPT_BASE64__", $uninstallScript)
$source | Out-File -FilePath $generatedSource -Encoding UTF8 -Force

$csc = @(
    (Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe"),
    (Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"),
    (Join-Path $env:WINDIR "Microsoft.NET\Framework\v3.5\csc.exe")
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $csc) {
    throw "Compilador C# do .NET Framework nao encontrado. Nao foi possivel gerar o instalador grafico."
}

& $csc /nologo /target:winexe /out:$exePath /reference:System.Windows.Forms.dll $generatedSource

if (Test-Path $exePath) {
    New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
    Copy-Item -LiteralPath $exePath -Destination $releaseExePath -Force
    Write-Host "Instalador standalone criado: $exePath" -ForegroundColor Green
    Write-Host "Copia versionada atualizada: $releaseExePath" -ForegroundColor Green
} else {
    throw "Compilacao executou, mas o EXE nao foi encontrado: $exePath"
}
