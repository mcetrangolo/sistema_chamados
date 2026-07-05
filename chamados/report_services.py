from django.db.models import Avg, Count
from django.utils import timezone

from .forms import RelatorioChamadosForm
from .models import Chamado, SolicitacaoServico


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


def agrupamento_do_form(form):
    if form.is_valid():
        return form.cleaned_data.get("agrupamento") or "status"
    return "status"


def resumo_relatorio(chamados, agrupamento):
    campo, titulo = AGRUPAMENTO_MAP.get(agrupamento, AGRUPAMENTO_MAP["status"])
    linhas = chamados.values(campo).annotate(total=Count("id")).order_by(campo)
    return campo, titulo, linhas


def linhas_analiticas(chamados, limite=500):
    return chamados.order_by("-criado_em")[:limite]


def nome_atendente(chamado):
    if chamado.tecnico_responsavel:
        return chamado.tecnico_responsavel.get_full_name() or chamado.tecnico_responsavel.username
    return "Nao atribuido"


def rotulo_choice(valor, choices):
    mapa = dict(choices)
    return mapa.get(valor, valor or "Nao informado")


def chart_data(linhas, label_field):
    return {
        "labels": [linha.get(label_field) or "Nao informado" for linha in linhas],
        "data": [linha["total"] for linha in linhas],
    }


def chart_data_choices(linhas, label_field, choices):
    return {
        "labels": [rotulo_choice(linha.get(label_field), choices) for linha in linhas],
        "data": [linha["total"] for linha in linhas],
    }


def chart_data_atendentes(linhas):
    labels = []
    for linha in linhas:
        nome = "Nao atribuido"
        if linha.get("tecnico_responsavel__first_name") or linha.get("tecnico_responsavel__last_name"):
            nome = (
                f"{linha.get('tecnico_responsavel__first_name') or ''} "
                f"{linha.get('tecnico_responsavel__last_name') or ''}"
            ).strip()
        elif linha.get("tecnico_responsavel__username"):
            nome = linha["tecnico_responsavel__username"]
        labels.append(nome)
    return {"labels": labels, "data": [linha["total"] for linha in linhas]}


def dados_graficos_chamados(chamados):
    return {
        "status": chart_data_choices(
            chamados.values("status").annotate(total=Count("id")).order_by("status"),
            "status",
            Chamado.Status.choices,
        ),
        "tipo": chart_data_choices(
            chamados.values("tipo").annotate(total=Count("id")).order_by("tipo"),
            "tipo",
            Chamado.Tipo.choices,
        ),
        "setor": chart_data(
            chamados.values("setor__nome").annotate(total=Count("id")).order_by("setor__nome"),
            "setor__nome",
        ),
        "categoria": chart_data(
            chamados.values("categoria__nome").annotate(total=Count("id")).order_by("categoria__nome"),
            "categoria__nome",
        ),
        "prioridade": chart_data_choices(
            chamados.values("prioridade").annotate(total=Count("id")).order_by("prioridade"),
            "prioridade",
            Chamado.Prioridade.choices,
        ),
        "atendente": chart_data_atendentes(
            chamados.values(
                "tecnico_responsavel__username",
                "tecnico_responsavel__first_name",
                "tecnico_responsavel__last_name",
            )
            .annotate(total=Count("id"))
            .order_by("tecnico_responsavel__username")
        ),
    }


def contexto_relatorio_chamados(params):
    form, chamados = filtrar_chamados_relatorio(params)
    agrupamento = agrupamento_do_form(form)
    campo_agrupamento, titulo_agrupamento, resumo = resumo_relatorio(chamados, agrupamento)
    graficos = dados_graficos_chamados(chamados)

    return {
        "form": form,
        "chamados_queryset": chamados,
        "total": chamados.count(),
        "resumo": resumo,
        "campo_agrupamento": campo_agrupamento,
        "titulo_agrupamento": titulo_agrupamento,
        "chamados": linhas_analiticas(chamados),
        "abertos": chamados.exclude(
            status__in=[Chamado.Status.ENCERRADO, Chamado.Status.CANCELADO]
        ).count(),
        "resolvidos": chamados.filter(status=Chamado.Status.RESOLVIDO).count(),
        "encerrados": chamados.filter(status=Chamado.Status.ENCERRADO).count(),
        "sla_vencidos": chamados.filter(vencimento_em__lt=timezone.now())
        .exclude(status__in=[Chamado.Status.RESOLVIDO, Chamado.Status.ENCERRADO, Chamado.Status.CANCELADO])
        .count(),
        "avaliacao_media": chamados.filter(avaliacao__isnull=False).aggregate(
            media=Avg("avaliacao__nota")
        )["media"],
        "servicos_mais_solicitados": (
            SolicitacaoServico.objects.values("servico__nome")
            .annotate(total=Count("id"))
            .order_by("-total")[:10]
        ),
        "status_chart": graficos["status"],
        "tipo_chart": graficos["tipo"],
        "setor_chart": graficos["setor"],
        "categoria_chart": graficos["categoria"],
        "prioridade_chart": graficos["prioridade"],
        "atendente_chart": graficos["atendente"],
    }
