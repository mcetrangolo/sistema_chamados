from django.contrib import admin

from .models import SolicitacaoGovernanca


@admin.register(SolicitacaoGovernanca)
class SolicitacaoGovernancaAdmin(admin.ModelAdmin):
    list_display = ("protocolo", "tipo", "nome", "matricula", "setor", "status", "criado_em")
    list_filter = ("tipo", "status", "criado_em")
    search_fields = ("protocolo", "nome", "matricula", "email", "setor")
    readonly_fields = ("protocolo", "documento_caminho", "criado_em", "atualizado_em")
