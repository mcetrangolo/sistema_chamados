from django import forms

from .models import AgendamentoVarredura, AtivoRede, CredencialSNMP, FaixaRede, MetodoDescoberta, OcorrenciaAtivo, TipoAtivo


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "form-check-input"
            field.widget.attrs.setdefault("class", css_class)


class TipoAtivoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = TipoAtivo
        fields = ["nome", "ativo"]


class CredencialSNMPForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = CredencialSNMP
        fields = ["nome", "versao", "community", "usuario", "ativo"]


class FaixaRedeForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = FaixaRede
        fields = ["nome", "cidr", "credencial_snmp", "ativa"]


class AtivoRedeForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = AtivoRede
        fields = [
            "nome",
            "tipo",
            "setor",
            "ip",
            "mac",
            "hostname",
            "fabricante",
            "modelo",
            "numero_serie",
            "sistema_operacional",
            "arquitetura",
            "processador",
            "memoria_total_gb",
            "disco_total_gb",
            "office",
            "softwares_instalados",
            "usuario_logado",
            "dominio",
            "localizacao",
            "responsavel",
            "funcao",
            "status",
            "origem",
            "observacoes",
        ]
        widgets = {
            "observacoes": forms.Textarea(attrs={"rows": 4}),
            "softwares_instalados": forms.Textarea(attrs={"rows": 8}),
        }


class OcorrenciaAtivoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = OcorrenciaAtivo
        fields = ["tipo", "titulo", "descricao"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 4}),
        }


class VarreduraRedeForm(BootstrapFormMixin, forms.Form):
    metodo = forms.ChoiceField(
        label="Método de descoberta",
        choices=MetodoDescoberta.Codigo.choices,
        initial=MetodoDescoberta.Codigo.PING,
    )
    portas = forms.CharField(
        label="Portas TCP",
        required=False,
        help_text="Use apenas para TCP. Exemplo: 22,80,443,3389",
    )


class AgendamentoVarreduraForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = AgendamentoVarredura
        fields = ["nome", "faixa", "metodo", "portas", "intervalo_horas", "ativo"]
