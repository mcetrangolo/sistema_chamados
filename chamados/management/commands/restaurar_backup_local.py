from pathlib import Path
from shutil import copy2, copytree, rmtree
from zipfile import BadZipFile, ZipFile

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "Restaura um backup ZIP criado pelo comando backup_local."

    def add_arguments(self, parser):
        parser.add_argument("arquivo", help="Caminho ou nome do arquivo .zip dentro da pasta backups.")
        parser.add_argument(
            "--confirmar",
            action="store_true",
            help="Confirma a restauracao. Sem isso, o comando apenas valida o backup.",
        )
        parser.add_argument(
            "--sem-backup-previo",
            action="store_true",
            help="Nao cria copia de seguranca do estado atual antes de restaurar.",
        )

    def handle(self, *args, **options):
        engine = settings.DATABASES["default"]["ENGINE"]
        if not engine.endswith("sqlite3"):
            raise CommandError(
                "Este comando restaura apenas backups locais SQLite/media. "
                "Para PostgreSQL, use scripts/restore_docker.sh."
            )

        arquivo = self._resolver_arquivo(options["arquivo"])
        self._validar_zip(arquivo)

        if not options["confirmar"]:
            self.stdout.write(self.style.WARNING("Backup validado, mas nada foi restaurado."))
            self.stdout.write("Para restaurar de verdade, execute novamente com --confirmar.")
            self.stdout.write(f"Arquivo: {arquivo}")
            return

        if not options["sem_backup_previo"]:
            self._backup_previo()

        with ZipFile(arquivo) as zipf:
            self._restaurar_db(zipf)
            self._restaurar_media(zipf)

        self.stdout.write(self.style.SUCCESS("Backup restaurado com sucesso."))
        self.stdout.write("Reinicie o servidor da aplicacao antes de usar o sistema.")

    def _resolver_arquivo(self, valor):
        caminho = Path(valor)
        if caminho.exists():
            return caminho.resolve()

        caminho_backups = settings.BASE_DIR / "backups" / valor
        if caminho_backups.exists():
            return caminho_backups.resolve()

        raise CommandError(f"Backup nao encontrado: {valor}")

    def _validar_zip(self, arquivo):
        try:
            with ZipFile(arquivo) as zipf:
                nomes = zipf.namelist()
                if "db.sqlite3" not in nomes:
                    raise CommandError("Backup invalido: db.sqlite3 nao encontrado no ZIP.")
                for nome in nomes:
                    destino = (settings.BASE_DIR / nome).resolve()
                    if not str(destino).startswith(str(settings.BASE_DIR.resolve())):
                        raise CommandError(f"Backup invalido: caminho inseguro detectado ({nome}).")
        except BadZipFile as exc:
            raise CommandError("Arquivo ZIP invalido ou corrompido.") from exc

    def _backup_previo(self):
        from django.core.management import call_command

        self.stdout.write("Criando backup previo do estado atual...")
        call_command("backup_local")

    def _restaurar_db(self, zipf):
        db_path = settings.BASE_DIR / "db.sqlite3"
        temporario = settings.BASE_DIR / "db.sqlite3.restore"
        with zipf.open("db.sqlite3") as origem, temporario.open("wb") as destino:
            destino.write(origem.read())

        if db_path.exists():
            copia = settings.BASE_DIR / f"db.sqlite3.antes_restore_{timezone.now():%Y%m%d_%H%M%S}"
            copy2(db_path, copia)
        temporario.replace(db_path)

    def _restaurar_media(self, zipf):
        nomes_media = [nome for nome in zipf.namelist() if nome.startswith("media/") and not nome.endswith("/")]
        media_root = Path(settings.MEDIA_ROOT)

        if media_root.exists():
            copia_media = settings.BASE_DIR / f"media_antes_restore_{timezone.now():%Y%m%d_%H%M%S}"
            copytree(media_root, copia_media)
            rmtree(media_root)

        media_root.mkdir(parents=True, exist_ok=True)
        for nome in nomes_media:
            destino = (settings.BASE_DIR / nome).resolve()
            if not str(destino).startswith(str(settings.BASE_DIR.resolve())):
                raise CommandError(f"Caminho inseguro detectado ao restaurar media: {nome}")
            destino.parent.mkdir(parents=True, exist_ok=True)
            with zipf.open(nome) as origem, destino.open("wb") as saida:
                saida.write(origem.read())
