import ipaddress
import asyncio
import platform
import shutil
import socket
import subprocess
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from .models import (
    AtivoRede,
    HistoricoAlteracaoAtivo,
    InterfaceRede,
    MetodoDescoberta,
    RegistroColetaAgente,
    TipoAtivo,
)


@dataclass
class DescobertaAtivo:
    ip: str = ""
    nome: str = ""
    hostname: str = ""
    fabricante: str = ""
    modelo: str = ""
    numero_serie: str = ""
    mac: str = ""
    sistema_operacional: str = ""
    localizacao: str = ""
    origem: str = AtivoRede.Origem.MANUAL
    observacoes: str = ""
    interfaces: list = None

    def __post_init__(self):
        if self.interfaces is None:
            self.interfaces = []


class ColetaAgenteErro(Exception):
    def __init__(self, mensagem, status=400):
        self.mensagem = mensagem
        self.status = status
        super().__init__(mensagem)


def normalizar_texto(valor, limite=250):
    if valor is None:
        return ""
    return str(valor).strip()[:limite]


def identificador_valido(valor):
    normalizado = (valor or "").strip().lower()
    invalidos = {
        "",
        "none",
        "unknown",
        "default string",
        "to be filled by o.e.m.",
        "to be filled by oem",
        "system serial number",
        "00000000",
        "000000000000",
    }
    return normalizado not in invalidos


def decimal_ou_none(valor):
    try:
        if valor in ("", None):
            return None
        return round(float(valor), 2)
    except (TypeError, ValueError):
        return None


def localizar_ativo_por_identidade(serial="", mac="", hostname="", ip=None):
    if identificador_valido(serial):
        ativo = AtivoRede.objects.filter(numero_serie__iexact=serial).order_by("id").first()
        if ativo:
            return ativo
    if identificador_valido(mac) and mac.replace(":", "").replace("-", "") != "000000000000":
        ativo = AtivoRede.objects.filter(mac__iexact=mac).order_by("id").first()
        if ativo:
            return ativo
    if identificador_valido(hostname):
        ativo = AtivoRede.objects.filter(
            Q(hostname__iexact=hostname) | Q(nome__iexact=hostname)
        ).order_by("id").first()
        if ativo:
            return ativo
    if not ip:
        return None

    candidato = AtivoRede.objects.filter(ip=ip).order_by("id").first()
    if not candidato:
        return None
    conflitos = [
        (
            identificador_valido(serial)
            and identificador_valido(candidato.numero_serie)
            and serial.lower() != candidato.numero_serie.lower()
        ),
        (
            identificador_valido(mac)
            and identificador_valido(candidato.mac)
            and mac.lower() != candidato.mac.lower()
        ),
        (
            identificador_valido(hostname)
            and identificador_valido(candidato.hostname)
            and hostname.lower() != candidato.hostname.lower()
        ),
    ]
    return None if any(conflitos) else candidato


def registrar_alteracoes_ativo(ativo, antes, campos, origem):
    alteracoes = []
    for campo in campos:
        anterior = antes.get(campo)
        novo = getattr(ativo, campo)
        if str(anterior or "") != str(novo or ""):
            alteracoes.append(
                HistoricoAlteracaoAtivo(
                    ativo=ativo,
                    campo=campo,
                    valor_anterior=str(anterior or ""),
                    valor_novo=str(novo or ""),
                    origem=origem,
                )
            )
    if alteracoes:
        HistoricoAlteracaoAtivo.objects.bulk_create(alteracoes)


def _softwares_para_texto(softwares):
    if isinstance(softwares, list):
        return "\n".join(
            normalizar_texto(item, 220)
            for item in softwares
            if normalizar_texto(item, 220)
        )
    return normalizar_texto(softwares, 12000)


def _resumo_interfaces(interfaces):
    interfaces_txt = []
    for interface in interfaces[:10]:
        interfaces_txt.append(
            " / ".join(
                parte
                for parte in [
                    normalizar_texto(interface.get("nome"), 80),
                    normalizar_texto(interface.get("ip"), 45),
                    normalizar_texto(interface.get("mac"), 30),
                ]
                if parte
            )
        )
    return interfaces_txt


