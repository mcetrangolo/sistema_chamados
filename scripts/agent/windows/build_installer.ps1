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
$sedPath = Join-Path $outputDirFull "SistemaChamadosAgentSetup.sed"
$exePath = Join-Path $outputDirFull $OutputName

if (Test-Path $packageDir) {
    Remove-Item -Path $packageDir -Recurse -Force
}
New-Item -ItemType Directory -Path $packageDir -Force | Out-Null

foreach ($file in @("agent.ps1", "install.ps1", "install_gui.ps1", "install_launcher.vbs", "install.cmd", "uninstall.ps1")) {
    Copy-Item -Path (Join-Path $baseDir $file) -Destination (Join-Path $packageDir $file) -Force
}

$csc = @(
    (Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe"),
    (Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"),
    (Join-Path $env:WINDIR "Microsoft.NET\Framework\v3.5\csc.exe")
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $csc) {
    throw "Compilador C# do .NET Framework nao encontrado. Nao foi possivel gerar o launcher grafico."
}

$launcherSource = Join-Path $baseDir "AgentSetupLauncher.cs"
$launcherExe = Join-Path $packageDir "AgentSetupLauncher.exe"
& $csc /nologo /target:winexe /out:$launcherExe /reference:System.Windows.Forms.dll $launcherSource
if (-not (Test-Path $launcherExe)) {
    throw "Nao foi possivel compilar AgentSetupLauncher.exe."
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

$escapedToken = $AgentToken.Replace("\", "\\").Replace('"', '\"')
foreach ($script in @("install.ps1", "install_gui.ps1")) {
    $scriptPath = Join-Path $packageDir $script
    $content = Get-Content $scriptPath -Raw
    $content = $content -replace '\[string\]\$Token = ".*?"', "[string]`$Token = `"$escapedToken`""
    $content | Out-File -FilePath $scriptPath -Encoding UTF8 -Force
}

$iexpress = Join-Path $env:WINDIR "System32\iexpress.exe"
if (-not (Test-Path $iexpress)) {
    Write-Warning "IExpress nao encontrado. Distribua a pasta: $packageDir"
    exit 0
}
$sed = @"
[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=0
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=%InstallPrompt%
DisplayLicense=%DisplayLicense%
FinishMessage=%FinishMessage%
TargetName=%TargetName%
FriendlyName=%FriendlyName%
AppLaunched=%AppLaunched%
PostInstallCmd=%PostInstallCmd%
AdminQuietInstCmd=%AdminQuietInstCmd%
UserQuietInstCmd=%UserQuietInstCmd%
SourceFiles=SourceFiles
[Strings]
InstallPrompt=
DisplayLicense=
FinishMessage=
TargetName=$exePath
FriendlyName=Sistema Chamados Agent Setup
AppLaunched=AgentSetupLauncher.exe
PostInstallCmd=<None>
AdminQuietInstCmd=
UserQuietInstCmd=
FILE0=agent.ps1
FILE1=install.ps1
FILE2=install_gui.ps1
FILE3=install_launcher.vbs
FILE4=install.cmd
FILE5=uninstall.ps1
FILE6=AgentSetupLauncher.exe
[SourceFiles]
SourceFiles0=$packageDir
[SourceFiles0]
%FILE0%=
%FILE1%=
%FILE2%=
%FILE3%=
%FILE4%=
%FILE5%=
%FILE6%=
"@

$sed | Out-File -FilePath $sedPath -Encoding ASCII -Force
& $iexpress /N /Q $sedPath

for ($i = 0; $i -lt 10 -and -not (Test-Path $exePath); $i++) {
    Start-Sleep -Milliseconds 500
}

if (Test-Path $exePath) {
    Write-Host "Instalador criado: $exePath" -ForegroundColor Green
} else {
    throw "IExpress executou, mas o EXE nao foi encontrado: $exePath"
}
