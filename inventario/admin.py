from django.contrib import admin

from .models import (
    AtivoRede,
    AgendamentoVarredura,
    CampoExternoAtivo,
    CredencialSNMP,
    FaixaRede,
    InterfaceRede,
    HistoricoAlteracaoAtivo,
    MetodoDescoberta,
    MovimentacaoAtivo,
    OcorrenciaAtivo,
    RelacionamentoAtivo,
    RegistroColetaAgente,
    SondaRemota,
    TermoResponsabilidadeAtivo,
    ExecucaoSonda,
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


class HistoricoAlteracaoInline(admin.TabularInline):
    model = HistoricoAlteracaoAtivo
    extra = 0
    readonly_fields = ("campo", "valor_anterior", "valor_novo", "origem", "criado_em")
    can_delete = False


class CampoExternoInline(admin.TabularInline):
    model = CampoExternoAtivo
    extra = 0


class MovimentacaoInline(admin.TabularInline):
    model = MovimentacaoAtivo
    extra = 0
    readonly_fields = ("criado_em", "movimentado_por")


class RelacionamentoOrigemInline(admin.TabularInline):
    model = RelacionamentoAtivo
    fk_name = "origem"
    extra = 0


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
    list_display = ("nome", "tipo", "ip", "hostname", "sistema_operacional", "office", "status", "origem", "ultima_coleta_em")
    list_filter = ("tipo", "status", "origem", "setor", "sistema_operacional", "office")
    search_fields = ("nome", "ip", "mac", "hostname", "fabricante", "modelo", "numero_serie", "processador", "office")
    inlines = [InterfaceInline, CampoExternoInline, RelacionamentoOrigemInline, OcorrenciaInline, HistoricoAlteracaoInline, MovimentacaoInline]


@admin.register(RegistroColetaAgente)
class RegistroColetaAgenteAdmin(admin.ModelAdmin):
    list_display = ("criado_em", "ativo", "hostname", "status", "ip_origem", "versao_agente")
    list_filter = ("status", "criado_em")
    search_fields = ("ativo__nome", "hostname", "mensagem", "ip_origem")
    readonly_fields = ("ativo", "hostname", "status", "mensagem", "ip_origem", "versao_agente", "criado_em")


@admin.register(SondaRemota)
class SondaRemotaAdmin(admin.ModelAdmin):
    list_display = ("nome", "localidade", "ativa", "ultima_comunicacao_em", "token_prefixo")
    list_filter = ("ativa",)
    filter_horizontal = ("faixas",)


@admin.register(ExecucaoSonda)
class ExecucaoSondaAdmin(admin.ModelAdmin):
    list_display = ("sonda", "status", "ativos_encontrados", "criado_em")
    list_filter = ("status", "sonda")


@admin.register(MovimentacaoAtivo)
class MovimentacaoAtivoAdmin(admin.ModelAdmin):
    list_display = ("ativo", "ciclo_anterior", "ciclo_novo", "setor_destino", "movimentado_por", "criado_em")
    list_filter = ("ciclo_novo", "setor_destino", "criado_em")


@admin.register(TermoResponsabilidadeAtivo)
class TermoResponsabilidadeAtivoAdmin(admin.ModelAdmin):
    list_display = ("ativo", "tipo", "responsavel", "matricula", "data_evento", "aceite_em")
    list_filter = ("tipo", "data_evento", "setor")
    search_fields = ("ativo__nome", "ativo__patrimonio", "responsavel", "matricula")


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


@admin.register(RelacionamentoAtivo)
class RelacionamentoAtivoAdmin(admin.ModelAdmin):
    list_display = ("origem", "tipo", "destino", "descricao")
    list_filter = ("tipo",)
    search_fields = ("origem__nome", "destino__nome", "descricao")


@admin.register(CampoExternoAtivo)
class CampoExternoAtivoAdmin(admin.ModelAdmin):
    list_display = ("ativo", "chave", "valor", "atualizado_em")
    search_fields = ("ativo__nome", "chave", "valor")


@admin.register(HistoricoAlteracaoAtivo)
class HistoricoAlteracaoAtivoAdmin(admin.ModelAdmin):
    list_display = ("ativo", "campo", "origem", "criado_em")
    list_filter = ("campo", "origem", "criado_em")
    search_fields = ("ativo__nome", "campo", "valor_anterior", "valor_novo")
