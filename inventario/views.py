import csv
import io
import ipaddress
import json
import secrets
import socket
from html import escape
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.core.paginator import Paginator
from django.core import signing
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import FileResponse, Http404, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.crypto import constant_time_compare
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import CreateView, DetailView, ListView, RedirectView, TemplateView, UpdateView
from core.audit import registrar_evento
from core.models import ConfiguracaoInstitucional
from core.models import RegistroAuditoria
from core.permissions import usuario_e_suporte_n2
from governanca.pdf import montar_pdf

from .forms import (
    AtivoRedeForm,
    AgendamentoVarreduraForm,
    AnexoLicencaSoftwareForm,
    CampoExternoAtivoForm,
    CredencialSNMPForm,
    FaixaRedeForm,
    ImportacaoAtivosCSVForm,
    IntegracaoExternaForm,
    LicencaSoftwareForm,
    MesclarAtivosForm,
    MovimentacaoAtivoForm,
    OcorrenciaAtivoForm,
    RelacionamentoAtivoForm,
    RelatorioInventarioForm,
    SondaRemotaForm,
    TermoResponsabilidadeAtivoForm,
    TipoAtivoForm,
    VarreduraRedeForm,
)
from .models import (
    AgendamentoVarredura,
    AnexoLicencaSoftware,
    AtivoRede,
    CampoExternoAtivo,
    CredencialSNMP,
    FaixaRede,
    IntegracaoExterna,
    InterfaceRede,
    LicencaSoftware,
    HistoricoAlteracaoAtivo,
    MetodoDescoberta,
    MovimentacaoAtivo,
    OcorrenciaAtivo,
    RelacionamentoAtivo,
    RegistroAcessoIntegracao,
    RegistroColetaAgente,
    SondaRemota,
    TermoResponsabilidadeAtivo,
    ExecucaoSonda,
    TipoAtivo,
    VarreduraRede,
)
from .services import (
    ColetaAgenteErro,
    DescobertaAtivo,
    descobrir_por_faixa,
    descobrir_por_host,
    ping_host,
    processar_coleta_agente,
)


AGENTE_WINDOWS_EXE = "SistemaChamadosAgentSetup.exe"
AGENTE_LINUX_INSTALLER = "install.sh"


def ip_origem_request(request):
    encaminhado = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    return encaminhado or request.META.get("REMOTE_ADDR") or None


def limite_ativos_sem_comunicacao():
    return timezone.now() - timezone.timedelta(days=settings.INVENTARIO_DIAS_SEM_COMUNICACAO)


def filtro_ativos_sem_comunicacao():
    limite = limite_ativos_sem_comunicacao()
    return Q(ultima_coleta_em__lt=limite) | Q(ultima_coleta_em__isnull=True, criado_em__lt=limite)


def queryset_ativos_sem_comunicacao():
    return (
        AtivoRede.objects.select_related("tipo", "setor")
        .filter(filtro_ativos_sem_comunicacao())
        .exclude(status=AtivoRede.Status.DESATIVADO)
    )


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


def _identificador_valido(valor):
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


def localizar_ativo_por_identidade(serial="", mac="", hostname="", ip=None):
    if _identificador_valido(serial):
        ativo = AtivoRede.objects.filter(numero_serie__iexact=serial).order_by("id").first()
        if ativo:
            return ativo
    if _identificador_valido(mac) and mac.replace(":", "").replace("-", "") != "000000000000":
        ativo = AtivoRede.objects.filter(mac__iexact=mac).order_by("id").first()
        if ativo:
            return ativo
    if _identificador_valido(hostname):
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
        (_identificador_valido(serial) and _identificador_valido(candidato.numero_serie) and serial.lower() != candidato.numero_serie.lower()),
        (_identificador_valido(mac) and _identificador_valido(candidato.mac) and mac.lower() != candidato.mac.lower()),
        (_identificador_valido(hostname) and _identificador_valido(candidato.hostname) and hostname.lower() != candidato.hostname.lower()),
    ]
    return None if any(conflitos) else candidato


def _base_url_agente(request):
    url_detectada = request.build_absolute_uri("/").rstrip("/")
    return settings.PUBLIC_BASE_URL or url_detectada


def _ip_rede_preferencial():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as conexao:
            conexao.connect(("8.8.8.8", 80))
            ip = conexao.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass
    ips = _ips_rede_local()
    return ips[0] if ips else ""


def _base_url_qr(request):
    base_url = settings.PUBLIC_BASE_URL or request.build_absolute_uri("/").rstrip("/")
    partes = urlsplit(base_url)
    if partes.hostname not in {"localhost", "127.0.0.1", "::1"}:
        return base_url.rstrip("/")

    ip = _ip_rede_preferencial()
    if not ip:
        return base_url.rstrip("/")
    porta = partes.port
    netloc = f"{ip}:{porta}" if porta else ip
    return urlunsplit((partes.scheme or "http", netloc, "", "", "")).rstrip("/")


def _token_qr_ativo(ativo):
    return signing.dumps(ativo.pk, salt="inventario.ativo.qr")


def _url_publica_qr_ativo(request, ativo):
    caminho = reverse("inventario:ativo_identificacao", kwargs={"token": _token_qr_ativo(ativo)})
    return f"{_base_url_qr(request)}{caminho}"


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
@user_passes_test(lambda user: user.is_superuser)
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
@user_passes_test(lambda user: user.is_superuser)
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


