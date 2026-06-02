from django.core.management.base import BaseCommand
from django.utils import timezone

from inventario.models import AgendamentoVarredura
from inventario.views import executar_varredura


class Command(BaseCommand):
    help = "Executa agendamentos de varredura vencidos."

    def handle(self, *args, **options):
        agora = timezone.now()
        agendamentos = AgendamentoVarredura.objects.filter(ativo=True).filter(
            proxima_execucao__isnull=True
        ) | AgendamentoVarredura.objects.filter(ativo=True, proxima_execucao__lte=agora)
        total = 0
        for agendamento in agendamentos.distinct():
            executar_varredura(agendamento.faixa, agendamento.metodo, agendamento.portas)
            agendamento.ultima_execucao = agora
            agendamento.proxima_execucao = agora + timezone.timedelta(hours=agendamento.intervalo_horas)
            agendamento.save(update_fields=["ultima_execucao", "proxima_execucao"])
            total += 1
        self.stdout.write(self.style.SUCCESS(f"{total} agendamento(s) executado(s)."))
