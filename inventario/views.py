import csv
import io
import ipaddress
import json
import socket
from html import escape
from zipfile import ZIP_DEFLATED, ZipFile

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Sum
from django.http import FileResponse, Http404, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView
from core.models import ConfiguracaoInstitucional
from governanca.pdf import montar_pdf

from .forms import (
    AtivoRedeForm,
    AgendamentoVarreduraForm,
    AnexoLicencaSoftwareForm,
    CredencialSNMPForm,
    FaixaRedeForm,
    ImportacaoAtivosCSVForm,
    LicencaSoftwareForm,
    OcorrenciaAtivoForm,
    RelacionamentoAtivoForm,
    RelatorioInventarioForm,
    TipoAtivoForm,
    VarreduraRedeForm,
)
from .models import (
    AgendamentoVarredura,
    AnexoLicencaSoftware,
    AtivoRede,
    CredencialSNMP,
    FaixaRede,
    InterfaceRede,
    LicencaSoftware,
    HistoricoAlteracaoAtivo,
    MetodoDescoberta,
    OcorrenciaAtivo,
    RelacionamentoAtivo,
    TipoAtivo,
    VarreduraRede,
)
from .services import descobrir_por_faixa, descobrir_por_host, ping_host


AGENTE_WINDOWS_EXE = "SistemaChamadosAgentSetup.exe"
AGENTE_WINDOWS_ZIP = "SistemaChamadosAgentSource.zip"
AGENTE_LINUX_INSTALLER = "install.sh"


def _caminho_agente_windows():
    candidatos = [
        settings.BASE_DIR / "releases" / "agents" / "windows" / AGENTE_WINDOWS_EXE,
        settings.BASE_DIR / "dist" / AGENTE_WINDOWS_EXE,
    ]
    for caminho in candidatos:
        caminho = caminho.resolve()
        if caminho.exists():
            return caminho
    return candidatos[0].resolve()


def _caminho_pacote_windows_zip():
    return (settings.BASE_DIR / "releases" / "agents" / "windows" / AGENTE_WINDOWS_ZIP).resolve()


def _arquivos_pacote_windows_zip():
    base_windows = (settings.BASE_DIR / "scripts" / "agent" / "windows").resolve()
    return {
        "agent.ps1": base_windows / "agent.ps1",
        "install.ps1": base_windows / "install.ps1",
        "install_gui.ps1": base_windows / "install_gui.ps1",
        "uninstall.ps1": base_windows / "uninstall.ps1",
        "README.md": base_windows / "README.md",
    }


def _ips_rede_local():
    ips = []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if ip and not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    return ips


def _normalizar_texto(valor, limite=250):
    if valor is None:
        return ""
    return str(valor).strip()[:limite]


def _base_url_agente(request):
    url_detectada = request.build_absolute_uri("/").rstrip("/")
    return settings.PUBLIC_BASE_URL or url_detectada


def _decimal_ou_none(valor):
    try:
        if valor in ("", None):
            return None
        return round(float(valor), 2)
    except (TypeError, ValueError):
        return None


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


@login_required
def baixar_agente_windows(request):
    caminho = _caminho_agente_windows()
    bases_permitidas = [
        (settings.BASE_DIR / "releases" / "agents" / "windows").resolve(),
        (settings.BASE_DIR / "dist").resolve(),
    ]
    if not any(str(caminho).startswith(str(base)) for base in bases_permitidas) or not caminho.exists():
        raise Http404(
            "Instalador do agente nao encontrado. Gere o arquivo com scripts/agent/windows/build_installer.ps1."
        )
    return FileResponse(
        caminho.open("rb"),
        as_attachment=True,
        filename=AGENTE_WINDOWS_EXE,
        content_type="application/vnd.microsoft.portable-executable",
    )


@login_required
def baixar_agente_windows_zip(request):
    arquivos = _arquivos_pacote_windows_zip()
    faltantes = [nome for nome, caminho in arquivos.items() if not caminho.exists()]
    if faltantes:
        raise Http404(f"Arquivos do agente Windows nao encontrados: {', '.join(faltantes)}.")

    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as zipf:
        for nome, caminho in arquivos.items():
            conteudo = caminho.read_text(encoding="utf-8")
            if nome in {"install.ps1", "install_gui.ps1"}:
                token = settings.INVENTARIO_AGENT_TOKEN.replace("\\", "\\\\").replace('"', '\\"')
                conteudo = conteudo.replace(
                    '[string]$Token = "sistema-chamados-agent-local"',
                    f'[string]$Token = "{token}"',
                )
            zipf.writestr(nome, conteudo)
        zipf.writestr(
            "InstalarAgente.cmd",
            '@echo off\r\n'
            'cd /d "%~dp0"\r\n'
            'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_gui.ps1"\r\n'
            "pause\r\n",
        )
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{AGENTE_WINDOWS_ZIP}"'
    return response