def _sincronizar_interfaces(ativo, interfaces):
    for interface in interfaces[:20]:
        nome_interface = normalizar_texto(interface.get("nome"), 120)
        mac_interface = normalizar_texto(interface.get("mac"), 30)
        ip_interface = normalizar_texto(interface.get("ip"), 45) or None
        if not nome_interface and not mac_interface and not ip_interface:
            continue
        filtro_interface = {"ativo": ativo}
        if mac_interface:
            filtro_interface["mac__iexact"] = mac_interface
        elif nome_interface:
            filtro_interface["nome__iexact"] = nome_interface
        else:
            filtro_interface["ip"] = ip_interface

        registro = InterfaceRede.objects.filter(**filtro_interface).first()
        if not registro:
            registro = InterfaceRede(ativo=ativo)
        registro.nome = nome_interface or registro.nome or "Interface"
        registro.mac = mac_interface or registro.mac
        registro.ip = ip_interface or registro.ip
        registro.status = normalizar_texto(interface.get("status"), 80) or registro.status
        registro.velocidade = normalizar_texto(interface.get("velocidade"), 80) or registro.velocidade
        registro.save()


def processar_coleta_agente(dados, ip_origem=None):
    hostname = normalizar_texto(dados.get("hostname"), 150)
    ip = normalizar_texto(dados.get("ip"), 45) or None
    serial = normalizar_texto(dados.get("numero_serie") or dados.get("serial"), 120)
    mac = normalizar_texto(dados.get("mac"), 30)
    if not identificador_valido(serial):
        serial = ""

    if not any([hostname, ip, serial, mac]):
        RegistroColetaAgente.objects.create(
            hostname=hostname,
            status=RegistroColetaAgente.Status.ERRO,
            mensagem="Coleta sem identificador valido.",
            ip_origem=ip_origem,
        )
        raise ColetaAgenteErro("Informe hostname, IP, serial ou MAC.")

    tipo_padrao, _ = TipoAtivo.objects.get_or_create(nome="Computador")
    ativo = localizar_ativo_por_identidade(serial=serial, mac=mac, hostname=hostname, ip=ip)
    criado = ativo is None
    if criado:
        ativo = AtivoRede(tipo=tipo_padrao)

    campos_monitorados = [
        "nome",
        "hostname",
        "ip",
        "mac",
        "fabricante",
        "modelo",
        "numero_serie",
        "sistema_operacional",
        "processador",
        "memoria_total_gb",
        "disco_total_gb",
        "office",
        "softwares_instalados",
        "usuario_logado",
        "dominio",
        "status",
    ]
    antes = {campo: getattr(ativo, campo, "") for campo in campos_monitorados}

    interfaces = dados.get("interfaces") or []
    if not isinstance(interfaces, list):
        interfaces = []
    interfaces_txt = _resumo_interfaces(interfaces)
    observacoes = [
        "Coleta recebida pelo agente de inventario.",
        f"Usuario logado: {normalizar_texto(dados.get('usuario_logado'), 120) or '-'}",
        f"Dominio/grupo: {normalizar_texto(dados.get('dominio'), 120) or '-'}",
        f"CPU: {normalizar_texto(dados.get('processador'), 180) or '-'}",
        f"Memoria: {normalizar_texto(dados.get('memoria_total_gb'), 40) or '-'} GB",
        f"Disco: {normalizar_texto(dados.get('disco_total_gb'), 40) or '-'} GB",
        f"Office: {normalizar_texto(dados.get('office'), 180) or '-'}",
    ]
    if interfaces_txt:
        observacoes.append("Interfaces: " + " | ".join(interfaces_txt))

    ativo.nome = hostname or ativo.nome or f"Ativo {ip or serial or mac}"
    ativo.hostname = hostname or ativo.hostname
    ativo.ip = ip or ativo.ip
    ativo.mac = mac or ativo.mac
    ativo.fabricante = normalizar_texto(dados.get("fabricante"), 120) or ativo.fabricante
    ativo.modelo = normalizar_texto(dados.get("modelo"), 120) or ativo.modelo
    ativo.numero_serie = serial or ativo.numero_serie
    ativo.sistema_operacional = normalizar_texto(dados.get("sistema_operacional"), 150) or ativo.sistema_operacional
    ativo.arquitetura = normalizar_texto(dados.get("arquitetura"), 40) or ativo.arquitetura
    ativo.processador = normalizar_texto(dados.get("processador"), 180) or ativo.processador
    ativo.memoria_total_gb = decimal_ou_none(dados.get("memoria_total_gb")) or ativo.memoria_total_gb
    ativo.disco_total_gb = decimal_ou_none(dados.get("disco_total_gb")) or ativo.disco_total_gb
    ativo.office = normalizar_texto(dados.get("office"), 180) or ativo.office
    ativo.softwares_instalados = _softwares_para_texto(dados.get("softwares_instalados") or []) or ativo.softwares_instalados
    ativo.usuario_logado = normalizar_texto(dados.get("usuario_logado"), 150) or ativo.usuario_logado
    ativo.dominio = normalizar_texto(dados.get("dominio"), 150) or ativo.dominio
    ativo.responsavel = normalizar_texto(dados.get("usuario_logado"), 150) or ativo.responsavel
    estava_arquivado = ativo.status == AtivoRede.Status.DESATIVADO
    ativo.status = AtivoRede.Status.ONLINE
    if estava_arquivado:
        ativo.ciclo_vida = AtivoRede.CicloVida.EM_USO
        ativo.data_baixa = None
        ativo.motivo_baixa = ""
    ativo.origem = AtivoRede.Origem.AGENTE
    ativo.observacoes = "\n".join(observacoes)
    ativo.ultima_coleta_em = timezone.now()
    ativo.coleta_solicitada_em = None
    ativo.save()

    registrar_alteracoes_ativo(ativo, antes, campos_monitorados, "agente")
    RegistroColetaAgente.objects.create(
        ativo=ativo,
        hostname=hostname,
        status=RegistroColetaAgente.Status.SUCESSO,
        mensagem="Inventario recebido e processado.",
        ip_origem=ip_origem,
        versao_agente=normalizar_texto(dados.get("versao_agente"), 40),
    )
    _sincronizar_interfaces(ativo, interfaces)

    return {
        "ok": True,
        "criado": criado,
        "ativo_id": ativo.pk,
        "ativo": ativo.nome,
        "ultima_coleta_em": ativo.ultima_coleta_em.isoformat(),
    }


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
    snmp = consultar_snmp_basico(ip_texto, faixa.credencial_snmp)
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
        fabricante=snmp.get("fabricante", "") if snmp else "",
        modelo=snmp.get("modelo", "") if snmp else "",
        numero_serie=snmp.get("numero_serie", "") if snmp else "",
        mac=snmp.get("mac", "") if snmp else "",
        localizacao=snmp.get("localizacao", "") if snmp else "",
        origem=origem,
        observacoes=observacoes,
        interfaces=snmp.get("interfaces", []) if snmp else [],
    )


