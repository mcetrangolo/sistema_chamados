from pathlib import Path
from html import escape
from io import BytesIO
import socket

from django.contrib import messages
from django.core.files import File
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import Group
from django.db.models.deletion import ProtectedError
from django.db.models import Avg, Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView
from core.models import ConfiguracaoInstitucional

from .forms import (
    AtualizacaoChamadoForm,
    AnexoChamadoForm,
    ArtigoConhecimentoForm,
    AtribuicaoChamadoForm,
    AvaliacaoChamadoForm,
    CategoriaForm,
    ChamadoForm,
    CampoServicoCatalogoForm,
    ComentarioInternoForm,
    ComentarioPortalForm,
    ConsultaChamadoForm,
    EquipeAtendimentoForm,
    PortalChamadoForm,
    RegraSLAForm,
    RelatorioChamadosForm,
    MudancaForm,
    ProblemaForm,
    RespostaProntaForm,
    ServicoCatalogoForm,
    SetorForm,
    SolicitacaoServicoForm,
    TarefaChamadoForm,
    TecnicoForm,
    TopicoAjudaForm,
)
from .models import (
    AnexoChamado,
    ArtigoConhecimento,
    AprovacaoSolicitacao,
    AvaliacaoChamado,
    Categoria,
    Chamado,
    CampoServicoCatalogo,
    ComentarioChamado,
    EquipeAtendimento,
    HistoricoChamado,
    RegraSLA,
    Mudanca,
    Problema,
    RespostaPronta,
    ServicoCatalogo,
    Setor,
    SolicitacaoServico,
    TarefaChamado,
    TopicoAjuda,
)


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


def obter_ip_cliente(request):
    encaminhado = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if encaminhado:
        return encaminhado.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def resolver_hostname_cliente(ip_cliente):
    if not ip_cliente:
        return ""
    try:
        return socket.gethostbyaddr(ip_cliente)[0]
    except (socket.herror, socket.gaierror, OSError):
        return ""


def detectar_ativo_cliente(request):
    from inventario.models import AtivoRede

    ip_cliente = obter_ip_cliente(request)
    hostname_cliente = resolver_hostname_cliente(ip_cliente)
    ativo = None

    if ip_cliente:
        ativo = AtivoRede.objects.filter(ip=ip_cliente).first()

    if not ativo and hostname_cliente:
        hostname_curto = hostname_cliente.split(".")[0]
        ativo = (
            AtivoRede.objects.filter(
                Q(hostname__iexact=hostname_cliente)
                | Q(nome__iexact=hostname_cliente)
                | Q(hostname__iexact=hostname_curto)
                | Q(nome__iexact=hostname_curto)
            )
            .order_by("nome")
            .first()
        )

    return ativo, ip_cliente, hostname_cliente


class PortalChamadoCreateView(CreateView):
    model = Chamado
    form_class = PortalChamadoForm
    template_name = "chamados/public/abrir_chamado.html"
    success_url = reverse_lazy("chamados:portal_consultar")

    def dispatch(self, request, *args, **kwargs):
        (
            self.ativo_detectado,
            self.ip_cliente,
            self.hostname_cliente,
        ) = detectar_ativo_cliente(request)
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        if self.ativo_detectado:
            initial["ativo_rede"] = self.ativo_detectado.pk
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "ativo_detectado": self.ativo_detectado,
                "ip_cliente": self.ip_cliente,
                "hostname_cliente": self.hostname_cliente,
            }
        )
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ativo_detectado"] = self.ativo_detectado
        context["ip_cliente"] = self.ip_cliente
        context["hostname_cliente"] = self.hostname_cliente
        return context

    def form_valid(self, form):
        if self.ativo_detectado and not form.instance.ativo_rede_id:
            form.instance.ativo_rede = self.ativo_detectado
        response = super().form_valid(form)
        comentario = "Chamado aberto pelo portal."
        if self.ativo_detectado:
            comentario += f" Ativo detectado automaticamente: {self.ativo_detectado}."
        HistoricoChamado.objects.create(
            chamado=self.object,
            status=self.object.status,
            comentario=comentario,
        )
        messages.success(
            self.request,
            f"Chamado aberto com sucesso. Guarde o número {self.object.numero}.",
        )
        return response


class PortalConsultaView(TemplateView):
    template_name = "chamados/public/consultar_chamado.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = kwargs.get("form") or ConsultaChamadoForm()
        context["comentario_form"] = kwargs.get("comentario_form") or ComentarioPortalForm()
        context["anexo_form"] = kwargs.get("anexo_form") or AnexoChamadoForm()
        context["avaliacao_form"] = kwargs.get("avaliacao_form") or AvaliacaoChamadoForm()
        context["chamado"] = kwargs.get("chamado")
        return context

    def post(self, request, *args, **kwargs):
        form = ConsultaChamadoForm(request.POST)
        chamado = None
        if form.is_valid():
            chamado = Chamado.objects.filter(
                numero__iexact=form.cleaned_data["numero"].strip(),
                email__iexact=form.cleaned_data["email"].strip(),
            ).first()
            if not chamado:
                messages.error(request, "Chamado não localizado com os dados informados.")
        return self.render_to_response(self.get_context_data(form=form, chamado=chamado))


class PainelView(LoginRequiredMixin, TemplateView):
    template_name = "chamados/painel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chamados = Chamado.objects.all()
        abertos = chamados.exclude(
            status__in=[Chamado.Status.ENCERRADO, Chamado.Status.CANCELADO]
        )

        context["contadores"] = {
            "total": chamados.count(),
            "abertos": chamados.filter(status=Chamado.Status.ABERTO).count(),
            "em_atendimento": chamados.filter(status=Chamado.Status.EM_ATENDIMENTO).count(),
            "aguardando": chamados.filter(
                status__in=[
                    Chamado.Status.AGUARDANDO_USUARIO,
                    Chamado.Status.AGUARDANDO_FORNECEDOR,
                ]
            ).count(),
            "resolvidos": chamados.filter(status=Chamado.Status.RESOLVIDO).count(),
            "encerrados": chamados.filter(status=Chamado.Status.ENCERRADO).count(),
            "atrasados": chamados.filter(vencimento_em__lt=timezone.now()).exclude(
                status__in=[Chamado.Status.RESOLVIDO, Chamado.Status.ENCERRADO, Chamado.Status.CANCELADO]
            ).count(),
            "reabertos": chamados.filter(comentarios__mensagem__icontains="reabertura").distinct().count(),
            "nao_atribuidos": abertos.filter(tecnico_responsavel__isnull=True).count(),
            "criticos": abertos.filter(prioridade=Chamado.Prioridade.CRITICA).count(),
            "sem_primeira_resposta": abertos.filter(primeira_resposta_em__isnull=True).count(),
        }
        total_com_sla = abertos.filter(vencimento_em__isnull=False).count()
        dentro_sla = abertos.filter(vencimento_em__gte=timezone.now()).count()
        context["sla_operacional"] = {
            "total_com_sla": total_com_sla,
            "dentro": dentro_sla,
            "fora": context["contadores"]["atrasados"],
            "percentual": round((dentro_sla / total_com_sla) * 100, 1) if total_com_sla else None,
        }
        context["ultimos_chamados"] = Chamado.objects.select_related(
            "setor", "categoria", "equipe_responsavel", "tecnico_responsavel"
        )[:10]
        context["backlog_por_prioridade"] = list(
            abertos.values("prioridade").annotate(total=Count("id")).order_by("prioridade")
        )
        context["status_chart"] = {
            "labels": [label for _, label in Chamado.Status.choices],
            "data": [chamados.filter(status=value).count() for value, _ in Chamado.Status.choices],
        }
        context["categoria_chart"] = {
            "labels": list(
                chamados.values_list("categoria__nome", flat=True)
                .order_by("categoria__nome")
                .distinct()
            ),
            "data": [
                chamados.filter(categoria__nome=nome).count()
                for nome in chamados.values_list("categoria__nome", flat=True)
                .order_by("categoria__nome")
                .distinct()
            ],
        }
        context["tecnico_chart"] = {
            "labels": [
                item["tecnico_responsavel__username"] or "Não atribuído"
                for item in chamados.values("tecnico_responsavel__username")
                .annotate(total=Count("id"))
                .order_by("tecnico_responsavel__username")
            ],
            "data": [
                item["total"]
                for item in chamados.values("tecnico_responsavel__username")
                .annotate(total=Count("id"))
                .order_by("tecnico_responsavel__username")
            ],
        }
        context["tipo_chart"] = {
            "labels": [label for _, label in Chamado.Tipo.choices],
            "data": [chamados.filter(tipo=value).count() for value, _ in Chamado.Tipo.choices],
        }
        context["avaliacao_media"] = chamados.filter(avaliacao__isnull=False).aggregate(
            media=Avg("avaliacao__nota")
        )["media"]
        context["volume_mensal"] = (
            chamados.extra(select={"mes": "strftime('%%Y-%%m', criado_em)"})
            .values("mes")
            .annotate(total=Count("id"))
            .order_by("-mes")[:6]
        )
        context["top_categorias"] = (
            chamados.values("categoria__nome")
            .annotate(total=Count("id"))
            .order_by("-total")[:5]
        )
        try:
            from contratos.models import ContratoPublico
            from inventario.models import AtivoRede, LicencaSoftware

            contratos = ContratoPublico.objects.all()
            limite_coleta = timezone.now() - timezone.timedelta(days=7)
            context["indicadores_executivos"] = {
                "contratos_a_vencer": sum(1 for contrato in contratos if contrato.em_alerta),
                "contratos_vencidos": sum(1 for contrato in contratos if contrato.vencido),
                "agentes_sem_coleta": AtivoRede.objects.filter(
                    origem=AtivoRede.Origem.AGENTE,
                    ultima_coleta_em__lt=limite_coleta,
                ).count(),
                "licencas_vencidas": LicencaSoftware.objects.filter(status=LicencaSoftware.Status.VENCIDA).count(),
            }
        except Exception:
            context["indicadores_executivos"] = {}
        return context


