from django.urls import path

from . import views


app_name = "documentacao"

urlpatterns = [
    path("", views.DocumentoInfraListView.as_view(), name="lista"),
    path("novo/", views.DocumentoInfraCreateView.as_view(), name="novo"),
    path("<int:pk>/", views.DocumentoInfraDetailView.as_view(), name="detalhe"),
    path("<int:pk>/editar/", views.DocumentoInfraUpdateView.as_view(), name="editar"),
    path("<int:pk>/anexos/", views.anexar_documento, name="anexo_novo"),
]