def _dados_credencial_snmp(credencial):
    if not credencial:
        return "", "2c"
    if isinstance(credencial, str):
        return credencial, "2c"
    return getattr(credencial, "community", "") or "", getattr(credencial, "versao", "2c") or "2c"


def _mp_model_snmp(versao):
    return 0 if str(versao) == "1" else 1


def consultar_snmp_basico(ip, credencial):
    community, versao = _dados_credencial_snmp(credencial)
    if not community:
        return None
    dados = _consultar_snmp_basico_atual(ip, community, versao)
    if dados:
        return dados
    return _consultar_snmp_basico_legado(ip, community, versao)


def _status_interface(valor):
    return {
        "1": "up",
        "2": "down",
        "3": "testing",
        "4": "unknown",
        "5": "dormant",
        "6": "notPresent",
        "7": "lowerLayerDown",
    }.get(str(valor), str(valor))


def _formatar_mac(valor):
    if not valor:
        return ""
    try:
        octetos = valor.asOctets()
        return ":".join(f"{octeto:02X}" for octeto in octetos) if octetos else ""
    except Exception:
        texto = str(valor).strip()
        if texto.startswith("0x") and len(texto) > 2:
            hex_texto = texto[2:]
            return ":".join(hex_texto[i : i + 2].upper() for i in range(0, len(hex_texto), 2))
        return texto


