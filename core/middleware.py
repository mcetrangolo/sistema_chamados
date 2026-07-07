from django.contrib import messages
from django.shortcuts import redirect

from .permissions import pode_acessar_inventario, pode_acessar_sistema


class PerfilAcessoMiddleware:
    ROTAS_PUBLICAS_INVENTARIO = (
        "/inventario/agente/coleta/",
        "/inventario/agente/coleta/solicitada/",
        "/inventario/sondas/coleta/",
        "/inventario/ativos/identificacao/",
    )

    ROTAS_SISTEMA_ADMIN = (
        "/admin/",
        "/configuracoes/institucional/",
        "/configuracoes/backup/",
        "/configuracoes/atualizacoes/",
        "/configuracoes/auditoria/",
        "/configuracoes/ldap/",
        "/configuracoes/usuarios/",
    )

    ROTAS_SUPORTE_N2 = (
        "/contratos/",
        "/documentacao/",
        "/governanca/gestao/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            caminho = request.path
            if caminho.startswith("/inventario/") and not caminho.startswith(self.ROTAS_PUBLICAS_INVENTARIO):
                if not pode_acessar_inventario(request.user):
                    messages.warning(request, "Seu perfil nao possui acesso ao modulo de inventario.")
                    return redirect("chamados:painel")

            if caminho.startswith(self.ROTAS_SUPORTE_N2) and not pode_acessar_inventario(request.user):
                messages.warning(request, "Seu perfil nao possui acesso a este modulo.")
                return redirect("chamados:painel")

            if caminho.startswith(self.ROTAS_SISTEMA_ADMIN) and not pode_acessar_sistema(request.user):
                messages.warning(request, "Seu perfil nao possui acesso a gestao do sistema.")
                return redirect("chamados:painel")

        return self.get_response(request)
