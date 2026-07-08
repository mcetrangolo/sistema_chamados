from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import ListView, RedirectView, TemplateView

from chamados.models import Chamado
from chamados.services import criar_chamado_de_governanca

from .forms import UsuarioAcessoForm, WifiCorporativoForm
from .models import SolicitacaoGovernanca
from .terms import TERMO_REDE_TEXTO, TERMO_REDE_VERSAO, TERMO_WIFI_TEXTO, TERMO_WIFI_VERSAO


def obter_ip_cliente(request):
    encaminhado = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if encaminhado:
        return encaminhado.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR")


def registrar_aceite(solicitacao, request, versao, texto):
    solicitacao.termo_versao = versao
    solicitacao.termo_texto_aceito = texto
    solicitacao.termo_aceito_em = timezone.now()
    solicitacao.termo_aceito_ip = obter_ip_cliente(request)
    solicitacao.termo_aceito_user_agent = request.META.get("HTTP_USER_AGENT", "")[:300]


class GovernancaPortalView(RedirectView):
    pattern_name = "chamados:catalogo"
    permanent = False


class UsuarioAcessoCreateView(TemplateView):
    template_name = "governanca/form_usuario_acesso.html"

    def get_initial(self):
        tipo = self.request.GET.get("tipo", "")
        tipos_validos = {codigo for codigo, _ in SolicitacaoGovernanca.TipoSolicitacaoRede.choices}
        if tipo in tipos_validos:
            return {"tipo_solicitacao_rede": tipo}
        return {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = kwargs.get("form") or UsuarioAcessoForm(initial=self.get_initial())
        context["termo_texto"] = TERMO_REDE_TEXTO
        context["termo_versao"] = TERMO_REDE_VERSAO
        return context

    def post(self, request, *args, **kwargs):
        form = UsuarioAcessoForm(request.POST)
        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.tipo = SolicitacaoGovernanca.Tipo.USUARIO_ACESSO
            registrar_aceite(solicitacao, request, TERMO_REDE_VERSAO, TERMO_REDE_TEXTO)
            solicitacao.save()
            chamado = criar_chamado_de_governanca(solicitacao.pk)
            messages.success(request, f"Chamado de governança aberto: {chamado.numero}.")
            return redirect("governanca:portal")
        return self.render_to_response(self.get_context_data(form=form))


class WifiCorporativoCreateView(TemplateView):
    template_name = "governanca/form_wifi.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = kwargs.get("form") or WifiCorporativoForm()
        context["termo_texto"] = TERMO_WIFI_TEXTO
        context["termo_versao"] = TERMO_WIFI_VERSAO
        return context

    def post(self, request, *args, **kwargs):
        form = WifiCorporativoForm(request.POST)
        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.tipo = SolicitacaoGovernanca.Tipo.WIFI_CORPORATIVO
            registrar_aceite(solicitacao, request, TERMO_WIFI_VERSAO, TERMO_WIFI_TEXTO)
            solicitacao.save()
            chamado = criar_chamado_de_governanca(solicitacao.pk)
            messages.success(request, f"Chamado de governança aberto: {chamado.numero}.")
            return redirect("governanca:portal")
        return self.render_to_response(self.get_context_data(form=form))


class SolicitacaoGovernancaListView(ListView):
    model = Chamado
    template_name = "governanca/solicitacao_list.html"
    context_object_name = "chamados_governanca"
    paginate_by = 25

    def get_queryset(self):
        return (
            Chamado.objects.filter(numero__startswith="GOV-")
            .select_related("setor", "categoria", "tecnico_responsavel", "equipe_responsavel")
            .order_by("-criado_em")
        )
