from .models import ConfiguracaoInstitucional


def institucional(request):
    return {"config_institucional": ConfiguracaoInstitucional.atual()}
