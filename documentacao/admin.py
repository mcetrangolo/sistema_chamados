from django.contrib import admin

from .models import AcessoDocumentoInfra, AnexoDocumentoInfra, DocumentoInfra


class AnexoDocumentoInfraInline(admin.TabularInline):
    model = AnexoDocumentoInfra
    extra = 0
    readonly_fields = ("criado_em",)


@admin.register(DocumentoInfra)
class DocumentoInfraAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "criticidade", "localizacao", "ativo", "atualizado_em")
    list_filter = ("tipo", "criticidade", "ativo")
    search_fields = ("titulo", "localizacao", "resumo", "conteudo")
    filter_horizontal = ("usuarios_autorizados",)
    readonly_fields = ("criado_por", "atualizado_por", "criado_em", "atualizado_em")
    inlines = [AnexoDocumentoInfraInline]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.criado_por = request.user
        obj.atualizado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(AcessoDocumentoInfra)
class AcessoDocumentoInfraAdmin(admin.ModelAdmin):
    list_display = ("documento", "usuario", "acao", "ip", "criado_em")
    list_filter = ("acao", "criado_em")
    search_fields = ("documento__titulo", "usuario__username", "ip")
    readonly_fields = ("documento", "usuario", "acao", "ip", "user_agent", "criado_em")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