def _contexto_saude_agentes():
    agora = timezone.now()
    agentes = list(
        AtivoRede.objects.filter(origem=AtivoRede.Origem.AGENTE)
        .exclude(status=AtivoRede.Status.DESATIVADO)
        .select_related("tipo", "setor")
        .order_by("nome")
    )
    contadores = {"saudavel": 0, "atrasado": 0, "critico": 0}
    for agente in agentes:
        if not agente.ultima_coleta_em:
            agente.estado_agente = "critico"
            agente.tempo_sem_coleta = "Nunca coletou"
        else:
            horas = int((agora - agente.ultima_coleta_em).total_seconds() // 3600)
            agente.tempo_sem_coleta = f"{horas} hora(s)"
            if horas <= 24:
                agente.estado_agente = "saudavel"
            elif horas <= 168:
                agente.estado_agente = "atrasado"
            else:
                agente.estado_agente = "critico"
        contadores[agente.estado_agente] += 1
    return {
        "agentes": agentes,
        "contadores": contadores,
        "eventos": RegistroColetaAgente.objects.select_related("ativo")[:100],
        "rejeitadas_24h": RegistroColetaAgente.objects.filter(
            status=RegistroColetaAgente.Status.REJEITADA,
            criado_em__gte=agora - timezone.timedelta(hours=24),
        ).count(),
    }


@login_required
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
    linux_download_url = f"{base_url}/inventario/agente/linux/download/"
    contexto = {
        "pode_configurar_agente": request.user.is_superuser,
        "token": settings.INVENTARIO_AGENT_TOKEN if request.user.is_superuser else "",
        "token_origem": settings.INVENTARIO_AGENT_TOKEN_ORIGEM if request.user.is_superuser else "",
        "endpoint": endpoint,
        "download_url": download_url,
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
    }
    contexto.update(_contexto_saude_agentes())
    return TemplateView.as_view(template_name="inventario/agente_config.html")(request, **contexto)


@login_required
def downloads_agente(request):
    caminho = _caminho_agente_windows()
    url_detectada = request.build_absolute_uri("/").rstrip("/")
    base_url = _base_url_agente(request)
    porta = request.get_port()
    esquema = "https" if request.is_secure() else "http"
    bases_sugeridas = [f"{esquema}://{ip}:{porta}" for ip in _ips_rede_local()]
    contexto = {
        "pode_baixar_agente": request.user.is_superuser,
        "token": settings.INVENTARIO_AGENT_TOKEN if request.user.is_superuser else "",
        "token_origem": settings.INVENTARIO_AGENT_TOKEN_ORIGEM if request.user.is_superuser else "",
        "endpoint": f"{base_url}/inventario/agente/coleta/",
        "url_detectada": url_detectada,
        "public_base_url": settings.PUBLIC_BASE_URL,
        "bases_sugeridas": bases_sugeridas,
        "usa_endereco_local": "localhost" in base_url.lower() or "127.0.0.1" in base_url,
        "instalador_windows_existe": caminho.exists(),
        "instalador_windows_nome": AGENTE_WINDOWS_EXE,
        "instalador_windows_tamanho": caminho.stat().st_size if caminho.exists() else None,
        "instalador_windows_atualizado_em": timezone.datetime.fromtimestamp(
            caminho.stat().st_mtime,
            tz=timezone.get_current_timezone(),
        )
        if caminho.exists()
        else None,
        "instalador_linux_nome": "sistema-chamados-agent-linux.sh",
    }
    return TemplateView.as_view(template_name="inventario/agente_downloads.html")(request, **contexto)


@csrf_exempt
@require_POST
def receber_coleta_agente(request):
    token_configurado = settings.INVENTARIO_AGENT_TOKEN
    autorizacao = request.headers.get("Authorization", "").strip()
    token_recebido = autorizacao[7:].strip() if autorizacao.lower().startswith("bearer ") else ""
    token_recebido = token_recebido or request.headers.get("X-Agent-Token", "").strip()
    if not token_configurado or not constant_time_compare(token_recebido, token_configurado):
        RegistroColetaAgente.objects.create(
            status=RegistroColetaAgente.Status.REJEITADA,
            mensagem="Token diferente do servidor. Reconfigure o agente com o token exibido na tela de agentes.",
            ip_origem=ip_origem_request(request),
        )
        return JsonResponse(
            {"erro": "Token invalido. Use no agente o token exibido em Inventario > Agentes de inventario."},
            status=403,
        )

    try:
        dados = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        RegistroColetaAgente.objects.create(
            status=RegistroColetaAgente.Status.ERRO,
            mensagem="JSON invalido.",
            ip_origem=ip_origem_request(request),
        )
        return JsonResponse({"erro": "JSON invalido."}, status=400)

    try:
        resposta = processar_coleta_agente(dados, ip_origem=ip_origem_request(request))
    except ColetaAgenteErro as exc:
        return JsonResponse({"erro": exc.mensagem}, status=exc.status)

    return JsonResponse(resposta)


@require_GET
def consultar_solicitacao_coleta_agente(request):
    token_configurado = settings.INVENTARIO_AGENT_TOKEN
    autorizacao = request.headers.get("Authorization", "").strip()
    token_recebido = autorizacao[7:].strip() if autorizacao.lower().startswith("bearer ") else ""
    token_recebido = token_recebido or request.headers.get("X-Agent-Token", "").strip()
    if not token_configurado or not constant_time_compare(token_recebido, token_configurado):
        return JsonResponse({"erro": "Token invalido."}, status=403)

    hostname = _normalizar_texto(request.GET.get("hostname"), 150)
    if not hostname:
        return JsonResponse({"erro": "Informe o hostname."}, status=400)

    ativo = (
        AtivoRede.objects.filter(hostname__iexact=hostname, origem=AtivoRede.Origem.AGENTE)
        .exclude(status=AtivoRede.Status.DESATIVADO)
        .order_by("-ultima_coleta_em", "-id")
        .first()
    )
    solicitada_em = ativo.coleta_solicitada_em if ativo else None
    return JsonResponse(
        {
            "coleta_solicitada": bool(solicitada_em),
            "solicitada_em": solicitada_em.isoformat() if solicitada_em else None,
        }
    )


class InventarioPainelView(LoginRequiredMixin, TemplateView):
    template_name = "inventario/painel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        todos_ativos = AtivoRede.objects.select_related("tipo", "setor")
        ativos = todos_ativos.exclude(status=AtivoRede.Status.DESATIVADO)
        ativos_painel = ativos.order_by("-atualizado_em", "nome")
        paginator = Paginator(ativos_painel, 20)
        page_obj = paginator.get_page(self.request.GET.get("page"))
        context["contadores"] = {
            "total": ativos.count(),
            "online": ativos.filter(status=AtivoRede.Status.ONLINE).count(),
            "offline": ativos.filter(status=AtivoRede.Status.OFFLINE).count(),
            "snmp": ativos.filter(origem=AtivoRede.Origem.SNMP).count(),
            "licencas": LicencaSoftware.objects.count(),
            "relacoes": RelacionamentoAtivo.objects.count(),
            "sem_comunicacao": queryset_ativos_sem_comunicacao().count(),
            "arquivados": todos_ativos.filter(status=AtivoRede.Status.DESATIVADO).count(),
        }
        context["por_tipo"] = ativos.values("tipo__nome").annotate(total=Count("id")).order_by("tipo__nome")
        context["ultimos_ativos"] = page_obj.object_list
        context["page_obj"] = page_obj
        context["paginator"] = paginator
        context["is_paginated"] = page_obj.has_other_pages()
        context["ultimas_varreduras"] = VarreduraRede.objects.select_related("faixa")[:5]
        return context


class SaudeAgentesView(LoginRequiredMixin, RedirectView):
    pattern_name = "inventario:agente_config"
    permanent = False


@login_required
@require_POST
def solicitar_coleta_agente(request, pk):
    ativo = get_object_or_404(AtivoRede, pk=pk, origem=AtivoRede.Origem.AGENTE)
    ativo.coleta_solicitada_em = timezone.now()
    ativo.save(update_fields=["coleta_solicitada_em", "atualizado_em"])
    messages.success(request, "Nova coleta solicitada. O agente atualizado verificara o pedido em ate um minuto.")
    return redirect("inventario:agente_config")


class SondaRemotaListView(LoginRequiredMixin, ListView):
    model = SondaRemota
    template_name = "inventario/sonda_list.html"
    context_object_name = "sondas"

    def get_queryset(self):
        return SondaRemota.objects.prefetch_related("faixas")


class SondaRemotaCreateView(LoginRequiredMixin, CreateView):
    model = SondaRemota
    form_class = SondaRemotaForm
    template_name = "inventario/sonda_form.html"

    def form_valid(self, form):
        token = secrets.token_urlsafe(32)
        self.object = form.save(commit=False)
        self.object.definir_token(token)
        self.object.save()
        form.save_m2m()
        self.request.session[f"sonda_token_{self.object.pk}"] = token
        messages.success(self.request, "Sonda criada. Guarde o token exibido; ele nao sera recuperado depois.")
        return redirect("inventario:sonda_detalhe", pk=self.object.pk)


class SondaRemotaUpdateView(LoginRequiredMixin, UpdateView):
    model = SondaRemota
    form_class = SondaRemotaForm
    template_name = "inventario/sonda_form.html"

    def get_success_url(self):
        return reverse_lazy("inventario:sonda_detalhe", kwargs={"pk": self.object.pk})


class SondaRemotaDetailView(LoginRequiredMixin, DetailView):
    model = SondaRemota
    template_name = "inventario/sonda_detail.html"
    context_object_name = "sonda"

    def get_queryset(self):
        return SondaRemota.objects.prefetch_related("faixas", "execucoes")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["token"] = self.request.session.get(f"sonda_token_{self.object.pk}", "")
        return context


@login_required
@require_POST
def regenerar_token_sonda(request, pk):
    sonda = get_object_or_404(SondaRemota, pk=pk)
    token = secrets.token_urlsafe(32)
    sonda.definir_token(token)
    sonda.save(update_fields=["token_hash", "token_prefixo", "atualizado_em"])
    request.session[f"sonda_token_{sonda.pk}"] = token
    messages.success(request, "Token regenerado. Atualize o script instalado na sonda.")
    return redirect("inventario:sonda_detalhe", pk=sonda.pk)


@login_required
def baixar_script_sonda(request, pk):
    sonda = get_object_or_404(SondaRemota.objects.prefetch_related("faixas"), pk=pk)
    token = request.session.get(f"sonda_token_{sonda.pk}", "")
    if not token:
        messages.error(request, "Regenerar o token e necessario antes de baixar um novo script.")
        return redirect("inventario:sonda_detalhe", pk=sonda.pk)
    template_path = settings.BASE_DIR / "scripts" / "probe" / "sonda.py.template"
    conteudo = template_path.read_text(encoding="utf-8")
    conteudo = conteudo.replace("__SERVER_URL__", _base_url_agente(request))
    conteudo = conteudo.replace("__TOKEN__", token)
    conteudo = conteudo.replace("__CIDRS__", json.dumps(list(sonda.faixas.values_list("cidr", flat=True))))
    resposta = HttpResponse(conteudo, content_type="text/x-python; charset=utf-8")
    resposta["Content-Disposition"] = f'attachment; filename="sonda-{sonda.pk}.py"'
    return resposta


@csrf_exempt
@require_POST
def receber_coleta_sonda(request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "", 1).strip()
    sonda = next((item for item in SondaRemota.objects.filter(ativa=True) if item.verificar_token(token)), None)
    if not sonda:
        return JsonResponse({"erro": "Token de sonda invalido."}, status=403)
    try:
        dados = json.loads(request.body.decode("utf-8"))
        ativos_recebidos = dados.get("ativos") or []
    except (UnicodeDecodeError, json.JSONDecodeError):
        ExecucaoSonda.objects.create(sonda=sonda, status=ExecucaoSonda.Status.ERRO, mensagem="JSON invalido")
        return JsonResponse({"erro": "JSON invalido."}, status=400)

    tipo, _ = TipoAtivo.objects.get_or_create(nome="Dispositivo descoberto")
    processados = 0
    for item in ativos_recebidos[:5000]:
        ip = _normalizar_texto(item.get("ip"), 45)
        if not ip:
            continue
        descoberta = DescobertaAtivo(
            ip=ip,
            nome=_normalizar_texto(item.get("nome"), 150) or f"Host {ip}",
            hostname=_normalizar_texto(item.get("hostname"), 150),
            observacoes=f"Detectado pela sonda {sonda.nome}. Portas: {item.get('portas') or []}",
        )
        localizar_ou_criar_ativo_descoberto(descoberta, tipo, origem=f"sonda:{sonda.pk}")
        processados += 1
    sonda.ultima_comunicacao_em = timezone.now()
    sonda.ultima_mensagem = _normalizar_texto(dados.get("mensagem"), 500) or f"{processados} ativo(s) processados"
    sonda.save(update_fields=["ultima_comunicacao_em", "ultima_mensagem", "atualizado_em"])
    ExecucaoSonda.objects.create(
        sonda=sonda,
        status=ExecucaoSonda.Status.SUCESSO,
        ativos_encontrados=processados,
        mensagem=sonda.ultima_mensagem,
    )
    return JsonResponse({"ok": True, "processados": processados})


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
        ciclo_vida = self.request.GET.get("ciclo_vida", "")
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
        else:
            queryset = queryset.exclude(status=AtivoRede.Status.DESATIVADO)
        if ciclo_vida:
            queryset = queryset.filter(ciclo_vida=ciclo_vida)
        return queryset.order_by("nome", "id")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tipos"] = TipoAtivo.objects.filter(ativo=True)
        context["status_choices"] = AtivoRede.Status.choices
        context["ciclo_vida_choices"] = AtivoRede.CicloVida.choices
        context["filtros"] = self.request.GET
        query_params = self.request.GET.copy()
        query_params.pop("page", None)
        context["querystring_sem_pagina"] = query_params.urlencode()
        context["total_sem_comunicacao"] = queryset_ativos_sem_comunicacao().count()
        return context


class AtivosSemComunicacaoView(LoginRequiredMixin, ListView):
    model = AtivoRede
    template_name = "inventario/ativos_sem_comunicacao.html"
    context_object_name = "ativos"
    paginate_by = 30

    def get_queryset(self):
        situacao = self.request.GET.get("situacao", "pendentes")
        if situacao == "arquivados":
            queryset = AtivoRede.objects.select_related("tipo", "setor").filter(
                status=AtivoRede.Status.DESATIVADO
            )
        else:
            queryset = queryset_ativos_sem_comunicacao()

        agora = timezone.now()
        ativos = list(queryset.order_by("ultima_coleta_em", "criado_em"))
        for ativo in ativos:
            referencia = ativo.ultima_coleta_em or ativo.criado_em
            ativo.dias_sem_comunicacao = max(0, (agora - referencia).days)
        return ativos

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["situacao"] = self.request.GET.get("situacao", "pendentes")
        context["dias_limite"] = settings.INVENTARIO_DIAS_SEM_COMUNICACAO
        context["total_pendentes"] = queryset_ativos_sem_comunicacao().count()
        context["total_arquivados"] = AtivoRede.objects.filter(status=AtivoRede.Status.DESATIVADO).count()
        return context


class AtivosDuplicadosView(LoginRequiredMixin, TemplateView):
    template_name = "inventario/ativos_duplicados.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        grupos = []
        campos = [
            ("numero_serie", "Numero de serie"),
            ("patrimonio", "Patrimonio"),
            ("mac", "MAC"),
            ("hostname", "Hostname"),
            ("ip", "IP"),
        ]
        ativos_base = AtivoRede.objects.select_related("tipo", "setor")
        for campo, rotulo in campos:
            consulta = ativos_base
            if campo == "ip":
                consulta = consulta.exclude(ip__isnull=True)
            else:
                consulta = consulta.exclude(**{campo: ""})
            repetidos = consulta.values(campo).annotate(total=Count("id")).filter(total__gt=1)
            for repetido in repetidos:
                valor = repetido[campo]
                ativos = list(ativos_base.filter(**{campo: valor}).order_by("id"))
                grupos.append({"campo": rotulo, "valor": valor, "ativos": ativos, "ids": ",".join(str(a.pk) for a in ativos)})
        context["grupos"] = grupos
        context["total_grupos"] = len(grupos)
        return context


class MesclarAtivosView(LoginRequiredMixin, TemplateView):
    template_name = "inventario/mesclar_ativos.html"

    def ids_sugeridos(self):
        return [int(item) for item in self.request.GET.get("ids", "").split(",") if item.isdigit()]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ids = self.ids_sugeridos()
        form = kwargs.get("form") or MesclarAtivosForm()
        if ids:
            form.fields["principal"].queryset = AtivoRede.objects.filter(pk__in=ids)
            form.fields["duplicados"].queryset = AtivoRede.objects.filter(pk__in=ids)
        context["form"] = form
        context["ativos_sugeridos"] = AtivoRede.objects.filter(pk__in=ids)
        return context

    def post(self, request, *args, **kwargs):
        form = MesclarAtivosForm(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))
        principal = form.cleaned_data["principal"]
        duplicados = list(form.cleaned_data["duplicados"])
        mesclar_ativos(principal, duplicados, request.user)
        messages.success(request, f"{len(duplicados)} registro(s) incorporado(s) ao ativo {principal.nome}.")
        return redirect(principal)


