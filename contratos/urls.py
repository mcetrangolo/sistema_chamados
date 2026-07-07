from django.urls import path

from . import views


app_name = "contratos"

urlpatterns = [
    path("", views.ContratoListView.as_view(), name="lista"),
    path("novo/", views.ContratoCreateView.as_view(), name="novo"),
    path("<int:pk>/", views.ContratoDetailView.as_view(), name="detalhe"),
    path("<int:pk>/editar/", views.ContratoUpdateView.as_view(), name="editar"),
    path("<int:pk>/excluir/", views.excluir_contrato, name="excluir"),
    path("<int:pk>/anexos/novo/", views.anexar_contrato, name="anexo_novo"),
    path("<int:contrato_pk>/prorrogacoes/nova/", views.PedidoProrrogacaoCreateView.as_view(), name="prorrogacao_nova"),
    path("<int:contrato_pk>/aditivos/novo/", views.AditivoContratoCreateView.as_view(), name="aditivo_novo"),
    path("fornecedores/", views.FornecedorListView.as_view(), name="fornecedores"),
    path("fornecedores/novo/", views.FornecedorCreateView.as_view(), name="fornecedor_novo"),
    path("fornecedores/<int:pk>/editar/", views.FornecedorUpdateView.as_view(), name="fornecedor_editar"),
    path("fornecedores/<int:pk>/excluir/", views.excluir_fornecedor, name="fornecedor_excluir"),
]
