from pathlib import Path

from django.core.files import File
from django.core.mail import send_mail
from django.utils import timezone

from .models import (
    AnexoChamado,
    AprovacaoSolicitacao,
    Categoria,
    Chamado,
    ComentarioChamado,
    HistoricoChamado,
    Setor,
    SolicitacaoServico,
)


class ChamadoErro(Exception):
    pass


def nome_usuario(usuario):
    return usuario.get_full_name() or usuario.username


def registrar_historico(chamado, usuario=None, comentario=""):
    return HistoricoChamado.objects.create(
        chamado=chamado,
        usuario=usuario,
        status=chamado.status,
        comentario=comentario,
    )


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
        descricao=f"Solicitacao de servico: {servico.nome}\n\n{detalhes}",
        origem=Chamado.Origem.PORTAL,
        status=(
            Chamado.Status.AGUARDANDO_APROVACAO
            if servico.requer_aprovacao
            else Chamado.Status.ABERTO
        ),
        aprovacao_necessaria=servico.requer_aprovacao,
        tecnico_responsavel=servico.aprovador_padrao if servico.requer_aprovacao else None,
    )
    solicitacao.chamado = chamado
    solicitacao.status = SolicitacaoServico.Status.CONVERTIDA
    solicitacao.save(update_fields=["chamado", "status"])
    registrar_historico(
        chamado,
        comentario=f"Chamado criado pelo catalogo de servicos ({solicitacao.protocolo}).",
    )
    notificar_chamado(chamado, "Chamado aberto", "Sua solicitacao foi convertida em chamado.")
    return chamado


def criar_chamado_de_governanca(governanca_id):
    from governanca.models import SolicitacaoGovernanca

    solicitacao = SolicitacaoGovernanca.objects.get(pk=governanca_id)
    setor, _ = Setor.objects.get_or_create(nome=solicitacao.setor, defaults={"ativo": True})
    categoria, _ = Categoria.objects.get_or_create(nome="Governanca", defaults={"ativo": True})
    detalhes = [
        f"Solicitacao de governanca: {solicitacao.get_tipo_display()}",
        f"Protocolo: {solicitacao.protocolo}",
        f"Matricula: {solicitacao.matricula}",
        f"Cargo: {solicitacao.cargo or '-'}",
        "",
    ]
    if solicitacao.acessos_solicitados:
        detalhes.extend(["Acessos solicitados:", solicitacao.acessos_solicitados, ""])
    if solicitacao.tipo_solicitacao_rede:
        detalhes.extend(["Tipo de solicitacao:", solicitacao.get_tipo_solicitacao_rede_display(), ""])
    if solicitacao.usuario_rede_existente:
        detalhes.extend(["Usuario de rede existente:", solicitacao.usuario_rede_existente, ""])
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
            f"Versao: {solicitacao.termo_versao or '-'}",
            (
                f"Data/hora: {solicitacao.termo_aceito_em:%d/%m/%Y %H:%M:%S}"
                if solicitacao.termo_aceito_em
                else "Data/hora: -"
            ),
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
                descricao=f"Formulario {solicitacao.protocolo}",
                nome_enviado_por=solicitacao.nome,
                publico=True,
            )
            anexo.arquivo.save(pdf_path.name, File(arquivo), save=True)

    registrar_historico(
        chamado,
        comentario=f"Chamado criado a partir da solicitacao de governanca {solicitacao.protocolo}.",
    )
    notificar_chamado(
        chamado,
        "Chamado aberto",
        "Sua solicitacao de governanca foi aprovada e convertida em chamado.",
    )
    return chamado


def aprovar_solicitacao(aprovacao, usuario, observacao=""):
    aprovacao.aprovado_por = usuario
    aprovacao.observacao = (observacao or "").strip()
    aprovacao.decidido_em = timezone.now()
    aprovacao.status = AprovacaoSolicitacao.Status.APROVADA

    if aprovacao.solicitacao_servico:
        chamado = aprovacao.solicitacao_servico.chamado
        if not chamado:
            chamado = criar_chamado_de_solicitacao(aprovacao.solicitacao_servico)
        chamado.aprovacao_necessaria = True
        chamado.aprovado_por = usuario
        chamado.aprovado_em = timezone.now()
        chamado.status = Chamado.Status.ABERTO
        chamado.save(
            update_fields=[
                "aprovacao_necessaria",
                "aprovado_por",
                "aprovado_em",
                "status",
                "atualizado_em",
            ]
        )
        registrar_historico(
            chamado,
            usuario=usuario,
            comentario=f"Solicitacao aprovada. {aprovacao.observacao}",
        )
    elif aprovacao.origem == AprovacaoSolicitacao.Origem.GOVERNANCA and aprovacao.governanca_id:
        criar_chamado_de_governanca(aprovacao.governanca_id)

    aprovacao.save()
    return aprovacao