@transaction.atomic
def mesclar_ativos(principal, duplicados, usuario):
    principal = AtivoRede.objects.select_for_update().get(pk=principal.pk)
    campos = [
        "ip", "mac", "hostname", "fabricante", "modelo", "numero_serie", "patrimonio",
        "sistema_operacional", "arquitetura", "processador", "memoria_total_gb", "disco_total_gb",
        "office", "softwares_instalados", "usuario_logado", "dominio", "localizacao", "responsavel",
        "funcao", "observacoes", "ultima_coleta_em", "data_aquisicao", "garantia_ate",
    ]
    incorporados = []
    for duplicado in AtivoRede.objects.select_for_update().filter(pk__in=[item.pk for item in duplicados]).exclude(pk=principal.pk):
        incorporados.append(f"{duplicado.pk}:{duplicado.nome}")
        for campo in campos:
            atual = getattr(principal, campo)
            valor = getattr(duplicado, campo)
            if not atual and valor:
                setattr(principal, campo, valor)
        duplicado.interfaces.update(ativo=principal)
        duplicado.ocorrencias.update(ativo=principal)
        duplicado.historico_alteracoes.update(ativo=principal)
        duplicado.movimentacoes.update(ativo=principal)
        duplicado.registros_coleta.update(ativo=principal)
        duplicado.chamados.update(ativo_rede=principal)
        for licenca in duplicado.licencas.all():
            licenca.ativos.add(principal)
        RelacionamentoAtivo.objects.filter(origem=duplicado).update(origem=principal)
        RelacionamentoAtivo.objects.filter(destino=duplicado).update(destino=principal)
        RelacionamentoAtivo.objects.filter(origem=principal, destino=principal).delete()
        duplicado.delete()
    principal.save()
    HistoricoAlteracaoAtivo.objects.create(
        ativo=principal,
        campo="mesclagem",
        valor_anterior="",
        valor_novo="; ".join(incorporados),
        origem=f"mesclagem_por_{usuario.pk}",
    )


