from django.contrib import admin

from .models import ConfiguracaoBackup, ConfiguracaoInstitucional, ConfiguracaoLDAP, Notificacao, RegistroAuditoria, RegistroBackup


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
                    "cor_texto",
                    "cor_menu_texto",
                    "texto_rodape",
                )
            },
        ),
    )


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("criado_em", "usuario", "acao", "app_label", "modelo", "objeto")
    list_filter = ("acao", "app_label", "modelo", "criado_em")
    search_fields = ("objeto", "objeto_id", "modelo", "caminho", "usuario__username")
    readonly_fields = ("usuario", "acao", "app_label", "modelo", "objeto_id", "objeto", "caminho", "criado_em")


admin.site.register(ConfiguracaoBackup)
admin.site.register(RegistroBackup)
admin.site.register(Notificacao)
admin.site.register(ConfiguracaoLDAP)