def _inferir_fabricante_modelo(descricao, sys_object_id=""):
    texto = (descricao or "").strip()
    texto_lower = texto.lower()
    fabricantes = [
        "Cisco",
        "HP",
        "HPE",
        "Aruba",
        "Ubiquiti",
        "MikroTik",
        "Dell",
        "D-Link",
        "TP-Link",
        "Intelbras",
        "Epson",
        "Brother",
        "Canon",
        "Lexmark",
        "Zebra",
        "Kyocera",
    ]
    fabricante = next((nome for nome in fabricantes if nome.lower() in texto_lower), "")
    modelo = ""
    if texto:
        primeira_linha = texto.splitlines()[0]
        partes = [parte.strip() for parte in primeira_linha.replace(",", " ").split() if parte.strip()]
        if fabricante and fabricante in partes:
            indice = partes.index(fabricante)
            modelo = " ".join(partes[indice + 1 : indice + 4])
        elif partes:
            modelo = " ".join(partes[:4])
    if not modelo and sys_object_id:
        modelo = f"OID {sys_object_id}"
    return fabricante, modelo[:120]


async def _snmp_get_async(ip, community, versao, *oids):
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
            CommunityData(community, mpModel=_mp_model_snmp(versao)),
            await UdpTransportTarget.create((str(ip), 161), timeout=1, retries=0),
            *[ObjectType(ObjectIdentity(oid)) for oid in oids],
        )
    finally:
        close = getattr(dispatcher, "close_dispatcher", None)
        if close:
            close()
    if erro or status:
        return {}
    return {oid: valor for oid, (_, valor) in zip(oids, var_binds)}


async def _snmp_walk_async(ip, community, versao, oid_raiz, limite=128):
    from pysnmp.hlapi.v1arch.asyncio import (
        CommunityData,
        ObjectIdentity,
        ObjectType,
        SnmpDispatcher,
        UdpTransportTarget,
        walk_cmd,
    )

    dispatcher = SnmpDispatcher()
    itens = []
    try:
        async for erro, status, _, var_binds in walk_cmd(
            dispatcher,
            CommunityData(community, mpModel=_mp_model_snmp(versao)),
            await UdpTransportTarget.create((str(ip), 161), timeout=1, retries=0),
            ObjectType(ObjectIdentity(oid_raiz)),
            lexicographicMode=False,
        ):
            if erro or status:
                break
            for nome, valor in var_binds:
                itens.append((str(nome), valor))
                if len(itens) >= limite:
                    return itens
    finally:
        close = getattr(dispatcher, "close_dispatcher", None)
        if close:
            close()
    return itens


def _indice_oid(nome):
    return str(nome).rsplit(".", 1)[-1]


async def _consultar_snmp_basico_async(ip, community, versao):
    valores = await _snmp_get_async(
        ip,
        community,
        versao,
        "1.3.6.1.2.1.1.5.0",
        "1.3.6.1.2.1.1.1.0",
        "1.3.6.1.2.1.1.2.0",
        "1.3.6.1.2.1.1.6.0",
    )
    if not valores:
        return None

    hostname = str(valores.get("1.3.6.1.2.1.1.5.0", "")).strip()
    descricao = str(valores.get("1.3.6.1.2.1.1.1.0", "")).strip()
    sys_object_id = str(valores.get("1.3.6.1.2.1.1.2.0", "")).strip()
    localizacao = str(valores.get("1.3.6.1.2.1.1.6.0", "")).strip()
    fabricante, modelo = _inferir_fabricante_modelo(descricao, sys_object_id)

    descricoes = {_indice_oid(nome): str(valor) for nome, valor in await _snmp_walk_async(ip, community, versao, "1.3.6.1.2.1.2.2.1.2")}
    velocidades = {_indice_oid(nome): str(valor) for nome, valor in await _snmp_walk_async(ip, community, versao, "1.3.6.1.2.1.2.2.1.5")}
    macs = {_indice_oid(nome): _formatar_mac(valor) for nome, valor in await _snmp_walk_async(ip, community, versao, "1.3.6.1.2.1.2.2.1.6")}
    oper_status = {_indice_oid(nome): _status_interface(valor) for nome, valor in await _snmp_walk_async(ip, community, versao, "1.3.6.1.2.1.2.2.1.8")}

    interfaces = []
    for indice, descricao_interface in descricoes.items():
        if not descricao_interface:
            continue
        interfaces.append(
            {
                "nome": descricao_interface[:120],
                "descricao": descricao_interface[:250],
                "mac": macs.get(indice, ""),
                "velocidade": velocidades.get(indice, ""),
                "status": oper_status.get(indice, ""),
            }
        )

    return {
        "hostname": hostname,
        "descricao": descricao,
        "fabricante": fabricante,
        "modelo": modelo,
        "mac": next((item["mac"] for item in interfaces if item.get("mac")), ""),
        "localizacao": localizacao,
        "interfaces": interfaces,
    }


