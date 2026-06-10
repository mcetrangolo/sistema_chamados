from django.contrib import admin

from .models import AnexoContrato, AditivoContrato, ContratoPublico, Fornecedor, PedidoProrrogacao


@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ("nome", "cnpj", "email", "telefone", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome", "cnpj", "email")


class PedidoProrrogacaoInline(admin.TabularInline):
    model = PedidoProrrogacao
    extra = 0


class AditivoContratoInline(admin.TabularInline):
    model = AditivoContrato
    extra = 0


class AnexoContratoInline(admin.TabularInline):
    model = AnexoContrato
    extra = 0
    readonly_fields = ("enviado_por", "criado_em")


@admin.register(ContratoPublico)
class ContratoPublicoAdmin(admin.ModelAdmin):
    list_display = ("numero", "ano", "fornecedor", "lei_regencia", "status", "data_fim", "gestor", "fiscal")
    list_filter = ("lei_regencia", "status", "tipo", "data_fim")
    search_fields = ("numero", "processo_administrativo", "objeto", "fornecedor__nome", "fornecedor__cnpj")
    inlines = [PedidoProrrogacaoInline, AditivoContratoInline, AnexoContratoInline]


@admin.register(PedidoProrrogacao)
class PedidoProrrogacaoAdmin(admin.ModelAdmin):
    list_display = ("contrato", "novo_fim", "status", "solicitado_por", "solicitado_em")
    list_filter = ("status", "solicitado_em")
    search_fields = ("contrato__numero", "justificativa")


@admin.register(AditivoContrato)
class AditivoContratoAdmin(admin.ModelAdmin):
    list_display = ("contrato", "numero", "tipo", "data_assinatura", "nova_data_fim", "valor_acrescimo")
    list_filter = ("tipo", "data_assinatura")
    search_fields = ("contrato__numero", "numero", "observacao")


@admin.register(AnexoContrato)
class AnexoContratoAdmin(admin.ModelAdmin):
    list_display = ("contrato", "tipo", "descricao", "enviado_por", "criado_em")
    list_filter = ("tipo", "criado_em")
    search_fields = ("contrato__numero", "descricao", "arquivo")
