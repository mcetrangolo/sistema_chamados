from django.urls import path

from . import views


app_name = "processos"

urlpatterns = [
    path("", views.DiagramaBPMNListView.as_view(), name="lista"),
    path("novo/", views.DiagramaBPMNCreateView.as_view(), name="novo"),
    path("<int:pk>/", views.DiagramaBPMNDetailView.as_view(), name="detalhe"),
    path("<int:pk>/editar/", views.DiagramaBPMNUpdateView.as_view(), name="editar"),
    path("<int:pk>/editar/amplo/", views.DiagramaBPMNFullEditorView.as_view(), name="editar_amplo"),
    path("<int:pk>/exportar/", views.exportar_diagrama_bpmn, name="exportar"),
    path("<int:pk>/excluir/", views.DiagramaBPMNDeleteView.as_view(), name="excluir"),
]
