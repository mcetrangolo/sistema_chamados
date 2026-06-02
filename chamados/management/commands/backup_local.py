from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Cria um backup simples do banco SQLite e da pasta media."

    def handle(self, *args, **options):
        destino = settings.BASE_DIR / "backups"
        destino.mkdir(exist_ok=True)
        nome = destino / f"backup_{timezone.now():%Y%m%d_%H%M%S}.zip"

        with ZipFile(nome, "w", ZIP_DEFLATED) as zipf:
            db_path = settings.BASE_DIR / "db.sqlite3"
            if db_path.exists():
                zipf.write(db_path, "db.sqlite3")
            media = Path(settings.MEDIA_ROOT)
            if media.exists():
                for arquivo in media.rglob("*"):
                    if arquivo.is_file():
                        zipf.write(arquivo, arquivo.relative_to(settings.BASE_DIR))

        self.stdout.write(self.style.SUCCESS(f"Backup criado em {nome}"))
