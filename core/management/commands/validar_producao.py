from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verifica configuracoes essenciais antes de publicar o sistema em producao."

    def handle(self, *args, **options):
        verificacoes = [
            ("DEBUG=False", settings.DEBUG is False),
            ("SECRET_KEY alterada", not settings.SECRET_KEY.startswith("django-insecure") and "dev" not in settings.SECRET_KEY.lower()),
            ("ALLOWED_HOSTS configurado", bool(settings.ALLOWED_HOSTS)),
            ("Banco em PostgreSQL", settings.DATABASES["default"]["ENGINE"].endswith("postgresql")),
            ("SMTP configurado", "smtp" in settings.EMAIL_BACKEND and bool(settings.EMAIL_HOST)),
            ("DEFAULT_FROM_EMAIL configurado", "localhost" not in settings.DEFAULT_FROM_EMAIL),
            ("Active Directory configurado", all([settings.AD_SERVER, settings.AD_USER, settings.AD_PASSWORD, settings.AD_BASE_DN])),
            ("Pasta de governanca configurada", bool(settings.GOVERNANCA_DOCUMENT_ROOT)),
            ("STATIC_ROOT configurado", bool(settings.STATIC_ROOT)),
            ("MEDIA_ROOT configurado", bool(settings.MEDIA_ROOT)),
        ]

        pendencias = []
        for nome, ok in verificacoes:
            marcador = self.style.SUCCESS("OK") if ok else self.style.WARNING("PENDENTE")
            self.stdout.write(f"{marcador} - {nome}")
            if not ok:
                pendencias.append(nome)

        if pendencias:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Ainda existem pendencias para producao."))
            return

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Configuracoes essenciais de producao estao preenchidas."))
