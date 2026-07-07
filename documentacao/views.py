from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import AnexoDocumentoInfraForm, DocumentoInfraForm
from .models import AcessoDocumentoInfra, DocumentoInfra


def obter_ip_cliente(request):
    encaminhado = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if encaminhado:
        return encaminhado.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR")


def registrar_acesso(request, documento, acao):
    AcessoDocumentoInfra.objects.create(
        documento=documento,
        usuario=request.user if request.user.is_authenticated else None,
        acao=acao,
        ip=obter_ip_cliente(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
    )


def usuario_pode_acessar(documento, usuario):
    if not usuario.is_authenticated:
        return False
    if usuario.is_superuser:
        return True
    return documento.ativo and documento.usuarios_autorizados.filter(pk=usuario.pk).exists()


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


class DocumentoInfraListView(LoginRequiredMixin, ListView):
    model = DocumentoInfra
    template_name = "documentacao/documento_list.html"
    context_object_name = "documentos"
    paginate_by = 20

    def get_queryset(self):
        queryset = DocumentoInfra.objects.prefetch_related("usuarios_autorizados")
        if not self.request.user.is_superuser:
            queryset = queryset.filter(ativo=True, usuarios_autorizados=self.request.user)
        q = self.request.GET.get("q", "").strip()
        tipo = self.request.GET.get("tipo", "")
        if q:
            queryset = queryset.filter(
                Q(titulo__icontains=q)
                | Q(localizacao__icontains=q)
                | Q(resumo__icontains=q)
                | Q(conteudo__icontains=q)
            )
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tipo_choices"] = DocumentoInfra.Tipo.choices
        context["filtros"] = self.request.GET
        return context


class DocumentoInfraDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = DocumentoInfra
    template_name = "documentacao/documento_detail.html"
    context_object_name = "documento"

    def test_func(self):
        return usuario_pode_acessar(self.get_object(), self.request.user)

    def get_queryset(self):
        return DocumentoInfra.objects.prefetch_related("usuarios_autorizados", "anexos")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["anexo_form"] = AnexoDocumentoInfraForm()
        context["logs"] = self.object.logs_acesso.select_related("usuario")[:15]
        return context

    def render_to_response(self, context, **response_kwargs):
        registrar_acesso(self.request, self.object, AcessoDocumentoInfra.Acao.VISUALIZACAO)
        return super().render_to_response(context, **response_kwargs)


class DocumentoInfraCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = DocumentoInfra
    form_class = DocumentoInfraForm
    template_name = "documentacao/documento_form.html"
    success_url = reverse_lazy("documentacao:lista")

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        form.instance.atualizado_por = self.request.user
        response = super().form_valid(form)
        registrar_acesso(self.request, self.object, AcessoDocumentoInfra.Acao.CRIACAO)
        messages.success(self.request, "Documentação restrita criada com sucesso.")
        return response


class DocumentoInfraUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = DocumentoInfra
    form_class = DocumentoInfraForm
    template_name = "documentacao/documento_form.html"

    def form_valid(self, form):
        form.instance.atualizado_por = self.request.user
        response = super().form_valid(form)
        registrar_acesso(self.request, self.object, AcessoDocumentoInfra.Acao.EDICAO)
        messages.success(self.request, "Documentação restrita atualizada com sucesso.")
        return response


@login_required
def anexar_documento(request, pk):
    documento = get_object_or_404(DocumentoInfra, pk=pk)
    if not request.user.is_superuser:
        messages.error(request, "Apenas administradores podem anexar arquivos.")
        return redirect("documentacao:lista")
    if request.method == "POST":
        form = AnexoDocumentoInfraForm(request.POST, request.FILES)
        if form.is_valid():
            anexo = form.save(commit=False)
            anexo.documento = documento
            anexo.enviado_por = request.user
            anexo.save()
            registrar_acesso(request, documento, AcessoDocumentoInfra.Acao.ANEXO)
            messages.success(request, "Anexo enviado com sucesso.")
        else:
            messages.error(request, "Não foi possível enviar o anexo.")
    return redirect(documento)


@login_required
def excluir_documento(request, pk):
    documento = get_object_or_404(DocumentoInfra, pk=pk)
    if not request.user.is_superuser:
        messages.error(request, "Apenas administradores podem excluir documentos.")
        return redirect("documentacao:lista")
    if request.method == "POST":
        titulo = documento.titulo
        try:
            documento.delete()
            messages.success(request, f"Documento {titulo} excluído com sucesso.")
        except ProtectedError:
            documento.ativo = False
            documento.atualizado_por = request.user
            documento.save(update_fields=["ativo", "atualizado_por", "atualizado_em"])
            messages.warning(request, f"Documento {titulo} possui vínculos e foi marcado como inativo.")
    return redirect("documentacao:lista")
