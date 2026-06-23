from .models import ConfiguracaoInstitucional
from .version import SISTEMA_VERSAO, SISTEMA_VERSAO_NOME


def institucional(request):
    contexto = {
        "config_institucional": ConfiguracaoInstitucional.atual(),
        "sistema_versao": SISTEMA_VERSAO,
        "sistema_versao_nome": SISTEMA_VERSAO_NOME,
    }
    if request.user.is_authenticated:
        contexto["notificacoes_nao_lidas"] = request.user.notificacoes.filter(lida_em__isnull=True).count()
    return contexto
