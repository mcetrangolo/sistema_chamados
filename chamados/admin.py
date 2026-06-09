from django.contrib import admin

from .models import (
    AnexoChamado,
    ArtigoConhecimento,
    AvaliacaoChamado,
    AprovacaoSolicitacao,
    Categoria,
    Chamado,
    ComentarioChamado,
    EquipeAtendimento,
    HistoricoChamado,
    RegraSLA,
    RespostaPronta,
    ServicoCatalogo,
    Setor,
    SolicitacaoServico,
    TarefaChamado,
    TopicoAjuda,
)


@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome",)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome",)


@admin.register(EquipeAtendimento)
class EquipeAtendimentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "responsavel", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome", "descricao")
    filter_horizontal = ("membros",)


@admin.register(TopicoAjuda)
class TopicoAjudaAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "prioridade_padrao", "atendente_padrao", "sla_horas", "ativo")
    list_filter = ("ativo", "categoria", "prioridade_padrao")
    search_fields = ("nome", "descricao")


class HistoricoInline(admin.TabularInline):
    model = HistoricoChamado
    extra = 0
    readonly_fields = ("usuario", "status", "comentario", "criado_em")
    can_delete = False


class AnexoInline(admin.TabularInline):
    model = AnexoChamado
    extra = 0
    readonly_fields = ("enviado_por", "criado_em")


class ComentarioInline(admin.TabularInline):
    model = ComentarioChamado
    extra = 0
    readonly_fields = ("autor", "nome_autor", "email_autor", "mensagem", "publico", "criado_em")
    can_delete = False


class TarefaInline(admin.TabularInline):
    model = TarefaChamado
    extra = 0


@admin.register(Chamado)
class ChamadoAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "nome_solicitante",
        "setor",
        "categoria",
        "equipe_responsavel",
        "prioridade",
        "status",
        "tecnico_responsavel",
        "aprovacao_necessaria",
        "criado_em",
    )
    list_filter = ("status", "prioridade", "setor", "categoria", "equipe_responsavel", "tecnico_responsavel")
    search_fields = ("numero", "nome_solicitante", "email", "descricao")
    readonly_fields = ("numero", "criado_em", "atualizado_em", "concluido_em", "aprovado_em")
    inlines = [HistoricoInline, ComentarioInline, AnexoInline, TarefaInline]


@admin.register(HistoricoChamado)
class HistoricoChamadoAdmin(admin.ModelAdmin):
    list_display = ("chamado", "usuario", "status", "criado_em")
    list_filter = ("status", "criado_em")
    search_fields = ("chamado__numero", "comentario", "usuario__username")


@admin.register(RegraSLA)
class RegraSLAAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "prioridade", "categoria", "setor", "equipe", "prazo_solucao_horas", "ativo")
    list_filter = ("ativo", "tipo", "prioridade", "categoria", "setor", "equipe")
    search_fields = ("nome",)


@admin.register(AnexoChamado)
class AnexoChamadoAdmin(admin.ModelAdmin):
    list_display = ("chamado", "descricao", "enviado_por", "nome_enviado_por", "publico", "criado_em")
    search_fields = ("chamado__numero", "descricao")


@admin.register(ComentarioChamado)
class ComentarioChamadoAdmin(admin.ModelAdmin):
    list_display = ("chamado", "autor", "nome_autor", "publico", "criado_em")
    list_filter = ("publico", "criado_em")
    search_fields = ("chamado__numero", "mensagem", "nome_autor", "email_autor")


@admin.register(RespostaPronta)
class RespostaProntaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "ativo")
    list_filter = ("ativo",)
    search_fields = ("titulo", "conteudo")


@admin.register(TarefaChamado)
class TarefaChamadoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "chamado", "responsavel", "status", "prazo")
    list_filter = ("status", "responsavel")
    search_fields = ("titulo", "descricao", "chamado__numero")


@admin.register(ArtigoConhecimento)
class ArtigoConhecimentoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "topico_ajuda", "tem_video", "tem_imagem", "publico", "ativo", "atualizado_em")
    list_filter = ("publico", "ativo", "topico_ajuda")
    search_fields = ("titulo", "resumo", "conteudo")
    prepopulated_fields = {"slug": ("titulo",)}

    def tem_video(self, obj):
        return bool(obj.video_youtube_url)

    tem_video.boolean = True
    tem_video.short_description = "Vídeo"

    def tem_imagem(self, obj):
        return bool(obj.imagem)

    tem_imagem.boolean = True
    tem_imagem.short_description = "Imagem"


@admin.register(AvaliacaoChamado)
class AvaliacaoChamadoAdmin(admin.ModelAdmin):
    list_display = ("chamado", "nota", "criado_em")
    list_filter = ("nota", "criado_em")
    search_fields = ("chamado__numero", "comentario")


@admin.register(ServicoCatalogo)
class ServicoCatalogoAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "prioridade_padrao", "equipe_padrao", "requer_aprovacao", "ativo")
    list_filter = ("ativo", "categoria", "prioridade_padrao", "requer_aprovacao")
    search_fields = ("nome", "descricao", "instrucoes")
    prepopulated_fields = {"slug": ("nome",)}


@admin.register(SolicitacaoServico)
class SolicitacaoServicoAdmin(admin.ModelAdmin):
    list_display = ("protocolo", "servico", "nome", "setor", "status", "chamado", "criado_em")
    list_filter = ("status", "servico", "setor", "criado_em")
    search_fields = ("protocolo", "nome", "email", "matricula", "detalhes", "chamado__numero")
    readonly_fields = ("protocolo", "chamado", "criado_em")


@admin.register(AprovacaoSolicitacao)
class AprovacaoSolicitacaoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "origem", "solicitante", "status", "aprovado_por", "criado_em", "decidido_em")
    list_filter = ("origem", "status", "criado_em")
    search_fields = ("titulo", "solicitante", "observacao")
