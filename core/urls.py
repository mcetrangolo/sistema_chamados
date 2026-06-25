from django.urls import path

from . import views


app_name = "core"

urlpatterns = [
    path("ajuda/", views.AjudaSistemaView.as_view(), name="ajuda"),
    path("perfil/", views.PerfilUsuarioView.as_view(), name="perfil"),
    path("usuarios/", views.UsuarioSistemaListView.as_view(), name="usuarios"),
    path("usuarios/<int:pk>/editar/", views.UsuarioSistemaUpdateView.as_view(), name="usuario_editar"),
    path("institucional/", views.ConfiguracaoInstitucionalView.as_view(), name="configuracao"),
    path("backup/", views.BackupConfiguracaoView.as_view(), name="backup"),
    path("backup/<str:nome>/baixar/", views.baixar_backup, name="backup_baixar"),
    path("atualizacoes/", views.AtualizacaoSistemaView.as_view(), name="atualizacoes"),
    path("servicos/", views.ControleServicosView.as_view(), name="servicos"),
    path("auditoria/", views.AuditoriaListView.as_view(), name="auditoria"),
    path("notificacoes/", views.NotificacaoListView.as_view(), name="notificacoes"),
    path("notificacoes/<int:pk>/lida/", views.marcar_notificacao_lida, name="notificacao_lida"),
    path("notificacoes/lidas/", views.marcar_todas_notificacoes_lidas, name="notificacoes_lidas"),
    path("ldap/", views.ConfiguracaoLDAPView.as_view(), name="ldap"),
]