def filtrar_ativos_relatorio(params):
    form = RelatorioInventarioForm(params or None)
    ativos = (
        AtivoRede.objects.select_related("tipo", "setor")
        .exclude(status=AtivoRede.Status.DESATIVADO)
        .order_by("nome")
    )
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
        if dados.get("ciclo_vida"):
            ativos = ativos.filter(ciclo_vida=dados["ciclo_vida"])
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
    duplicados_ip = ativos.exclude(ip__isnull=True).values("ip").annotate(total=Count("id")).filter(total__gt=1)
    duplicados_mac = ativos.exclude(mac="").values("mac").annotate(total=Count("id")).filter(total__gt=1)
    duplicados_serial = ativos.exclude(numero_serie="").values("numero_serie").annotate(total=Count("id")).filter(total__gt=1)
    return {
        "total": ativos.count(),
        "online": ativos.filter(status=AtivoRede.Status.ONLINE).count(),
        "offline": ativos.filter(status=AtivoRede.Status.OFFLINE).count(),
        "sem_coleta": ativos.filter(ultima_coleta_em__isnull=True).count(),
        "sem_comunicacao": ativos.filter(filtro_ativos_sem_comunicacao()).count(),
        "ips_duplicados": duplicados_ip.count(),
        "macs_duplicados": duplicados_mac.count(),
        "seriais_duplicados": duplicados_serial.count(),
        "por_tipo": ativos.values("tipo__nome").annotate(total=Count("id")).order_by("tipo__nome"),
        "por_status": ativos.values("status").annotate(total=Count("id")).order_by("status"),
        "por_ciclo_vida": ativos.values("ciclo_vida").annotate(total=Count("id")).order_by("ciclo_vida"),
        "por_origem": ativos.values("origem").annotate(total=Count("id")).order_by("origem"),
        "por_so": (
            ativos.exclude(sistema_operacional="")
            .values("sistema_operacional")
            .annotate(total=Count("id"))
            .order_by("sistema_operacional")
        ),
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
        context["sistema_operacional_chart"] = chart_data(
            indicadores["por_so"],
            "sistema_operacional",
        )
        context["querystring"] = self.request.GET.urlencode()
        return context


@login_required
@user_passes_test(usuario_e_suporte_n2)
def exportar_ativos_xls(request):
    registrar_evento(
        RegistroAuditoria.Acao.EXPORTACAO,
        "InventarioAtivos",
        objeto="Exportacao XLS",
        usuario=request.user,
        caminho=request.path,
    )
    ativos = (
        AtivoRede.objects.select_related("tipo", "setor")
        .exclude(status=AtivoRede.Status.DESATIVADO)
        .order_by("nome")
    )
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
        "Patrimonio",
        "Ciclo de vida",
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
            ativo.patrimonio,
            ativo.get_ciclo_vida_display(),
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
def qr_code_ativo(request, pk):
    ativo = get_object_or_404(AtivoRede, pk=pk)
    import qrcode
    from qrcode.constants import ERROR_CORRECT_H

    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_H, box_size=8, border=4)
    qr.add_data(_url_publica_qr_ativo(request, ativo))
    qr.make(fit=True)
    imagem = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")
    response = HttpResponse(buffer.getvalue(), content_type="image/png")
    response["Cache-Control"] = "no-store"
    return response


