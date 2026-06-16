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
            "tipo_solicitacao_rede",
            "usuario_rede_existente",
            "acessos_solicitados",
            "chefia_imediata",
            "justificativa",
            "termo_ciencia",
        ]
        widgets = {
            "acessos_solicitados": forms.Textarea(attrs={"rows": 5}),
            "justificativa": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "acessos_solicitados": "Acesso solicitado",
            "termo_ciencia": "Li e aceito o termo de ciência desta solicitação",
        }

    def clean_termo_ciencia(self):
        valor = self.cleaned_data["termo_ciencia"]
        if not valor:
            raise forms.ValidationError("É necessário declarar ciência para enviar a solicitação.")
        return valor

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo_solicitacao_rede")
        acessos = (cleaned_data.get("acessos_solicitados") or "").strip()
        usuario = (cleaned_data.get("usuario_rede_existente") or "").strip()
        if not tipo:
            self.add_error("tipo_solicitacao_rede", "Informe o tipo de solicitação.")
        if tipo in {
            SolicitacaoGovernanca.TipoSolicitacaoRede.NOVO_ACESSO,
            SolicitacaoGovernanca.TipoSolicitacaoRede.ALTERACAO_PERMISSAO,
        } and not acessos:
            self.add_error("acessos_solicitados", "Informe o acesso solicitado.")
        if tipo == SolicitacaoGovernanca.TipoSolicitacaoRede.TROCA_SENHA and not usuario:
            self.add_error("usuario_rede_existente", "Informe o nome do usuário da conta existente.")
        return cleaned_data


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
        labels = {
            "aparelhos": "Equipamentos",
            "termo_ciencia": "Li e aceito os termos de acesso à internet Wi-Fi",
        }
        help_texts = {
            "aparelhos": "Informe tipo de equipamento, fabricante, modelo, número de série e endereço MAC.",
        }

    def clean_termo_ciencia(self):
        valor = self.cleaned_data["termo_ciencia"]
        if not valor:
            raise forms.ValidationError("É necessário declarar ciência das responsabilidades para enviar a solicitação.")
        return valor
