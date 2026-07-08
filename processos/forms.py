from django import forms

from .models import DiagramaBPMN


class DiagramaBPMNForm(forms.ModelForm):
    class Meta:
        model = DiagramaBPMN
        fields = ["titulo", "descricao", "xml", "ativo", "exibir_portal"]
        labels = {
            "exibir_portal": "Exibir no portal público",
        }
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "xml": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "form-check-input"
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs.setdefault("class", css_class)
