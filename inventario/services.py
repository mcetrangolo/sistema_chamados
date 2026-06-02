import ipaddress
import platform
import socket
import subprocess
from dataclasses import dataclass

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
    resultado = subprocess.run(
        ["ping", parametro, "1", timeout_param, timeout_value, str(ip)],
        capture_output=True,
        text=True,
        timeout=max(2, timeout_ms // 1000 + 1),
    )
    return resultado.returncode == 0


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


def consultar_snmp_basico(ip, community):
    if not community:
        return None
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
    except Exception:
        return None

    try:
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


def descobrir_por_faixa(faixa, metodo, portas=""):
    if metodo == MetodoDescoberta.Codigo.AD:
        return descobrir_ad()

    descobertos = []
    portas_lista = [p.strip() for p in portas.split(",") if p.strip()]

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