class ChamadoListView(LoginRequiredMixin, ListView):
    model = Chamado
    template_name = "chamados/chamado_list.html"
    context_object_name = "chamados"
    paginate_by = 15

    def get_queryset(self):
        queryset = Chamado.objects.select_related(
            "setor", "categoria", "equipe_responsavel", "tecnico_responsavel", "solicitante"
        )
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        tipo = self.request.GET.get("tipo", "")
        setor = self.request.GET.get("setor", "")
        prioridade = self.request.GET.get("prioridade", "")
        categoria = self.request.GET.get("categoria", "")
        equipe = self.request.GET.get("equipe", "")
        data_inicio = self.request.GET.get("data_inicio", "")
        data_fim = self.request.GET.get("data_fim", "")

        if q:
            queryset = queryset.filter(
                Q(numero__icontains=q)
                | Q(nome_solicitante__icontains=q)
                | Q(email__icontains=q)
                | Q(descricao__icontains=q)
                | Q(tipo__icontains=q)
            )
        if status:
            queryset = queryset.filter(status=status)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if setor:
            queryset = queryset.filter(setor_id=setor)
        if prioridade:
            queryset = queryset.filter(prioridade=prioridade)
        if categoria:
            queryset = queryset.filter(categoria_id=categoria)
        if equipe:
            queryset = queryset.filter(equipe_responsavel_id=equipe)
        if data_inicio:
            queryset = queryset.filter(criado_em__date__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(criado_em__date__lte=data_fim)
        fila = self.kwargs.get("fila")
        if fila == "meus":
            queryset = queryset.filter(tecnico_responsavel=self.request.user)
        elif fila == "nao-atribuidos":
            queryset = queryset.filter(tecnico_responsavel__isnull=True)
        elif fila == "atrasados":
            queryset = queryset.filter(
                vencimento_em__lt=timezone.now()
            ).exclude(
                status__in=[
                    Chamado.Status.RESOLVIDO,
                    Chamado.Status.ENCERRADO,
                    Chamado.Status.CANCELADO,
                ]
            )
        elif fila == "abertos":
            queryset = queryset.exclude(
                status__in=[Chamado.Status.ENCERRADO, Chamado.Status.CANCELADO]
            )
        elif fila == "problemas":
            queryset = queryset.filter(tipo=Chamado.Tipo.PROBLEMA)
        elif fila == "mudancas":
            queryset = queryset.filter(tipo=Chamado.Tipo.MUDANCA)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = Chamado.Status.choices
        context["tipo_choices"] = Chamado.Tipo.choices
        context["prioridade_choices"] = Chamado.Prioridade.choices
        context["setores"] = Setor.objects.filter(ativo=True)
        context["categorias"] = Categoria.objects.filter(ativo=True)
        context["equipes"] = EquipeAtendimento.objects.filter(ativo=True)
        context["filtros"] = self.request.GET
        context["fila"] = self.kwargs.get("fila", "todos")
        return context


class ChamadoCreateView(LoginRequiredMixin, CreateView):
    model = Chamado
    form_class = ChamadoForm
    template_name = "chamados/chamado_form.html"

    def form_valid(self, form):
        form.instance.solicitante = self.request.user
        form.instance.origem = Chamado.Origem.INTERNO
        response = super().form_valid(form)
        HistoricoChamado.objects.create(
            chamado=self.object,
            usuario=self.request.user,
            status=self.object.status,
            comentario="Chamado aberto pela equipe de TI.",
        )
        messages.success(self.request, "Chamado aberto com sucesso.")
        return response


class ChamadoDetailView(LoginRequiredMixin, DetailView):
    model = Chamado
    template_name = "chamados/chamado_detail.html"
    context_object_name = "chamado"

    def get_queryset(self):
        return Chamado.objects.select_related(
            "setor", "categoria", "equipe_responsavel", "tecnico_responsavel", "solicitante"
        ).prefetch_related("historico", "anexos", "tarefas", "comentarios")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tarefa_form"] = TarefaChamadoForm()
        context["comentario_form"] = ComentarioInternoForm(initial={"publico": True})
        context["anexo_form"] = AnexoChamadoForm()
        context["atribuicao_form"] = AtribuicaoChamadoForm(instance=self.object)
        context["aprovacao_pendente"] = AprovacaoSolicitacao.objects.filter(
            solicitacao_servico__chamado=self.object,
            status=AprovacaoSolicitacao.Status.PENDENTE,
        ).first()
        return context


class ChamadoPrintView(LoginRequiredMixin, DetailView):
    model = Chamado
    template_name = "chamados/chamado_print.html"
    context_object_name = "chamado"

    def get_queryset(self):
        return Chamado.objects.select_related(
            "setor",
            "categoria",
            "topico_ajuda",
            "equipe_responsavel",
            "tecnico_responsavel",
            "solicitante",
            "ativo_rede",
        ).prefetch_related("historico", "anexos", "tarefas", "comentarios")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["emitido_em"] = timezone.now()
        return context


class ChamadoUpdateView(LoginRequiredMixin, UpdateView):
    model = Chamado
    form_class = AtualizacaoChamadoForm
    template_name = "chamados/chamado_update.html"

    def form_valid(self, form):
        status_anterior = Chamado.objects.get(pk=self.object.pk).status
        response = super().form_valid(form)
        registro = form.cleaned_data.get("registro_atendimento", "").strip()

        if status_anterior != self.object.status or registro:
            if registro and not self.object.primeira_resposta_em:
                self.object.primeira_resposta_em = timezone.now()
                self.object.save(update_fields=["primeira_resposta_em", "atualizado_em"])
            HistoricoChamado.objects.create(
                chamado=self.object,
                usuario=self.request.user,
                status=self.object.status,
                comentario=registro,
            )

        messages.success(self.request, "Chamado atualizado com sucesso.")
        return response


class SetorListView(LoginRequiredMixin, ListView):
    model = Setor
    template_name = "chamados/cadastros/setor_list.html"
    context_object_name = "setores"


class SetorCreateView(LoginRequiredMixin, CreateView):
    model = Setor
    form_class = SetorForm
    template_name = "chamados/cadastros/setor_form.html"
    success_url = reverse_lazy("chamados:setores")

    def form_valid(self, form):
        messages.success(self.request, "Setor cadastrado com sucesso.")
        return super().form_valid(form)


class SetorUpdateView(LoginRequiredMixin, UpdateView):
    model = Setor
    form_class = SetorForm
    template_name = "chamados/cadastros/setor_form.html"
    success_url = reverse_lazy("chamados:setores")

    def form_valid(self, form):
        messages.success(self.request, "Setor atualizado com sucesso.")
        return super().form_valid(form)

def excluir_cadastro(request, model, pk, redirect_name, nome_cadastro, campo_nome="nome"):
    objeto = get_object_or_404(model, pk=pk)
    nome = getattr(objeto, campo_nome, None) or str(objeto)
    try:
        objeto.delete()
        messages.success(request, f"{nome_cadastro} {nome} excluido com sucesso.")
    except ProtectedError:
        messages.warning(
            request,
            f"Este {nome_cadastro.lower()} possui registros vinculados. Para ocultar, edite e desmarque Ativo.",
        )
    return redirect(redirect_name)


@login_required
@require_POST
def excluir_setor(request, pk):
    return excluir_cadastro(request, Setor, pk, "chamados:setores", "Setor")


class CategoriaListView(LoginRequiredMixin, ListView):
    model = Categoria
    template_name = "chamados/cadastros/categoria_list.html"
    context_object_name = "categorias"


class CategoriaCreateView(LoginRequiredMixin, CreateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "chamados/cadastros/categoria_form.html"
    success_url = reverse_lazy("chamados:categorias")

    def form_valid(self, form):
        messages.success(self.request, "Categoria cadastrada com sucesso.")
        return super().form_valid(form)


class CategoriaUpdateView(LoginRequiredMixin, UpdateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = "chamados/cadastros/categoria_form.html"
    success_url = reverse_lazy("chamados:categorias")

    def form_valid(self, form):
        messages.success(self.request, "Categoria atualizada com sucesso.")
        return super().form_valid(form)


@login_required
@require_POST
def excluir_categoria(request, pk):
    return excluir_cadastro(request, Categoria, pk, "chamados:categorias", "Categoria")


class EquipeAtendimentoListView(LoginRequiredMixin, ListView):
    model = EquipeAtendimento
    template_name = "chamados/cadastros/equipe_list.html"
    context_object_name = "equipes"


class EquipeAtendimentoCreateView(LoginRequiredMixin, CreateView):
    model = EquipeAtendimento
    form_class = EquipeAtendimentoForm
    template_name = "chamados/cadastros/equipe_form.html"
    success_url = reverse_lazy("chamados:equipes")

    def form_valid(self, form):
        messages.success(self.request, "Equipe cadastrada com sucesso.")
        return super().form_valid(form)


class EquipeAtendimentoUpdateView(LoginRequiredMixin, UpdateView):
    model = EquipeAtendimento
    form_class = EquipeAtendimentoForm
    template_name = "chamados/cadastros/equipe_form.html"
    success_url = reverse_lazy("chamados:equipes")

    def form_valid(self, form):
        messages.success(self.request, "Equipe atualizada com sucesso.")
        return super().form_valid(form)


@login_required
@require_POST
def excluir_equipe(request, pk):
    return excluir_cadastro(request, EquipeAtendimento, pk, "chamados:equipes", "Equipe")


class RegraSLAListView(LoginRequiredMixin, ListView):
    model = RegraSLA
    template_name = "chamados/cadastros/sla_list.html"
    context_object_name = "regras"


class RegraSLACreateView(LoginRequiredMixin, CreateView):
    model = RegraSLA
    form_class = RegraSLAForm
    template_name = "chamados/cadastros/sla_form.html"
    success_url = reverse_lazy("chamados:sla_regras")

    def form_valid(self, form):
        messages.success(self.request, "Regra de SLA cadastrada com sucesso.")
        return super().form_valid(form)


class RegraSLAUpdateView(LoginRequiredMixin, UpdateView):
    model = RegraSLA
    form_class = RegraSLAForm
    template_name = "chamados/cadastros/sla_form.html"
    success_url = reverse_lazy("chamados:sla_regras")

    def form_valid(self, form):
        messages.success(self.request, "Regra de SLA atualizada com sucesso.")
        return super().form_valid(form)


@login_required
@require_POST
def excluir_sla(request, pk):
    return excluir_cadastro(request, RegraSLA, pk, "chamados:sla_regras", "Regra de SLA")


class TopicoAjudaListView(LoginRequiredMixin, ListView):
    model = TopicoAjuda
    template_name = "chamados/cadastros/topico_list.html"
    context_object_name = "topicos"


class TopicoAjudaCreateView(LoginRequiredMixin, CreateView):
    model = TopicoAjuda
    form_class = TopicoAjudaForm
    template_name = "chamados/cadastros/topico_form.html"
    success_url = reverse_lazy("chamados:topicos")

    def form_valid(self, form):
        messages.success(self.request, "Tópico de ajuda cadastrado com sucesso.")
        return super().form_valid(form)


class TopicoAjudaUpdateView(LoginRequiredMixin, UpdateView):
    model = TopicoAjuda
    form_class = TopicoAjudaForm
    template_name = "chamados/cadastros/topico_form.html"
    success_url = reverse_lazy("chamados:topicos")

    def form_valid(self, form):
        messages.success(self.request, "Tópico de ajuda atualizado com sucesso.")
        return super().form_valid(form)


@login_required
@require_POST
def excluir_topico(request, pk):
    return excluir_cadastro(request, TopicoAjuda, pk, "chamados:topicos", "Topico")


class RespostaProntaListView(LoginRequiredMixin, ListView):
    model = RespostaPronta
    template_name = "chamados/cadastros/resposta_list.html"
    context_object_name = "respostas"


class RespostaProntaCreateView(LoginRequiredMixin, CreateView):
    model = RespostaPronta
    form_class = RespostaProntaForm
    template_name = "chamados/cadastros/resposta_form.html"
    success_url = reverse_lazy("chamados:respostas")

    def form_valid(self, form):
        messages.success(self.request, "Resposta pronta cadastrada com sucesso.")
        return super().form_valid(form)


class RespostaProntaUpdateView(LoginRequiredMixin, UpdateView):
    model = RespostaPronta
    form_class = RespostaProntaForm
    template_name = "chamados/cadastros/resposta_form.html"
    success_url = reverse_lazy("chamados:respostas")

    def form_valid(self, form):
        messages.success(self.request, "Resposta pronta atualizada com sucesso.")
        return super().form_valid(form)


@login_required
@require_POST
def excluir_resposta(request, pk):
    return excluir_cadastro(request, RespostaPronta, pk, "chamados:respostas", "Resposta pronta", "titulo")


class ArtigoConhecimentoPublicListView(ListView):
    model = ArtigoConhecimento
    template_name = "chamados/public/conhecimento_list.html"
    context_object_name = "artigos"

    def get_queryset(self):
        queryset = ArtigoConhecimento.objects.filter(ativo=True, publico=True).select_related("topico_ajuda")
        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(
                Q(titulo__icontains=q) | Q(resumo__icontains=q) | Q(conteudo__icontains=q)
            )
        return queryset


class ArtigoConhecimentoPublicDetailView(DetailView):
    model = ArtigoConhecimento
    template_name = "chamados/public/conhecimento_detail.html"
    context_object_name = "artigo"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return ArtigoConhecimento.objects.filter(ativo=True, publico=True).select_related("topico_ajuda")


class ArtigoConhecimentoListView(LoginRequiredMixin, ListView):
    model = ArtigoConhecimento
    template_name = "chamados/cadastros/artigo_list.html"
    context_object_name = "artigos"


class ArtigoConhecimentoCreateView(LoginRequiredMixin, CreateView):
    model = ArtigoConhecimento
    form_class = ArtigoConhecimentoForm
    template_name = "chamados/cadastros/artigo_form.html"
    success_url = reverse_lazy("chamados:artigos")

    def form_valid(self, form):
        messages.success(self.request, "Artigo criado com sucesso.")
        return super().form_valid(form)


class ArtigoConhecimentoUpdateView(LoginRequiredMixin, UpdateView):
    model = ArtigoConhecimento
    form_class = ArtigoConhecimentoForm
    template_name = "chamados/cadastros/artigo_form.html"
    success_url = reverse_lazy("chamados:artigos")

    def form_valid(self, form):
        messages.success(self.request, "Artigo atualizado com sucesso.")
        return super().form_valid(form)


@login_required
@require_POST
def excluir_artigo(request, pk):
    return excluir_cadastro(request, ArtigoConhecimento, pk, "chamados:artigos", "Artigo", "titulo")


class CatalogoServicoListView(ListView):
    model = ServicoCatalogo
    template_name = "chamados/public/catalogo_list.html"
    context_object_name = "servicos"

    def get_queryset(self):
        queryset = (
            ServicoCatalogo.objects.filter(ativo=True)
            .select_related("categoria", "topico_ajuda")
        )
        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(Q(nome__icontains=q) | Q(descricao__icontains=q))
        return queryset


class CatalogoServicoSolicitarView(TemplateView):
    template_name = "chamados/public/catalogo_solicitar.html"
    servicos_governanca = {
        "acesso-a-internetwi-fi": "/governanca/wifi-corporativo/",
        "novo-usuario-de-rede": "/governanca/usuario-acesso/?tipo=novo_acesso",
        "troca-de-senha": "/governanca/usuario-acesso/?tipo=troca_senha",
    }

    def get_servico(self):
        return get_object_or_404(ServicoCatalogo, slug=self.kwargs["slug"], ativo=True)

    def dispatch(self, request, *args, **kwargs):
        destino = self.servicos_governanca.get(kwargs.get("slug"))
        if destino:
            return redirect(destino)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        servico = self.get_servico()
        context["servico"] = servico
        context["form"] = kwargs.get("form") or SolicitacaoServicoForm(servico=servico)
        return context

    def post(self, request, *args, **kwargs):
        servico = self.get_servico()
        form = SolicitacaoServicoForm(request.POST, servico=servico)
        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.servico = servico
            solicitacao.save()
            chamado = criar_chamado_de_solicitacao(solicitacao)
            if servico.requer_aprovacao:
                AprovacaoSolicitacao.objects.create(
                    origem=AprovacaoSolicitacao.Origem.CATALOGO,
                    solicitacao_servico=solicitacao,
                    titulo=f"Aprovar serviço: {servico.nome}",
                    solicitante=solicitacao.nome,
                )
                mensagem = f"Solicitação registrada para aprovação. Protocolo {solicitacao.protocolo}; chamado {chamado.numero}."
            else:
                mensagem = f"Solicitação registrada. Protocolo {solicitacao.protocolo}; chamado {chamado.numero}."
            messages.success(
                request,
                mensagem,
            )
            return redirect("chamados:portal_consultar")
        return self.render_to_response(self.get_context_data(form=form))


class ServicoCatalogoListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = ServicoCatalogo
    template_name = "chamados/cadastros/servico_list.html"
    context_object_name = "servicos"


class ServicoCatalogoCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = ServicoCatalogo
    form_class = ServicoCatalogoForm
    template_name = "chamados/cadastros/servico_form.html"
    success_url = reverse_lazy("chamados:servicos")

    def form_valid(self, form):
        messages.success(self.request, "Serviço cadastrado com sucesso.")
        return super().form_valid(form)


class ServicoCatalogoUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = ServicoCatalogo
    form_class = ServicoCatalogoForm
    template_name = "chamados/cadastros/servico_form.html"
    success_url = reverse_lazy("chamados:servicos")

    def form_valid(self, form):
        messages.success(self.request, "Serviço atualizado com sucesso.")
        return super().form_valid(form)


@login_required
@user_passes_test(lambda user: user.is_superuser)
@require_POST
def excluir_servico(request, pk):
    return excluir_cadastro(request, ServicoCatalogo, pk, "chamados:servicos", "Servico")


class CampoServicoCatalogoListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = CampoServicoCatalogo
    template_name = "chamados/cadastros/campo_servico_list.html"
    context_object_name = "campos"

    def dispatch(self, request, *args, **kwargs):
        self.servico = get_object_or_404(ServicoCatalogo, pk=kwargs["servico_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.servico.campos.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["servico"] = self.servico
        return context


class CampoServicoCatalogoCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = CampoServicoCatalogo
    form_class = CampoServicoCatalogoForm
    template_name = "chamados/cadastros/campo_servico_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.servico = get_object_or_404(ServicoCatalogo, pk=kwargs["servico_pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.servico = self.servico
        messages.success(self.request, "Campo cadastrado com sucesso.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("chamados:servico_campos", kwargs={"servico_pk": self.servico.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["servico"] = self.servico
        return context


class CampoServicoCatalogoUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = CampoServicoCatalogo
    form_class = CampoServicoCatalogoForm
    template_name = "chamados/cadastros/campo_servico_form.html"

    def get_queryset(self):
        return CampoServicoCatalogo.objects.select_related("servico")

    def get_success_url(self):
        return reverse_lazy("chamados:servico_campos", kwargs={"servico_pk": self.object.servico.pk})

    def form_valid(self, form):
        messages.success(self.request, "Campo atualizado com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["servico"] = self.object.servico
        return context


@login_required
@user_passes_test(lambda user: user.is_superuser)
@require_POST
def excluir_campo_servico(request, pk):
    campo = get_object_or_404(CampoServicoCatalogo.objects.select_related("servico"), pk=pk)
    servico_pk = campo.servico.pk
    nome = campo.rotulo
    campo.delete()
    messages.success(request, f"Campo {nome} excluido com sucesso.")
    return redirect("chamados:servico_campos", servico_pk=servico_pk)


class ProblemaListView(LoginRequiredMixin, ListView):
    model = Problema
    template_name = "chamados/problema_list.html"
    context_object_name = "problemas"
    paginate_by = 20

    def get_queryset(self):
        queryset = Problema.objects.select_related("responsavel", "chamado_principal")
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        if q:
            queryset = queryset.filter(Q(titulo__icontains=q) | Q(causa_raiz__icontains=q) | Q(workaround__icontains=q))
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = Problema.Status.choices
        context["filtros"] = self.request.GET
        return context


class ProblemaCreateView(LoginRequiredMixin, CreateView):
    model = Problema
    form_class = ProblemaForm
    template_name = "chamados/problema_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Problema registrado com sucesso.")
        return super().form_valid(form)


class ProblemaUpdateView(LoginRequiredMixin, UpdateView):
    model = Problema
    form_class = ProblemaForm
    template_name = "chamados/problema_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Problema atualizado com sucesso.")
        return super().form_valid(form)


class ProblemaDetailView(LoginRequiredMixin, DetailView):
    model = Problema
    template_name = "chamados/problema_detail.html"
    context_object_name = "problema"

    def get_queryset(self):
        return Problema.objects.select_related("responsavel", "chamado_principal").prefetch_related("chamados_relacionados")


class MudancaListView(LoginRequiredMixin, ListView):
    model = Mudanca
    template_name = "chamados/mudanca_list.html"
    context_object_name = "mudancas"
    paginate_by = 20

    def get_queryset(self):
        queryset = Mudanca.objects.select_related("responsavel", "aprovador", "chamado")
        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        risco = self.request.GET.get("risco", "")
        if q:
            queryset = queryset.filter(Q(titulo__icontains=q) | Q(impacto__icontains=q) | Q(plano_execucao__icontains=q))
        if status:
            queryset = queryset.filter(status=status)
        if risco:
            queryset = queryset.filter(risco=risco)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = Mudanca.Status.choices
        context["risco_choices"] = Mudanca.Risco.choices
        context["filtros"] = self.request.GET
        return context


class MudancaCreateView(LoginRequiredMixin, CreateView):
    model = Mudanca
    form_class = MudancaForm
    template_name = "chamados/mudanca_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Mudanca registrada com sucesso.")
        return super().form_valid(form)


class MudancaUpdateView(LoginRequiredMixin, UpdateView):
    model = Mudanca
    form_class = MudancaForm
    template_name = "chamados/mudanca_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Mudanca atualizada com sucesso.")
        return super().form_valid(form)


class MudancaDetailView(LoginRequiredMixin, DetailView):
    model = Mudanca
    template_name = "chamados/mudanca_detail.html"
    context_object_name = "mudanca"

    def get_queryset(self):
        return Mudanca.objects.select_related("responsavel", "aprovador", "chamado")


class BuscaGlobalView(LoginRequiredMixin, TemplateView):
    template_name = "chamados/busca_global.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get("q", "").strip()
        data_inicio = self.request.GET.get("data_inicio", "")
        data_fim = self.request.GET.get("data_fim", "")
        context["q"] = q
        context["data_inicio"] = data_inicio
        context["data_fim"] = data_fim
        context["chamados"] = []
        context["ativos"] = []
        context["artigos"] = []
        context["servicos"] = []
        if q or data_inicio or data_fim:
            chamados = Chamado.objects.select_related("setor", "categoria", "tecnico_responsavel")
            if q:
                chamados = chamados.filter(
                    Q(numero__icontains=q)
                    | Q(nome_solicitante__icontains=q)
                    | Q(email__icontains=q)
                    | Q(descricao__icontains=q)
                    | Q(tipo__icontains=q)
                    | Q(setor__nome__icontains=q)
                    | Q(categoria__nome__icontains=q)
                    | Q(status__icontains=q)
                )
            if data_inicio:
                chamados = chamados.filter(criado_em__date__gte=data_inicio)
            if data_fim:
                chamados = chamados.filter(criado_em__date__lte=data_fim)
            context["chamados"] = chamados[:25]
        if q:
            try:
                from inventario.models import AtivoRede

                context["ativos"] = AtivoRede.objects.filter(
                    Q(nome__icontains=q)
                    | Q(ip__icontains=q)
                    | Q(mac__icontains=q)
                    | Q(hostname__icontains=q)
                    | Q(numero_serie__icontains=q)
                ).select_related("tipo", "setor")[:10]
            except Exception:
                context["ativos"] = []
            context["artigos"] = ArtigoConhecimento.objects.filter(
                Q(titulo__icontains=q) | Q(resumo__icontains=q) | Q(conteudo__icontains=q)
            )[:10]
            context["servicos"] = ServicoCatalogo.objects.filter(
                Q(nome__icontains=q) | Q(descricao__icontains=q)
            )[:10]
        return context


class AprovacaoListView(LoginRequiredMixin, ListView):
    model = AprovacaoSolicitacao
    template_name = "chamados/aprovacao_list.html"
    context_object_name = "aprovacoes"
    paginate_by = 25


@login_required
def decidir_aprovacao(request, pk, decisao):
    aprovacao = get_object_or_404(AprovacaoSolicitacao, pk=pk)
    chamado_destino = aprovacao.solicitacao_servico.chamado if aprovacao.solicitacao_servico else None
    if request.method == "POST" and aprovacao.status == AprovacaoSolicitacao.Status.PENDENTE:
        aprovacao.aprovado_por = request.user
        aprovacao.observacao = request.POST.get("observacao", "").strip()
        aprovacao.decidido_em = timezone.now()
        if decisao == "aprovar":
            aprovacao.status = AprovacaoSolicitacao.Status.APROVADA
            if aprovacao.solicitacao_servico:
                chamado = aprovacao.solicitacao_servico.chamado
                if not chamado:
                    chamado = criar_chamado_de_solicitacao(aprovacao.solicitacao_servico)
                chamado.aprovacao_necessaria = True
                chamado.aprovado_por = request.user
                chamado.aprovado_em = timezone.now()
                chamado.status = Chamado.Status.ABERTO
                chamado.save(update_fields=["aprovacao_necessaria", "aprovado_por", "aprovado_em", "status", "atualizado_em"])
                HistoricoChamado.objects.create(
                    chamado=chamado,
                    usuario=request.user,
                    status=chamado.status,
                    comentario=f"Solicitacao aprovada. {aprovacao.observacao}",
                )
            elif aprovacao.origem == AprovacaoSolicitacao.Origem.GOVERNANCA and aprovacao.governanca_id:
                criar_chamado_de_governanca(aprovacao.governanca_id)
            messages.success(request, "Solicitação aprovada.")
        else:
            aprovacao.status = AprovacaoSolicitacao.Status.REJEITADA
            if aprovacao.solicitacao_servico and aprovacao.solicitacao_servico.chamado:
                chamado = aprovacao.solicitacao_servico.chamado
                chamado.status = Chamado.Status.CANCELADO
                chamado.save(update_fields=["status", "atualizado_em"])
                HistoricoChamado.objects.create(
                    chamado=chamado,
                    usuario=request.user,
                    status=chamado.status,
                    comentario=f"Solicitacao rejeitada. {aprovacao.observacao}",
                )
            if aprovacao.origem == AprovacaoSolicitacao.Origem.GOVERNANCA and aprovacao.governanca_id:
                from governanca.models import SolicitacaoGovernanca

                SolicitacaoGovernanca.objects.filter(pk=aprovacao.governanca_id).update(
                    status=SolicitacaoGovernanca.Status.NEGADA,
                    atualizado_em=timezone.now(),
                )
            messages.success(request, "Solicitação rejeitada.")
        aprovacao.save()
    if chamado_destino:
        return redirect(chamado_destino)
    return redirect("chamados:aprovacoes")


def criar_chamado_de_solicitacao(solicitacao):
    servico = solicitacao.servico
    detalhes_personalizados = []
    for item in (solicitacao.dados_personalizados or {}).values():
        detalhes_personalizados.append(f"{item.get('rotulo')}: {item.get('valor')}")
    detalhes = solicitacao.detalhes
    if detalhes_personalizados:
        detalhes = f"{detalhes}\n\nCampos do formulario:\n" + "\n".join(detalhes_personalizados)
    chamado = Chamado.objects.create(
        nome_solicitante=solicitacao.nome,
        email=solicitacao.email,
        telefone=solicitacao.telefone,
        setor=solicitacao.setor,
        categoria=servico.categoria,
        topico_ajuda=servico.topico_ajuda,
        equipe_responsavel=servico.equipe_padrao,
        tipo=servico.tipo_chamado,
        prioridade=servico.prioridade_padrao,
        descricao=f"Solicitação de serviço: {servico.nome}\n\n{detalhes}",
        origem=Chamado.Origem.PORTAL,
        status=Chamado.Status.AGUARDANDO_APROVACAO if servico.requer_aprovacao else Chamado.Status.ABERTO,
        aprovacao_necessaria=servico.requer_aprovacao,
        tecnico_responsavel=servico.aprovador_padrao if servico.requer_aprovacao else None,
    )
    solicitacao.chamado = chamado
    solicitacao.status = SolicitacaoServico.Status.CONVERTIDA
    solicitacao.save(update_fields=["chamado", "status"])
    HistoricoChamado.objects.create(
        chamado=chamado,
        status=chamado.status,
        comentario=f"Chamado criado pelo catálogo de serviços ({solicitacao.protocolo}).",
    )
    notificar_chamado(chamado, "Chamado aberto", "Sua solicitação foi convertida em chamado.")
    return chamado


def criar_chamado_de_governanca(governanca_id):
    from governanca.models import SolicitacaoGovernanca

    solicitacao = get_object_or_404(SolicitacaoGovernanca, pk=governanca_id)
    setor, _ = Setor.objects.get_or_create(nome=solicitacao.setor, defaults={"ativo": True})
    categoria, _ = Categoria.objects.get_or_create(nome="Governança", defaults={"ativo": True})
    detalhes = [
        f"Solicitação de governança: {solicitacao.get_tipo_display()}",
        f"Protocolo: {solicitacao.protocolo}",
        f"Matrícula: {solicitacao.matricula}",
        f"Cargo: {solicitacao.cargo or '-'}",
        "",
    ]
    if solicitacao.acessos_solicitados:
        detalhes.extend(["Acessos solicitados:", solicitacao.acessos_solicitados, ""])
    if solicitacao.tipo_solicitacao_rede:
        detalhes.extend(["Tipo de solicitação:", solicitacao.get_tipo_solicitacao_rede_display(), ""])
    if solicitacao.usuario_rede_existente:
        detalhes.extend(["Usuário de rede existente:", solicitacao.usuario_rede_existente, ""])
    if solicitacao.chefia_imediata:
        detalhes.extend(["Chefia/autorizador informado:", solicitacao.chefia_imediata, ""])
    if solicitacao.aparelhos:
        detalhes.extend(["Aparelhos:", solicitacao.aparelhos, ""])
    detalhes.extend(
        [
            "Justificativa:",
            solicitacao.justificativa or "-",
            "",
            "Aceite registrado:",
            f"Versão: {solicitacao.termo_versao or '-'}",
            f"Data/hora: {solicitacao.termo_aceito_em:%d/%m/%Y %H:%M:%S}" if solicitacao.termo_aceito_em else "Data/hora: -",
            f"IP: {solicitacao.termo_aceito_ip or '-'}",
        ]
    )

    chamado = Chamado.objects.create(
        nome_solicitante=solicitacao.nome,
        email=solicitacao.email,
        telefone=solicitacao.telefone,
        setor=setor,
        categoria=categoria,
        prioridade=Chamado.Prioridade.MEDIA,
        descricao="\n".join(detalhes),
        origem=Chamado.Origem.PORTAL,
    )
    solicitacao.status = SolicitacaoGovernanca.Status.EM_ANALISE
    solicitacao.save(update_fields=["status", "atualizado_em"])

    if not solicitacao.documento_caminho:
        from governanca.pdf import gerar_documento_solicitacao

        solicitacao.documento_caminho = gerar_documento_solicitacao(solicitacao)
        solicitacao.save(update_fields=["documento_caminho", "atualizado_em"])

    pdf_path = Path(solicitacao.documento_caminho or "")
    if pdf_path.is_file():
        with pdf_path.open("rb") as arquivo:
            anexo = AnexoChamado(
                chamado=chamado,
                descricao=f"Formulário {solicitacao.protocolo}",
                nome_enviado_por=solicitacao.nome,
                publico=True,
            )
            anexo.arquivo.save(pdf_path.name, File(arquivo), save=True)

    HistoricoChamado.objects.create(
        chamado=chamado,
        status=chamado.status,
        comentario=f"Chamado criado a partir da solicitação de governança {solicitacao.protocolo}.",
    )
    notificar_chamado(chamado, "Chamado aberto", "Sua solicitação de governança foi aprovada e convertida em chamado.")
    return chamado


class TecnicoListView(LoginRequiredMixin, ListView):
    template_name = "chamados/cadastros/tecnico_list.html"
    context_object_name = "tecnicos"

    def get_queryset(self):
        grupo = Group.objects.filter(name="Técnicos de TI").first()
        users = get_user_model().objects.filter(is_active=True)
        if grupo:
            users = users.filter(groups=grupo)
        else:
            users = users.filter(is_staff=True)
        return users.order_by("first_name", "username")


class TecnicoCreateView(LoginRequiredMixin, CreateView):
    form_class = TecnicoForm
    template_name = "chamados/cadastros/tecnico_form.html"
    success_url = reverse_lazy("chamados:tecnicos")

    def form_valid(self, form):
        messages.success(self.request, "Atendente cadastrado com sucesso.")
        return super().form_valid(form)


@login_required
@require_POST
def desativar_tecnico(request, pk):
    tecnico = get_object_or_404(get_user_model(), pk=pk)
    if tecnico == request.user:
        messages.warning(request, "Nao e possivel desativar o proprio usuario logado.")
        return redirect("chamados:tecnicos")
    tecnico.is_active = False
    tecnico.save(update_fields=["is_active"])
    messages.success(request, f"Atendente {tecnico.get_full_name() or tecnico.username} desativado com sucesso.")
    return redirect("chamados:tecnicos")


AGRUPAMENTO_MAP = {
    "status": ("status", "Status"),
    "tipo": ("tipo", "Tipo"),
    "atendente": ("tecnico_responsavel__username", "Atendente"),
    "setor": ("setor__nome", "Setor"),
    "categoria": ("categoria__nome", "Categoria"),
    "prioridade": ("prioridade", "Prioridade"),
}


def filtrar_chamados_relatorio(params):
    form = RelatorioChamadosForm(params or None)
    chamados = Chamado.objects.select_related("setor", "categoria", "tecnico_responsavel")

    if form.is_valid():
        dados = form.cleaned_data
        if dados.get("data_inicio"):
            chamados = chamados.filter(criado_em__date__gte=dados["data_inicio"])
        if dados.get("data_fim"):
            chamados = chamados.filter(criado_em__date__lte=dados["data_fim"])
        if dados.get("status"):
            chamados = chamados.filter(status=dados["status"])
        if dados.get("tipo"):
            chamados = chamados.filter(tipo=dados["tipo"])
        if dados.get("prioridade"):
            chamados = chamados.filter(prioridade=dados["prioridade"])
        if dados.get("setor"):
            chamados = chamados.filter(setor=dados["setor"])
        if dados.get("categoria"):
            chamados = chamados.filter(categoria=dados["categoria"])
        if dados.get("atendente"):
            chamados = chamados.filter(tecnico_responsavel=dados["atendente"])

    return form, chamados


def resumo_relatorio(chamados, agrupamento):
    campo, titulo = AGRUPAMENTO_MAP.get(agrupamento, AGRUPAMENTO_MAP["status"])
    linhas = chamados.values(campo).annotate(total=Count("id")).order_by(campo)
    return campo, titulo, linhas


def linhas_analiticas(chamados):
    return chamados.order_by("-criado_em")[:500]


def nome_atendente(chamado):
    if chamado.tecnico_responsavel:
        return chamado.tecnico_responsavel.get_full_name() or chamado.tecnico_responsavel.username
    return "Não atribuído"


def dados_inventario_relatorio():
    try:
        from inventario.models import AtivoRede
    except Exception:
        return {
            "disponivel": False,
            "total": 0,
            "por_status": [],
            "por_tipo": [],
            "por_so": [],
            "por_office": [],
            "ativos": [],
        }

    ativos = AtivoRede.objects.select_related("tipo", "setor").order_by("nome")
    return {
        "disponivel": True,
        "total": ativos.count(),
        "por_status": ativos.values("status").annotate(total=Count("id")).order_by("status"),
        "por_tipo": ativos.values("tipo__nome").annotate(total=Count("id")).order_by("tipo__nome"),
        "por_so": (
            ativos.exclude(sistema_operacional="")
            .values("sistema_operacional")
            .annotate(total=Count("id"))
            .order_by("sistema_operacional")
        ),
        "por_office": (
            ativos.exclude(office="")
            .values("office")
            .annotate(total=Count("id"))
            .order_by("office")
        ),
        "ativos": ativos[:500],
    }


def chart_data(linhas, label_field):
    return {
        "labels": [linha.get(label_field) or "Nao informado" for linha in linhas],
        "data": [linha["total"] for linha in linhas],
    }


class RelatorioChamadosView(LoginRequiredMixin, TemplateView):
    template_name = "chamados/relatorio.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form, chamados = filtrar_chamados_relatorio(self.request.GET)
        agrupamento = form.cleaned_data.get("agrupamento") if form.is_valid() else "status"
        campo_agrupamento, titulo_agrupamento, resumo = resumo_relatorio(
            chamados, agrupamento or "status"
        )

        context["total"] = chamados.count()
        context["form"] = form
        context["resumo"] = resumo
        context["campo_agrupamento"] = campo_agrupamento
        context["titulo_agrupamento"] = titulo_agrupamento
        context["chamados"] = linhas_analiticas(chamados)
        context["abertos"] = chamados.exclude(
            status__in=[Chamado.Status.ENCERRADO, Chamado.Status.CANCELADO]
        ).count()
        context["resolvidos"] = chamados.filter(status=Chamado.Status.RESOLVIDO).count()
        context["encerrados"] = chamados.filter(status=Chamado.Status.ENCERRADO).count()
        context["sla_vencidos"] = chamados.filter(vencimento_em__lt=timezone.now()).exclude(
            status__in=[Chamado.Status.RESOLVIDO, Chamado.Status.ENCERRADO, Chamado.Status.CANCELADO]
        ).count()
        context["avaliacao_media"] = chamados.filter(avaliacao__isnull=False).aggregate(
            media=Avg("avaliacao__nota")
        )["media"]
        context["servicos_mais_solicitados"] = (
            SolicitacaoServico.objects.values("servico__nome")
            .annotate(total=Count("id"))
            .order_by("-total")[:10]
        )
        inventario = dados_inventario_relatorio()
        context["inventario"] = inventario
        context["inventario_so_chart"] = chart_data(inventario["por_so"], "sistema_operacional")
        context["inventario_office_chart"] = chart_data(inventario["por_office"], "office")
        context["inventario_tipo_chart"] = chart_data(inventario["por_tipo"], "tipo__nome")
        context["inventario_status_chart"] = chart_data(inventario["por_status"], "status")
        context["querystring"] = self.request.GET.urlencode()
        return context


@login_required
def exportar_relatorio_xls(request):
    form, chamados = filtrar_chamados_relatorio(request.GET)
    agrupamento = form.cleaned_data.get("agrupamento") if form.is_valid() else "status"
    campo_agrupamento, titulo_agrupamento, resumo = resumo_relatorio(
        chamados, agrupamento or "status"
    )
    inventario = dados_inventario_relatorio()

    response = HttpResponse(content_type="application/vnd.ms-excel; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="relatorio_chamados.xls"'
    response.write("<html><head><meta charset='utf-8'></head><body>")
    config = ConfiguracaoInstitucional.atual()
    if config.logo:
        logo_url = request.build_absolute_uri(config.logo.url)
        response.write(f"<p><img src='{escape(logo_url)}' style='max-height:80px;max-width:220px'></p>")
    response.write(f"<h1>{escape(config.nome_instituicao)}</h1>")
    response.write(f"<p>{escape(config.cnpj)} {escape(config.endereco)}</p>")
    response.write("<h1>Relatório de chamados</h1>")
    response.write(f"<p>Total: {chamados.count()}</p>")
    response.write(f"<h2>Agrupamento por {escape(titulo_agrupamento)}</h2>")
    response.write("<table border='1'><tr><th>Grupo</th><th>Total</th></tr>")
    for linha in resumo:
        valor = linha.get(campo_agrupamento) or "Não informado"
        response.write(f"<tr><td>{escape(str(valor))}</td><td>{linha['total']}</td></tr>")
    response.write("</table><br>")
    response.write("<table border='1'><tr>")
    cabecalhos = [
        "Número",
        "Tipo",
        "Abertura",
        "Solicitante",
        "Setor",
        "Categoria",
        "Prioridade",
        "Status",
        "Atendente",
    ]
    for cabecalho in cabecalhos:
        response.write(f"<th>{escape(cabecalho)}</th>")
    response.write("</tr>")
    for chamado in linhas_analiticas(chamados):
        valores = [
            chamado.numero,
            chamado.get_tipo_display(),
            chamado.criado_em.strftime("%d/%m/%Y %H:%M"),
            chamado.nome_solicitante,
            chamado.setor.nome,
            chamado.categoria.nome,
            chamado.get_prioridade_display(),
            chamado.get_status_display(),
            nome_atendente(chamado),
        ]
        response.write("<tr>")
        for valor in valores:
            response.write(f"<td>{escape(str(valor))}</td>")
        response.write("</tr>")
    response.write("</table><br>")

    response.write("<h1>Inventario</h1>")
    response.write(f"<p>Total de ativos: {inventario['total']}</p>")
    for titulo, linhas, campo in [
        ("Inventario por status", inventario["por_status"], "status"),
        ("Inventario por tipo", inventario["por_tipo"], "tipo__nome"),
        ("Sistemas operacionais instalados", inventario["por_so"], "sistema_operacional"),
        ("Office / Microsoft 365", inventario["por_office"], "office"),
    ]:
        response.write(f"<h2>{escape(titulo)}</h2>")
        response.write("<table border='1'><tr><th>Grupo</th><th>Total</th></tr>")
        for linha in linhas:
            response.write(f"<tr><td>{escape(str(linha.get(campo) or 'Nao informado'))}</td><td>{linha['total']}</td></tr>")
        response.write("</table><br>")

    response.write("<h2>Equipamentos inventariados</h2>")
    cabecalhos_inventario = [
        "Equipamento",
        "IP",
        "MAC",
        "Tipo",
        "Setor",
        "Fabricante",
        "Modelo",
        "SO",
        "Office",
        "CPU",
        "Memoria GB",
        "Disco GB",
        "Serial",
        "Usuario",
        "Ultima coleta",
    ]
    response.write("<table border='1'><tr>")
    for cabecalho in cabecalhos_inventario:
        response.write(f"<th>{escape(cabecalho)}</th>")
    response.write("</tr>")
    for ativo in inventario["ativos"]:
        valores = [
            ativo.nome,
            ativo.ip or "",
            ativo.mac,
            ativo.tipo.nome if ativo.tipo else "",
            ativo.setor.nome if ativo.setor else "",
            ativo.fabricante,
            ativo.modelo,
            ativo.sistema_operacional,
            ativo.office,
            ativo.processador,
            ativo.memoria_total_gb or "",
            ativo.disco_total_gb or "",
            ativo.numero_serie,
            ativo.usuario_logado,
            ativo.ultima_coleta_em.strftime("%d/%m/%Y %H:%M") if ativo.ultima_coleta_em else "",
        ]
        response.write("<tr>")
        for valor in valores:
            response.write(f"<td>{escape(str(valor))}</td>")
        response.write("</tr>")
    response.write("</table></body></html>")
    return response


def pdf_escape(texto):
    return str(texto).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def montar_pdf_simples(linhas):
    comandos = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"]
    for linha in linhas[:48]:
        comandos.append(f"({pdf_escape(linha)}) Tj")
        comandos.append("T*")
    comandos.append("ET")
    stream = "\n".join(comandos).encode("latin-1", "replace")
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for indice, objeto in enumerate(objetos, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{indice} 0 obj\n".encode())
        pdf.extend(objeto)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        f"trailer << /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    )
    return bytes(pdf)


@login_required
def exportar_relatorio_pdf(request):
    form, chamados = filtrar_chamados_relatorio(request.GET)
    agrupamento = form.cleaned_data.get("agrupamento") if form.is_valid() else "status"
    campo_agrupamento, titulo_agrupamento, resumo = resumo_relatorio(
        chamados, agrupamento or "status"
    )

    config = ConfiguracaoInstitucional.atual()
    inventario = dados_inventario_relatorio()
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas
    except Exception:
        linhas = [
            config.nome_instituicao,
            f"CNPJ: {config.cnpj or '-'}",
            f"Endereco: {config.endereco or '-'}",
            "",
            "Relatorio de chamados",
            f"Total: {chamados.count()}",
            f"Agrupamento por {titulo_agrupamento}",
            f"Total de ativos inventariados: {inventario['total']}",
            "",
        ]
        for linha in resumo:
            valor = linha.get(campo_agrupamento) or "Nao informado"
            linhas.append(f"{valor}: {linha['total']}")

        response = HttpResponse(montar_pdf_simples(linhas), content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="relatorio_chamados.pdf"'
        return response

    fonte_regular = "Helvetica"
    fonte_negrito = "Helvetica-Bold"
    fontes_candidatas = [
        (
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
            "ArialUnicodeApp",
            "ArialUnicodeAppBold",
        ),
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            "DejaVuSansApp",
            "DejaVuSansAppBold",
        ),
    ]
    for regular, negrito, nome_regular, nome_negrito in fontes_candidatas:
        if regular.exists() and negrito.exists():
            try:
                pdfmetrics.registerFont(TTFont(nome_regular, str(regular)))
                pdfmetrics.registerFont(TTFont(nome_negrito, str(negrito)))
                fonte_regular = nome_regular
                fonte_negrito = nome_negrito
                break
            except Exception:
                continue

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4
    margem = 18 * mm
    y = altura - margem

    def nova_pagina():
        nonlocal y
        pdf.showPage()
        y = altura - margem

    def escrever_linha(texto, x=margem, tamanho=9, negrito=False, cor=colors.black):
        nonlocal y
        if y < margem:
            nova_pagina()
        pdf.setFillColor(cor)
        pdf.setFont(fonte_negrito if negrito else fonte_regular, tamanho)
        pdf.drawString(x, y, str(texto)[:120])
        y -= 5 * mm

    logo_path = ""
    if config.logo:
        try:
            logo_path = config.logo.path
        except Exception:
            logo_path = ""
    if logo_path:
        try:
            pdf.drawImage(ImageReader(logo_path), margem, y - 18 * mm, width=38 * mm, height=18 * mm, preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    texto_x = margem + (45 * mm if config.logo else 0)
    pdf.setFillColor(colors.HexColor(config.cor_primaria or "#155eef"))
    pdf.setFont(fonte_negrito, 16)
    pdf.drawString(texto_x, y - 2 * mm, config.nome_instituicao[:70])
    pdf.setFillColor(colors.black)
    pdf.setFont(fonte_regular, 9)
    detalhes = " | ".join(parte for parte in [config.cnpj, config.endereco, config.telefone, config.email] if parte)
    pdf.drawString(texto_x, y - 8 * mm, detalhes[:110] if detalhes else "Sistema de chamados")
    y -= 26 * mm
    pdf.setStrokeColor(colors.HexColor(config.cor_primaria or "#155eef"))
    pdf.line(margem, y, largura - margem, y)
    y -= 8 * mm

    escrever_linha("Relatorio de chamados", tamanho=14, negrito=True)
    escrever_linha(f"Total filtrado: {chamados.count()} | Agrupamento por {titulo_agrupamento}", tamanho=10)
    y -= 3 * mm

    escrever_linha("Resumo", tamanho=11, negrito=True)
    for linha in resumo:
        valor = linha.get(campo_agrupamento) or "Nao informado"
        escrever_linha(f"{valor}: {linha['total']}")

    y -= 3 * mm
    escrever_linha("Chamados", tamanho=11, negrito=True)
    escrever_linha("Numero | Tipo | Abertura | Solicitante | Status | Atendente", tamanho=8, negrito=True)
    for chamado in linhas_analiticas(chamados)[:120]:
        escrever_linha(
            f"{chamado.numero} | {chamado.get_tipo_display()} | {chamado.criado_em:%d/%m/%Y} | "
            f"{chamado.nome_solicitante} | {chamado.get_status_display()} | "
            f"{nome_atendente(chamado)}",
            tamanho=8,
        )

    y -= 3 * mm
    escrever_linha("Inventario", tamanho=11, negrito=True)
    escrever_linha(f"Total de ativos: {inventario['total']}", tamanho=9)

    escrever_linha("Sistemas operacionais", tamanho=9, negrito=True)
    for item in inventario["por_so"][:20]:
        escrever_linha(f"{item.get('sistema_operacional') or 'Nao informado'}: {item['total']}", tamanho=8)

    escrever_linha("Office / Microsoft 365", tamanho=9, negrito=True)
    for item in inventario["por_office"][:20]:
        escrever_linha(f"{item.get('office') or 'Nao informado'}: {item['total']}", tamanho=8)

    escrever_linha("Equipamentos inventariados", tamanho=9, negrito=True)
    escrever_linha("Nome | IP | Fabricante | Modelo | Status | Origem", tamanho=8, negrito=True)
    for ativo in inventario["ativos"][:80]:
        escrever_linha(
            f"{ativo.nome} | {ativo.ip or '-'} | {ativo.fabricante or '-'} | "
            f"{ativo.modelo or '-'} | {ativo.get_status_display()} | {ativo.get_origem_display()}",
            tamanho=7,
        )

    if config.texto_rodape:
        if y < margem + 8 * mm:
            nova_pagina()
        pdf.setFillColor(colors.grey)
        pdf.setFont(fonte_regular, 8)
        pdf.drawString(margem, margem / 2, config.texto_rodape[:120])

    pdf.save()
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="relatorio_chamados.pdf"'
    return response


@login_required
def encerrar_chamado(request, pk):
    chamado = get_object_or_404(Chamado, pk=pk)
    if request.method == "POST":
        solucao = request.POST.get("solucao_aplicada", "").strip()
        if not solucao:
            messages.error(request, "Informe a solução aplicada para encerrar o chamado.")
            return redirect(chamado)

        chamado.solucao_aplicada = solucao
        chamado.status = Chamado.Status.ENCERRADO
        chamado.save()
        HistoricoChamado.objects.create(
            chamado=chamado,
            usuario=request.user,
            status=chamado.status,
            comentario="Chamado encerrado.",
        )
        messages.success(request, "Chamado encerrado com sucesso.")
    return redirect(chamado)


@login_required
def atribuir_chamado_mim(request, pk):
    chamado = get_object_or_404(Chamado, pk=pk)
    if request.method == "POST":
        chamado.tecnico_responsavel = request.user
        if chamado.status == Chamado.Status.ABERTO:
            chamado.status = Chamado.Status.EM_ATENDIMENTO
        chamado.save()
        HistoricoChamado.objects.create(
            chamado=chamado,
            usuario=request.user,
            status=chamado.status,
            comentario="Chamado atribuído ao atendente logado.",
        )
        messages.success(request, "Chamado atribuído a você.")
    return redirect(chamado)


@login_required
def atribuir_chamado(request, pk):
    chamado = get_object_or_404(Chamado, pk=pk)
    if request.method == "POST":
        form = AtribuicaoChamadoForm(request.POST, instance=chamado)
        if form.is_valid():
            chamado = form.save(commit=False)
            if chamado.tecnico_responsavel_id and chamado.status == Chamado.Status.ABERTO:
                chamado.status = Chamado.Status.EM_ATENDIMENTO
            chamado.save()
            HistoricoChamado.objects.create(
                chamado=chamado,
                usuario=request.user,
                status=chamado.status,
                comentario="Chamado encaminhado/reatribuído.",
            )
            messages.success(request, "Chamado encaminhado com sucesso.")
        else:
            messages.error(request, "Não foi possível encaminhar o chamado.")
    return redirect(chamado)


@login_required
def resolver_chamado_rapido(request, pk):
    chamado = get_object_or_404(Chamado, pk=pk)
    if request.method == "POST":
        solucao = request.POST.get("solucao_aplicada", "").strip()
        if not solucao:
            messages.error(request, "Informe a solução aplicada.")
            return redirect(chamado)
        chamado.solucao_aplicada = solucao
        chamado.status = Chamado.Status.RESOLVIDO
        if not chamado.primeira_resposta_em:
            chamado.primeira_resposta_em = timezone.now()
        chamado.save()
        ComentarioChamado.objects.create(
            chamado=chamado,
            autor=request.user,
            nome_autor=request.user.get_full_name() or request.user.username,
            email_autor=request.user.email,
            mensagem=solucao,
            publico=True,
        )
        HistoricoChamado.objects.create(
            chamado=chamado,
            usuario=request.user,
            status=chamado.status,
            comentario="Chamado resolvido rapidamente.",
        )
        notificar_chamado(chamado, "Chamado resolvido", solucao)
        messages.success(request, "Chamado resolvido com sucesso.")
    return redirect(chamado)


@login_required
def criar_tarefa_chamado(request, pk):
    chamado = get_object_or_404(Chamado, pk=pk)
    if request.method == "POST":
        form = TarefaChamadoForm(request.POST)
        if form.is_valid():
            tarefa = form.save(commit=False)
            tarefa.chamado = chamado
            tarefa.save()
            messages.success(request, "Tarefa adicionada ao chamado.")
        else:
            messages.error(request, "Não foi possível adicionar a tarefa. Verifique os campos.")
    return redirect(chamado)


@login_required
def responder_chamado(request, pk):
    chamado = get_object_or_404(Chamado, pk=pk)
    if request.method == "POST":
        form = ComentarioInternoForm(request.POST)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.chamado = chamado
            comentario.autor = request.user
            comentario.nome_autor = request.user.get_full_name() or request.user.username
            comentario.email_autor = request.user.email
            comentario.save()
            HistoricoChamado.objects.create(
                chamado=chamado,
                usuario=request.user,
                status=chamado.status,
                comentario="Resposta registrada no chamado.",
            )
            messages.success(request, "Resposta registrada com sucesso.")
            if comentario.publico:
                if not chamado.primeira_resposta_em:
                    chamado.primeira_resposta_em = timezone.now()
                    chamado.save(update_fields=["primeira_resposta_em", "atualizado_em"])
                notificar_chamado(chamado, "Nova resposta no chamado", comentario.mensagem)
        else:
            messages.error(request, "Não foi possível registrar a resposta.")
    return redirect(chamado)


def notificar_chamado(chamado, assunto, mensagem):
    if not chamado.email:
        return
    try:
        send_mail(
            f"{assunto} {chamado.numero}",
            f"{mensagem}\n\nChamado: {chamado.numero}",
            None,
            [chamado.email],
            fail_silently=True,
        )
    except Exception:
        return


@login_required
def anexar_arquivo_chamado(request, pk):
    chamado = get_object_or_404(Chamado, pk=pk)
    if request.method == "POST":
        form = AnexoChamadoForm(request.POST, request.FILES)
        if form.is_valid():
            anexo = form.save(commit=False)
            anexo.chamado = chamado
            anexo.enviado_por = request.user
            anexo.nome_enviado_por = request.user.get_full_name() or request.user.username
            anexo.publico = True
            anexo.save()
            messages.success(request, "Anexo enviado com sucesso.")
        else:
            messages.error(request, "Não foi possível enviar o anexo.")
    return redirect(chamado)


def responder_chamado_portal(request, pk):
    chamado = get_object_or_404(Chamado, pk=pk)
    if request.method == "POST":
        email = request.POST.get("email_confirmacao", "").strip()
        if email.lower() != chamado.email.lower():
            messages.error(request, "E-mail de confirmação inválido.")
            return redirect("chamados:portal_consultar")

        form = ComentarioPortalForm(request.POST)
        anexo_form = AnexoChamadoForm(request.POST, request.FILES)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.chamado = chamado
            comentario.nome_autor = chamado.nome_solicitante
            comentario.email_autor = chamado.email
            comentario.publico = True
            comentario.save()
            if anexo_form.is_valid() and request.FILES.get("arquivo"):
                anexo = anexo_form.save(commit=False)
                anexo.chamado = chamado
                anexo.nome_enviado_por = chamado.nome_solicitante
                anexo.publico = True
                anexo.save()
            HistoricoChamado.objects.create(
                chamado=chamado,
                status=chamado.status,
                comentario="Solicitante respondeu pelo portal.",
            )
            messages.success(request, "Mensagem enviada para a equipe de TI.")
        else:
            messages.error(request, "Não foi possível enviar a mensagem.")
    return redirect("chamados:portal_consultar")


def avaliar_chamado_portal(request, pk):
    chamado = get_object_or_404(Chamado, pk=pk)
    if request.method == "POST":
        email = request.POST.get("email_confirmacao", "").strip()
        if email.lower() != chamado.email.lower():
            messages.error(request, "E-mail de confirmação inválido.")
            return redirect("chamados:portal_consultar")

        if hasattr(chamado, "avaliacao"):
            messages.info(request, "Este chamado já foi avaliado.")
            return redirect("chamados:portal_consultar")

        form = AvaliacaoChamadoForm(request.POST)
        if form.is_valid():
            avaliacao = form.save(commit=False)
            avaliacao.chamado = chamado
            avaliacao.save()
            messages.success(request, "Obrigado pela avaliação.")
        else:
            messages.error(request, "Não foi possível registrar a avaliação.")
    return redirect("chamados:portal_consultar")


def reabrir_chamado_portal(request, pk):
    chamado = get_object_or_404(Chamado, pk=pk)
    if request.method == "POST":
        email = request.POST.get("email_confirmacao", "").strip()
        motivo = request.POST.get("motivo", "").strip()
        if email.lower() != chamado.email.lower():
            messages.error(request, "E-mail de confirmação inválido.")
            return redirect("chamados:portal_consultar")
        if not motivo:
            messages.error(request, "Informe o motivo da reabertura.")
            return redirect("chamados:portal_consultar")

        chamado.status = Chamado.Status.EM_ATENDIMENTO
        chamado.concluido_em = None
        chamado.save(update_fields=["status", "concluido_em", "atualizado_em"])
        ComentarioChamado.objects.create(
            chamado=chamado,
            nome_autor=chamado.nome_solicitante,
            email_autor=chamado.email,
            mensagem=f"Solicitação de reabertura: {motivo}",
            publico=True,
        )
        HistoricoChamado.objects.create(
            chamado=chamado,
            status=chamado.status,
            comentario="Chamado reaberto pelo solicitante.",
        )
        messages.success(request, "Chamado reaberto e enviado para a equipe de TI.")
    return redirect("chamados:portal_consultar")