def rejeitar_solicitacao(aprovacao, usuario, observacao=""):
    aprovacao.aprovado_por = usuario
    aprovacao.observacao = (observacao or "").strip()
    aprovacao.decidido_em = timezone.now()
    aprovacao.status = AprovacaoSolicitacao.Status.REJEITADA

    if aprovacao.solicitacao_servico and aprovacao.solicitacao_servico.chamado:
        chamado = aprovacao.solicitacao_servico.chamado
        chamado.status = Chamado.Status.CANCELADO
        chamado.save(update_fields=["status", "atualizado_em"])
        registrar_historico(
            chamado,
            usuario=usuario,
            comentario=f"Solicitacao rejeitada. {aprovacao.observacao}",
        )

    if aprovacao.origem == AprovacaoSolicitacao.Origem.GOVERNANCA and aprovacao.governanca_id:
        from governanca.models import SolicitacaoGovernanca

        SolicitacaoGovernanca.objects.filter(pk=aprovacao.governanca_id).update(
            status=SolicitacaoGovernanca.Status.NEGADA,
            atualizado_em=timezone.now(),
        )

    aprovacao.save()
    return aprovacao


def decidir_solicitacao(aprovacao, decisao, usuario, observacao=""):
    if aprovacao.status != AprovacaoSolicitacao.Status.PENDENTE:
        return aprovacao
    if decisao == "aprovar":
        return aprovar_solicitacao(aprovacao, usuario, observacao)
    return rejeitar_solicitacao(aprovacao, usuario, observacao)


def registrar_chamado_aberto(chamado, usuario, comentario):
    registrar_historico(chamado, usuario=usuario, comentario=comentario)


def atualizar_chamado(chamado, usuario, status_anterior, registro=""):
    registro = (registro or "").strip()
    if status_anterior == chamado.status and not registro:
        return
    if registro and not chamado.primeira_resposta_em:
        chamado.primeira_resposta_em = timezone.now()
        chamado.save(update_fields=["primeira_resposta_em", "atualizado_em"])
    registrar_historico(chamado, usuario=usuario, comentario=registro)


def encerrar_chamado(chamado, usuario, solucao):
    solucao = (solucao or "").strip()
    if not solucao:
        raise ChamadoErro("Informe a solucao aplicada para encerrar o chamado.")
    chamado.solucao_aplicada = solucao
    chamado.status = Chamado.Status.ENCERRADO
    chamado.save()
    registrar_historico(chamado, usuario=usuario, comentario="Chamado encerrado.")
    return chamado


def atribuir_chamado_para_usuario(chamado, usuario):
    chamado.tecnico_responsavel = usuario
    if chamado.status == Chamado.Status.ABERTO:
        chamado.status = Chamado.Status.EM_ATENDIMENTO
    chamado.save()
    registrar_historico(
        chamado,
        usuario=usuario,
        comentario="Chamado atribuido ao atendente logado.",
    )
    return chamado


def registrar_atribuicao_chamado(chamado, usuario):
    if chamado.tecnico_responsavel_id and chamado.status == Chamado.Status.ABERTO:
        chamado.status = Chamado.Status.EM_ATENDIMENTO
    chamado.save()
    registrar_historico(
        chamado,
        usuario=usuario,
        comentario="Chamado encaminhado/reatribuido.",
    )
    return chamado


def resolver_chamado_rapido(chamado, usuario, solucao):
    solucao = (solucao or "").strip()
    if not solucao:
        raise ChamadoErro("Informe a solucao aplicada.")
    chamado.solucao_aplicada = solucao
    chamado.status = Chamado.Status.RESOLVIDO
    if not chamado.primeira_resposta_em:
        chamado.primeira_resposta_em = timezone.now()
    chamado.save()
    ComentarioChamado.objects.create(
        chamado=chamado,
        autor=usuario,
        nome_autor=nome_usuario(usuario),
        email_autor=usuario.email,
        mensagem=solucao,
        publico=True,
    )
    registrar_historico(
        chamado,
        usuario=usuario,
        comentario="Chamado resolvido rapidamente.",
    )
    notificar_chamado(chamado, "Chamado resolvido", solucao)
    return chamado


def registrar_resposta_interna(chamado, usuario, comentario):
    comentario.chamado = chamado
    comentario.autor = usuario
    comentario.nome_autor = nome_usuario(usuario)
    comentario.email_autor = usuario.email
    comentario.save()
    registrar_historico(
        chamado,
        usuario=usuario,
        comentario="Resposta registrada no chamado.",
    )
    if comentario.publico:
        if not chamado.primeira_resposta_em:
            chamado.primeira_resposta_em = timezone.now()
            chamado.save(update_fields=["primeira_resposta_em", "atualizado_em"])
        notificar_chamado(chamado, "Nova resposta no chamado", comentario.mensagem)
    return comentario


def reabrir_chamado_pelo_portal(chamado, motivo):
    motivo = (motivo or "").strip()
    if not motivo:
        raise ChamadoErro("Informe o motivo da reabertura.")
    chamado.status = Chamado.Status.EM_ATENDIMENTO
    chamado.concluido_em = None
    chamado.save(update_fields=["status", "concluido_em", "atualizado_em"])
    ComentarioChamado.objects.create(
        chamado=chamado,
        nome_autor=chamado.nome_solicitante,
        email_autor=chamado.email,
        mensagem=f"Solicitacao de reabertura: {motivo}",
        publico=True,
    )
    registrar_historico(chamado, comentario="Chamado reaberto pelo solicitante.")
    return chamado
