from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from core.permissions import usuario_e_suporte_n2

from .forms import DiagramaBPMNForm
from .models import DEFAULT_BPMN_XML, DiagramaBPMN


class SuporteN2RequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return usuario_e_suporte_n2(self.request.user)


class DiagramaBPMNListView(LoginRequiredMixin, SuporteN2RequiredMixin, ListView):
    model = DiagramaBPMN
    template_name = "processos/diagrama_list.html"
    context_object_name = "diagramas"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related("criado_por", "atualizado_por")
        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(titulo__icontains=q)
        return queryset


class DiagramaBPMNDetailView(LoginRequiredMixin, SuporteN2RequiredMixin, DetailView):
    model = DiagramaBPMN
    template_name = "processos/diagrama_detail.html"
    context_object_name = "diagrama"


class DiagramaBPMNCreateView(LoginRequiredMixin, SuporteN2RequiredMixin, CreateView):
    model = DiagramaBPMN
    form_class = DiagramaBPMNForm
    template_name = "processos/diagrama_form.html"

    def get_initial(self):
        initial = super().get_initial()
        initial["xml"] = DEFAULT_BPMN_XML
        return initial

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        form.instance.atualizado_por = self.request.user
        messages.success(self.request, "Fluxo BPMN criado com sucesso.")
        return super().form_valid(form)


class DiagramaBPMNUpdateView(LoginRequiredMixin, SuporteN2RequiredMixin, UpdateView):
    model = DiagramaBPMN
    form_class = DiagramaBPMNForm
    template_name = "processos/diagrama_form.html"

    def form_valid(self, form):
        form.instance.atualizado_por = self.request.user
        messages.success(self.request, "Fluxo BPMN atualizado com sucesso.")
        return super().form_valid(form)


class DiagramaBPMNDeleteView(LoginRequiredMixin, SuporteN2RequiredMixin, DeleteView):
    model = DiagramaBPMN
    template_name = "processos/diagrama_confirm_delete.html"
    context_object_name = "diagrama"
    success_url = reverse_lazy("processos:lista")

    def form_valid(self, form):
        messages.success(self.request, "Fluxo BPMN excluído com sucesso.")
        return super().form_valid(form)


@login_required
@user_passes_test(usuario_e_suporte_n2)
def exportar_diagrama_bpmn(request, pk):
    diagrama = get_object_or_404(DiagramaBPMN, pk=pk)
    response = HttpResponse(diagrama.xml, content_type="application/xml; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{diagrama.nome_arquivo}"'
    return response
