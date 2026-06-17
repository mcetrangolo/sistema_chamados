from django.core.management.base import BaseCommand

from inventario.models import AtivoRede
from inventario.views import atualizar_status_por_ping


class Command(BaseCommand):
    help = "Valida uma vez o status dos ativos com IP por ping, sem sobrescrever manutencao/desativado."

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout",
            type=int,
            default=800,
            help="Timeout do ping em milissegundos. Padrao: 800.",
        )

    def handle(self, *args, **options):
        timeout_ms = options["timeout"]
        totais = {"online": 0, "offline": 0, "sem_ip": 0, "ignorado": 0}

        ativos = AtivoRede.objects.all().order_by("nome")
        for ativo in ativos:
            resultado = atualizar_status_por_ping(ativo, timeout_ms=timeout_ms)
            if resultado == AtivoRede.Status.ONLINE:
                totais["online"] += 1
            elif resultado == AtivoRede.Status.OFFLINE:
                totais["offline"] += 1
            elif resultado == "sem_ip":
                totais["sem_ip"] += 1
            else:
                totais["ignorado"] += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Validacao de status concluida. "
                f"Online: {totais['online']}. Offline: {totais['offline']}. "
                f"Sem IP: {totais['sem_ip']}. Ignorados: {totais['ignorado']}."
            )
        )