@login_required
def baixar_agente_linux(request):
    caminho = (settings.BASE_DIR / "scripts" / "agent" / "linux" / AGENTE_LINUX_INSTALLER).resolve()
    base_linux = (settings.BASE_DIR / "scripts" / "agent" / "linux").resolve()
    if not str(caminho).startswith(str(base_linux)) or not caminho.exists():
        raise Http404("Instalador Linux do agente nao encontrado.")
    conteudo = caminho.read_text(encoding="utf-8")
    conteudo = conteudo.replace("__AGENT_TOKEN_DEFAULT__", settings.INVENTARIO_AGENT_TOKEN)
    conteudo = conteudo.replace("__SERVER_URL_DEFAULT__", _base_url_agente(request))
    response = HttpResponse(conteudo, content_type="text/x-shellscript; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="sistema-chamados-agent-linux.sh"'
    return response


@login_required
@user_passes_test(lambda user: user.is_superuser)
def configuracao_agente(request):
    caminho = _caminho_agente_windows()
    url_detectada = request.build_absolute_uri("/").rstrip("/")
    base_url = _base_url_agente(request)
    porta = request.get_port()
    esquema = "https" if request.is_secure() else "http"
    ips_rede = _ips_rede_local()
    bases_sugeridas = [f"{esquema}://{ip}:{porta}" for ip in ips_rede]
    usa_endereco_local = "localhost" in base_url.lower() or "127.0.0.1" in base_url
    endpoint = f"{base_url}/inventario/agente/coleta/"
    download_url = f"{base_url}/inventario/agente/windows/download/"
    windows_zip_download_url = f"{base_url}/inventario/agente/windows/source.zip"
    linux_download_url = f"{base_url}/inventario/agente/linux/download/"
    arquivos_zip = _arquivos_pacote_windows_zip()
    zip_pronto = all(caminho.exists() for caminho in arquivos_zip.values())
    contexto = {
        "token": settings.INVENTARIO_AGENT_TOKEN,
        "endpoint": endpoint,
        "download_url": download_url,
        "windows_zip_download_url": windows_zip_download_url,
        "linux_download_url": linux_download_url,
        "url_detectada": url_detectada,
        "public_base_url": settings.PUBLIC_BASE_URL,
        "bases_sugeridas": bases_sugeridas,
        "usa_endereco_local": usa_endereco_local,
        "instalador_existe": caminho.exists(),
        "instalador_nome": AGENTE_WINDOWS_EXE,
        "instalador_tamanho": caminho.stat().st_size if caminho.exists() else None,
        "instalador_atualizado_em": timezone.datetime.fromtimestamp(
            caminho.stat().st_mtime,
            tz=timezone.get_current_timezone(),
        )
        if caminho.exists()
        else None,
        "windows_zip_existe": zip_pronto,
        "windows_zip_nome": AGENTE_WINDOWS_ZIP,
        "windows_zip_tamanho": None,
    }
    return TemplateView.as_view(template_name="inventario/agente_config.html")(request, **contexto)


@csrf_exempt
@require_POST
def receber_coleta_agente(request):
    token_configurado = settings.INVENTARIO_AGENT_TOKEN
    token_recebido = request.headers.get("Authorization", "").replace("Bearer ", "", 1).strip()
    if not token_configurado or token_recebido != token_configurado:
        return JsonResponse({"erro": "Token invalido ou nao configurado."}, status=403)

    try:
        dados = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"erro": "JSON invalido."}, status=400)

    hostname = _normalizar_texto(dados.get("hostname"), 150)
    ip = _normalizar_texto(dados.get("ip"), 45) or None
    serial = _normalizar_texto(dados.get("numero_serie") or dados.get("serial"), 120)
    mac = _normalizar_texto(dados.get("mac"), 30)

    if not any([hostname, ip, serial, mac]):
        return JsonResponse({"erro": "Informe hostname, IP, serial ou MAC."}, status=400)

    tipo_padrao, _ = TipoAtivo.objects.get_or_create(nome="Computador")
    filtros = []
    if serial:
        filtros.append(Q(numero_serie__iexact=serial))
    if hostname:
        filtros.append(Q(hostname__iexact=hostname) | Q(nome__iexact=hostname))
    if ip:
        filtros.append(Q(ip=ip))
    if mac:
        filtros.append(Q(mac__iexact=mac))

    consulta = filtros[0]
    for filtro in filtros[1:]:
        consulta |= filtro

    ativo = AtivoRede.objects.filter(consulta).order_by("id").first()
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
    interfaces_txt = []
    for interface in interfaces[:10]:
        interfaces_txt.append(
            " / ".join(
                parte
                for parte in [
                    _normalizar_texto(interface.get("nome"), 80),
                    _normalizar_texto(interface.get("ip"), 45),
                    _normalizar_texto(interface.get("mac"), 30),
                ]
                if parte
            )
        )

    observacoes = [
        "Coleta recebida pelo agente de inventario.",
        f"Usuario logado: {_normalizar_texto(dados.get('usuario_logado'), 120) or '-'}",
        f"Dominio/grupo: {_normalizar_texto(dados.get('dominio'), 120) or '-'}",
        f"CPU: {_normalizar_texto(dados.get('processador'), 180) or '-'}",
        f"Memoria: {_normalizar_texto(dados.get('memoria_total_gb'), 40) or '-'} GB",
        f"Disco: {_normalizar_texto(dados.get('disco_total_gb'), 40) or '-'} GB",
        f"Office: {_normalizar_texto(dados.get('office'), 180) or '-'}",
    ]
    if interfaces_txt:
        observacoes.append("Interfaces: " + " | ".join(interfaces_txt))

    softwares = dados.get("softwares_instalados") or []
    if isinstance(softwares, list):
        softwares_texto = "\n".join(_normalizar_texto(item, 220) for item in softwares if _normalizar_texto(item, 220))
    else:
        softwares_texto = _normalizar_texto(softwares, 12000)

    ativo.nome = hostname or ativo.nome or f"Ativo {ip or serial or mac}"
    ativo.hostname = hostname or ativo.hostname
    ativo.ip = ip or ativo.ip
    ativo.mac = mac or ativo.mac
    ativo.fabricante = _normalizar_texto(dados.get("fabricante"), 120) or ativo.fabricante
    ativo.modelo = _normalizar_texto(dados.get("modelo"), 120) or ativo.modelo
    ativo.numero_serie = serial or ativo.numero_serie
    ativo.sistema_operacional = _normalizar_texto(dados.get("sistema_operacional"), 150) or ativo.sistema_operacional
    ativo.arquitetura = _normalizar_texto(dados.get("arquitetura"), 40) or ativo.arquitetura
    ativo.processador = _normalizar_texto(dados.get("processador"), 180) or ativo.processador
    ativo.memoria_total_gb = _decimal_ou_none(dados.get("memoria_total_gb")) or ativo.memoria_total_gb
    ativo.disco_total_gb = _decimal_ou_none(dados.get("disco_total_gb")) or ativo.disco_total_gb
    ativo.office = _normalizar_texto(dados.get("office"), 180) or ativo.office
    ativo.softwares_instalados = softwares_texto or ativo.softwares_instalados
    ativo.usuario_logado = _normalizar_texto(dados.get("usuario_logado"), 150) or ativo.usuario_logado
    ativo.dominio = _normalizar_texto(dados.get("dominio"), 150) or ativo.dominio
    ativo.responsavel = _normalizar_texto(dados.get("usuario_logado"), 150) or ativo.responsavel
    ativo.status = AtivoRede.Status.ONLINE
    ativo.origem = AtivoRede.Origem.AGENTE
    ativo.observacoes = "\n".join(observacoes)
    ativo.ultima_coleta_em = timezone.now()
    ativo.save()
    registrar_alteracoes_ativo(ativo, antes, campos_monitorados, "agente")

    for interface in interfaces[:20]:
        nome_interface = _normalizar_texto(interface.get("nome"), 120)
        mac_interface = _normalizar_texto(interface.get("mac"), 30)
        ip_interface = _normalizar_texto(interface.get("ip"), 45) or None
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
        registro.status = _normalizar_texto(interface.get("status"), 80) or registro.status
        registro.velocidade = _normalizar_texto(interface.get("velocidade"), 80) or registro.velocidade
        registro.save()

    return JsonResponse(
        {
            "ok": True,
            "criado": criado,
            "ativo_id": ativo.pk,
            "ativo": ativo.nome,
            "ultima_coleta_em": ativo.ultima_coleta_em.isoformat(),
        }
    )


class InventarioPainelView(LoginRequiredMixin, TemplateView):
    template_name = "inventario/painel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ativos = AtivoRede.objects.select_related("tipo", "setor")
        context["contadores"] = {
            "total": ativos.count(),
            "online": ativos.filter(status=AtivoRede.Status.ONLINE).count(),
            "offline": ativos.filter(status=AtivoRede.Status.OFFLINE).count(),
            "snmp": ativos.filter(origem=AtivoRede.Origem.SNMP).count(),
            "licencas": LicencaSoftware.objects.count(),
            "relacoes": RelacionamentoAtivo.objects.count(),
        }
        context["por_tipo"] = ativos.values("tipo__nome").annotate(total=Count("id")).order_by("tipo__nome")
        context["ultimos_ativos"] = ativos.order_by("-atualizado_em")[:10]
        context["ultimas_varreduras"] = VarreduraRede.objects.select_related("faixa")[:5]
        return context


class AtivoRedeListView(LoginRequiredMixin, ListView):
    model = AtivoRede
    template_name = "inventario/ativo_list.html"
    context_object_name = "ativos"
    paginate_by = 20

    def get_queryset(self):
        queryset = AtivoRede.objects.select_related("tipo", "setor")
        q = self.request.GET.get("q", "").strip()
        tipo = self.request.GET.get("tipo", "")
        status = self.request.GET.get("status", "")
        if q:
            queryset = queryset.filter(
                Q(nome__icontains=q)
                | Q(ip__icontains=q)
                | Q(mac__icontains=q)
                | Q(hostname__icontains=q)
                | Q(modelo__icontains=q)
                | Q(numero_serie__icontains=q)
                | Q(sistema_operacional__icontains=q)
            )
        if tipo:
            queryset = queryset.filter(tipo_id=tipo)
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tipos"] = TipoAtivo.objects.filter(ativo=True)
        context["status_choices"] = AtivoRede.Status.choices
        context["filtros"] = self.request.GET
        return context


