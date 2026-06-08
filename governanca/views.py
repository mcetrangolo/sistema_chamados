from pathlib import Path

from django.contrib import messages
from django.core.files import File
from django.views.generic import TemplateView, ListView
from django.shortcuts import redirect

from chamados.models import AnexoChamado, Categoria, Chamado, HistoricoChamado, Setor, TopicoAjuda

from .forms import UsuarioAcessoForm, WifiCorporativoForm
from .models import SolicitacaoGovernanca
from .pdf import gerar_documento_solicitacao


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
    if solicitacao.aparelhos:
        detalhes.extend(["Aparelhos:", solicitacao.aparelhos, ""])
    detalhes.extend(["Justificativa:", solicitacao.justificativa or "-"])

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
        comentario=f"Chamado criado automaticamente pela governança ({solicitacao.protocolo}).",
    )
    return chamado


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
        return context

    def post(self, request, *args, **kwargs):
        form = WifiCorporativoForm(request.POST)
        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.tipo = SolicitacaoGovernanca.Tipo.WIFI_CORPORATIVO
            solicitacao.save()
            solicitacao.documento_caminho = gerar_documento_solicitacao(solicitacao)
            solicitacao.save(update_fields=["documento_caminho"])
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
