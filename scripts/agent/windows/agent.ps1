param(
    [string]$ConfigPath = "$env:ProgramData\SistemaChamadosAgent\config.json",
    [switch]$SomenteSeSolicitada
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
    return ConvertTo-AgentJsonValue $obj
}

function Escape-AgentJsonString {
    param([string]$Value)
    if ($null -eq $Value) { return "" }
    $s = $Value.Replace('\', '\\')
    $s = $s.Replace('"', '\"')
    $s = $s.Replace("`r", '\r')
    $s = $s.Replace("`n", '\n')
    $s = $s.Replace("`t", '\t')
    return $s
}

function ConvertTo-AgentJsonValue {
    param($Value)

    if ($null -eq $Value) { return "null" }

    if ($Value -is [string]) {
        return '"' + (Escape-AgentJsonString $Value) + '"'
    }

    if ($Value -is [bool]) {
        if ($Value) { return "true" } else { return "false" }
    }

    if ($Value -is [byte] -or $Value -is [int16] -or $Value -is [int32] -or $Value -is [int64] -or
        $Value -is [single] -or $Value -is [double] -or $Value -is [decimal]) {
        return ([string]$Value).Replace(',', '.')
    }

    if ($Value -is [System.Collections.IDictionary]) {
        $parts = @()
        foreach ($key in $Value.Keys) {
            $parts += ('"' + (Escape-AgentJsonString ([string]$key)) + '":' + (ConvertTo-AgentJsonValue $Value[$key]))
        }
        return "{" + ([string]::Join(',', $parts)) + "}"
    }

    if ($Value -is [System.Collections.IEnumerable]) {
        $parts = @()
        foreach ($item in $Value) {
            $parts += (ConvertTo-AgentJsonValue $item)
        }
        return "[" + ([string]::Join(',', $parts)) + "]"
    }

    return '"' + (Escape-AgentJsonString ([string]$Value)) + '"'
}

function Read-AgentConfig {
    param([string]$Path)

    $text = [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
    $config = @{}

    $stringKeys = @("server_url", "token", "numero_serie_manual", "installed_at")
    foreach ($key in $stringKeys) {
        $pattern = '"' + [regex]::Escape($key) + '"\s*:\s*"((?:\\.|[^"\\])*)"'
        $match = [regex]::Match($text, $pattern)
        if ($match.Success) {
            $value = $match.Groups[1].Value
            $value = $value.Replace('\"', '"').Replace('\\', '\')
            $config[$key] = $value
        } else {
            $config[$key] = ""
        }
    }

    $numPattern = '"interval_hours"\s*:\s*([0-9]+)'
    $numMatch = [regex]::Match($text, $numPattern)
    if ($numMatch.Success) {
        $config["interval_hours"] = [int]$numMatch.Groups[1].Value
    } else {
        $config["interval_hours"] = 6
    }

    return $config
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

function Get-OperatingSystemName {
    param($WmiOs)

    $productName = ""
    $currentVersion = ""
    $currentBuild = ""
    $servicePack = ""

    try {
        $reg = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion" -ErrorAction SilentlyContinue
        if ($reg) {
            $productName = [string]$reg.ProductName
            $currentVersion = [string]$reg.CurrentVersion
            $currentBuild = [string]$reg.CurrentBuildNumber
            $servicePack = [string]$reg.CSDVersion
        }
    } catch {}

    if (-not $productName -and $WmiOs) {
        $productName = [string]$WmiOs.Caption
    }

    if (-not $currentVersion -and $WmiOs) {
        $currentVersion = [string]$WmiOs.Version
    }

    if (-not $currentBuild -and $WmiOs) {
        $currentBuild = [string]$WmiOs.BuildNumber
    }

    if ($currentVersion -like "6.1*" -or $currentBuild -eq "7600" -or $currentBuild -eq "7601") {
        if ($productName -match "Windows 10") {
            $productName = "Microsoft Windows 7"
        }
    }
    if ($currentVersion -like "6.3*" -and $productName -match "Windows 10") {
        $productName = "Microsoft Windows 8.1"
    }
    if ($currentVersion -like "6.2*" -and $productName -match "Windows 10") {
        $productName = "Microsoft Windows 8"
    }

    $parts = @()
    if ($productName) { $parts += $productName }
    if ($servicePack) { $parts += $servicePack }
    if ($currentVersion) { $parts += $currentVersion }
    if ($currentBuild) { $parts += "build $currentBuild" }

    return ([string]::Join(" ", $parts)).Trim()
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
        versao_agente = "1.4.7"
        hostname = [string]$env:COMPUTERNAME
        ip = $ip
        mac = $mac
        usuario_logado = "$env:USERDOMAIN\$env:USERNAME"
        dominio = [string]$computer.Domain
        fabricante = [string]$computer.Manufacturer
        modelo = [string]$computer.Model
        numero_serie = $serial
        sistema_operacional = Get-OperatingSystemName -WmiOs $os
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
    try {
        return $client.UploadString($Endpoint, "POST", $Json)
    } catch [System.Net.WebException] {
        $detalhe = ""
        if ($_.Exception.Response) {
            try {
                $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                $detalhe = $reader.ReadToEnd()
                $reader.Close()
            } catch {}
        }
        if ($detalhe) {
            try {
                $errPath = Join-Path $logDir "last-server-error.txt"
                $detalhe | Out-File -FilePath $errPath -Encoding utf8 -Force
            } catch {}
            throw "Falha HTTP ao enviar inventario: $detalhe"
        }
        throw
    } finally {
        $client.Dispose()
    }
}

function Test-CollectionRequested {
    param(
        [string]$ServerUrl,
        [string]$Token,
        [string]$Hostname
    )

    Enable-Tls12IfAvailable
    $hostnameEscaped = [Uri]::EscapeDataString($Hostname)
    $endpoint = "$($ServerUrl.TrimEnd('/'))/inventario/agente/coleta/solicitada/?hostname=$hostnameEscaped"
    $client = New-Object System.Net.WebClient
    $client.Encoding = [System.Text.Encoding]::UTF8
    $client.Headers.Add("Authorization", "Bearer $Token")
    try {
        $response = $client.DownloadString($endpoint)
        return $response -match '"coleta_solicitada"\s*:\s*true'
    } finally {
        $client.Dispose()
    }
}

try {
    if (-not (Test-Path $ConfigPath)) {
        throw "Arquivo de configuracao nao encontrado: $ConfigPath"
    }

    $config = Read-AgentConfig -Path $ConfigPath

    $serverUrl = [string]$config["server_url"]
    $token = [string]$config["token"]
    $serialManual = [string]$config["numero_serie_manual"]

    if (-not $serverUrl -or -not $token) {
        throw "Configure server_url e token em $ConfigPath"
    }

    $serverUrl = $serverUrl.TrimEnd("/")
    if ($SomenteSeSolicitada) {
        if (-not (Test-CollectionRequested -ServerUrl $serverUrl -Token $token -Hostname $env:COMPUTERNAME)) {
            exit 0
        }
        Write-AgentLog "INFO Coleta solicitada remotamente pelo servidor."
    }
    $endpoint = "$serverUrl/inventario/agente/coleta/"
    Write-AgentLog "INFO Enviando coleta para $endpoint"
    $payload = Get-AgentPayload -SerialManual $serialManual
    $json = ConvertTo-AgentJson $payload
    try {
        $jsonLog = Join-Path $logDir "last-payload.json"
        $json | Out-File -FilePath $jsonLog -Encoding utf8 -Force
    } catch {}
    $response = Send-AgentPayload -Endpoint $endpoint -Token $token -Json $json
    Write-AgentLog "OK $response"
    exit 0
} catch {
    Write-AgentLog "ERRO $($_.Exception.Message)"
    exit 1
}