def identificacao_publica_ativo(request, token):
    try:
        ativo_id = signing.loads(token, salt="inventario.ativo.qr")
    except (signing.BadSignature, ValueError, TypeError):
        raise Http404("Identificacao de ativo invalida.")
    ativo = get_object_or_404(AtivoRede.objects.select_related("tipo", "setor"), pk=ativo_id)
    return TemplateView.as_view(template_name="inventario/ativo_identificacao_publica.html")(
        request,
        ativo=ativo,
    )


@login_required
def etiqueta_ativo_pdf(request, pk):
    ativo = get_object_or_404(AtivoRede, pk=pk)
    import qrcode
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    qr = qrcode.make(_url_publica_qr_ativo(request, ativo))
    qr_buffer = io.BytesIO()
    qr.save(qr_buffer, format="PNG")
    saida = io.BytesIO()
    pdf = canvas.Canvas(saida, pagesize=A4)
    largura, altura = A4
    x, y, w, h = 40, altura - 190, 360, 130
    pdf.roundRect(x, y, w, h, 6)
    pdf.drawImage(ImageReader(io.BytesIO(qr_buffer.getvalue())), x + 10, y + 10, 110, 110)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(x + 135, y + 98, str(ativo.nome)[:34])
    pdf.setFont("Helvetica", 10)
    pdf.drawString(x + 135, y + 78, f"Patrimonio: {ativo.patrimonio or '-'}")
    pdf.drawString(x + 135, y + 62, f"Serial: {ativo.numero_serie or '-'}"[:42])
    pdf.drawString(x + 135, y + 46, f"Tipo: {ativo.tipo}")
    pdf.drawString(x + 135, y + 30, f"Setor: {ativo.setor or '-'}"[:42])
    pdf.setFont("Helvetica", 7)
    pdf.drawString(x + 135, y + 14, "Leia o QR Code para consultar a ficha no inventario.")
    pdf.save()
    resposta = HttpResponse(saida.getvalue(), content_type="application/pdf")
    resposta["Content-Disposition"] = f'inline; filename="etiqueta-ativo-{ativo.pk}.pdf"'
    return resposta


