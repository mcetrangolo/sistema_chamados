from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView
from core.models import ConfiguracaoInstitucional

from .forms import (
    AtivoRedeForm,
    AgendamentoVarreduraForm,
    CredencialSNMPForm,
    FaixaRedeForm,
    OcorrenciaAtivoForm,
    TipoAtivoForm,
    VarreduraRedeForm,
)
from .models import AgendamentoVarredura, AtivoRede, CredencialSNMP, FaixaRede, MetodoDescoberta, OcorrenciaAtivo, TipoAtivo, VarreduraRede
from .services import descobrir_por_faixa


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
    cabecalhos = ["Nome", "Tipo", "IP", "MAC", "Hostname", "Setor", "Fabricante", "Modelo", "Serial", "Status", "Origem"]
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
            "interfaces", "ocorrencias", "chamados"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ocorrencia_form"] = OcorrenciaAtivoForm()
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
