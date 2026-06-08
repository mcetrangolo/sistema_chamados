from django import forms
from django.contrib.auth import get_user_model

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
            "portal_rotulo",
            "portal_titulo",
            "portal_subtitulo",
            "portal_texto_apoio",
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
            "portal_subtitulo": forms.Textarea(attrs={"rows": 3}),
            "portal_texto_apoio": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "tema_visual": "Escolha Personalizado para liberar o uso manual das cores abaixo.",
        }


class PerfilUsuarioForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ["first_name", "last_name", "email"]
        labels = {
            "first_name": "Nome",
            "last_name": "Sobrenome",
            "email": "E-mail",
        }