@login_required
@user_passes_test(usuario_e_suporte_n2)
def exportar_relatorio_inventario_xls(request):
    registrar_evento(
        RegistroAuditoria.Acao.EXPORTACAO,
        "RelatorioInventario",
        objeto="Exportacao XLS",
        usuario=request.user,
        caminho=request.path,
    )
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
    response.write("<p>Ativos arquivados/desativados foram excluidos deste relatorio.</p>")
    response.write(f"<p>Sem comunicacao: {indicadores['sem_comunicacao']}</p>")
    response.write(
        f"<p>Duplicidades: IP {indicadores['ips_duplicados']}, MAC {indicadores['macs_duplicados']}, "
        f"serial {indicadores['seriais_duplicados']}.</p>"
    )

    for titulo, linhas, campo in [
        ("Ativos por tipo", indicadores["por_tipo"], "tipo__nome"),
        ("Ativos por status", indicadores["por_status"], "status"),
        ("Ativos por origem", indicadores["por_origem"], "origem"),
        ("Ativos por fabricante", indicadores["por_fabricante"], "fabricante"),
        ("Sistemas operacionais", indicadores["por_so"], "sistema_operacional"),
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
        "Patrimonio",
        "Ciclo de vida",
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
            ativo.patrimonio,
            ativo.get_ciclo_vida_display(),
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
@user_passes_test(usuario_e_suporte_n2)
def exportar_relatorio_inventario_pdf(request):
    registrar_evento(
        RegistroAuditoria.Acao.EXPORTACAO,
        "RelatorioInventario",
        objeto="Exportacao PDF",
        usuario=request.user,
        caminho=request.path,
    )
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
        f"Sem comunicacao: {indicadores['sem_comunicacao']}",
        "Ativos arquivados/desativados excluidos dos totais operacionais.",
        "",
        "COBERTURA DOS DADOS",
        f"Sem fabricante: {indicadores['sem_fabricante']}",
        f"Sem modelo: {indicadores['sem_modelo']}",
        f"Sem serial: {indicadores['sem_serial']}",
        f"Com interfaces: {indicadores['com_interfaces']}",
        f"IPs duplicados: {indicadores['ips_duplicados']}",
        f"MACs duplicados: {indicadores['macs_duplicados']}",
        f"Seriais duplicados: {indicadores['seriais_duplicados']}",
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

    linhas.extend(["", "SISTEMAS OPERACIONAIS"])
    for item in indicadores["por_so"]:
        linhas.append(f"{item.get('sistema_operacional') or 'Nao informado'}: {item['total']}")

    linhas.extend(["", "LICENCAS"])
    for item in indicadores["licencas_lista"][:30]:
        licenca = item["licenca"]
        linhas.append(
            f"{licenca.nome} | {licenca.get_status_display()} | total {licenca.quantidade_total} | "
            f"uso {item['em_uso']} | saldo {item['saldo']}"
        )

    linhas.extend(["", "ATIVOS FILTRADOS", "Nome | Patrimonio | IP | Tipo | Ciclo | Status | Coleta"])
    for ativo in ativos[:200]:
        coleta = ativo.ultima_coleta_em.strftime("%d/%m/%Y %H:%M") if ativo.ultima_coleta_em else "-"
        linhas.append(
            f"{ativo.nome} | {ativo.patrimonio or '-'} | {ativo.ip or '-'} | {ativo.tipo or '-'} | "
            f"{ativo.get_ciclo_vida_display()} | {ativo.get_status_display()} | {coleta}"
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
            "interfaces", "ocorrencias", "chamados", "relacoes_origem__destino", "relacoes_destino__origem", "licencas", "historico_alteracoes", "movimentacoes", "termos_responsabilidade", "campos_externos"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["qr_public_url"] = _url_publica_qr_ativo(self.request, self.object)
        context["ocorrencia_form"] = OcorrenciaAtivoForm()
        context["relacionamento_form"] = RelacionamentoAtivoForm()
        context["varredura_form"] = VarreduraRedeForm()
        context["movimentacao_form"] = MovimentacaoAtivoForm(initial={"ciclo_novo": self.object.ciclo_vida})
        context["termo_form"] = TermoResponsabilidadeAtivoForm(initial={
            "responsavel": self.object.responsavel,
            "setor": self.object.setor,
            "data_evento": timezone.localdate(),
        })
        integracoes = []
        for integracao in IntegracaoExterna.objects.filter(ativo=True):
            integracoes.append({
                "objeto": integracao,
                "url": integracao.renderizar_url(self.object),
            })
        context["integracoes_externas"] = integracoes
        context["campo_externo_form"] = CampoExternoAtivoForm()
        return context


class SuporteN2RequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return usuario_e_suporte_n2(self.request.user)


class IntegracaoExternaListView(LoginRequiredMixin, SuporteN2RequiredMixin, ListView):
    model = IntegracaoExterna
    template_name = "inventario/integracao_list.html"
    context_object_name = "integracoes"


class IntegracaoExternaCreateView(LoginRequiredMixin, SuporteN2RequiredMixin, CreateView):
    model = IntegracaoExterna
    form_class = IntegracaoExternaForm
    template_name = "inventario/integracao_form.html"
    success_url = reverse_lazy("inventario:integracoes")

    def form_valid(self, form):
        messages.success(self.request, "Integracao experimental criada com sucesso.")
        return super().form_valid(form)


class IntegracaoExternaUpdateView(LoginRequiredMixin, SuporteN2RequiredMixin, UpdateView):
    model = IntegracaoExterna
    form_class = IntegracaoExternaForm
    template_name = "inventario/integracao_form.html"
    success_url = reverse_lazy("inventario:integracoes")

    def form_valid(self, form):
        messages.success(self.request, "Integracao experimental atualizada com sucesso.")
        return super().form_valid(form)


@login_required
def abrir_integracao_ativo(request, ativo_pk, integracao_pk):
    ativo = get_object_or_404(AtivoRede.objects.prefetch_related("campos_externos"), pk=ativo_pk)
    integracao = get_object_or_404(IntegracaoExterna, pk=integracao_pk, ativo=True)
    url = integracao.renderizar_url(ativo)
    RegistroAcessoIntegracao.objects.create(
        usuario=request.user,
        ativo=ativo,
        integracao=integracao,
        url_gerada=url,
        modo=integracao.tipo,
        ip_origem=ip_origem_request(request),
    )
    if integracao.tipo == IntegracaoExterna.Tipo.IFRAME:
        return TemplateView.as_view(template_name="inventario/integracao_iframe.html")(
            request,
            ativo=ativo,
            integracao=integracao,
            url_integracao=url,
        )
    return redirect(url)


@login_required
@user_passes_test(usuario_e_suporte_n2)
def salvar_campo_externo_ativo(request, pk):
    ativo = get_object_or_404(AtivoRede, pk=pk)
    form = CampoExternoAtivoForm(request.POST)
    if form.is_valid():
        CampoExternoAtivo.objects.update_or_create(
            ativo=ativo,
            chave=form.cleaned_data["chave"],
            defaults={
                "valor": form.cleaned_data["valor"],
                "descricao": form.cleaned_data["descricao"],
            },
        )
        messages.success(request, "Campo externo salvo para este ativo.")
    else:
        messages.error(request, "Revise o campo externo informado.")
    return redirect(ativo)


@login_required
@user_passes_test(usuario_e_suporte_n2)
def excluir_campo_externo_ativo(request, pk, campo_pk):
    ativo = get_object_or_404(AtivoRede, pk=pk)
    campo = get_object_or_404(CampoExternoAtivo, pk=campo_pk, ativo=ativo)
    if request.method == "POST":
        campo.delete()
        messages.success(request, "Campo externo removido.")
    return redirect(ativo)


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
        context["ativos_vigentes"] = self.object.ativos.exclude(status=AtivoRede.Status.DESATIVADO)
        context["ativos_arquivados"] = self.object.ativos.filter(status=AtivoRede.Status.DESATIVADO)
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
        for ativo in AtivoRede.objects.exclude(
            status=AtivoRede.Status.DESATIVADO
        ).exclude(softwares_instalados="").only("id", "nome", "softwares_instalados"):
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
@require_POST
def verificar_ativo_sem_comunicacao(request, pk):
    ativo = get_object_or_404(AtivoRede, pk=pk)
    resultado = atualizar_status_por_ping(ativo)
    if resultado == AtivoRede.Status.ONLINE:
        messages.success(request, f"{ativo.nome} respondeu e saiu da fila de revisão.")
    elif resultado == "sem_ip":
        messages.warning(request, "O ativo nao possui IP para verificacao. Revise ou arquive manualmente.")
    elif resultado == "ignorado":
        messages.info(request, "O ativo esta em manutencao ou ja foi desativado.")
    else:
        messages.warning(request, f"{ativo.nome} continua sem responder.")
    return redirect("inventario:ativos_sem_comunicacao")


@login_required
@require_POST
def arquivar_ativo_sem_comunicacao(request, pk):
    ativo = get_object_or_404(AtivoRede, pk=pk)
    if ativo.status == AtivoRede.Status.DESATIVADO:
        messages.info(request, "O ativo ja esta arquivado.")
        return redirect("inventario:ativos_sem_comunicacao")
    if not AtivoRede.objects.filter(pk=ativo.pk).filter(filtro_ativos_sem_comunicacao()).exists():
        messages.warning(request, "O ativo voltou a comunicar e nao precisa ser arquivado.")
        return redirect("inventario:ativos_sem_comunicacao")

    antes = {"status": ativo.status, "ciclo_vida": ativo.ciclo_vida, "data_baixa": ativo.data_baixa}
    ativo.status = AtivoRede.Status.DESATIVADO
    ativo.ciclo_vida = AtivoRede.CicloVida.BAIXADO
    ativo.data_baixa = timezone.localdate()
    ativo.motivo_baixa = f"Sem comunicacao por mais de {settings.INVENTARIO_DIAS_SEM_COMUNICACAO} dias."
    ativo.save(update_fields=["status", "ciclo_vida", "data_baixa", "motivo_baixa", "atualizado_em"])
    registrar_alteracoes_ativo(ativo, antes, ["status", "ciclo_vida", "data_baixa"], "revisao_sem_comunicacao")
    OcorrenciaAtivo.objects.create(
        ativo=ativo,
        tipo=OcorrenciaAtivo.Tipo.OBSERVACAO,
        titulo="Ativo arquivado por falta de comunicacao",
        descricao=(
            f"Arquivado apos mais de {settings.INVENTARIO_DIAS_SEM_COMUNICACAO} dias sem comunicacao. "
            "O registro foi preservado para revisao antes de eventual exclusao."
        ),
        registrado_por=request.user,
    )
    messages.success(request, f"{ativo.nome} foi arquivado sem perder o historico.")
    return redirect("inventario:ativos_sem_comunicacao")


@login_required
@require_POST
def reativar_ativo_arquivado(request, pk):
    ativo = get_object_or_404(AtivoRede, pk=pk, status=AtivoRede.Status.DESATIVADO)
    antes = {"status": ativo.status, "ciclo_vida": ativo.ciclo_vida, "data_baixa": ativo.data_baixa}
    ativo.status = AtivoRede.Status.DESCONHECIDO
    ativo.ciclo_vida = AtivoRede.CicloVida.EM_USO
    ativo.data_baixa = None
    ativo.motivo_baixa = ""
    ativo.save(update_fields=["status", "ciclo_vida", "data_baixa", "motivo_baixa", "atualizado_em"])
    registrar_alteracoes_ativo(ativo, antes, ["status", "ciclo_vida", "data_baixa"], "reativacao_manual")
    OcorrenciaAtivo.objects.create(
        ativo=ativo,
        tipo=OcorrenciaAtivo.Tipo.OBSERVACAO,
        titulo="Ativo reativado",
        descricao="Ativo devolvido ao inventario ativo durante a revisao dos arquivados.",
        registrado_por=request.user,
    )
    messages.success(request, f"{ativo.nome} foi reativado.")
    return redirect("inventario:ativos_sem_comunicacao")


@login_required
@require_POST
def arquivar_ativo(request, pk):
    ativo = get_object_or_404(AtivoRede, pk=pk)
    if ativo.status == AtivoRede.Status.DESATIVADO:
        messages.info(request, "O ativo ja esta arquivado.")
        return redirect(ativo)

    antes = {"status": ativo.status, "ciclo_vida": ativo.ciclo_vida, "data_baixa": ativo.data_baixa}
    ativo.status = AtivoRede.Status.DESATIVADO
    ativo.ciclo_vida = AtivoRede.CicloVida.BAIXADO
    ativo.data_baixa = timezone.localdate()
    ativo.motivo_baixa = f"Arquivamento manual realizado por {request.user.get_username()}."
    ativo.save(update_fields=["status", "ciclo_vida", "data_baixa", "motivo_baixa", "atualizado_em"])
    registrar_alteracoes_ativo(
        ativo,
        antes,
        ["status", "ciclo_vida", "data_baixa"],
        "arquivamento_manual",
    )
    OcorrenciaAtivo.objects.create(
        ativo=ativo,
        tipo=OcorrenciaAtivo.Tipo.OBSERVACAO,
        titulo="Ativo arquivado manualmente",
        descricao="Registro retirado dos relatorios operacionais e enviado para revisao antes da exclusao.",
        registrado_por=request.user,
    )
    messages.success(request, f"{ativo.nome} foi arquivado. Agora ele pode ser excluido definitivamente.")
    return redirect(ativo)


@login_required
@require_POST
def excluir_ativo_arquivado(request, pk):
    ativo = get_object_or_404(AtivoRede, pk=pk, status=AtivoRede.Status.DESATIVADO)
    nome = ativo.nome
    ativo.delete()
    messages.success(request, f"Ativo arquivado {nome} excluido definitivamente.")
    return redirect("inventario:ativos_sem_comunicacao")


@login_required
def excluir_ativo(request, pk):
    ativo = get_object_or_404(AtivoRede, pk=pk)
    if request.method == "POST":
        if ativo.status != AtivoRede.Status.DESATIVADO:
            messages.warning(request, "Arquive o ativo antes de realizar a exclusao definitiva.")
            return redirect("inventario:ativos_sem_comunicacao")
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
        elegiveis = AtivoRede.objects.filter(id__in=ids, status=AtivoRede.Status.DESATIVADO)
        if not elegiveis.exists():
            messages.warning(request, "Somente ativos arquivados podem ser excluidos definitivamente.")
            return redirect("inventario:ativos_sem_comunicacao")
        total_ativos = elegiveis.count()
        elegiveis.delete()
        messages.success(request, f"{total_ativos} ativo(s) excluído(s) do inventário.")
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
    antes = {"status": ativo.status, "ultima_coleta_em": ativo.ultima_coleta_em}
    campos_alterados = []
    if ativo.status != novo_status:
        ativo.status = novo_status
        campos_alterados.append("status")
    if novo_status == AtivoRede.Status.ONLINE:
        ativo.ultima_coleta_em = timezone.now()
        campos_alterados.append("ultima_coleta_em")
    if campos_alterados:
        ativo.save(update_fields=[*campos_alterados, "atualizado_em"])
        registrar_alteracoes_ativo(ativo, antes, campos_alterados, "validacao_ping")
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


@login_required
@require_POST
def movimentar_ativo(request, pk):
    ativo = get_object_or_404(AtivoRede, pk=pk)
    form = MovimentacaoAtivoForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Revise os dados da movimentacao.")
        return redirect(ativo)
    movimento = form.save(commit=False)
    movimento.ativo = ativo
    movimento.setor_origem = ativo.setor
    movimento.local_origem = ativo.localizacao
    movimento.responsavel_origem = ativo.responsavel
    movimento.ciclo_anterior = ativo.ciclo_vida
    movimento.movimentado_por = request.user
    movimento.save()

    antes = {
        "setor": ativo.setor,
        "localizacao": ativo.localizacao,
        "responsavel": ativo.responsavel,
        "ciclo_vida": ativo.ciclo_vida,
        "status": ativo.status,
        "data_baixa": ativo.data_baixa,
    }
    ativo.setor = movimento.setor_destino
    ativo.localizacao = movimento.local_destino
    ativo.responsavel = movimento.responsavel_destino
    ativo.ciclo_vida = movimento.ciclo_novo
    if movimento.ciclo_novo in {AtivoRede.CicloVida.BAIXADO, AtivoRede.CicloVida.DESCARTADO}:
        ativo.status = AtivoRede.Status.DESATIVADO
        ativo.data_baixa = timezone.localdate()
        ativo.motivo_baixa = movimento.motivo
    elif ativo.status == AtivoRede.Status.DESATIVADO:
        ativo.status = AtivoRede.Status.DESCONHECIDO
        ativo.data_baixa = None
        ativo.motivo_baixa = ""
    ativo.save()
    registrar_alteracoes_ativo(
        ativo,
        antes,
        ["setor", "localizacao", "responsavel", "ciclo_vida", "status", "data_baixa"],
        "movimentacao",
    )
    messages.success(request, "Movimentacao patrimonial registrada.")
    return redirect(ativo)


@login_required
@require_POST
def criar_termo_responsabilidade(request, pk):
    ativo = get_object_or_404(AtivoRede, pk=pk)
    form = TermoResponsabilidadeAtivoForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Revise os dados do termo de responsabilidade.")
        return redirect(ativo)
    termo = form.save(commit=False)
    termo.ativo = ativo
    termo.criado_por = request.user
    termo.aceite_em = timezone.now()
    termo.texto_termo = (
        f"O responsavel {termo.responsavel}, matricula {termo.matricula or '-'}, declara receber/devolver "
        f"o equipamento {ativo.nome}, patrimonio {ativo.patrimonio or '-'}, serial {ativo.numero_serie or '-'}, "
        "comprometendo-se com sua guarda, uso institucional e devolucao nas condicoes registradas."
    )
    termo.save()
    antes = {"responsavel": ativo.responsavel, "setor": ativo.setor, "ciclo_vida": ativo.ciclo_vida}
    if termo.tipo in {TermoResponsabilidadeAtivo.Tipo.ENTREGA, TermoResponsabilidadeAtivo.Tipo.EMPRESTIMO}:
        ativo.responsavel = termo.responsavel
        ativo.setor = termo.setor
        ativo.ciclo_vida = (
            AtivoRede.CicloVida.EMPRESTADO if termo.tipo == TermoResponsabilidadeAtivo.Tipo.EMPRESTIMO
            else AtivoRede.CicloVida.EM_USO
        )
    elif termo.tipo == TermoResponsabilidadeAtivo.Tipo.DEVOLUCAO:
        ativo.responsavel = ""
        ativo.ciclo_vida = AtivoRede.CicloVida.ESTOQUE
    ativo.save(update_fields=["responsavel", "setor", "ciclo_vida", "atualizado_em"])
    registrar_alteracoes_ativo(ativo, antes, ["responsavel", "setor", "ciclo_vida"], "termo_responsabilidade")
    messages.success(request, "Termo registrado e disponivel em PDF.")
    return redirect(ativo)


@login_required
def termo_responsabilidade_pdf(request, pk):
    termo = get_object_or_404(TermoResponsabilidadeAtivo.objects.select_related("ativo", "setor"), pk=pk)
    ativo = termo.ativo
    linhas = [
        "TERMO DE RESPONSABILIDADE DE EQUIPAMENTO",
        "",
        f"Tipo: {termo.get_tipo_display()}",
        f"Data: {termo.data_evento:%d/%m/%Y}",
        f"Responsavel: {termo.responsavel}",
        f"Matricula: {termo.matricula or '-'}",
        f"Setor: {termo.setor or '-'}",
        "",
        f"Equipamento: {ativo.nome}",
        f"Tipo: {ativo.tipo}",
        f"Patrimonio: {ativo.patrimonio or '-'}",
        f"Serial: {ativo.numero_serie or '-'}",
        f"Fabricante/modelo: {ativo.fabricante or '-'} / {ativo.modelo or '-'}",
        "",
        termo.texto_termo,
        "",
        f"Finalidade/observacoes: {termo.finalidade or '-'}",
        f"Aceite registrado em: {termo.aceite_em:%d/%m/%Y %H:%M:%S}",
        f"Assinatura declarada por: {termo.assinatura_nome or termo.responsavel}",
        "",
        "Assinatura: ______________________________________________",
    ]
    resposta = HttpResponse(montar_pdf(linhas), content_type="application/pdf")
    resposta["Content-Disposition"] = f'inline; filename="termo-{termo.pk}.pdf"'
    return resposta


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


def localizar_ou_criar_ativo_descoberto(item, tipo_padrao, origem="varredura"):
    ativo = localizar_ativo_por_identidade(
        serial=getattr(item, "numero_serie", ""),
        mac=getattr(item, "mac", ""),
        hostname=item.hostname or item.nome,
        ip=item.ip or None,
    )

    if ativo:
        aplicar_descoberta_no_ativo(ativo, item, origem=origem)
        return ativo, False

    ativo = AtivoRede.objects.create(
        ip=item.ip or None,
        hostname=item.hostname,
        nome=item.nome or item.hostname or "Ativo descoberto",
        tipo=tipo_padrao,
        status=AtivoRede.Status.DESCONHECIDO,
        origem=item.origem,
        mac=item.mac,
        fabricante=item.fabricante,
        modelo=item.modelo,
        numero_serie=item.numero_serie,
        sistema_operacional=item.sistema_operacional,
        localizacao=item.localizacao,
        observacoes=item.observacoes,
        ultima_coleta_em=timezone.now(),
    )
    sincronizar_interfaces_descobertas(ativo, item)
    return ativo, True


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
            if not item.observacoes:
                item.observacoes = mensagem_pre_inventario(metodo, portas)
            localizar_ou_criar_ativo_descoberto(item, tipo_padrao, origem="varredura manual")
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
        localizar_ou_criar_ativo_descoberto(item, tipo_padrao, origem="varredura agendada")
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
