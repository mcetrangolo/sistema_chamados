from django.contrib import admin

from .models import ConfiguracaoInstitucional


@admin.register(ConfiguracaoInstitucional)
class ConfiguracaoInstitucionalAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "Instituição",
            {
                "fields": (
                    "nome_instituicao",
                    "sigla",
                    "cnpj",
                    "endereco",
                    "telefone",
                    "email",
                    "site",
                    "logo",
                )
            },
        ),
        (
            "Tema visual",
            {
                "fields": (
                    "tema_visual",
                    "cor_primaria",
                    "cor_secundaria",
                    "cor_fundo",
                    "texto_rodape",
                )
            },
        ),
    )
