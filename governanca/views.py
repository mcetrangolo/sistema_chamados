from django.contrib import messages
from django.views.generic import ListView, RedirectView, TemplateView
from django.shortcuts import redirect
from django.utils import timezone

from chamados.models import Categoria, Chamado, HistoricoChamado, Setor, TopicoAjuda

from .forms import UsuarioAcessoForm, WifiCorporativoForm
from .models import SolicitacaoGovernanca
from .pdf import gerar_documento_solicitacao
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


def criar_chamado_governanca(solicitacao):
    setor, _ = Setor.objects.get_or_create(
        nome=solicitacao.setor,
        defaults={"ativo": True},
    )
    categoria, _ = Categoria.objects.get_or_create(
        nome="Governança",
        defaults={"ativo": True},
    )
    topico, _ = TopicoAjuda.objects.get_or_create(
        nome=solicitacao.get_tipo_display(),
        defaults={
            "categoria": categoria,
            "prioridade_padrao": Chamado.Prioridade.MEDIA,
            "sla_horas": 48,
            "ativo": True,
        },
    )

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
        topico_ajuda=topico,
        tipo=Chamado.Tipo.REQUISICAO,
        prioridade=topico.prioridade_padrao,
        descricao="\n".join(detalhes),
        origem=Chamado.Origem.PORTAL,
    )

    HistoricoChamado.objects.create(
        chamado=chamado,
        status=chamado.status,
        comentario=f"Chamado criado automaticamente pela governança ({solicitacao.protocolo}).",
    )
    return chamado


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
            solicitacao.documento_caminho = gerar_documento_solicitacao(solicitacao)
            solicitacao.save(update_fields=["documento_caminho", "atualizado_em"])
            chamado = criar_chamado_governanca(solicitacao)
            solicitacao.status = SolicitacaoGovernanca.Status.EM_ANALISE
            solicitacao.save(update_fields=["status", "atualizado_em"])
            messages.success(request, f"Solicitação registrada e chamado aberto: {chamado.numero}.")
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
            solicitacao.documento_caminho = gerar_documento_solicitacao(solicitacao)
            solicitacao.save(update_fields=["documento_caminho", "atualizado_em"])
            chamado = criar_chamado_governanca(solicitacao)
            solicitacao.status = SolicitacaoGovernanca.Status.EM_ANALISE
            solicitacao.save(update_fields=["status", "atualizado_em"])
            messages.success(request, f"Solicitação registrada e chamado aberto: {chamado.numero}.")
            return redirect("governanca:portal")
        return self.render_to_response(self.get_context_data(form=form))


class SolicitacaoGovernancaListView(ListView):
    model = SolicitacaoGovernanca
    template_name = "governanca/solicitacao_list.html"
    context_object_name = "solicitacoes"
    paginate_by = 25
