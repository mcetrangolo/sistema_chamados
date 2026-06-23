from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from chamados.models import Chamado
from contratos.models import ContratoPublico
from inventario.models import AtivoRede
from core.models import Notificacao
from core.notifications import criar_notificacao


class Command(BaseCommand):
    help = "Envia resumo de alertas operacionais para administradores."

    def handle(self, *args, **options):
        agora = timezone.now()
        limite_coleta = agora - timezone.timedelta(days=settings.INVENTARIO_DIAS_SEM_COMUNICACAO)
        chamados_atrasados = (
            Chamado.objects.filter(vencimento_em__lt=agora)
            .exclude(status__in=[Chamado.Status.RESOLVIDO, Chamado.Status.ENCERRADO, Chamado.Status.CANCELADO])
            .count()
        )
        contratos = ContratoPublico.objects.all()
        contratos_a_vencer = sum(1 for contrato in contratos if contrato.em_alerta)
        contratos_vencidos = sum(1 for contrato in contratos if contrato.vencido)
        agentes_sem_coleta = AtivoRede.objects.filter(
            origem=AtivoRede.Origem.AGENTE,
            ultima_coleta_em__lt=limite_coleta,
        ).exclude(status=AtivoRede.Status.DESATIVADO).count()

        linhas = [
            "Resumo de alertas operacionais",
            "",
            f"Chamados com SLA vencido: {chamados_atrasados}",
            f"Contratos a vencer: {contratos_a_vencer}",
            f"Contratos vencidos: {contratos_vencidos}",
            f"Ativos de agente sem coleta ha mais de {settings.INVENTARIO_DIAS_SEM_COMUNICACAO} dias: {agentes_sem_coleta}",
        ]
        mensagem = "\n".join(linhas)
        nivel = Notificacao.Nivel.CRITICO if chamados_atrasados or contratos_vencidos else Notificacao.Nivel.ALERTA
        for usuario in get_user_model().objects.filter(is_active=True, is_superuser=True):
            criar_notificacao(
                usuario,
                "Alertas operacionais",
                mensagem,
                nivel=nivel,
                link="/gestao/",
                chave=f"alertas-operacionais-{agora:%Y-%m-%d}",
            )
        self.stdout.write(mensagem)
