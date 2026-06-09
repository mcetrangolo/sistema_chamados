from threading import local

from django.db import OperationalError, ProgrammingError
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import RegistroAuditoria


_state = local()


class AuditoriaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        _state.user = user if user and user.is_authenticated else None
        _state.path = request.path[:250]
        try:
            return self.get_response(request)
        finally:
            _state.user = None
            _state.path = ""


def registrar(modelo, instance, acao):
    app_label = modelo._meta.app_label
    if modelo.__name__ == "Migration":
        return
    if app_label == "core" and modelo.__name__ == "RegistroAuditoria":
        return
    if app_label in {"sessions", "admin", "contenttypes", "auth"}:
        return
    try:
        RegistroAuditoria.objects.create(
            usuario=getattr(_state, "user", None),
            acao=acao,
            app_label=app_label,
            modelo=modelo.__name__,
            objeto_id=str(getattr(instance, "pk", "") or ""),
            objeto=str(instance)[:250],
            caminho=getattr(_state, "path", "")[:250],
        )
    except (OperationalError, ProgrammingError):
        return


@receiver(post_save)
def auditar_save(sender, instance, created, **kwargs):
    if not getattr(sender._meta, "app_label", ""):
        return
    registrar(sender, instance, RegistroAuditoria.Acao.CRIACAO if created else RegistroAuditoria.Acao.ALTERACAO)


@receiver(pre_delete)
def auditar_delete(sender, instance, **kwargs):
    if not getattr(sender._meta, "app_label", ""):
        return
    registrar(sender, instance, RegistroAuditoria.Acao.EXCLUSAO)
