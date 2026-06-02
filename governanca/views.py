from django.contrib import messages
from django.views.generic import TemplateView, ListView
from django.shortcuts import redirect

from .forms import UsuarioAcessoForm, WifiCorporativoForm
from .models import SolicitacaoGovernanca
from .pdf import gerar_documento_solicitacao


class GovernancaPortalView(TemplateView):
    template_name = "governanca/portal.html"


class UsuarioAcessoCreateView(TemplateView):
    template_name = "governanca/form_usuario_acesso.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = kwargs.get("form") or UsuarioAcessoForm()
        return context

    def post(self, request, *args, **kwargs):
        form = UsuarioAcessoForm(request.POST)
        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.tipo = SolicitacaoGovernanca.Tipo.USUARIO_ACESSO
            solicitacao.save()
            solicitacao.documento_caminho = gerar_documento_solicitacao(solicitacao)
            solicitacao.save(update_fields=["documento_caminho"])
            messages.success(request, f"Solicitação registrada: {solicitacao.protocolo}.")
            return redirect("governanca:portal")
        return self.render_to_response(self.get_context_data(form=form))


class WifiCorporativoCreateView(TemplateView):
    template_name = "governanca/form_wifi.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = kwargs.get("form") or WifiCorporativoForm()
        return context

    def post(self, request, *args, **kwargs):
        form = WifiCorporativoForm(request.POST)
        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.tipo = SolicitacaoGovernanca.Tipo.WIFI_CORPORATIVO
            solicitacao.save()
            solicitacao.documento_caminho = gerar_documento_solicitacao(solicitacao)
            solicitacao.save(update_fields=["documento_caminho"])
            messages.success(request, f"Solicitação registrada: {solicitacao.protocolo}.")
            return redirect("governanca:portal")
        return self.render_to_response(self.get_context_data(form=form))


class SolicitacaoGovernancaListView(ListView):
    model = SolicitacaoGovernanca
    template_name = "governanca/solicitacao_list.html"
    context_object_name = "solicitacoes"
    paginate_by = 25
