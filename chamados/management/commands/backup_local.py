from pathlib import Path
from shutil import copy2
import sqlite3
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.backup_utils import criptografar_backup, sha256_arquivo, validar_backup_zip
from core.models import ConfiguracaoBackup, RegistroBackup
from core.models import Notificacao
from core.notifications import criar_notificacao


class Command(BaseCommand):
    help = "Cria um backup simples do banco SQLite e da pasta media."

    def handle(self, *args, **options):
        destino = settings.BASE_DIR / "backups"
        destino.mkdir(exist_ok=True)
        nome = destino / f"backup_{timezone.now():%Y%m%d_%H%M%S}.zip"
        configuracao = ConfiguracaoBackup.atual()
        try:
            db_path = Path(settings.DATABASES["default"]["NAME"])
            with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as temporario:
                snapshot = Path(temporario.name)
            origem = sqlite3.connect(db_path)
            copia = sqlite3.connect(snapshot)
            origem.backup(copia)
            copia.close()
            origem.close()

            with ZipFile(nome, "w", ZIP_DEFLATED) as zipf:
                zipf.write(snapshot, "db.sqlite3")
                media = Path(settings.MEDIA_ROOT)
                if media.exists():
                    for arquivo in media.rglob("*"):
                        if arquivo.is_file():
                            zipf.write(arquivo, arquivo.relative_to(settings.BASE_DIR))
            snapshot.unlink(missing_ok=True)
            validar_backup_zip(nome)
            nome = criptografar_backup(nome)

            destino_externo = ""
            if configuracao.pasta_destino:
                pasta_externa = Path(configuracao.pasta_destino)
                pasta_externa.mkdir(parents=True, exist_ok=True)
                copia_externa = pasta_externa / nome.name
                copy2(nome, copia_externa)
                destino_externo = str(copia_externa)

            registro = RegistroBackup.objects.create(
                nome_arquivo=nome.name,
                status=RegistroBackup.Status.SUCESSO,
                tamanho_bytes=nome.stat().st_size,
                sha256=sha256_arquivo(nome),
                destino=destino_externo or str(nome),
                mensagem="Backup criado e validado com sucesso.",
                validado_em=timezone.now(),
            )
            self._aplicar_retencao(destino, configuracao.manter_ultimos)
            for usuario in get_user_model().objects.filter(is_active=True, is_superuser=True):
                criar_notificacao(
                    usuario,
                    "Backup concluido",
                    f"{nome.name} validado. SHA-256: {registro.sha256}",
                    nivel=Notificacao.Nivel.SUCESSO,
                    link="/configuracoes/backup/",
                    chave=f"backup-{nome.name}",
                    enviar_email=False,
                )
            self.stdout.write(self.style.SUCCESS(f"Backup criado em {nome} | SHA-256 {registro.sha256}"))
        except Exception as exc:
            RegistroBackup.objects.create(
                nome_arquivo=nome.name,
                status=RegistroBackup.Status.ERRO,
                destino=str(nome),
                mensagem=str(exc),
            )
            for usuario in get_user_model().objects.filter(is_active=True, is_superuser=True):
                criar_notificacao(
                    usuario,
                    "Falha no backup",
                    str(exc),
                    nivel=Notificacao.Nivel.CRITICO,
                    link="/configuracoes/backup/",
                    chave=f"backup-erro-{timezone.now():%Y-%m-%d}",
                )
            raise

    def _aplicar_retencao(self, pasta, manter):
        arquivos = sorted(
            [*pasta.glob("backup_*.zip"), *pasta.glob("backup_*.zip.enc")],
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for antigo in arquivos[max(1, manter):]:
            antigo.unlink(missing_ok=True)
