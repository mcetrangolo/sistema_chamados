from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verifica configuracoes essenciais antes de publicar o sistema."

    def handle(self, *args, **options):
        verificacoes = [
            ("DEBUG=False", settings.DEBUG is False, True),
            ("SECRET_KEY alterada", not settings.SECRET_KEY.startswith("django-insecure") and "dev" not in settings.SECRET_KEY.lower(), True),
            ("ALLOWED_HOSTS configurado", bool(settings.ALLOWED_HOSTS), True),
            ("Banco configurado", bool(settings.DATABASES["default"]["ENGINE"]), True),
            ("SMTP configurado", "smtp" in settings.EMAIL_BACKEND and bool(settings.EMAIL_HOST), False),
            ("DEFAULT_FROM_EMAIL configurado", "localhost" not in settings.DEFAULT_FROM_EMAIL, False),
            ("Active Directory configurado", all([settings.AD_SERVER, settings.AD_USER, settings.AD_PASSWORD, settings.AD_BASE_DN]), False),
            ("Pasta de governanca configurada", bool(settings.GOVERNANCA_DOCUMENT_ROOT), True),
            ("STATIC_ROOT configurado", bool(settings.STATIC_ROOT), True),
            ("MEDIA_ROOT configurado", bool(settings.MEDIA_ROOT), True),
        ]

        pendencias_obrigatorias = []
        for nome, ok, obrigatorio in verificacoes:
            if ok:
                marcador = self.style.SUCCESS("OK")
            elif obrigatorio:
                marcador = self.style.ERROR("PENDENTE")
                pendencias_obrigatorias.append(nome)
            else:
                marcador = self.style.WARNING("AJUSTAR DEPOIS")
            self.stdout.write(f"{marcador} - {nome}")

        if pendencias_obrigatorias:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR("Existem pendencias obrigatorias para publicar."))
            return

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Configuracoes obrigatorias preenchidas."))
