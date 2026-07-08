from django.db import migrations


def criar_chamados_gov(apps, schema_editor):
    SolicitacaoGovernanca = apps.get_model("governanca", "SolicitacaoGovernanca")
    Chamado = apps.get_model("chamados", "Chamado")
    Setor = apps.get_model("chamados", "Setor")
    Categoria = apps.get_model("chamados", "Categoria")
    HistoricoChamado = apps.get_model("chamados", "HistoricoChamado")

    for solicitacao in SolicitacaoGovernanca.objects.all():
        if not solicitacao.protocolo or Chamado.objects.filter(numero=solicitacao.protocolo).exists():
            continue

        setor, _ = Setor.objects.get_or_create(nome=solicitacao.setor or "Não informado", defaults={"ativo": True})
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
        detalhes.extend(["Justificativa:", solicitacao.justificativa or "-"])

        chamado = Chamado.objects.create(
            numero=solicitacao.protocolo,
            nome_solicitante=solicitacao.nome,
            email=solicitacao.email,
            telefone=solicitacao.telefone,
            setor=setor,
            categoria=categoria,
            tipo="requisicao",
            prioridade="media",
            descricao="\n".join(detalhes),
            origem="portal",
            status="aberto",
        )
        solicitacao.status = "em_analise"
        solicitacao.save(update_fields=["status", "atualizado_em"])
        HistoricoChamado.objects.create(
            chamado=chamado,
            status=chamado.status,
            comentario=f"Chamado GOV criado a partir da solicitação de governança {solicitacao.protocolo}.",
        )


class Migration(migrations.Migration):
    dependencies = [
        ("chamados", "0016_artigos_base_conhecimento_ti"),
        ("governanca", "0002_aceite_rede_wifi"),
    ]

    operations = [
        migrations.RunPython(criar_chamados_gov, migrations.RunPython.noop),
    ]
