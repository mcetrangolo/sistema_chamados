from django.urls import path

from . import views


app_name = "core"

urlpatterns = [
    path("institucional/", views.ConfiguracaoInstitucionalView.as_view(), name="configuracao"),
    path("backup/", views.BackupConfiguracaoView.as_view(), name="backup"),
    path("backup/<str:nome>/baixar/", views.baixar_backup, name="backup_baixar"),
    path("atualizacoes/", views.AtualizacaoSistemaView.as_view(), name="atualizacoes"),
]
