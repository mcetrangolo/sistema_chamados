from threading import local

from django.contrib.auth.signals import user_logged_in, user_logged_out
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
        _state.ip_origem = ip_origem_request(request)
        try:
            return self.get_response(request)
        finally:
            _state.user = None
            _state.path = ""
            _state.ip_origem = None


def ip_origem_request(request):
    encaminhado = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    return encaminhado or request.META.get("REMOTE_ADDR") or None


def registrar(modelo, instance, acao):
    app_label = modelo._meta.app_label
    if getattr(modelo, "__module__", "") == "__fake__":
        return
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
            ip_origem=getattr(_state, "ip_origem", None),
        )
    except (OperationalError, ProgrammingError):
        return


def registrar_evento(acao, modelo, objeto="", usuario=None, objeto_id="", caminho="", ip_origem=None):
    try:
        RegistroAuditoria.objects.create(
            usuario=usuario if usuario and usuario.is_authenticated else getattr(_state, "user", None),
            acao=acao,
            app_label="sistema",
            modelo=str(modelo)[:120],
            objeto_id=str(objeto_id or "")[:80],
            objeto=str(objeto or "")[:250],
            caminho=(caminho or getattr(_state, "path", ""))[:250],
            ip_origem=ip_origem or getattr(_state, "ip_origem", None),
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


@receiver(user_logged_in)
def auditar_login(sender, request, user, **kwargs):
    registrar_evento(
        RegistroAuditoria.Acao.LOGIN,
        "Autenticacao",
        objeto=user.get_username(),
        usuario=user,
        objeto_id=user.pk,
        caminho=request.path,
        ip_origem=ip_origem_request(request),
    )


@receiver(user_logged_out)
def auditar_logout(sender, request, user, **kwargs):
    registrar_evento(
        RegistroAuditoria.Acao.LOGOUT,
        "Autenticacao",
        objeto=user.get_username() if user else "",
        usuario=user,
        objeto_id=getattr(user, "pk", ""),
        caminho=request.path if request else "",
        ip_origem=ip_origem_request(request) if request else None,
    )
