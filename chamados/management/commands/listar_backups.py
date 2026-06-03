from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Lista backups locais disponiveis na pasta backups."

    def handle(self, *args, **options):
        pasta = settings.BASE_DIR / "backups"
        if not pasta.exists():
            self.stdout.write("Nenhuma pasta de backups encontrada.")
            return

        backups = sorted(pasta.glob("*.zip"), reverse=True)

        if not backups:
            self.stdout.write("Nenhum backup encontrado.")
            return

        self.stdout.write(self.style.SUCCESS("Backups locais ZIP:"))
        for arquivo in backups:
            tamanho_mb = arquivo.stat().st_size / 1024 / 1024
            self.stdout.write(f"- {arquivo.name} ({tamanho_mb:.2f} MB)")
