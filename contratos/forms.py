from django import forms

from chamados.forms import BootstrapFormMixin

from .models import AditivoContrato, ContratoPublico, Fornecedor, PedidoProrrogacao


class FornecedorForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Fornecedor
        fields = ["nome", "cnpj", "email", "telefone", "endereco", "ativo"]
        widgets = {"endereco": forms.Textarea(attrs={"rows": 3})}


class ContratoPublicoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ContratoPublico
        fields = [
            "numero",
            "ano",
            "processo_administrativo",
            "objeto",
            "fornecedor",
            "lei_regencia",
            "modalidade",
            "tipo",
            "valor_global",
            "data_assinatura",
            "data_inicio",
            "data_fim",
            "status",
            "gestor",
            "fiscal",
            "permite_prorrogacao",
            "limite_prorrogacao_meses",
            "alerta_dias",
            "observacoes",
        ]
        widgets = {
            "objeto": forms.Textarea(attrs={"rows": 4}),
            "observacoes": forms.Textarea(attrs={"rows": 4}),
            "data_assinatura": forms.DateInput(attrs={"type": "date"}),
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_fim": forms.DateInput(attrs={"type": "date"}),
        }


class PedidoProrrogacaoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = PedidoProrrogacao
        fields = ["novo_fim", "justificativa", "status"]
        widgets = {
            "novo_fim": forms.DateInput(attrs={"type": "date"}),
            "justificativa": forms.Textarea(attrs={"rows": 5}),
        }


class AditivoContratoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = AditivoContrato
        fields = ["numero", "tipo", "data_assinatura", "nova_data_fim", "valor_acrescimo", "observacao"]
        widgets = {
            "data_assinatura": forms.DateInput(attrs={"type": "date"}),
            "nova_data_fim": forms.DateInput(attrs={"type": "date"}),
            "observacao": forms.Textarea(attrs={"rows": 4}),
        }
