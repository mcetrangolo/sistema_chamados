param(
    [string]$ConfigPath = "$env:ProgramData\SistemaChamadosAgent\config.json"
)

$ErrorActionPreference = "Stop"

function Get-PrimaryInterface {
    $interfaces = Get-NetIPConfiguration |
        Where-Object { $_.IPv4Address -and $_.NetAdapter.Status -eq "Up" } |
        Sort-Object { if ($_.NetAdapter.Name -like "*Ethernet*") { 0 } else { 1 } }

    return $interfaces | Select-Object -First 1
}

function Get-InstalledOffice {
    $paths = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
    )

    $apps = foreach ($path in $paths) {
        Get-ItemProperty $path -ErrorAction SilentlyContinue |
            Where-Object {
                $_.DisplayName -and (
                    $_.DisplayName -match "Microsoft 365" -or
                    $_.DisplayName -match "Microsoft Office" -or
                    $_.DisplayName -match "Office LTSC" -or
                    $_.DisplayName -match "Office Professional" -or
                    $_.DisplayName -match "Office Standard"
                )
            } |
            Select-Object DisplayName, DisplayVersion
    }

    $office = $apps |
        Sort-Object DisplayName, DisplayVersion -Unique |
        Select-Object -First 1

    if ($office) {
        return "$($office.DisplayName) $($office.DisplayVersion)".Trim()
    }

    $clickToRun = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration" -ErrorAction SilentlyContinue
    if ($clickToRun -and $clickToRun.ProductReleaseIds) {
        return "$($clickToRun.ProductReleaseIds) $($clickToRun.VersionToReport)".Trim()
    }

    return ""
}

function Get-InstalledSoftwareList {
    $paths = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*"
    )

    $apps = foreach ($path in $paths) {
        Get-ItemProperty $path -ErrorAction SilentlyContinue |
            Where-Object {
                $_.DisplayName -and
                $_.SystemComponent -ne 1 -and
                $_.ReleaseType -ne "Update" -and
                $_.ParentKeyName -eq $null
            } |
            ForEach-Object {
                if ($_.DisplayVersion) {
                    "$($_.DisplayName) $($_.DisplayVersion)"
                } else {
                    "$($_.DisplayName)"
                }
            }
    }

    return $apps |
        Where-Object { $_ -and $_.Trim() } |
        Sort-Object -Unique |
        Select-Object -First 200
}

function Get-LocalDiskTotalGb {
    $total = Get-CimInstance Win32_LogicalDisk |
        Where-Object { $_.DriveType -eq 3 -and $_.Size } |
        Measure-Object -Property Size -Sum

    if ($total.Sum) {
        return [math]::Round($total.Sum / 1GB, 2)
    }
    return $null
}

function Get-AgentPayload {
    param(
        [string]$SerialManual = ""
    )

    $computer = Get-CimInstance Win32_ComputerSystem
    $bios = Get-CimInstance Win32_BIOS
    $os = Get-CimInstance Win32_OperatingSystem
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    $primary = Get-PrimaryInterface
    $interfaces = @()

    Get-NetIPConfiguration |
        Where-Object { $_.IPv4Address -and $_.NetAdapter.MacAddress -and $_.NetAdapter.Status -eq "Up" } |
        ForEach-Object {
            $interfaces += @{
                nome = $_.NetAdapter.Name
                ip = ($_.IPv4Address | Select-Object -First 1).IPAddress
                mac = $_.NetAdapter.MacAddress
                status = $_.NetAdapter.Status
                velocidade = $_.NetAdapter.LinkSpeed
            }
        }

    $ip = ""
    $mac = ""
    if ($primary) {
        $ip = ($primary.IPv4Address | Select-Object -First 1).IPAddress
        $mac = $primary.NetAdapter.MacAddress
    }

    $serial = $bios.SerialNumber
    if ($SerialManual.Trim()) {
        $serial = $SerialManual.Trim()
    }

    return @{
        hostname = $env:COMPUTERNAME
        ip = $ip
        mac = $mac
        usuario_logado = "$env:USERDOMAIN\$env:USERNAME"
        dominio = $computer.Domain
        fabricante = $computer.Manufacturer
        modelo = $computer.Model
        numero_serie = $serial
        sistema_operacional = "$($os.Caption) $($os.Version) build $($os.BuildNumber)"
        arquitetura = $os.OSArchitecture
        processador = $cpu.Name
        memoria_total_gb = [math]::Round($computer.TotalPhysicalMemory / 1GB, 2)
        disco_total_gb = Get-LocalDiskTotalGb
        office = Get-InstalledOffice
        softwares_instalados = @(Get-InstalledSoftwareList)
        interfaces = $interfaces
        coletado_em = (Get-Date).ToString("o")
    }
}

if (-not (Test-Path $ConfigPath)) {
    throw "Arquivo de configuracao nao encontrado: $ConfigPath"
}

$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$serverUrl = [string]$config.server_url
$token = [string]$config.token
$serialManual = [string]$config.numero_serie_manual

if (-not $serverUrl -or -not $token) {
    throw "Configure server_url e token em $ConfigPath"
}

$serverUrl = $serverUrl.TrimEnd("/")
$endpoint = "$serverUrl/inventario/agente/coleta/"
$payload = Get-AgentPayload -SerialManual $serialManual
$json = $payload | ConvertTo-Json -Depth 5

$headers = @{
    Authorization = "Bearer $token"
}

$response = Invoke-RestMethod -Method Post -Uri $endpoint -Headers $headers -Body $json -ContentType "application/json; charset=utf-8" -TimeoutSec 30
$logDir = Split-Path $ConfigPath
$logPath = Join-Path $logDir "last-run.log"
"$(Get-Date -Format o) OK $($response | ConvertTo-Json -Compress)" | Out-File -FilePath $logPath -Encoding utf8
