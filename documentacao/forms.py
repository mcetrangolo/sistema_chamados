from django import forms

from .models import AnexoDocumentoInfra, DocumentoInfra


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "form-check-input"
            if isinstance(field.widget, forms.SelectMultiple):
                css_class = "form-select"
                field.widget.attrs.setdefault("size", "8")
            field.widget.attrs.setdefault("class", css_class)


class DocumentoInfraForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = DocumentoInfra
        fields = [
            "titulo",
            "tipo",
            "criticidade",
            "localizacao",
            "resumo",
            "conteudo",
            "conteudo_restrito",
            "usuarios_autorizados",
            "ativo",
        ]
        widgets = {
            "resumo": forms.Textarea(attrs={"rows": 3}),
            "conteudo": forms.Textarea(attrs={"rows": 10}),
            "conteudo_restrito": forms.Textarea(attrs={"rows": 8}),
        }


class AnexoDocumentoInfraForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = AnexoDocumentoInfra
        fields = ["arquivo", "descricao"]
