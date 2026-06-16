from django.contrib import admin

from .models import SolicitacaoGovernanca


@admin.register(SolicitacaoGovernanca)
class SolicitacaoGovernancaAdmin(admin.ModelAdmin):
    list_display = ("protocolo", "tipo", "nome", "matricula", "setor", "termo_aceito_em", "status", "criado_em")
    list_filter = ("tipo", "status", "criado_em")
    search_fields = ("protocolo", "nome", "matricula", "email", "setor")
    readonly_fields = (
        "protocolo",
        "termo_versao",
        "termo_texto_aceito",
        "termo_aceito_em",
        "termo_aceito_ip",
        "termo_aceito_user_agent",
        "documento_caminho",
        "criado_em",
        "atualizado_em",
    )
