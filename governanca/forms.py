from django import forms

from .models import SolicitacaoGovernanca


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "form-check-input"
            field.widget.attrs.setdefault("class", css_class)


class UsuarioAcessoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = SolicitacaoGovernanca
        fields = [
            "matricula",
            "nome",
            "email",
            "setor",
            "cargo",
            "telefone",
            "acessos_solicitados",
            "justificativa",
            "termo_ciencia",
        ]
        widgets = {
            "acessos_solicitados": forms.Textarea(attrs={"rows": 5}),
            "justificativa": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_termo_ciencia(self):
        valor = self.cleaned_data["termo_ciencia"]
        if not valor:
            raise forms.ValidationError("É necessário declarar ciência para enviar a solicitação.")
        return valor


class WifiCorporativoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = SolicitacaoGovernanca
        fields = [
            "matricula",
            "nome",
            "email",
            "setor",
            "cargo",
            "telefone",
            "aparelhos",
            "justificativa",
            "termo_ciencia",
        ]
        widgets = {
            "aparelhos": forms.Textarea(attrs={"rows": 5}),
            "justificativa": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_termo_ciencia(self):
        valor = self.cleaned_data["termo_ciencia"]
        if not valor:
            raise forms.ValidationError("É necessário declarar ciência das responsabilidades para enviar a solicitação.")
        return valor
