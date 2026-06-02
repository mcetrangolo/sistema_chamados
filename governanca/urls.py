from django.urls import path

from . import views


app_name = "governanca"

urlpatterns = [
    path("", views.GovernancaPortalView.as_view(), name="portal"),
    path("usuario-acesso/", views.UsuarioAcessoCreateView.as_view(), name="usuario_acesso"),
    path("wifi-corporativo/", views.WifiCorporativoCreateView.as_view(), name="wifi"),
    path("gestao/solicitacoes/", views.SolicitacaoGovernancaListView.as_view(), name="solicitacoes"),
]
