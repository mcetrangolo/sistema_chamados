from django import forms
from chamados.models import Setor

from .models import (
    AgendamentoVarredura,
    AnexoLicencaSoftware,
    AtivoRede,
    CredencialSNMP,
    FaixaRede,
    LicencaSoftware,
    MetodoDescoberta,
    MovimentacaoAtivo,
    OcorrenciaAtivo,
    RelacionamentoAtivo,
    SondaRemota,
    TermoResponsabilidadeAtivo,
    TipoAtivo,
)


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
            "patrimonio",
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
            "ciclo_vida",
            "data_aquisicao",
            "garantia_ate",
            "data_baixa",
            "motivo_baixa",
            "origem",
            "observacoes",
        ]
        widgets = {
            "observacoes": forms.Textarea(attrs={"rows": 4}),
            "softwares_instalados": forms.Textarea(attrs={"rows": 8}),
            "data_aquisicao": forms.DateInput(attrs={"type": "date"}),
            "garantia_ate": forms.DateInput(attrs={"type": "date"}),
            "data_baixa": forms.DateInput(attrs={"type": "date"}),
            "motivo_baixa": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from chamados.models import Setor

        setores = Setor.objects.filter(ativo=True)
        if self.instance and self.instance.setor_id:
            setores = setores | Setor.objects.filter(pk=self.instance.setor_id)
        self.fields["setor"].queryset = setores.distinct()


class OcorrenciaAtivoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = OcorrenciaAtivo
        fields = ["tipo", "titulo", "descricao"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 4}),
        }


class RelacionamentoAtivoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = RelacionamentoAtivo
        fields = ["destino", "tipo", "descricao"]


class MovimentacaoAtivoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = MovimentacaoAtivo
        fields = [
            "setor_destino",
            "local_destino",
            "responsavel_destino",
            "ciclo_novo",
            "motivo",
        ]
        widgets = {"motivo": forms.Textarea(attrs={"rows": 4})}


class TermoResponsabilidadeAtivoForm(BootstrapFormMixin, forms.ModelForm):
    confirmar_aceite = forms.BooleanField(label="Confirmo a assinatura/aceite informado", required=True)

    class Meta:
        model = TermoResponsabilidadeAtivo
        fields = [
            "tipo", "responsavel", "matricula", "setor", "finalidade", "data_evento",
            "assinatura_nome", "confirmar_aceite",
        ]
        widgets = {
            "finalidade": forms.Textarea(attrs={"rows": 3}),
            "data_evento": forms.DateInput(attrs={"type": "date"}),
        }


class MesclarAtivosForm(BootstrapFormMixin, forms.Form):
    principal = forms.ModelChoiceField(queryset=AtivoRede.objects.all(), label="Registro principal")
    duplicados = forms.ModelMultipleChoiceField(
        queryset=AtivoRede.objects.all(), label="Registros que serao incorporados"
    )

    def clean(self):
        dados = super().clean()
        principal = dados.get("principal")
        duplicados = dados.get("duplicados")
        if principal and duplicados and principal in duplicados:
            self.add_error("duplicados", "O registro principal nao pode ser marcado como duplicado.")
        return dados


class SondaRemotaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = SondaRemota
        fields = ["nome", "localidade", "descricao", "faixas", "ativa"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "faixas": forms.SelectMultiple(attrs={"size": 8}),
        }


class LicencaSoftwareForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = LicencaSoftware
        fields = ["nome", "fabricante", "chave", "quantidade_total", "validade", "status", "ativos", "observacoes"]
        widgets = {
            "validade": forms.DateInput(attrs={"type": "date"}),
            "ativos": forms.SelectMultiple(attrs={"size": 10}),
            "observacoes": forms.Textarea(attrs={"rows": 4}),
        }


class AnexoLicencaSoftwareForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = AnexoLicencaSoftware
        fields = ["arquivo", "descricao"]


class ImportacaoAtivosCSVForm(BootstrapFormMixin, forms.Form):
    arquivo = forms.FileField(label="Arquivo CSV")
    atualizar_existentes = forms.BooleanField(
        label="Atualizar ativos existentes",
        required=False,
        initial=True,
    )


class VarreduraRedeForm(BootstrapFormMixin, forms.Form):
    metodo = forms.ChoiceField(
        label="Método de descoberta",
        choices=MetodoDescoberta.Codigo.choices,
        initial=MetodoDescoberta.Codigo.AUTO,
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


class RelatorioInventarioForm(BootstrapFormMixin, forms.Form):
    q = forms.CharField(
        label="Busca",
        required=False,
        help_text="Nome, IP, MAC, hostname, modelo ou serial.",
    )
    data_inicio = forms.DateField(
        label="Coleta inicial",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    data_fim = forms.DateField(
        label="Coleta final",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    tipo = forms.ModelChoiceField(
        label="Tipo",
        required=False,
        queryset=TipoAtivo.objects.filter(ativo=True),
        empty_label="Todos",
    )
    setor = forms.ModelChoiceField(
        label="Setor",
        required=False,
        queryset=Setor.objects.filter(ativo=True),
        empty_label="Todos",
    )
    status = forms.ChoiceField(
        label="Status",
        required=False,
        choices=[("", "Todos ativos")] + [
            escolha for escolha in AtivoRede.Status.choices if escolha[0] != AtivoRede.Status.DESATIVADO
        ],
    )
    ciclo_vida = forms.ChoiceField(
        label="Ciclo de vida",
        required=False,
        choices=[("", "Todos")] + list(AtivoRede.CicloVida.choices),
    )
    origem = forms.ChoiceField(
        label="Origem",
        required=False,
        choices=[("", "Todas")] + list(AtivoRede.Origem.choices),
    )
    familia_so = forms.ChoiceField(
        label="Familia do SO",
        required=False,
        choices=[
            ("", "Todas"),
            ("windows", "Windows"),
            ("linux", "Linux"),
            ("macos", "macOS"),
        ],
    )
    sistema_operacional = forms.ChoiceField(
        label="Sistema operacional",
        required=False,
        choices=[("", "Todos")],
    )
    fabricante = forms.ChoiceField(
        label="Fabricante",
        required=False,
        choices=[("", "Todos")],
    )
    modelo = forms.CharField(
        label="Modelo contem",
        required=False,
    )
    software = forms.CharField(
        label="Software contem",
        required=False,
    )
    coleta = forms.ChoiceField(
        label="Coleta",
        required=False,
        choices=[
            ("", "Todos"),
            ("com", "Com coleta"),
            ("sem", "Sem coleta"),
        ],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sistemas = (
            AtivoRede.objects.exclude(status=AtivoRede.Status.DESATIVADO)
            .exclude(sistema_operacional="")
            .values_list("sistema_operacional", flat=True)
            .order_by("sistema_operacional")
            .distinct()
        )
        fabricantes = (
            AtivoRede.objects.exclude(status=AtivoRede.Status.DESATIVADO)
            .exclude(fabricante="")
            .values_list("fabricante", flat=True)
            .order_by("fabricante")
            .distinct()
        )
        self.fields["sistema_operacional"].choices = [("", "Todos")] + [(item, item) for item in sistemas]
        self.fields["fabricante"].choices = [("", "Todos")] + [(item, item) for item in fabricantes]
