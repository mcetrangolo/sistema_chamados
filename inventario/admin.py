from django.contrib import admin

from .models import (
    AtivoRede,
    AgendamentoVarredura,
    CredencialSNMP,
    FaixaRede,
    InterfaceRede,
    MetodoDescoberta,
    OcorrenciaAtivo,
    TipoAtivo,
    VarreduraRede,
)


class InterfaceInline(admin.TabularInline):
    model = InterfaceRede
    extra = 0


class OcorrenciaInline(admin.TabularInline):
    model = OcorrenciaAtivo
    extra = 0
    readonly_fields = ("registrado_por", "criado_em")


@admin.register(TipoAtivo)
class TipoAtivoAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome",)


@admin.register(CredencialSNMP)
class CredencialSNMPAdmin(admin.ModelAdmin):
    list_display = ("nome", "versao", "ativo", "criado_em")
    list_filter = ("versao", "ativo")
    search_fields = ("nome",)


@admin.register(FaixaRede)
class FaixaRedeAdmin(admin.ModelAdmin):
    list_display = ("nome", "cidr", "credencial_snmp", "ativa")
    list_filter = ("ativa", "credencial_snmp")
    search_fields = ("nome", "cidr")


@admin.register(MetodoDescoberta)
class MetodoDescobertaAdmin(admin.ModelAdmin):
    list_display = ("nome", "codigo", "ativo")
    list_filter = ("ativo", "codigo")
    search_fields = ("nome", "descricao")


@admin.register(AtivoRede)
class AtivoRedeAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "ip", "hostname", "setor", "status", "origem", "ultima_coleta_em")
    list_filter = ("tipo", "status", "origem", "setor")
    search_fields = ("nome", "ip", "mac", "hostname", "fabricante", "modelo", "numero_serie")
    inlines = [InterfaceInline, OcorrenciaInline]


@admin.register(VarreduraRede)
class VarreduraRedeAdmin(admin.ModelAdmin):
    list_display = ("faixa", "metodo", "status", "ativos_encontrados", "iniciado_por", "iniciado_em", "concluido_em")
    list_filter = ("status", "metodo", "faixa")
    search_fields = ("faixa__nome", "mensagem")


@admin.register(AgendamentoVarredura)
class AgendamentoVarreduraAdmin(admin.ModelAdmin):
    list_display = ("nome", "faixa", "metodo", "intervalo_horas", "ativo", "ultima_execucao", "proxima_execucao")
    list_filter = ("ativo", "metodo", "faixa")
    search_fields = ("nome", "faixa__nome")


@admin.register(OcorrenciaAtivo)
class OcorrenciaAtivoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "ativo", "tipo", "registrado_por", "criado_em")
    list_filter = ("tipo", "registrado_por")
    search_fields = ("titulo", "descricao", "ativo__nome")
