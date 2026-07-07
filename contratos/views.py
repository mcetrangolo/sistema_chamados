from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import AnexoContratoForm, AditivoContratoForm, ContratoPublicoForm, FornecedorForm, PedidoProrrogacaoForm
from .models import AnexoContrato, AditivoContrato, ContratoPublico, Fornecedor, PedidoProrrogacao


class ContratoListView(LoginRequiredMixin, ListView):
    model = ContratoPublico
    template_name = "contratos/contrato_list.html"
    context_object_name = "contratos"
    paginate_by = 20

    def get_queryset(self):
        queryset = ContratoPublico.objects.select_related("fornecedor", "gestor", "fiscal")
        q = self.request.GET.get("q", "").strip()
        lei = self.request.GET.get("lei", "")
        status = self.request.GET.get("status", "")
        alerta = self.request.GET.get("alerta", "")

        if q:
            queryset = queryset.filter(
                Q(numero__icontains=q)
                | Q(processo_administrativo__icontains=q)
                | Q(objeto__icontains=q)
                | Q(fornecedor__nome__icontains=q)
                | Q(fornecedor__cnpj__icontains=q)
            )
        if lei:
            queryset = queryset.filter(lei_regencia=lei)
        if status:
            queryset = queryset.filter(status=status)
        if alerta == "vencidos":
            queryset = [contrato for contrato in queryset if contrato.vencido]
        elif alerta == "a_vencer":
            queryset = [contrato for contrato in queryset if contrato.em_alerta]
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        todos = ContratoPublico.objects.select_related("fornecedor")
        context["contadores"] = {
            "total": todos.count(),
            "vigentes": todos.filter(status=ContratoPublico.Status.VIGENTE).count(),
            "a_vencer": sum(1 for contrato in todos if contrato.em_alerta),
            "vencidos": sum(1 for contrato in todos if contrato.vencido),
            "prorrogacoes": PedidoProrrogacao.objects.exclude(status=PedidoProrrogacao.Status.FORMALIZADO).count(),
        }
        context["por_lei"] = todos.values("lei_regencia").annotate(total=Count("id")).order_by("lei_regencia")
        context["lei_choices"] = ContratoPublico.LeiRegencia.choices
        context["status_choices"] = ContratoPublico.Status.choices
        context["filtros"] = self.request.GET
        return context


class ContratoCreateView(LoginRequiredMixin, CreateView):
    model = ContratoPublico
    form_class = ContratoPublicoForm
    template_name = "contratos/contrato_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Contrato cadastrado com sucesso.")
        return super().form_valid(form)


class ContratoUpdateView(LoginRequiredMixin, UpdateView):
    model = ContratoPublico
    form_class = ContratoPublicoForm
    template_name = "contratos/contrato_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Contrato atualizado com sucesso.")
        return super().form_valid(form)


class ContratoDetailView(LoginRequiredMixin, DetailView):
    model = ContratoPublico
    template_name = "contratos/contrato_detail.html"
    context_object_name = "contrato"

    def get_queryset(self):
        return ContratoPublico.objects.select_related("fornecedor", "gestor", "fiscal").prefetch_related(
            "prorrogacoes", "aditivos", "anexos"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["anexo_form"] = AnexoContratoForm()
        return context


class FornecedorListView(LoginRequiredMixin, ListView):
    model = Fornecedor
    template_name = "contratos/fornecedor_list.html"
    context_object_name = "fornecedores"


class FornecedorCreateView(LoginRequiredMixin, CreateView):
    model = Fornecedor
    form_class = FornecedorForm
    template_name = "contratos/fornecedor_form.html"
    success_url = reverse_lazy("contratos:fornecedores")

    def form_valid(self, form):
        messages.success(self.request, "Fornecedor cadastrado com sucesso.")
        return super().form_valid(form)


class FornecedorUpdateView(LoginRequiredMixin, UpdateView):
    model = Fornecedor
    form_class = FornecedorForm
    template_name = "contratos/fornecedor_form.html"
    success_url = reverse_lazy("contratos:fornecedores")

    def form_valid(self, form):
        messages.success(self.request, "Fornecedor atualizado com sucesso.")
        return super().form_valid(form)


@login_required
def excluir_contrato(request, pk):
    contrato = get_object_or_404(ContratoPublico, pk=pk)
    if request.method == "POST":
        identificacao = f"{contrato.numero}/{contrato.ano}"
        contrato.delete()
        messages.success(request, f"Contrato {identificacao} excluído com sucesso.")
    return redirect("contratos:lista")


@login_required
def excluir_fornecedor(request, pk):
    fornecedor = get_object_or_404(Fornecedor, pk=pk)
    if request.method == "POST":
        nome = fornecedor.nome
        try:
            fornecedor.delete()
            messages.success(request, f"Fornecedor {nome} excluído com sucesso.")
        except ProtectedError:
            fornecedor.ativo = False
            fornecedor.save(update_fields=["ativo"])
            messages.warning(request, f"Fornecedor {nome} possui contratos vinculados e foi marcado como inativo.")
    return redirect("contratos:fornecedores")


class PedidoProrrogacaoCreateView(LoginRequiredMixin, CreateView):
    model = PedidoProrrogacao
    form_class = PedidoProrrogacaoForm
    template_name = "contratos/prorrogacao_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.contrato = get_object_or_404(ContratoPublico, pk=kwargs["contrato_pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.contrato = self.contrato
        form.instance.solicitado_por = self.request.user
        messages.success(self.request, "Pedido de prorrogacao registrado.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.contrato.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contrato"] = self.contrato
        return context


class AditivoContratoCreateView(LoginRequiredMixin, CreateView):
    model = AditivoContrato
    form_class = AditivoContratoForm
    template_name = "contratos/aditivo_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.contrato = get_object_or_404(ContratoPublico, pk=kwargs["contrato_pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.contrato = self.contrato
        response = super().form_valid(form)
        if self.object.nova_data_fim:
            self.contrato.data_fim = self.object.nova_data_fim
            self.contrato.save(update_fields=["data_fim", "atualizado_em"])
        messages.success(self.request, "Aditivo registrado com sucesso.")
        return response

    def get_success_url(self):
        return self.contrato.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contrato"] = self.contrato
        return context


@login_required
def anexar_contrato(request, pk):
    contrato = get_object_or_404(ContratoPublico, pk=pk)
    if request.method == "POST":
        form = AnexoContratoForm(request.POST, request.FILES)
        if form.is_valid():
            anexo = form.save(commit=False)
            anexo.contrato = contrato
            anexo.enviado_por = request.user
            anexo.save()
            messages.success(request, "Anexo enviado com sucesso.")
        else:
            messages.error(request, "Nao foi possivel enviar o anexo.")
    return redirect(contrato)
