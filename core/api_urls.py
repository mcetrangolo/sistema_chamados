from django.urls import path

from chamados import api as chamados_api
from inventario import api as inventario_api


app_name = "api"

urlpatterns = [
    path("v1/chamados/", chamados_api.chamados_collection, name="chamados"),
    path("v1/chamados/<int:pk>/", chamados_api.chamado_detail, name="chamado_detail"),
    path("v1/ativos/", inventario_api.ativos_collection, name="ativos"),
    path("v1/ativos/<int:pk>/", inventario_api.ativo_detail, name="ativo_detail"),
]
