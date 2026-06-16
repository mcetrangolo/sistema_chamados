import ipaddress
import asyncio
import platform
import shutil
import socket
import subprocess
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.conf import settings

from .models import AtivoRede, MetodoDescoberta


@dataclass
class DescobertaAtivo:
    ip: str = ""
    nome: str = ""
    hostname: str = ""
    sistema_operacional: str = ""
    origem: str = AtivoRede.Origem.MANUAL
    observacoes: str = ""


def hosts_da_faixa(cidr, limite=254):
    rede = ipaddress.ip_network(cidr, strict=False)
    return list(rede.hosts())[:limite]


def ping_host(ip, timeout_ms=800):
    is_windows = platform.system().lower() == "windows"
    parametro = "-n" if is_windows else "-c"
    timeout_param = "-w" if is_windows else "-W"
    timeout_value = str(timeout_ms if is_windows else max(1, timeout_ms // 1000))
    try:
        resultado = subprocess.run(
            ["ping", parametro, "1", timeout_param, timeout_value, str(ip)],
            capture_output=True,
            text=True,
            timeout=max(2, timeout_ms // 1000 + 1),
        )
        return resultado.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def dns_reverso(ip):
    try:
        return socket.gethostbyaddr(str(ip))[0]
    except (socket.herror, socket.gaierror, TimeoutError):
        return ""


def tcp_aberto(ip, portas, timeout=0.6):
    abertas = []
    for porta in portas:
        try:
            with socket.create_connection((str(ip), int(porta)), timeout=timeout):
                abertas.append(str(porta))
        except (OSError, ValueError):
            continue
    return abertas


def nmap_disponivel():
    return shutil.which("nmap") is not None


def descobrir_por_nmap(cidr, portas=""):
    if not nmap_disponivel():
        return []

    comando = ["nmap", "-n", "-oX", "-", "--host-timeout", "8s"]
    if portas:
        comando.extend(["-p", portas])
    else:
        comando.extend(["-sn"])
    comando.append(str(cidr))

    try:
        resultado = subprocess.run(comando, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return []
    if resultado.returncode not in (0, 1):
        return []

    try:
        import xml.etree.ElementTree as ET

        raiz = ET.fromstring(resultado.stdout)
    except Exception:
        return []

    descobertos = []
    for host in raiz.findall("host"):
        status = host.find("status")
        if status is not None and status.attrib.get("state") != "up":
            continue
        ip = ""
        mac = ""
        vendor = ""
        for address in host.findall("address"):
            tipo = address.attrib.get("addrtype")
            if tipo == "ipv4":
                ip = address.attrib.get("addr", "")
            elif tipo == "mac":
                mac = address.attrib.get("addr", "")
                vendor = address.attrib.get("vendor", "")
        if not ip:
            continue
        hostname = ""
        hostnames = host.find("hostnames")
        if hostnames is not None:
            item = hostnames.find("hostname")
            if item is not None:
                hostname = item.attrib.get("name", "")
        portas_abertas = []
        ports = host.find("ports")
        if ports is not None:
            for port in ports.findall("port"):
                state = port.find("state")
                if state is not None and state.attrib.get("state") == "open":
                    portas_abertas.append(port.attrib.get("portid", ""))
        obs = "Detectado por Nmap."
        if mac or vendor:
            obs += f" MAC: {mac} {vendor}".strip()
        if portas_abertas:
            obs += f" Portas abertas: {', '.join(portas_abertas)}."
        descobertos.append(
            DescobertaAtivo(
                ip=ip,
                nome=hostname or f"Host ativo {ip}",
                hostname=hostname,
                observacoes=obs,
            )
        )
    return descobertos


def _descobrir_host_auto(ip_texto, faixa, portas_lista):
    motivos = []
    hostname = dns_reverso(ip_texto)
    if hostname:
        motivos.append("DNS reverso")
    if ping_host(ip_texto):
        motivos.append("Ping/ICMP")
    abertas = tcp_aberto(ip_texto, portas_lista or ["22", "80", "443", "445", "3389", "135", "139"])
    if abertas:
        motivos.append(f"TCP {', '.join(abertas)}")
    snmp = consultar_snmp_basico(ip_texto, faixa.credencial_snmp.community if faixa.credencial_snmp else "")
    if snmp:
        motivos.append("SNMP")
        hostname = snmp.get("hostname") or hostname

    if not motivos:
        return None
    origem = AtivoRede.Origem.SNMP if snmp else AtivoRede.Origem.MANUAL
    observacoes = "Detectado automaticamente por " + "; ".join(motivos) + "."
    if snmp and snmp.get("descricao"):
        observacoes += f" SNMP sysDescr: {snmp.get('descricao')}"
    return DescobertaAtivo(
        ip=ip_texto,
        nome=hostname or f"Host ativo {ip_texto}",
        hostname=hostname,
        origem=origem,
        observacoes=observacoes,
    )


def consultar_snmp_basico(ip, community):
    if not community:
        return None
    dados = _consultar_snmp_basico_atual(ip, community)
    if dados:
        return dados
    return _consultar_snmp_basico_legado(ip, community)


async def _consultar_snmp_basico_async(ip, community):
    from pysnmp.hlapi.v1arch.asyncio import (
        CommunityData,
        ObjectIdentity,
        ObjectType,
        SnmpDispatcher,
        UdpTransportTarget,
        get_cmd,
    )

    dispatcher = SnmpDispatcher()
    try:
        erro, status, _, var_binds = await get_cmd(
            dispatcher,
            CommunityData(community, mpModel=1),
            await UdpTransportTarget.create((str(ip), 161), timeout=1, retries=0),
            ObjectType(ObjectIdentity("1.3.6.1.2.1.1.5.0")),
            ObjectType(ObjectIdentity("1.3.6.1.2.1.1.1.0")),
        )
    finally:
        close = getattr(dispatcher, "close_dispatcher", None)
        if close:
            close()
    if erro or status:
        return None
    valores = [str(valor) for _, valor in var_binds]
    return {
        "hostname": valores[0] if valores else "",
        "descricao": valores[1] if len(valores) > 1 else "",
    }


def _consultar_snmp_basico_atual(ip, community):
    try:
        return asyncio.run(_consultar_snmp_basico_async(ip, community))
    except Exception:
        return None


def _consultar_snmp_basico_legado(ip, community):
    try:
        from pysnmp.hlapi import (
            CommunityData,
            ContextData,
            ObjectIdentity,
            ObjectType,
            SnmpEngine,
            UdpTransportTarget,
            getCmd,
        )

        iterator = getCmd(
            SnmpEngine(),
            CommunityData(community, mpModel=1),
            UdpTransportTarget((str(ip), 161), timeout=1, retries=0),
            ContextData(),
            ObjectType(ObjectIdentity("1.3.6.1.2.1.1.5.0")),
            ObjectType(ObjectIdentity("1.3.6.1.2.1.1.1.0")),
        )
        erro, status, _, var_binds = next(iterator)
        if erro or status:
            return None
        valores = [str(valor) for _, valor in var_binds]
        return {
            "hostname": valores[0] if valores else "",
            "descricao": valores[1] if len(valores) > 1 else "",
        }
    except Exception:
        return None


def descobrir_por_host(ip, metodo, portas="", credencial_snmp=None):
    portas_lista = [p.strip() for p in portas.split(",") if p.strip()]
    ip_texto = str(ip)

    if metodo == MetodoDescoberta.Codigo.AUTO:
        if nmap_disponivel():
            via_nmap = descobrir_por_nmap(f"{ip_texto}/32", portas or "22,80,443,445,3389,135,139")
            if via_nmap:
                return via_nmap[0]
        faixa = type("FaixaAlvo", (), {"credencial_snmp": credencial_snmp})()
        return _descobrir_host_auto(ip_texto, faixa, portas_lista)

    if metodo == MetodoDescoberta.Codigo.PING and ping_host(ip_texto):
        return DescobertaAtivo(ip=ip_texto, nome=f"Host ativo {ip_texto}", observacoes="Detectado por Ping/ICMP.")
    if metodo == MetodoDescoberta.Codigo.DNS:
        hostname = dns_reverso(ip_texto)
        if hostname:
            return DescobertaAtivo(ip=ip_texto, nome=hostname, hostname=hostname, observacoes="Detectado por DNS reverso.")
    if metodo == MetodoDescoberta.Codigo.TCP:
        abertas = tcp_aberto(ip_texto, portas_lista or ["22", "80", "443", "3389"])
        if abertas:
            return DescobertaAtivo(ip=ip_texto, nome=f"Servico detectado {ip_texto}", observacoes=f"Portas abertas: {', '.join(abertas)}.")
    if metodo == MetodoDescoberta.Codigo.SNMP:
        dados = consultar_snmp_basico(ip_texto, credencial_snmp.community if credencial_snmp else "")
        if dados:
            return DescobertaAtivo(
                ip=ip_texto,
                nome=dados.get("hostname") or f"Dispositivo SNMP {ip_texto}",
                hostname=dados.get("hostname", ""),
                origem=AtivoRede.Origem.SNMP,
                observacoes=f"SNMP sysDescr: {dados.get('descricao', '')}",
            )
    return None


def descobrir_por_faixa(faixa, metodo, portas=""):
    if metodo == MetodoDescoberta.Codigo.AD:
        return descobrir_ad()

    descobertos = []
    portas_lista = [p.strip() for p in portas.split(",") if p.strip()]

    if metodo == MetodoDescoberta.Codigo.AUTO:
        via_nmap = descobrir_por_nmap(faixa.cidr, portas or "22,80,443,445,3389,135,139")
        por_ip = {item.ip: item for item in via_nmap}
        hosts_restantes = [str(ip) for ip in hosts_da_faixa(faixa.cidr) if str(ip) not in por_ip]
        max_workers = min(64, max(4, len(hosts_restantes) or 1))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futuros = {
                executor.submit(_descobrir_host_auto, ip_texto, faixa, portas_lista): ip_texto
                for ip_texto in hosts_restantes
            }
            for futuro in as_completed(futuros):
                try:
                    item = futuro.result()
                except Exception:
                    item = None
                if item:
                    por_ip[item.ip] = item
        return list(por_ip.values())

    for ip in hosts_da_faixa(faixa.cidr):
        ip_texto = str(ip)
        if metodo == MetodoDescoberta.Codigo.PING and ping_host(ip_texto):
            descobertos.append(DescobertaAtivo(ip=ip_texto, nome=f"Host ativo {ip_texto}", observacoes="Detectado por Ping/ICMP."))
        elif metodo == MetodoDescoberta.Codigo.DNS:
            hostname = dns_reverso(ip_texto)
            if hostname:
                descobertos.append(DescobertaAtivo(ip=ip_texto, nome=hostname, hostname=hostname, observacoes="Detectado por DNS reverso."))
        elif metodo == MetodoDescoberta.Codigo.TCP:
            abertas = tcp_aberto(ip_texto, portas_lista or ["22", "80", "443", "3389"])
            if abertas:
                descobertos.append(DescobertaAtivo(ip=ip_texto, nome=f"Serviço detectado {ip_texto}", observacoes=f"Portas abertas: {', '.join(abertas)}."))
        elif metodo == MetodoDescoberta.Codigo.SNMP:
            dados = consultar_snmp_basico(ip_texto, faixa.credencial_snmp.community if faixa.credencial_snmp else "")
            if dados:
                descobertos.append(
                    DescobertaAtivo(
                        ip=ip_texto,
                        nome=dados.get("hostname") or f"Dispositivo SNMP {ip_texto}",
                        hostname=dados.get("hostname", ""),
                        origem=AtivoRede.Origem.SNMP,
                        observacoes=f"SNMP sysDescr: {dados.get('descricao', '')}",
                    )
                )
    return descobertos


def descobrir_ad():
    if not all([settings.AD_SERVER, settings.AD_USER, settings.AD_PASSWORD, settings.AD_BASE_DN]):
        raise RuntimeError("Configurações do Active Directory não foram informadas no .env.")
    try:
        from ldap3 import ALL, Connection, Server
    except Exception as exc:
        raise RuntimeError("Biblioteca ldap3 não está instalada.") from exc

    server = Server(settings.AD_SERVER, get_info=ALL)
    conn = Connection(server, user=settings.AD_USER, password=settings.AD_PASSWORD, auto_bind=True)
    conn.search(
        settings.AD_BASE_DN,
        settings.AD_COMPUTERS_FILTER,
        attributes=["cn", "dNSHostName", "operatingSystem", "description"],
    )
    descobertos = []
    for entry in conn.entries:
        hostname = str(getattr(entry, "dNSHostName", "") or getattr(entry, "cn", ""))
        nome = str(getattr(entry, "cn", "") or hostname)
        descobertos.append(
            DescobertaAtivo(
                nome=nome,
                hostname=hostname,
                sistema_operacional=str(getattr(entry, "operatingSystem", "")),
                origem=AtivoRede.Origem.AD,
                observacoes=str(getattr(entry, "description", "")),
            )
        )
    conn.unbind()
    return descobertos
