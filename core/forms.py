from django import forms

from .models import ConfiguracaoInstitucional


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "form-check-input"
            field.widget.attrs.setdefault("class", css_class)


class ConfiguracaoInstitucionalForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ConfiguracaoInstitucional
        fields = [
            "nome_instituicao",
            "sigla",
            "cnpj",
            "endereco",
            "telefone",
            "email",
            "site",
            "logo",
            "tema_visual",
            "cor_primaria",
            "cor_secundaria",
            "cor_fundo",
            "texto_rodape",
        ]
        widgets = {
            "cor_primaria": forms.TextInput(attrs={"type": "color"}),
            "cor_secundaria": forms.TextInput(attrs={"type": "color"}),
            "cor_fundo": forms.TextInput(attrs={"type": "color"}),
        }
        help_texts = {
            "tema_visual": "Escolha Personalizado para liberar o uso manual das cores abaixo.",
        }
