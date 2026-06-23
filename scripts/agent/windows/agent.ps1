param(
    [string]$ConfigPath = "$env:ProgramData\SistemaChamadosAgent\config.json"
)

$ErrorActionPreference = "Stop"

$logDir = Split-Path $ConfigPath
if (-not $logDir) {
    $logDir = Join-Path $env:ProgramData "SistemaChamadosAgent"
}
$logPath = Join-Path $logDir "last-run.log"

function Write-AgentLog {
    param([string]$Message)
    try {
        if (-not (Test-Path $logDir)) {
            New-Item -ItemType Directory -Path $logDir -Force | Out-Null
        }
        "$(Get-Date -Format o) $Message" | Out-File -FilePath $logPath -Encoding utf8 -Append
    } catch {
        Write-Host $Message
    }
}

function Enable-Tls12IfAvailable {
    try {
        $tls12 = [Net.SecurityProtocolType]::Tls12
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor $tls12
    } catch {
        # Windows 7 sem .NET atualizado pode nao ter TLS 1.2; o envio HTTP local continua funcionando.
    }
}

function ConvertTo-AgentJson($obj) {
    if (Get-Command ConvertTo-Json -ErrorAction SilentlyContinue) {
        return $obj | ConvertTo-Json -Depth 8
    }

    try {
        Add-Type -AssemblyName System.Web.Extensions
        $serializer = New-Object System.Web.Script.Serialization.JavaScriptSerializer
        $serializer.MaxJsonLength = 10485760
        return $serializer.Serialize($obj)
    } catch {
        throw "Nao foi possivel serializar JSON. Instale PowerShell 3+ ou .NET com System.Web.Extensions."
    }
}

function Get-PrimaryInterface {
    $interfaces = Get-WmiObject Win32_NetworkAdapterConfiguration -Filter "IPEnabled=True" -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -and $_.MACAddress } |
        Sort-Object @{Expression = { if ($_.Description -match "Ethernet|Gigabit|Realtek|Intel") { 0 } else { 1 } } }

    return $interfaces | Select-Object -First 1
}

function Get-NetworkInterfaces {
    $items = @()
    Get-WmiObject Win32_NetworkAdapterConfiguration -Filter "IPEnabled=True" -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -and $_.MACAddress } |
        ForEach-Object {
            $ipv4 = @($_.IPAddress | Where-Object { $_ -match "^\d{1,3}(\.\d{1,3}){3}$" }) | Select-Object -First 1
            $items += @{
                nome = [string]$_.Description
                ip = [string]$ipv4
                mac = [string]$_.MACAddress
                status = "Up"
                velocidade = ""
            }
        }
    return $items
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

    $office = $apps | Sort-Object DisplayName, DisplayVersion -Unique | Select-Object -First 1
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

    return @($apps | Where-Object { $_ -and $_.Trim() } | Sort-Object -Unique | Select-Object -First 200)
}

function Get-LocalDiskTotalGb {
    $total = Get-WmiObject Win32_LogicalDisk -Filter "DriveType=3" -ErrorAction SilentlyContinue |
        Where-Object { $_.Size } |
        Measure-Object -Property Size -Sum

    if ($total.Sum) {
        return [math]::Round($total.Sum / 1GB, 2)
    }
    return $null
}

function Get-AgentPayload {
    param([string]$SerialManual = "")

    $computer = Get-WmiObject Win32_ComputerSystem
    $bios = Get-WmiObject Win32_BIOS
    $os = Get-WmiObject Win32_OperatingSystem
    $cpu = Get-WmiObject Win32_Processor | Select-Object -First 1
    $primary = Get-PrimaryInterface
    $interfaces = @(Get-NetworkInterfaces)

    $ip = ""
    $mac = ""
    if ($primary) {
        $ipv4 = @($primary.IPAddress | Where-Object { $_ -match "^\d{1,3}(\.\d{1,3}){3}$" }) | Select-Object -First 1
        $ip = [string]$ipv4
        $mac = [string]$primary.MACAddress
    }

    $serial = [string]$bios.SerialNumber
    if ($SerialManual.Trim()) {
        $serial = $SerialManual.Trim()
    }

    return @{
        versao_agente = "1.3.0"
        hostname = [string]$env:COMPUTERNAME
        ip = $ip
        mac = $mac
        usuario_logado = "$env:USERDOMAIN\$env:USERNAME"
        dominio = [string]$computer.Domain
        fabricante = [string]$computer.Manufacturer
        modelo = [string]$computer.Model
        numero_serie = $serial
        sistema_operacional = "$($os.Caption) $($os.Version) build $($os.BuildNumber)"
        arquitetura = [string]$os.OSArchitecture
        processador = [string]$cpu.Name
        memoria_total_gb = [math]::Round([double]$computer.TotalPhysicalMemory / 1GB, 2)
        disco_total_gb = Get-LocalDiskTotalGb
        office = Get-InstalledOffice
        softwares_instalados = @(Get-InstalledSoftwareList)
        interfaces = $interfaces
        coletado_em = (Get-Date).ToString("o")
    }
}

function Send-AgentPayload {
    param(
        [string]$Endpoint,
        [string]$Token,
        [string]$Json
    )

    Enable-Tls12IfAvailable
    $client = New-Object System.Net.WebClient
    $client.Encoding = [System.Text.Encoding]::UTF8
    $client.Headers.Add("Authorization", "Bearer $Token")
    $client.Headers.Add("Content-Type", "application/json; charset=utf-8")
    return $client.UploadString($Endpoint, "POST", $Json)
}

try {
    if (-not (Test-Path $ConfigPath)) {
        throw "Arquivo de configuracao nao encontrado: $ConfigPath"
    }

    $configText = Get-Content $ConfigPath -Raw
    if (Get-Command ConvertFrom-Json -ErrorAction SilentlyContinue) {
        $config = $configText | ConvertFrom-Json
    } else {
        Add-Type -AssemblyName System.Web.Extensions
        $serializer = New-Object System.Web.Script.Serialization.JavaScriptSerializer
        $config = $serializer.DeserializeObject($configText)
    }

    $serverUrl = [string]$config.server_url
    $token = [string]$config.token
    $serialManual = [string]$config.numero_serie_manual

    if (-not $serverUrl -or -not $token) {
        throw "Configure server_url e token em $ConfigPath"
    }

    $serverUrl = $serverUrl.TrimEnd("/")
    $endpoint = "$serverUrl/inventario/agente/coleta/"
    Write-AgentLog "INFO Enviando coleta para $endpoint"
    $payload = Get-AgentPayload -SerialManual $serialManual
    $json = ConvertTo-AgentJson $payload
    $response = Send-AgentPayload -Endpoint $endpoint -Token $token -Json $json
    Write-AgentLog "OK $response"
    exit 0
} catch {
    Write-AgentLog "ERRO $($_.Exception.Message)"
    exit 1
}
