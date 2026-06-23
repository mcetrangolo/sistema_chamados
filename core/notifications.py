from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Notificacao


def criar_notificacao(usuario, titulo, mensagem, nivel=Notificacao.Nivel.INFO, link="", chave="", enviar_email=True):
    if chave:
        existente = Notificacao.objects.filter(usuario=usuario, chave=chave, lida_em__isnull=True).first()
        if existente:
            existente.titulo = titulo
            existente.mensagem = mensagem
            existente.nivel = nivel
            existente.link = link
            existente.save(update_fields=["titulo", "mensagem", "nivel", "link"])
            return existente
    notificacao = Notificacao.objects.create(
        usuario=usuario, titulo=titulo, mensagem=mensagem, nivel=nivel, link=link, chave=chave
    )
    if enviar_email and usuario.email:
        try:
            send_mail(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [usuario.email], fail_silently=False)
            notificacao.email_enviado_em = timezone.now()
            notificacao.save(update_fields=["email_enviado_em"])
        except Exception:
            pass
    return notificacao
