import json
import socket

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import FileResponse, Http404, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView
from core.models import ConfiguracaoInstitucional

from .forms import (
    AtivoRedeForm,
    AgendamentoVarreduraForm,
    CredencialSNMPForm,
    FaixaRedeForm,
    LicencaSoftwareForm,
    OcorrenciaAtivoForm,
    RelacionamentoAtivoForm,
    TipoAtivoForm,
    VarreduraRedeForm,
)
from .models import (
    AgendamentoVarredura,
    AtivoRede,
    CredencialSNMP,
    FaixaRede,
    InterfaceRede,
    LicencaSoftware,
    MetodoDescoberta,
    OcorrenciaAtivo,
    RelacionamentoAtivo,
    TipoAtivo,
    VarreduraRede,
)
from .services import descobrir_por_faixa


AGENTE_WINDOWS_EXE = "SistemaChamadosAgentSetup.exe"
AGENTE_LINUX_INSTALLER = "install.sh"


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


@login_required
def baixar_agente_windows(request):
    caminho = (settings.BASE_DIR / "dist" / AGENTE_WINDOWS_EXE).resolve()
    base_dist = (settings.BASE_DIR / "dist").resolve()
    if not str(caminho).startswith(str(base_dist)) or not caminho.exists():
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
    caminho = (settings.BASE_DIR / "dist" / AGENTE_WINDOWS_EXE).resolve()
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
        "token": settings.INVENTARIO_AGENT_TOKEN,
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
        messages.success(self.request, "Ativo atualizado com sucesso.")
        return super().form_valid(form)


class AtivoRedeDetailView(LoginRequiredMixin, DetailView):
    model = AtivoRede
    template_name = "inventario/ativo_detail.html"
    context_object_name = "ativo"

    def get_queryset(self):
        return AtivoRede.objects.select_related("tipo", "setor").prefetch_related(
            "interfaces", "ocorrencias", "chamados", "relacoes_origem__destino", "relacoes_destino__origem", "licencas"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ocorrencia_form"] = OcorrenciaAtivoForm()
        context["relacionamento_form"] = RelacionamentoAtivoForm()
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
                    "sistema_operacional": item.sistema_operacional,
                    "observacoes": item.observacoes or mensagem_pre_inventario(metodo, portas),
                    "ultima_coleta_em": timezone.now(),
                },
            )
            if not criado:
                ativo.origem = item.origem
                ativo.hostname = item.hostname or ativo.hostname
                ativo.sistema_operacional = item.sistema_operacional or ativo.sistema_operacional
                ativo.observacoes = item.observacoes or ativo.observacoes
                ativo.ultima_coleta_em = timezone.now()
                ativo.save(update_fields=["origem", "hostname", "sistema_operacional", "observacoes", "ultima_coleta_em", "atualizado_em"])
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
                "sistema_operacional": item.sistema_operacional,
                "observacoes": item.observacoes,
                "ultima_coleta_em": timezone.now(),
            },
        )
        if not criado:
            ativo.origem = item.origem
            ativo.hostname = item.hostname or ativo.hostname
            ativo.sistema_operacional = item.sistema_operacional or ativo.sistema_operacional
            ativo.observacoes = item.observacoes or ativo.observacoes
            ativo.ultima_coleta_em = timezone.now()
            ativo.save(update_fields=["origem", "hostname", "sistema_operacional", "observacoes", "ultima_coleta_em", "atualizado_em"])
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
    return (
        f"Varredura {MetodoDescoberta.Codigo(metodo).label} concluída. "
        f"Ativos encontrados: {encontrados}. "
        f"{'Portas: ' + portas + '. ' if portas else ''}"
    )
