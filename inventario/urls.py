from django.urls import path

from . import views


app_name = "inventario"

urlpatterns = [
    path("agente/coleta/", views.receber_coleta_agente, name="agente_coleta"),
    path("agente/configuracao/", views.configuracao_agente, name="agente_config"),
    path("agente/windows/download/", views.baixar_agente_windows, name="agente_windows_download"),
    path("agente/windows/source.zip", views.baixar_agente_windows_zip, name="agente_windows_zip_download"),
    path("agente/linux/download/", views.baixar_agente_linux, name="agente_linux_download"),
    path("", views.InventarioPainelView.as_view(), name="painel"),
    path("ativos/", views.AtivoRedeListView.as_view(), name="ativos"),
    path("ativos/exportar/xls/", views.exportar_ativos_xls, name="ativos_xls"),
    path("ativos/importar/csv/", views.ImportarAtivosCSVView.as_view(), name="ativos_importar_csv"),
    path("ativos/excluir-lote/", views.excluir_ativos_lote, name="ativos_excluir_lote"),
    path("ativos/novo/", views.AtivoRedeCreateView.as_view(), name="ativo_novo"),
    path("ativos/<int:pk>/", views.AtivoRedeDetailView.as_view(), name="ativo_detalhe"),
    path("ativos/<int:pk>/editar/", views.AtivoRedeUpdateView.as_view(), name="ativo_editar"),
    path("ativos/<int:pk>/excluir/", views.excluir_ativo, name="ativo_excluir"),
    path("ativos/<int:pk>/revarrer/", views.revarrer_ativo, name="ativo_revarrer"),
    path("ativos/<int:pk>/ocorrencias/nova/", views.registrar_ocorrencia, name="ocorrencia_nova"),
    path("ativos/<int:pk>/relacionamentos/novo/", views.registrar_relacionamento, name="relacionamento_novo"),
    path("licencas/", views.LicencaSoftwareListView.as_view(), name="licencas"),
    path("licencas/nova/", views.LicencaSoftwareCreateView.as_view(), name="licenca_nova"),
    path("licencas/conciliacao/", views.ConciliacaoLicencasView.as_view(), name="licencas_conciliacao"),
    path("licencas/<int:pk>/", views.LicencaSoftwareDetailView.as_view(), name="licenca_detalhe"),
    path("licencas/<int:pk>/editar/", views.LicencaSoftwareUpdateView.as_view(), name="licenca_editar"),
    path("licencas/<int:pk>/anexos/novo/", views.anexar_licenca, name="licenca_anexo_novo"),
    path("tipos/", views.TipoAtivoListView.as_view(), name="tipos"),
    path("tipos/novo/", views.TipoAtivoCreateView.as_view(), name="tipo_novo"),
    path("tipos/<int:pk>/editar/", views.TipoAtivoUpdateView.as_view(), name="tipo_editar"),
    path("snmp/", views.CredencialSNMPListView.as_view(), name="snmp"),
    path("snmp/nova/", views.CredencialSNMPCreateView.as_view(), name="snmp_nova"),
    path("snmp/<int:pk>/editar/", views.CredencialSNMPUpdateView.as_view(), name="snmp_editar"),
    path("faixas/", views.FaixaRedeListView.as_view(), name="faixas"),
    path("faixas/nova/", views.FaixaRedeCreateView.as_view(), name="faixa_nova"),
    path("faixas/<int:pk>/editar/", views.FaixaRedeUpdateView.as_view(), name="faixa_editar"),
    path("faixas/<int:pk>/varrer-snmp/", views.iniciar_varredura_snmp, name="varrer_snmp"),
    path("agendamentos/", views.AgendamentoVarreduraListView.as_view(), name="agendamentos"),
    path("agendamentos/novo/", views.AgendamentoVarreduraCreateView.as_view(), name="agendamento_novo"),
    path("agendamentos/<int:pk>/editar/", views.AgendamentoVarreduraUpdateView.as_view(), name="agendamento_editar"),
]
