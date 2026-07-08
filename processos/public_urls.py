from django.urls import path

from . import views


app_name = "processos_publicos"

urlpatterns = [
    path("", views.DiagramaBPMNPublicListView.as_view(), name="lista"),
    path("<int:pk>/", views.DiagramaBPMNPublicDetailView.as_view(), name="detalhe"),
]
