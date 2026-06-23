import base64
import hashlib
import sqlite3
import tempfile
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from django.conf import settings
from django.core.management.base import CommandError


def sha256_arquivo(caminho):
    digest = hashlib.sha256()
    with Path(caminho).open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def validar_backup_zip(caminho):
    caminho = Path(caminho)
    try:
        with ZipFile(caminho) as zipf:
            if zipf.testzip():
                raise CommandError("Backup corrompido: falha de CRC no ZIP.")
            if "db.sqlite3" not in zipf.namelist():
                raise CommandError("Backup invalido: db.sqlite3 nao encontrado.")
            with tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False) as temporario:
                temporario.write(zipf.read("db.sqlite3"))
                temporario_path = Path(temporario.name)
        try:
            conexao = sqlite3.connect(temporario_path)
            resultado = conexao.execute("PRAGMA integrity_check").fetchone()[0]
            conexao.close()
        finally:
            temporario_path.unlink(missing_ok=True)
    except BadZipFile as exc:
        raise CommandError("Arquivo ZIP invalido ou corrompido.") from exc
    if resultado.lower() != "ok":
        raise CommandError(f"Banco SQLite inconsistente: {resultado}")
    return True


def _fernet():
    segredo = settings.BACKUP_ENCRYPTION_KEY
    if not segredo:
        return None
    from cryptography.fernet import Fernet

    chave = base64.urlsafe_b64encode(hashlib.sha256(segredo.encode("utf-8")).digest())
    return Fernet(chave)


def criptografar_backup(caminho):
    fernet = _fernet()
    if not fernet:
        return Path(caminho)
    caminho = Path(caminho)
    destino = caminho.with_suffix(caminho.suffix + ".enc")
    destino.write_bytes(fernet.encrypt(caminho.read_bytes()))
    caminho.unlink()
    return destino


def descriptografar_backup(caminho):
    caminho = Path(caminho)
    if caminho.suffix.lower() != ".enc":
        return caminho, False
    fernet = _fernet()
    if not fernet:
        raise CommandError("BACKUP_ENCRYPTION_KEY nao configurada para descriptografar o arquivo.")
    temporario = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    temporario.write(fernet.decrypt(caminho.read_bytes()))
    temporario.close()
    return Path(temporario.name), True