def filtrar_ativos_relatorio(params):
    form = RelatorioInventarioForm(params or None)
    ativos = AtivoRede.objects.select_related("tipo", "setor").order_by("nome")
    filtro_aplicado = False
    if form.is_valid():
        dados = form.cleaned_data
        filtro_aplicado = any(valor for valor in dados.values())
        if dados.get("q"):
            q = dados["q"].strip()
            ativos = ativos.filter(
                Q(nome__icontains=q)
                | Q(ip__icontains=q)
                | Q(mac__icontains=q)
                | Q(hostname__icontains=q)
                | Q(modelo__icontains=q)
                | Q(numero_serie__icontains=q)
            )
        if dados.get("data_inicio"):
            ativos = ativos.filter(ultima_coleta_em__date__gte=dados["data_inicio"])
        if dados.get("data_fim"):
            ativos = ativos.filter(ultima_coleta_em__date__lte=dados["data_fim"])
        if dados.get("tipo"):
            ativos = ativos.filter(tipo=dados["tipo"])
        if dados.get("setor"):
            ativos = ativos.filter(setor=dados["setor"])
        if dados.get("status"):
            ativos = ativos.filter(status=dados["status"])
        if dados.get("origem"):
            ativos = ativos.filter(origem=dados["origem"])
        if dados.get("familia_so") == "windows":
            ativos = ativos.filter(sistema_operacional__icontains="windows")
        elif dados.get("familia_so") == "linux":
            ativos = ativos.filter(
                Q(sistema_operacional__icontains="linux")
                | Q(sistema_operacional__icontains="ubuntu")
                | Q(sistema_operacional__icontains="debian")
                | Q(sistema_operacional__icontains="centos")
                | Q(sistema_operacional__icontains="red hat")
            )
        elif dados.get("familia_so") == "macos":
            ativos = ativos.filter(
                Q(sistema_operacional__icontains="macos")
                | Q(sistema_operacional__icontains="mac os")
                | Q(sistema_operacional__icontains="darwin")
            )
        if dados.get("sistema_operacional"):
            ativos = ativos.filter(sistema_operacional=dados["sistema_operacional"])
        if dados.get("fabricante"):
            ativos = ativos.filter(fabricante=dados["fabricante"])
        if dados.get("modelo"):
            ativos = ativos.filter(modelo__icontains=dados["modelo"].strip())
        if dados.get("software"):
            ativos = ativos.filter(softwares_instalados__icontains=dados["software"].strip())
        if dados.get("coleta") == "com":
            ativos = ativos.filter(ultima_coleta_em__isnull=False)
        elif dados.get("coleta") == "sem":
            ativos = ativos.filter(ultima_coleta_em__isnull=True)
    return form, ativos, filtro_aplicado


def dados_relatorio_inventario(ativos, filtro_aplicado=False):
    licencas = LicencaSoftware.objects.prefetch_related("ativos")
    if filtro_aplicado:
        licencas = licencas.filter(ativos__in=ativos).distinct()
    total_licencas = licencas.count()
    total_posicoes = licencas.aggregate(total=Sum("quantidade_total"))["total"] or 0
    licencas_lista = []
    total_em_uso = 0
    for licenca in licencas:
        em_uso = licenca.quantidade_em_uso
        total_em_uso += em_uso
        licencas_lista.append(
            {
                "licenca": licenca,
                "em_uso": em_uso,
                "saldo": licenca.quantidade_total - em_uso,
            }
        )
    softwares = softwares_detectados_relatorio(ativos)
    return {
        "total": ativos.count(),
        "online": ativos.filter(status=AtivoRede.Status.ONLINE).count(),
        "offline": ativos.filter(status=AtivoRede.Status.OFFLINE).count(),
        "sem_coleta": ativos.filter(ultima_coleta_em__isnull=True).count(),
        "por_tipo": ativos.values("tipo__nome").annotate(total=Count("id")).order_by("tipo__nome"),
        "por_status": ativos.values("status").annotate(total=Count("id")).order_by("status"),
        "por_origem": ativos.values("origem").annotate(total=Count("id")).order_by("origem"),
        "por_fabricante": (
            ativos.exclude(fabricante="")
            .values("fabricante")
            .annotate(total=Count("id"))
            .order_by("fabricante")
        ),
        "sem_fabricante": ativos.filter(fabricante="").count(),
        "sem_modelo": ativos.filter(modelo="").count(),
        "sem_serial": ativos.filter(numero_serie="").count(),
        "com_interfaces": ativos.filter(interfaces__isnull=False).distinct().count(),
        "interfaces": ativos.filter(interfaces__isnull=False).values("interfaces__status").annotate(total=Count("interfaces")).order_by("interfaces__status"),
        "softwares": softwares[:50],
        "softwares_total": len(softwares),
        "licencas_total": total_licencas,
        "licencas_ativas": licencas.filter(status=LicencaSoftware.Status.ATIVA).count(),
        "licencas_vencidas": licencas.filter(status=LicencaSoftware.Status.VENCIDA).count(),
        "licencas_a_vencer": licencas.filter(status=LicencaSoftware.Status.A_VENCER).count(),
        "licencas_posicoes": total_posicoes,
        "licencas_em_uso": total_em_uso,
        "licencas_saldo": total_posicoes - total_em_uso,
        "licencas_por_status": licencas.values("status").annotate(total=Count("id")).order_by("status"),
        "licencas_lista": sorted(licencas_lista, key=lambda item: (item["saldo"], item["licenca"].nome))[:50],
        "ultimas_varreduras": VarreduraRede.objects.select_related("faixa", "iniciado_por")[:10],
    }


def softwares_detectados_relatorio(ativos):
    licencas = list(LicencaSoftware.objects.values_list("nome", flat=True))
    encontrados = {}
    for ativo in ativos.exclude(softwares_instalados=""):
        for linha in ativo.softwares_instalados.splitlines():
            software = linha.strip()
            if not software:
                continue
            coberto = any(
                licenca.lower() in software.lower() or software.lower() in licenca.lower()
                for licenca in licencas
            )
            registro = encontrados.setdefault(
                software,
                {"nome": software, "total": 0, "coberto": coberto, "ativos": []},
            )
            registro["total"] += 1
            if len(registro["ativos"]) < 5:
                registro["ativos"].append(ativo.nome)
    return sorted(encontrados.values(), key=lambda item: (-item["total"], item["nome"]))


def chart_data(linhas, label_field):
    return {
        "labels": [linha.get(label_field) or "Nao informado" for linha in linhas],
        "data": [linha["total"] for linha in linhas],
    }


class RelatorioInventarioView(LoginRequiredMixin, TemplateView):
    template_name = "inventario/relatorio.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form, ativos, filtro_aplicado = filtrar_ativos_relatorio(self.request.GET)
        context["form"] = form
        context["ativos"] = ativos[:500]
        context["indicadores"] = dados_relatorio_inventario(ativos, filtro_aplicado)
        context["filtro_aplicado"] = filtro_aplicado
        indicadores = context["indicadores"]
        context["tipo_chart"] = chart_data(indicadores["por_tipo"], "tipo__nome")
        context["status_chart"] = chart_data(indicadores["por_status"], "status")
        context["origem_chart"] = chart_data(indicadores["por_origem"], "origem")
        context["fabricante_chart"] = chart_data(indicadores["por_fabricante"], "fabricante")
        context["licenca_status_chart"] = chart_data(indicadores["licencas_por_status"], "status")
        context["software_chart"] = {
            "labels": [item["nome"] for item in indicadores["softwares"][:10]],
            "data": [item["total"] for item in indicadores["softwares"][:10]],
        }
        context["querystring"] = self.request.GET.urlencode()
        return context


