from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from chamados.models import Chamado
from contratos.models import ContratoPublico
from inventario.models import AtivoRede


class Command(BaseCommand):
    help = "Envia resumo de alertas operacionais para administradores."

    def handle(self, *args, **options):
        agora = timezone.now()
        limite_coleta = agora - timezone.timedelta(days=7)
        chamados_atrasados = (
            Chamado.objects.filter(vencimento_em__lt=agora)
            .exclude(status__in=[Chamado.Status.RESOLVIDO, Chamado.Status.ENCERRADO, Chamado.Status.CANCELADO])
            .count()
        )
        contratos = ContratoPublico.objects.all()
        contratos_a_vencer = sum(1 for contrato in contratos if contrato.em_alerta)
        contratos_vencidos = sum(1 for contrato in contratos if contrato.vencido)
        agentes_sem_coleta = AtivoRede.objects.filter(origem=AtivoRede.Origem.AGENTE).filter(
            ultima_coleta_em__lt=limite_coleta
        ).count()

        linhas = [
            "Resumo de alertas operacionais",
            "",
            f"Chamados com SLA vencido: {chamados_atrasados}",
            f"Contratos a vencer: {contratos_a_vencer}",
            f"Contratos vencidos: {contratos_vencidos}",
            f"Ativos de agente sem coleta ha mais de 7 dias: {agentes_sem_coleta}",
        ]
        mensagem = "\n".join(linhas)
        emails = list(
            get_user_model()
            .objects.filter(is_active=True, is_superuser=True)
            .exclude(email="")
            .values_list("email", flat=True)
        )
        if emails:
            send_mail("Alertas do Sistema de Chamados", mensagem, None, emails, fail_silently=True)
        self.stdout.write(mensagem)
