from .models import ConfiguracaoInstitucional
from .permissions import (
    DESCRICAO_PAPEIS,
    papel_usuario,
    pode_acessar_inventario,
    pode_acessar_sistema,
    usuario_e_admin,
    usuario_e_suporte_n1,
    usuario_e_suporte_n2,
)
from .version import SISTEMA_VERSAO, SISTEMA_VERSAO_NOME


def institucional(request):
    contexto = {
        "config_institucional": ConfiguracaoInstitucional.atual(),
        "sistema_versao": SISTEMA_VERSAO,
        "sistema_versao_nome": SISTEMA_VERSAO_NOME,
    }
    if request.user.is_authenticated:
        contexto["notificacoes_nao_lidas"] = request.user.notificacoes.filter(lida_em__isnull=True).count()
        papel = papel_usuario(request.user)
        contexto["perfil_acesso"] = {
            "papel": papel,
            "descricao": DESCRICAO_PAPEIS[papel],
            "admin": usuario_e_admin(request.user),
            "suporte_n2": usuario_e_suporte_n2(request.user),
            "suporte_n1": usuario_e_suporte_n1(request.user),
            "inventario": pode_acessar_inventario(request.user),
            "sistema": pode_acessar_sistema(request.user),
        }
    return contexto
