from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Envia um e-mail de teste usando as configuracoes SMTP do .env."

    def add_arguments(self, parser):
        parser.add_argument("destinatario", help="E-mail que recebera a mensagem de teste.")

    def handle(self, *args, **options):
        destinatario = options["destinatario"]
        if "console" in settings.EMAIL_BACKEND:
            raise CommandError("EMAIL_BACKEND esta em modo console. Configure SMTP no .env antes do teste.")

        enviados = send_mail(
            subject="Teste SMTP - Sistema de Chamados",
            message=(
                "Este e-mail confirma que o SMTP do Sistema de Chamados esta configurado "
                "e conseguindo enviar mensagens."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatario],
            fail_silently=False,
        )
        if enviados != 1:
            raise CommandError("O Django nao confirmou o envio da mensagem.")
        self.stdout.write(self.style.SUCCESS(f"E-mail de teste enviado para {destinatario}."))
