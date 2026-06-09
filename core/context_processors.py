from .models import ConfiguracaoInstitucional
from .version import SISTEMA_VERSAO, SISTEMA_VERSAO_NOME


def institucional(request):
    return {
        "config_institucional": ConfiguracaoInstitucional.atual(),
        "sistema_versao": SISTEMA_VERSAO,
        "sistema_versao_nome": SISTEMA_VERSAO_NOME,
    }
