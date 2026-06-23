from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import ConfiguracaoBackup


class Command(BaseCommand):
    help = "Executa o backup quando o agendamento configurado estiver vencido."

    def handle(self, *args, **options):
        configuracao = ConfiguracaoBackup.atual()
        agora = timezone.now()
        if not configuracao.ativo:
            self.stdout.write("Backup agendado desativado.")
            return
        if configuracao.proxima_execucao and configuracao.proxima_execucao > agora:
            self.stdout.write(f"Proximo backup em {configuracao.proxima_execucao}.")
            return
        call_command("backup_local")
        configuracao.ultima_execucao = agora
        configuracao.proxima_execucao = agora + timezone.timedelta(hours=configuracao.intervalo_horas)
        configuracao.save(update_fields=["ultima_execucao", "proxima_execucao", "atualizado_em"])
        self.stdout.write(self.style.SUCCESS("Backup agendado concluido."))