def _consultar_snmp_basico_atual(ip, community, versao):
    try:
        return asyncio.run(_consultar_snmp_basico_async(ip, community, versao))
    except Exception:
        return None


def _consultar_snmp_basico_legado(ip, community, versao):
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
            CommunityData(community, mpModel=_mp_model_snmp(versao)),
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
        dados = consultar_snmp_basico(ip_texto, credencial_snmp)
        if dados:
            return DescobertaAtivo(
                ip=ip_texto,
                nome=dados.get("hostname") or f"Dispositivo SNMP {ip_texto}",
                hostname=dados.get("hostname", ""),
                fabricante=dados.get("fabricante", ""),
                modelo=dados.get("modelo", ""),
                numero_serie=dados.get("numero_serie", ""),
                mac=dados.get("mac", ""),
                localizacao=dados.get("localizacao", ""),
                origem=AtivoRede.Origem.SNMP,
                observacoes=f"SNMP sysDescr: {dados.get('descricao', '')}",
                interfaces=dados.get("interfaces", []),
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
            dados = consultar_snmp_basico(ip_texto, faixa.credencial_snmp)
            if dados:
                descobertos.append(
                    DescobertaAtivo(
                        ip=ip_texto,
                        nome=dados.get("hostname") or f"Dispositivo SNMP {ip_texto}",
                        hostname=dados.get("hostname", ""),
                        fabricante=dados.get("fabricante", ""),
                        modelo=dados.get("modelo", ""),
                        numero_serie=dados.get("numero_serie", ""),
                        mac=dados.get("mac", ""),
                        localizacao=dados.get("localizacao", ""),
                        origem=AtivoRede.Origem.SNMP,
                        observacoes=f"SNMP sysDescr: {dados.get('descricao', '')}",
                        interfaces=dados.get("interfaces", []),
                    )
                )
    return descobertos


def descobrir_ad():
    from core.models import ConfiguracaoLDAP

    configuracao = ConfiguracaoLDAP.atual()
    if configuracao.ativo:
        servidor_ldap = configuracao.servidor
        porta = configuracao.porta
        usar_ssl = configuracao.usar_ssl
        usuario = configuracao.usuario_bind
        senha = configuracao.obter_senha()
        base_dn = configuracao.base_dn
        filtro = configuracao.filtro_computadores
    else:
        servidor_ldap = settings.AD_SERVER
        porta = 389
        usar_ssl = False
        usuario = settings.AD_USER
        senha = settings.AD_PASSWORD
        base_dn = settings.AD_BASE_DN
        filtro = settings.AD_COMPUTERS_FILTER
    if not all([servidor_ldap, usuario, senha, base_dn]):
        raise RuntimeError("Configurações do Active Directory não foram informadas no .env.")
    try:
        from ldap3 import ALL, Connection, Server
    except Exception as exc:
        raise RuntimeError("Biblioteca ldap3 não está instalada.") from exc

    server = Server(servidor_ldap, port=porta, use_ssl=usar_ssl, get_info=ALL)
    conn = Connection(server, user=usuario, password=senha, auto_bind=True)
    conn.search(
        base_dn,
        filtro,
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