@login_required
def exportar_ativos_xls(request):
    ativos = AtivoRede.objects.select_related("tipo", "setor").order_by("nome")
    response = HttpResponse(content_type="application/vnd.ms-excel; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="inventario_ativos.xls"'
    response.write("<html><head><meta charset='utf-8'></head><body>")
    config = ConfiguracaoInstitucional.atual()
    response.write(f"<h1>{config.nome_instituicao}</h1>")
    response.write(f"<p>{config.cnpj} {config.endereco}</p>")
    response.write("<h1>Inventário de ativos</h1>")
    response.write("<table border='1'><tr>")
    cabecalhos = [
        "Nome",
        "Tipo",
        "IP",
        "MAC",
        "Hostname",
        "Setor",
        "Fabricante",
        "Modelo",
        "Serial",
        "Sistema operacional",
        "Arquitetura",
        "Processador",
        "Memoria GB",
        "Disco GB",
        "Office",
        "Softwares instalados",
        "Usuario logado",
        "Dominio",
        "Status",
        "Origem",
    ]
    for cabecalho in cabecalhos:
        response.write(f"<th>{cabecalho}</th>")
    response.write("</tr>")
    for ativo in ativos:
        valores = [
            ativo.nome,
            ativo.tipo.nome,
            ativo.ip or "",
            ativo.mac,
            ativo.hostname,
            ativo.setor.nome if ativo.setor else "",
            ativo.fabricante,
            ativo.modelo,
            ativo.numero_serie,
            ativo.sistema_operacional,
            ativo.arquitetura,
            ativo.processador,
            ativo.memoria_total_gb or "",
            ativo.disco_total_gb or "",
            ativo.office,
            ativo.softwares_instalados,
            ativo.usuario_logado,
            ativo.dominio,
            ativo.get_status_display(),
            ativo.get_origem_display(),
        ]
        response.write("<tr>")
        for valor in valores:
            response.write(f"<td>{valor}</td>")
        response.write("</tr>")
    response.write("</table></body></html>")
    return response


@login_required
def exportar_relatorio_inventario_xls(request):
    form, ativos, filtro_aplicado = filtrar_ativos_relatorio(request.GET)
    indicadores = dados_relatorio_inventario(ativos, filtro_aplicado)

    response = HttpResponse(content_type="application/vnd.ms-excel; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="relatorio_inventario.xls"'
    response.write("<html><head><meta charset='utf-8'></head><body>")
    config = ConfiguracaoInstitucional.atual()
    response.write(f"<h1>{escape(config.nome_instituicao)}</h1>")
    response.write(f"<p>{escape(config.cnpj)} {escape(config.endereco)}</p>")
    response.write("<h1>Relatorio de inventario</h1>")
    response.write(f"<p>Total filtrado: {indicadores['total']}</p>")

    for titulo, linhas, campo in [
        ("Ativos por tipo", indicadores["por_tipo"], "tipo__nome"),
        ("Ativos por status", indicadores["por_status"], "status"),
        ("Ativos por origem", indicadores["por_origem"], "origem"),
        ("Ativos por fabricante", indicadores["por_fabricante"], "fabricante"),
        ("Licencas por status", indicadores["licencas_por_status"], "status"),
    ]:
        response.write(f"<h2>{escape(titulo)}</h2>")
        response.write("<table border='1'><tr><th>Grupo</th><th>Total</th></tr>")
        for linha in linhas:
            response.write(f"<tr><td>{escape(str(linha.get(campo) or 'Nao informado'))}</td><td>{linha['total']}</td></tr>")
        response.write("</table><br>")

    response.write("<h2>Softwares detectados</h2>")
    response.write("<table border='1'><tr><th>Software</th><th>Ocorrencias</th><th>Cobertura</th><th>Exemplos de ativos</th></tr>")
    for item in indicadores["softwares"]:
        response.write(
            "<tr>"
            f"<td>{escape(item['nome'])}</td>"
            f"<td>{item['total']}</td>"
            f"<td>{'Licenciado' if item['coberto'] else 'Sem vinculo'}</td>"
            f"<td>{escape(', '.join(item['ativos']))}</td>"
            "</tr>"
        )
    response.write("</table><br>")

    response.write("<h2>Licencas</h2>")
    response.write("<table border='1'><tr><th>Licenca</th><th>Status</th><th>Total</th><th>Em uso</th><th>Saldo</th></tr>")
    for item in indicadores["licencas_lista"]:
        licenca = item["licenca"]
        response.write(
            "<tr>"
            f"<td>{escape(licenca.nome)}</td>"
            f"<td>{escape(licenca.get_status_display())}</td>"
            f"<td>{licenca.quantidade_total}</td>"
            f"<td>{item['em_uso']}</td>"
            f"<td>{item['saldo']}</td>"
            "</tr>"
        )
    response.write("</table><br>")

    cabecalhos = [
        "Nome",
        "IP",
        "MAC",
        "Tipo",
        "Setor",
        "Fabricante",
        "Modelo",
        "Serial",
        "Sistema operacional",
        "Status",
        "Origem",
        "Ultima coleta",
    ]
    response.write("<h2>Ativos filtrados</h2>")
    response.write("<table border='1'><tr>")
    for cabecalho in cabecalhos:
        response.write(f"<th>{escape(cabecalho)}</th>")
    response.write("</tr>")
    for ativo in ativos:
        valores = [
            ativo.nome,
            ativo.ip or "",
            ativo.mac,
            ativo.tipo.nome if ativo.tipo else "",
            ativo.setor.nome if ativo.setor else "",
            ativo.fabricante,
            ativo.modelo,
            ativo.numero_serie,
            ativo.sistema_operacional,
            ativo.get_status_display(),
            ativo.get_origem_display(),
            ativo.ultima_coleta_em.strftime("%d/%m/%Y %H:%M") if ativo.ultima_coleta_em else "",
        ]
        response.write("<tr>")
        for valor in valores:
            response.write(f"<td>{escape(str(valor))}</td>")
        response.write("</tr>")
    response.write("</table><br>")

    response.write("<h2>Ultimas varreduras</h2>")
    response.write("<table border='1'><tr><th>Faixa</th><th>Metodo</th><th>Status</th><th>Encontrados</th><th>Inicio</th><th>Conclusao</th></tr>")
    for varredura in indicadores["ultimas_varreduras"]:
        response.write(
            "<tr>"
            f"<td>{escape(str(varredura.faixa))}</td>"
            f"<td>{escape(varredura.get_metodo_display())}</td>"
            f"<td>{escape(varredura.get_status_display())}</td>"
            f"<td>{varredura.ativos_encontrados}</td>"
            f"<td>{varredura.iniciado_em.strftime('%d/%m/%Y %H:%M')}</td>"
            f"<td>{varredura.concluido_em.strftime('%d/%m/%Y %H:%M') if varredura.concluido_em else ''}</td>"
            "</tr>"
        )
    response.write("</table></body></html>")
    return response


@login_required
def exportar_relatorio_inventario_pdf(request):
    form, ativos, filtro_aplicado = filtrar_ativos_relatorio(request.GET)
    indicadores = dados_relatorio_inventario(ativos, filtro_aplicado)
    config = ConfiguracaoInstitucional.atual()

    linhas = [
        config.nome_instituicao,
        f"CNPJ: {config.cnpj or '-'}",
        f"Endereco: {config.endereco or '-'}",
        "",
        "RELATORIO DE INVENTARIO",
        f"Total filtrado: {indicadores['total']}",
        f"Softwares detectados: {indicadores['softwares_total']}",
        f"Licencas cadastradas: {indicadores['licencas_total']}",
        f"Posicoes de licenca: {indicadores['licencas_posicoes']}",
        f"Licencas em uso: {indicadores['licencas_em_uso']}",
        f"Saldo de licencas: {indicadores['licencas_saldo']}",
        f"Online: {indicadores['online']}",
        f"Offline: {indicadores['offline']}",
        f"Sem coleta: {indicadores['sem_coleta']}",
        "",
        "COBERTURA DOS DADOS",
        f"Sem fabricante: {indicadores['sem_fabricante']}",
        f"Sem modelo: {indicadores['sem_modelo']}",
        f"Sem serial: {indicadores['sem_serial']}",
        f"Com interfaces: {indicadores['com_interfaces']}",
        "",
        "ATIVOS POR TIPO",
    ]
    for item in indicadores["por_tipo"]:
        linhas.append(f"{item.get('tipo__nome') or 'Nao informado'}: {item['total']}")

    linhas.extend(["", "ATIVOS POR STATUS"])
    for item in indicadores["por_status"]:
        linhas.append(f"{item.get('status') or 'Nao informado'}: {item['total']}")

    linhas.extend(["", "ATIVOS POR ORIGEM"])
    for item in indicadores["por_origem"]:
        linhas.append(f"{item.get('origem') or 'Nao informado'}: {item['total']}")

    linhas.extend(["", "LICENCAS POR STATUS"])
    for item in indicadores["licencas_por_status"]:
        linhas.append(f"{item.get('status') or 'Nao informado'}: {item['total']}")

    linhas.extend(["", "SOFTWARES MAIS DETECTADOS"])
    for item in indicadores["softwares"][:30]:
        cobertura = "licenciado" if item["coberto"] else "sem vinculo"
        linhas.append(f"{item['nome']}: {item['total']} ocorrencia(s), {cobertura}")

    linhas.extend(["", "LICENCAS"])
    for item in indicadores["licencas_lista"][:30]:
        licenca = item["licenca"]
        linhas.append(
            f"{licenca.nome} | {licenca.get_status_display()} | total {licenca.quantidade_total} | "
            f"uso {item['em_uso']} | saldo {item['saldo']}"
        )

    linhas.extend(["", "ATIVOS FILTRADOS", "Nome | IP | Tipo | Fabricante | Modelo | Status | Coleta"])
    for ativo in ativos[:200]:
        coleta = ativo.ultima_coleta_em.strftime("%d/%m/%Y %H:%M") if ativo.ultima_coleta_em else "-"
        linhas.append(
            f"{ativo.nome} | {ativo.ip or '-'} | {ativo.tipo or '-'} | "
            f"{ativo.fabricante or '-'} | {ativo.modelo or '-'} | {ativo.get_status_display()} | {coleta}"
        )

    response = HttpResponse(montar_pdf(linhas), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="relatorio_inventario.pdf"'
    return response


class ImportarAtivosCSVView(LoginRequiredMixin, TemplateView):
    template_name = "inventario/importar_ativos.html"

    campos_alias = {
        "nome": ["nome", "name"],
        "tipo": ["tipo", "type"],
        "ip": ["ip", "endereco_ip", "endereco ip"],
        "mac": ["mac", "mac_address", "mac address"],
        "hostname": ["hostname", "host"],
        "fabricante": ["fabricante", "manufacturer"],
        "modelo": ["modelo", "model"],
        "numero_serie": ["serial", "numero_serie", "numero de serie", "patrimonio"],
        "sistema_operacional": ["sistema_operacional", "sistema operacional", "so", "os"],
        "responsavel": ["responsavel", "usuario", "user"],
        "localizacao": ["localizacao", "localização", "local"],
        "observacoes": ["observacoes", "observações", "observacao", "observação"],
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = kwargs.get("form") or ImportacaoAtivosCSVForm()
        context["campos_suportados"] = ", ".join(self.campos_alias.keys())
        return context

    def post(self, request, *args, **kwargs):
        form = ImportacaoAtivosCSVForm(request.POST, request.FILES)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        arquivo = form.cleaned_data["arquivo"]
        atualizar = form.cleaned_data["atualizar_existentes"]
        try:
            texto = arquivo.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            arquivo.seek(0)
            texto = arquivo.read().decode("latin-1")

        amostra = texto[:2048]
        try:
            dialect = csv.Sniffer().sniff(amostra, delimiters=";,")
        except csv.Error:
            dialect = csv.excel
            dialect.delimiter = ";"
        leitor = csv.DictReader(io.StringIO(texto), dialect=dialect)
        criados = 0
        atualizados = 0
        ignorados = 0
        tipo_default, _ = TipoAtivo.objects.get_or_create(nome="Dispositivo importado")

        for linha in leitor:
            dados = self.normalizar_linha(linha)
            if not any(dados.values()):
                continue
            if not any([dados.get("nome"), dados.get("ip"), dados.get("mac"), dados.get("hostname"), dados.get("numero_serie")]):
                ignorados += 1
                continue

            tipo = tipo_default
            if dados.get("tipo"):
                tipo, _ = TipoAtivo.objects.get_or_create(nome=dados["tipo"][:80])

            ativo = self.localizar_ativo(dados) if atualizar else None
            criado = ativo is None
            if criado:
                ativo = AtivoRede(tipo=tipo)

            antes = {campo: getattr(ativo, campo, "") for campo in dados.keys() if hasattr(ativo, campo)}
            ativo.tipo = tipo
            ativo.nome = dados.get("nome") or dados.get("hostname") or dados.get("ip") or ativo.nome or "Ativo importado"
            for campo, valor in dados.items():
                if valor and hasattr(ativo, campo) and campo not in {"tipo", "nome"}:
                    setattr(ativo, campo, valor)
            ativo.origem = AtivoRede.Origem.IMPORTACAO
            ativo.status = ativo.status or AtivoRede.Status.DESCONHECIDO
            ativo.save()
            registrar_alteracoes_ativo(ativo, antes, list(antes.keys()), "importacao_csv")
            criados += 1 if criado else 0
            atualizados += 0 if criado else 1

        messages.success(request, f"Importacao concluida. Criados: {criados}. Atualizados: {atualizados}. Ignorados: {ignorados}.")
        return redirect("inventario:ativos")

    def normalizar_linha(self, linha):
        normalizada = {}
        origem = {str(chave).strip().lower(): (valor or "").strip() for chave, valor in linha.items() if chave}
        for campo, aliases in self.campos_alias.items():
            for alias in aliases:
                if alias in origem and origem[alias]:
                    normalizada[campo] = origem[alias][:250]
                    break
        return normalizada

    def localizar_ativo(self, dados):
        filtros = []
        if dados.get("numero_serie"):
            filtros.append(Q(numero_serie__iexact=dados["numero_serie"]))
        if dados.get("mac"):
            filtros.append(Q(mac__iexact=dados["mac"]))
        if dados.get("ip"):
            filtros.append(Q(ip=dados["ip"]))
        if dados.get("hostname"):
            filtros.append(Q(hostname__iexact=dados["hostname"]) | Q(nome__iexact=dados["hostname"]))
        if not filtros:
            return None
        consulta = filtros[0]
        for filtro in filtros[1:]:
            consulta |= filtro
        return AtivoRede.objects.filter(consulta).order_by("id").first()


class AtivoRedeCreateView(LoginRequiredMixin, CreateView):
    model = AtivoRede
    form_class = AtivoRedeForm
    template_name = "inventario/ativo_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Ativo cadastrado com sucesso.")
        return super().form_valid(form)


class AtivoRedeUpdateView(LoginRequiredMixin, UpdateView):
    model = AtivoRede
    form_class = AtivoRedeForm
    template_name = "inventario/ativo_form.html"

    def form_valid(self, form):
        campos = list(form.changed_data)
        antes = {campo: getattr(self.object, campo, "") for campo in campos}
        messages.success(self.request, "Ativo atualizado com sucesso.")
        response = super().form_valid(form)
        registrar_alteracoes_ativo(self.object, antes, campos, "manual")
        return response


class AtivoRedeDetailView(LoginRequiredMixin, DetailView):
    model = AtivoRede
    template_name = "inventario/ativo_detail.html"
    context_object_name = "ativo"

    def get_queryset(self):
        return AtivoRede.objects.select_related("tipo", "setor").prefetch_related(
            "interfaces", "ocorrencias", "chamados", "relacoes_origem__destino", "relacoes_destino__origem", "licencas", "historico_alteracoes"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ocorrencia_form"] = OcorrenciaAtivoForm()
        context["relacionamento_form"] = RelacionamentoAtivoForm()
        context["varredura_form"] = VarreduraRedeForm()
        return context


class LicencaSoftwareListView(LoginRequiredMixin, ListView):
    model = LicencaSoftware
    template_name = "inventario/licenca_list.html"
    context_object_name = "licencas"
    paginate_by = 20

    def get_queryset(self):
        queryset = LicencaSoftware.objects.prefetch_related("ativos")
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        if q:
            queryset = queryset.filter(Q(nome__icontains=q) | Q(fabricante__icontains=q) | Q(chave__icontains=q))
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = LicencaSoftware.Status.choices
        context["filtros"] = self.request.GET
        return context


class LicencaSoftwareDetailView(LoginRequiredMixin, DetailView):
    model = LicencaSoftware
    template_name = "inventario/licenca_detail.html"
    context_object_name = "licenca"

    def get_queryset(self):
        return LicencaSoftware.objects.prefetch_related("ativos", "anexos")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["anexo_form"] = AnexoLicencaSoftwareForm()
        return context


class LicencaSoftwareCreateView(LoginRequiredMixin, CreateView):
    model = LicencaSoftware
    form_class = LicencaSoftwareForm
    template_name = "inventario/licenca_form.html"
    success_url = reverse_lazy("inventario:licencas")

    def form_valid(self, form):
        messages.success(self.request, "Licenca cadastrada com sucesso.")
        return super().form_valid(form)


class LicencaSoftwareUpdateView(LoginRequiredMixin, UpdateView):
    model = LicencaSoftware
    form_class = LicencaSoftwareForm
    template_name = "inventario/licenca_form.html"
    success_url = reverse_lazy("inventario:licencas")

    def form_valid(self, form):
        messages.success(self.request, "Licenca atualizada com sucesso.")
        return super().form_valid(form)


@login_required
def anexar_licenca(request, pk):
    licenca = get_object_or_404(LicencaSoftware, pk=pk)
    if request.method == "POST":
        form = AnexoLicencaSoftwareForm(request.POST, request.FILES)
        if form.is_valid():
            anexo = form.save(commit=False)
            anexo.licenca = licenca
            anexo.enviado_por = request.user
            anexo.save()
            messages.success(request, "Anexo enviado com sucesso.")
        else:
            messages.error(request, "Nao foi possivel enviar o anexo.")
    return redirect("inventario:licenca_detalhe", pk=licenca.pk)


class ConciliacaoLicencasView(LoginRequiredMixin, TemplateView):
    template_name = "inventario/conciliacao_licencas.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        licencas = list(LicencaSoftware.objects.values_list("nome", flat=True))
        encontrados = {}
        for ativo in AtivoRede.objects.exclude(softwares_instalados="").only("id", "nome", "softwares_instalados"):
            for linha in ativo.softwares_instalados.splitlines():
                software = linha.strip()
                if not software:
                    continue
                coberto = any(licenca.lower() in software.lower() or software.lower() in licenca.lower() for licenca in licencas)
                encontrados.setdefault(software, {"total": 0, "coberto": coberto, "ativos": []})
                encontrados[software]["total"] += 1
                if len(encontrados[software]["ativos"]) < 5:
                    encontrados[software]["ativos"].append(ativo.nome)
        context["softwares"] = sorted(encontrados.items(), key=lambda item: (-item[1]["total"], item[0]))[:200]
        return context


@login_required
def excluir_ativo(request, pk):
    ativo = get_object_or_404(AtivoRede, pk=pk)
    if request.method == "POST":
        nome = ativo.nome
        ativo.delete()
        messages.success(request, f"Ativo {nome} excluído com sucesso.")
        return redirect("inventario:ativos")
    messages.error(request, "A exclusão precisa ser confirmada por POST.")
    return redirect(ativo)


@login_required
def excluir_ativos_lote(request):
    if request.method == "POST":
        ids = request.POST.getlist("ativos")
        if not ids:
            messages.warning(request, "Selecione ao menos um ativo para excluir.")
            return redirect("inventario:ativos")
        total, _ = AtivoRede.objects.filter(id__in=ids).delete()
        messages.success(request, f"{total} registro(s) excluído(s) do inventário.")
    return redirect("inventario:ativos")


def atualizar_status_por_ping(ativo, timeout_ms=800):
    if ativo.status in {AtivoRede.Status.DESATIVADO, AtivoRede.Status.MANUTENCAO}:
        return "ignorado"
    if not ativo.ip:
        if ativo.status != AtivoRede.Status.DESCONHECIDO:
            ativo.status = AtivoRede.Status.DESCONHECIDO
            ativo.save(update_fields=["status", "atualizado_em"])
        return "sem_ip"

    novo_status = AtivoRede.Status.ONLINE if ping_host(ativo.ip, timeout_ms=timeout_ms) else AtivoRede.Status.OFFLINE
    if ativo.status != novo_status:
        antes = {"status": ativo.status}
        ativo.status = novo_status
        ativo.save(update_fields=["status", "atualizado_em"])
        registrar_alteracoes_ativo(ativo, antes, ["status"], "validacao_ping")
    return novo_status


@login_required
@require_POST
def verificar_status_ativo(request, pk):
    ativo = get_object_or_404(AtivoRede, pk=pk)
    resultado = atualizar_status_por_ping(ativo)
    if resultado == "ignorado":
        messages.info(request, "Status administrativo mantido. Ativos em manutencao ou desativados nao sao alterados por ping.")
    elif resultado == "sem_ip":
        messages.warning(request, "Este ativo nao possui IP cadastrado para validar por ping.")
    elif resultado == AtivoRede.Status.ONLINE:
        messages.success(request, f"{ativo.nome} respondeu ao ping e foi marcado como Online.")
    else:
        messages.warning(request, f"{ativo.nome} nao respondeu ao ping e foi marcado como Offline.")
    return redirect(ativo)


@login_required
@require_POST
def verificar_status_ativos_lote(request):
    ids = request.POST.getlist("ativos")
    if not ids:
        messages.warning(request, "Selecione ao menos um ativo para verificar.")
        return redirect("inventario:ativos")

    totais = {"online": 0, "offline": 0, "sem_ip": 0, "ignorado": 0}
    for ativo in AtivoRede.objects.filter(id__in=ids):
        resultado = atualizar_status_por_ping(ativo)
        if resultado == AtivoRede.Status.ONLINE:
            totais["online"] += 1
        elif resultado == AtivoRede.Status.OFFLINE:
            totais["offline"] += 1
        elif resultado == "sem_ip":
            totais["sem_ip"] += 1
        else:
            totais["ignorado"] += 1

    messages.success(
        request,
        "Validacao concluida. "
        f"Online: {totais['online']}. Offline: {totais['offline']}. "
        f"Sem IP: {totais['sem_ip']}. Ignorados: {totais['ignorado']}.",
    )
    return redirect("inventario:ativos")


class TipoAtivoListView(LoginRequiredMixin, ListView):
    model = TipoAtivo
    template_name = "inventario/cadastros/tipo_list.html"
    context_object_name = "tipos"


class TipoAtivoCreateView(LoginRequiredMixin, CreateView):
    model = TipoAtivo
    form_class = TipoAtivoForm
    template_name = "inventario/cadastros/tipo_form.html"
    success_url = reverse_lazy("inventario:tipos")


class TipoAtivoUpdateView(LoginRequiredMixin, UpdateView):
    model = TipoAtivo
    form_class = TipoAtivoForm
    template_name = "inventario/cadastros/tipo_form.html"
    success_url = reverse_lazy("inventario:tipos")


class CredencialSNMPListView(LoginRequiredMixin, ListView):
    model = CredencialSNMP
    template_name = "inventario/cadastros/snmp_list.html"
    context_object_name = "credenciais"


class CredencialSNMPCreateView(LoginRequiredMixin, CreateView):
    model = CredencialSNMP
    form_class = CredencialSNMPForm
    template_name = "inventario/cadastros/snmp_form.html"
    success_url = reverse_lazy("inventario:snmp")


class CredencialSNMPUpdateView(LoginRequiredMixin, UpdateView):
    model = CredencialSNMP
    form_class = CredencialSNMPForm
    template_name = "inventario/cadastros/snmp_form.html"
    success_url = reverse_lazy("inventario:snmp")


class FaixaRedeListView(LoginRequiredMixin, ListView):
    model = FaixaRede
    template_name = "inventario/cadastros/faixa_list.html"
    context_object_name = "faixas"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["varredura_form"] = VarreduraRedeForm()
        return context


class FaixaRedeCreateView(LoginRequiredMixin, CreateView):
    model = FaixaRede
    form_class = FaixaRedeForm
    template_name = "inventario/cadastros/faixa_form.html"
    success_url = reverse_lazy("inventario:faixas")


class FaixaRedeUpdateView(LoginRequiredMixin, UpdateView):
    model = FaixaRede
    form_class = FaixaRedeForm
    template_name = "inventario/cadastros/faixa_form.html"
    success_url = reverse_lazy("inventario:faixas")


class AgendamentoVarreduraListView(LoginRequiredMixin, ListView):
    model = AgendamentoVarredura
    template_name = "inventario/cadastros/agendamento_list.html"
    context_object_name = "agendamentos"


class AgendamentoVarreduraCreateView(LoginRequiredMixin, CreateView):
    model = AgendamentoVarredura
    form_class = AgendamentoVarreduraForm
    template_name = "inventario/cadastros/agendamento_form.html"
    success_url = reverse_lazy("inventario:agendamentos")


class AgendamentoVarreduraUpdateView(LoginRequiredMixin, UpdateView):
    model = AgendamentoVarredura
    form_class = AgendamentoVarreduraForm
    template_name = "inventario/cadastros/agendamento_form.html"
    success_url = reverse_lazy("inventario:agendamentos")


@login_required
def registrar_ocorrencia(request, pk):
    ativo = get_object_or_404(AtivoRede, pk=pk)
    if request.method == "POST":
        form = OcorrenciaAtivoForm(request.POST)
        if form.is_valid():
            ocorrencia = form.save(commit=False)
            ocorrencia.ativo = ativo
            ocorrencia.registrado_por = request.user
            ocorrencia.save()
            messages.success(request, "Ocorrência registrada com sucesso.")
        else:
            messages.error(request, "Não foi possível registrar a ocorrência.")
    return redirect(ativo)


@login_required
def registrar_relacionamento(request, pk):
    ativo = get_object_or_404(AtivoRede, pk=pk)
    if request.method == "POST":
        form = RelacionamentoAtivoForm(request.POST)
        if form.is_valid():
            relacao = form.save(commit=False)
            relacao.origem = ativo
            relacao.save()
            messages.success(request, "Relacionamento CMDB registrado.")
        else:
            messages.error(request, "Nao foi possivel registrar o relacionamento.")
    return redirect(ativo)


def faixa_por_ip(ip):
    try:
        endereco = ipaddress.ip_address(ip)
    except ValueError:
        return None
    for faixa in FaixaRede.objects.select_related("credencial_snmp").filter(ativa=True):
        try:
            if endereco in ipaddress.ip_network(faixa.cidr, strict=False):
                return faixa
        except ValueError:
            continue
    return None


def aplicar_descoberta_no_ativo(ativo, descoberta, origem="varredura manual"):
    campos = [
        "nome",
        "hostname",
        "ip",
        "mac",
        "fabricante",
        "modelo",
        "numero_serie",
        "sistema_operacional",
        "localizacao",
        "origem",
        "observacoes",
        "status",
        "ultima_coleta_em",
    ]
    antes = {campo: getattr(ativo, campo, "") for campo in campos}

    if descoberta.nome and (not ativo.nome or ativo.nome.startswith(("Host ativo", "Host descoberto", "Ativo descoberto"))):
        ativo.nome = descoberta.nome
    ativo.hostname = descoberta.hostname or ativo.hostname
    ativo.ip = descoberta.ip or ativo.ip
    ativo.mac = descoberta.mac or ativo.mac
    ativo.fabricante = descoberta.fabricante or ativo.fabricante
    ativo.modelo = descoberta.modelo or ativo.modelo
    ativo.numero_serie = descoberta.numero_serie or ativo.numero_serie
    ativo.sistema_operacional = descoberta.sistema_operacional or ativo.sistema_operacional
    ativo.localizacao = descoberta.localizacao or ativo.localizacao
    ativo.origem = descoberta.origem or ativo.origem
    ativo.status = AtivoRede.Status.ONLINE
    if descoberta.observacoes:
        ativo.observacoes = descoberta.observacoes
    ativo.ultima_coleta_em = timezone.now()
    ativo.save(update_fields=campos + ["atualizado_em"])
    sincronizar_interfaces_descobertas(ativo, descoberta)
    registrar_alteracoes_ativo(ativo, antes, campos, origem)


def sincronizar_interfaces_descobertas(ativo, descoberta):
    for item in getattr(descoberta, "interfaces", []) or []:
        nome = (item.get("nome") or item.get("descricao") or "").strip()[:120]
        if not nome:
            continue
        interface, _ = InterfaceRede.objects.get_or_create(ativo=ativo, nome=nome)
        interface.descricao = (item.get("descricao") or interface.descricao)[:250]
        interface.mac = (item.get("mac") or interface.mac)[:30]
        interface.velocidade = (item.get("velocidade") or interface.velocidade)[:80]
        interface.status = (item.get("status") or interface.status)[:80]
        interface.save()


@login_required
@require_POST
def revarrer_ativo(request, pk):
    ativo = get_object_or_404(AtivoRede, pk=pk)
    form = VarreduraRedeForm(request.POST or None)
    if not form.is_valid():
        messages.error(request, "Informe um metodo de descoberta valido.")
        return redirect(ativo)

    if not ativo.ip:
        messages.warning(request, "Este ativo ainda nao tem IP cadastrado para varrer novamente.")
        return redirect(ativo)

    metodo = form.cleaned_data["metodo"]
    portas = form.cleaned_data.get("portas", "")
    metodos_suportados = {
        MetodoDescoberta.Codigo.AUTO,
        MetodoDescoberta.Codigo.PING,
        MetodoDescoberta.Codigo.DNS,
        MetodoDescoberta.Codigo.TCP,
        MetodoDescoberta.Codigo.SNMP,
    }
    if metodo not in metodos_suportados:
        messages.error(request, "Para revarrer um ativo individual, use Automatico, Ping, DNS, TCP ou SNMP.")
        return redirect(ativo)

    faixa = faixa_por_ip(ativo.ip)
    credencial = faixa.credencial_snmp if faixa and faixa.credencial_snmp else CredencialSNMP.objects.filter(ativo=True).first()
    if metodo == MetodoDescoberta.Codigo.SNMP and not credencial:
        messages.error(request, "Cadastre uma credencial SNMP ativa ou associe uma credencial a faixa deste IP.")
        return redirect(ativo)

    try:
        descoberta = descobrir_por_host(ativo.ip, metodo, portas, credencial)
    except Exception as exc:
        messages.error(request, f"Nao foi possivel concluir a varredura do ativo: {exc}")
        return redirect(ativo)

    if not descoberta:
        messages.warning(
            request,
            "Nenhuma informacao nova foi localizada. Verifique firewall, rota, portas TCP, community SNMP e se o host esta ligado.",
        )
        return redirect(ativo)

    aplicar_descoberta_no_ativo(ativo, descoberta)
    messages.success(request, f"Varredura do ativo concluida por {MetodoDescoberta.Codigo(metodo).label}.")
    return redirect(ativo)


@login_required
def iniciar_varredura_snmp(request, pk):
    faixa = get_object_or_404(FaixaRede, pk=pk)
    form = VarreduraRedeForm(request.POST or None)
    if not form.is_valid():
        messages.error(request, "Informe um método de descoberta válido.")
        return redirect("inventario:faixas")

    metodo = form.cleaned_data["metodo"]
    portas = form.cleaned_data.get("portas", "")
    varredura = VarreduraRede.objects.create(
        faixa=faixa,
        metodo=metodo,
        portas=portas,
        iniciado_por=request.user,
        status=VarreduraRede.Status.CONCLUIDA,
    )
    tipo_nome = {
        MetodoDescoberta.Codigo.AUTO: "Dispositivo descoberto",
        MetodoDescoberta.Codigo.SNMP: "Dispositivo de rede",
        MetodoDescoberta.Codigo.PING: "Dispositivo desconhecido",
        MetodoDescoberta.Codigo.DNS: "Dispositivo desconhecido",
        MetodoDescoberta.Codigo.TCP: "Servidor ou serviço de rede",
        MetodoDescoberta.Codigo.AD: "Computador",
        MetodoDescoberta.Codigo.WINRM: "Computador",
        MetodoDescoberta.Codigo.CSV: "Dispositivo importado",
        MetodoDescoberta.Codigo.MANUAL: "Dispositivo manual",
    }.get(metodo, "Dispositivo desconhecido")
    tipo_padrao, _ = TipoAtivo.objects.get_or_create(nome=tipo_nome)

    try:
        descobertos = descobrir_por_faixa(faixa, metodo, portas)
        encontrados = 0
        for item in descobertos:
            filtro = {"ip": item.ip} if item.ip else {"hostname": item.hostname or item.nome}
            ativo, criado = AtivoRede.objects.get_or_create(
                **filtro,
                defaults={
                    "ip": item.ip or None,
                    "hostname": item.hostname,
                    "nome": item.nome or item.hostname or "Ativo descoberto",
                    "tipo": tipo_padrao,
                    "status": AtivoRede.Status.DESCONHECIDO,
                    "origem": item.origem,
                    "mac": item.mac,
                    "fabricante": item.fabricante,
                    "modelo": item.modelo,
                    "numero_serie": item.numero_serie,
                    "sistema_operacional": item.sistema_operacional,
                    "localizacao": item.localizacao,
                    "observacoes": item.observacoes or mensagem_pre_inventario(metodo, portas),
                    "ultima_coleta_em": timezone.now(),
                },
            )
            if not criado:
                ativo.origem = item.origem
                ativo.hostname = item.hostname or ativo.hostname
                ativo.mac = item.mac or ativo.mac
                ativo.fabricante = item.fabricante or ativo.fabricante
                ativo.modelo = item.modelo or ativo.modelo
                ativo.numero_serie = item.numero_serie or ativo.numero_serie
                ativo.sistema_operacional = item.sistema_operacional or ativo.sistema_operacional
                ativo.localizacao = item.localizacao or ativo.localizacao
                ativo.observacoes = item.observacoes or ativo.observacoes
                ativo.ultima_coleta_em = timezone.now()
                ativo.save(update_fields=["origem", "hostname", "mac", "fabricante", "modelo", "numero_serie", "sistema_operacional", "localizacao", "observacoes", "ultima_coleta_em", "atualizado_em"])
            sincronizar_interfaces_descobertas(ativo, item)
            encontrados += 1

        varredura.ativos_encontrados = encontrados
        varredura.mensagem = mensagem_varredura(metodo, portas, encontrados)
        varredura.concluido_em = timezone.now()
        varredura.save()
        messages.success(request, f"Varredura {varredura.get_metodo_display()} concluída com {encontrados} ativos encontrados.")
    except Exception as exc:
        varredura.status = VarreduraRede.Status.ERRO
        varredura.mensagem = str(exc)
        varredura.concluido_em = timezone.now()
        varredura.save()
        messages.error(request, f"Não foi possível concluir a varredura: {exc}")

    return redirect("inventario:faixas")


def executar_varredura(faixa, metodo, portas="", usuario=None):
    varredura = VarreduraRede.objects.create(
        faixa=faixa,
        metodo=metodo,
        portas=portas,
        iniciado_por=usuario,
        status=VarreduraRede.Status.CONCLUIDA,
    )
    tipo_nome = {
        MetodoDescoberta.Codigo.AUTO: "Dispositivo descoberto",
        MetodoDescoberta.Codigo.SNMP: "Dispositivo de rede",
        MetodoDescoberta.Codigo.PING: "Dispositivo desconhecido",
        MetodoDescoberta.Codigo.DNS: "Dispositivo desconhecido",
        MetodoDescoberta.Codigo.TCP: "Servidor ou serviço de rede",
        MetodoDescoberta.Codigo.AD: "Computador",
        MetodoDescoberta.Codigo.WINRM: "Computador",
        MetodoDescoberta.Codigo.CSV: "Dispositivo importado",
        MetodoDescoberta.Codigo.MANUAL: "Dispositivo manual",
    }.get(metodo, "Dispositivo desconhecido")
    tipo_padrao, _ = TipoAtivo.objects.get_or_create(nome=tipo_nome)

    from .services import descobrir_por_faixa

    descobertos = descobrir_por_faixa(faixa, metodo, portas)
    for item in descobertos:
        filtro = {"ip": item.ip} if item.ip else {"hostname": item.hostname or item.nome}
        ativo, criado = AtivoRede.objects.get_or_create(
            **filtro,
            defaults={
                "ip": item.ip or None,
                "hostname": item.hostname,
                "nome": item.nome or item.hostname or "Ativo descoberto",
                "tipo": tipo_padrao,
                "status": AtivoRede.Status.DESCONHECIDO,
                "origem": item.origem,
                "mac": item.mac,
                "fabricante": item.fabricante,
                "modelo": item.modelo,
                "numero_serie": item.numero_serie,
                "sistema_operacional": item.sistema_operacional,
                "localizacao": item.localizacao,
                "observacoes": item.observacoes,
                "ultima_coleta_em": timezone.now(),
            },
        )
        if not criado:
            ativo.origem = item.origem
            ativo.hostname = item.hostname or ativo.hostname
            ativo.mac = item.mac or ativo.mac
            ativo.fabricante = item.fabricante or ativo.fabricante
            ativo.modelo = item.modelo or ativo.modelo
            ativo.numero_serie = item.numero_serie or ativo.numero_serie
            ativo.sistema_operacional = item.sistema_operacional or ativo.sistema_operacional
            ativo.localizacao = item.localizacao or ativo.localizacao
            ativo.observacoes = item.observacoes or ativo.observacoes
            ativo.ultima_coleta_em = timezone.now()
            ativo.save(update_fields=["origem", "hostname", "mac", "fabricante", "modelo", "numero_serie", "sistema_operacional", "localizacao", "observacoes", "ultima_coleta_em", "atualizado_em"])
        sincronizar_interfaces_descobertas(ativo, item)
    varredura.ativos_encontrados = len(descobertos)
    varredura.mensagem = mensagem_varredura(metodo, portas, len(descobertos))
    varredura.concluido_em = timezone.now()
    varredura.save()
    return varredura


def origem_por_metodo(metodo):
    if metodo == MetodoDescoberta.Codigo.SNMP:
        return AtivoRede.Origem.SNMP
    if metodo == MetodoDescoberta.Codigo.AD:
        return AtivoRede.Origem.AD
    if metodo == MetodoDescoberta.Codigo.CSV:
        return AtivoRede.Origem.IMPORTACAO
    return AtivoRede.Origem.MANUAL


def nome_pre_inventario(metodo, ip):
    prefixos = {
        MetodoDescoberta.Codigo.AUTO: "Host descoberto",
        MetodoDescoberta.Codigo.PING: "Host ativo",
        MetodoDescoberta.Codigo.DNS: "Host DNS",
        MetodoDescoberta.Codigo.TCP: "Serviço detectado",
        MetodoDescoberta.Codigo.SNMP: "Dispositivo SNMP",
        MetodoDescoberta.Codigo.AD: "Computador AD",
        MetodoDescoberta.Codigo.WINRM: "Host Windows",
        MetodoDescoberta.Codigo.CSV: "Ativo importado",
        MetodoDescoberta.Codigo.MANUAL: "Ativo manual",
    }
    return f"{prefixos.get(metodo, 'Dispositivo')} {ip}"


def mensagem_pre_inventario(metodo, portas=""):
    mensagens = {
        MetodoDescoberta.Codigo.AUTO: "Pre-inventariado por descoberta automatica. Confirme tipo, responsavel, setor e localizacao.",
        MetodoDescoberta.Codigo.PING: "Pré-inventariado por ping/ICMP. Confirme tipo, responsável e localização.",
        MetodoDescoberta.Codigo.DNS: "Pré-inventariado por DNS reverso. Confirme hostname e características.",
        MetodoDescoberta.Codigo.TCP: f"Pré-inventariado por portas TCP ({portas or 'padrão'}). Confirme serviços e função.",
        MetodoDescoberta.Codigo.SNMP: "Pré-inventariado por SNMP. Confirme fabricante, modelo, interfaces e localização.",
        MetodoDescoberta.Codigo.AD: "Pré-inventariado por Active Directory. Confirme setor e usuário responsável.",
        MetodoDescoberta.Codigo.WINRM: "Pré-inventariado por WinRM/WMI. Confirme hardware e sistema operacional.",
        MetodoDescoberta.Codigo.CSV: "Pré-inventariado por importação CSV.",
        MetodoDescoberta.Codigo.MANUAL: "Pré-inventariado manualmente.",
    }
    return mensagens.get(metodo, "Pré-inventariado. Edite as características após validação.")


def mensagem_varredura(metodo, portas="", encontrados=0):
    mensagem = (
        f"Varredura {MetodoDescoberta.Codigo(metodo).label} concluída. "
        f"Ativos encontrados: {encontrados}. "
        f"{'Portas: ' + portas + '. ' if portas else ''}"
    )
    if encontrados == 0:
        mensagem += (
            "Nenhum host respondeu. Verifique rota para a VLAN/faixa, firewall/ACL entre servidor e rede alvo, "
            "bloqueio de ICMP/TCP/SNMP, community SNMP e disponibilidade do Nmap no servidor."
        )
    return mensagem
