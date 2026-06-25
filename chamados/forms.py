from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group

from .models import (
    AnexoChamado,
    ArtigoConhecimento,
    AvaliacaoChamado,
    CampoServicoCatalogo,
    Categoria,
    Chamado,
    ComentarioChamado,
    EquipeAtendimento,
    HistoricoChamado,
    RegraSLA,
    Mudanca,
    Problema,
    RespostaPronta,
    ServicoCatalogo,
    Setor,
    SolicitacaoServico,
    TarefaChamado,
    TopicoAjuda,
)


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "form-check-input"
            field.widget.attrs.setdefault("class", css_class)


class ChamadoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Chamado
        fields = [
            "nome_solicitante",
            "setor",
            "telefone",
            "email",
            "tipo",
            "topico_ajuda",
            "categoria",
            "equipe_responsavel",
            "ativo_rede",
            "impacto",
            "urgencia",
            "prioridade",
            "descricao",
        ]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["setor"].label = "Setor solicitante"
        setores = Setor.objects.filter(ativo=True)
        if self.instance and self.instance.setor_id:
            setores = setores | Setor.objects.filter(pk=self.instance.setor_id)
        self.fields["setor"].queryset = setores.distinct()
        if "categoria" in self.fields:
            self.fields["categoria"].required = False
        if "topico_ajuda" in self.fields:
            self.fields["topico_ajuda"].queryset = TopicoAjuda.objects.filter(ativo=True)
        if "equipe_responsavel" in self.fields:
            self.fields["equipe_responsavel"].queryset = EquipeAtendimento.objects.filter(ativo=True)

    def clean(self):
        cleaned_data = super().clean()
        topico = cleaned_data.get("topico_ajuda")
        categoria = cleaned_data.get("categoria")
        if topico:
            cleaned_data["categoria"] = topico.categoria
            self.instance.categoria = topico.categoria
            if not cleaned_data.get("prioridade"):
                self.instance.prioridade = topico.prioridade_padrao
            if topico.atendente_padrao_id:
                self.instance.tecnico_responsavel = topico.atendente_padrao
        elif not categoria:
            self.add_error("categoria", "Informe uma categoria ou selecione um tópico de ajuda.")
        return cleaned_data


class PortalChamadoForm(ChamadoForm):
    email = forms.EmailField(label="E-mail")

    class Meta(ChamadoForm.Meta):
        fields = [
            "nome_solicitante",
            "setor",
            "telefone",
            "email",
            "tipo",
            "categoria",
            "prioridade",
            "descricao",
        ]

    def __init__(
        self,
        *args,
        ativo_detectado=None,
        ip_cliente="",
        hostname_cliente="",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.fields["descricao"].label = "Descreva o problema ou solicitação"
        self.fields["descricao"].help_text = "Inclua local, equipamento afetado, mensagem de erro e desde quando acontece, se souber."
        self.fields["prioridade"].label = "Prioridade percebida"
        self.fields["tipo"].label = "Tipo de atendimento"
        self.instance.impacto = self.instance.impacto or Chamado.Impacto.MEDIO
        self.instance.urgencia = self.instance.urgencia or Chamado.Urgencia.MEDIA
        campo_ativo = self.fields.get("ativo_rede")
        if not campo_ativo:
            return

        campo_ativo.label = "Ativo/equipamento"
        campo_ativo.required = False
        campo_ativo.empty_label = "Nao sei / equipamento nao listado"

        if ativo_detectado:
            self.initial.setdefault("ativo_rede", ativo_detectado.pk)
            campo_ativo.help_text = (
                f"Detectado automaticamente pela rede: {ativo_detectado}. "
                "Voce pode alterar se o equipamento estiver incorreto."
            )
        elif ip_cliente:
            partes = [f"IP detectado: {ip_cliente}."]
            if hostname_cliente:
                partes.append(f"Nome identificado: {hostname_cliente}.")
            partes.append("Se o equipamento estiver no inventario, selecione-o.")
            campo_ativo.help_text = " ".join(partes)


class AtualizacaoChamadoForm(BootstrapFormMixin, forms.ModelForm):
    registro_atendimento = forms.CharField(
        label="Registro do atendimento",
        required=False,
        help_text="Use este campo para registrar andamento, orientação ao usuário ou solução aplicada.",
        widget=forms.Textarea(attrs={"rows": 5}),
    )

    class Meta:
        model = Chamado
        fields = [
            "tipo",
            "status",
            "impacto",
            "urgencia",
            "prioridade",
            "topico_ajuda",
            "categoria",
            "equipe_responsavel",
            "tecnico_responsavel",
            "registro_atendimento",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["topico_ajuda"].queryset = TopicoAjuda.objects.filter(ativo=True)
        self.fields["categoria"].required = False
        self.fields["equipe_responsavel"].queryset = EquipeAtendimento.objects.filter(ativo=True)
        self.fields["tecnico_responsavel"].label = "Atendente responsável"
        grupo = Group.objects.filter(name="Técnicos de TI").first()
        if grupo:
            self.fields["tecnico_responsavel"].queryset = get_user_model().objects.filter(
                groups=grupo,
                is_active=True,
            )

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        registro = cleaned_data.get("registro_atendimento", "").strip()
        topico = cleaned_data.get("topico_ajuda")
        categoria = cleaned_data.get("categoria")

        if topico:
            cleaned_data["categoria"] = topico.categoria
            self.instance.categoria = topico.categoria
            if topico.atendente_padrao_id and not cleaned_data.get("tecnico_responsavel"):
                cleaned_data["tecnico_responsavel"] = topico.atendente_padrao
                self.instance.tecnico_responsavel = topico.atendente_padrao
        elif not categoria:
            self.add_error("categoria", "Informe uma categoria ou selecione um tópico de ajuda.")

        if status in {Chamado.Status.RESOLVIDO, Chamado.Status.ENCERRADO}:
            if not registro and not self.instance.solucao_aplicada.strip():
                self.add_error(
                    "registro_atendimento",
                    "Informe o registro do atendimento para resolver ou encerrar o chamado.",
                )
            elif registro:
                self.instance.solucao_aplicada = registro

        return cleaned_data


class HistoricoChamadoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = HistoricoChamado
        fields = ["comentario"]
        widgets = {
            "comentario": forms.Textarea(attrs={"rows": 4}),
        }


class AtribuicaoChamadoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Chamado
        fields = ["equipe_responsavel", "tecnico_responsavel"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["equipe_responsavel"].label = "Encaminhar para equipe"
        self.fields["equipe_responsavel"].queryset = EquipeAtendimento.objects.filter(ativo=True)
        self.fields["tecnico_responsavel"].label = "Encaminhar para atendente"
        grupo = Group.objects.filter(name="Técnicos de TI").first()
        users = get_user_model().objects.filter(is_active=True)
        if grupo:
            users = users.filter(groups=grupo)
        else:
            users = users.filter(is_staff=True)
        self.fields["tecnico_responsavel"].queryset = users.order_by("first_name", "username")


class AnexoChamadoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = AnexoChamado
        fields = ["arquivo", "descricao"]


class ComentarioInternoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ComentarioChamado
        fields = ["mensagem", "publico"]
        widgets = {
            "mensagem": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "mensagem": "Resposta ou observação",
            "publico": "Visível para o solicitante",
        }


class ComentarioPortalForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ComentarioChamado
        fields = ["mensagem"]
        widgets = {
            "mensagem": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "mensagem": "Mensagem para a equipe de TI",
        }


class ConsultaChamadoForm(BootstrapFormMixin, forms.Form):
    numero = forms.CharField(label="Número do chamado", max_length=30)
    email = forms.EmailField(label="E-mail informado na abertura")


class SetorForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Setor
        fields = ["nome", "ativo"]


class CategoriaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ["nome", "ativo"]


class EquipeAtendimentoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = EquipeAtendimento
        fields = ["nome", "descricao", "responsavel", "membros", "ativo"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "membros": forms.SelectMultiple(attrs={"size": 8}),
        }


class RegraSLAForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = RegraSLA
        fields = [
            "nome",
            "tipo",
            "prioridade",
            "categoria",
            "setor",
            "equipe",
            "prazo_primeira_resposta_horas",
            "prazo_solucao_horas",
            "ativo",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        setores = Setor.objects.filter(ativo=True)
        if self.instance and self.instance.setor_id:
            setores = setores | Setor.objects.filter(pk=self.instance.setor_id)
        self.fields["setor"].queryset = setores.distinct()


class TopicoAjudaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = TopicoAjuda
        fields = [
            "nome",
            "descricao",
            "categoria",
            "prioridade_padrao",
            "atendente_padrao",
            "sla_horas",
            "ativo",
        ]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        grupo = Group.objects.filter(name="Técnicos de TI").first()
        users = get_user_model().objects.filter(is_active=True)
        if grupo:
            users = users.filter(groups=grupo)
        else:
            users = users.filter(is_staff=True)
        self.fields["atendente_padrao"].label = "Atendente padrão"
        self.fields["atendente_padrao"].queryset = users.order_by("first_name", "username")


class RespostaProntaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = RespostaPronta
        fields = ["titulo", "conteudo", "ativo"]
        widgets = {
            "conteudo": forms.Textarea(attrs={"rows": 6}),
        }


class TarefaChamadoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = TarefaChamado
        fields = ["titulo", "descricao", "responsavel", "status", "prazo"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
            "prazo": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class TecnicoForm(BootstrapFormMixin, UserCreationForm):
    first_name = forms.CharField(label="Nome", max_length=150)
    last_name = forms.CharField(label="Sobrenome", max_length=150, required=False)
    email = forms.EmailField(label="E-mail")
    is_staff = forms.BooleanField(
        label="Permitir acesso ao admin",
        required=False,
        initial=True,
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "is_staff",
            "password1",
            "password2",
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.is_staff = self.cleaned_data["is_staff"]

        if commit:
            user.save()
            grupo, _ = Group.objects.get_or_create(name="Técnicos de TI")
            user.groups.add(grupo)
        return user


class AtendenteExistenteForm(BootstrapFormMixin, forms.Form):
    usuario = forms.ModelChoiceField(
        label="Usuário do sistema",
        queryset=get_user_model().objects.none(),
        help_text="Selecione um usuário já cadastrado para atuar como atendente.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        grupo = Group.objects.filter(name="Técnicos de TI").first()
        usuarios = get_user_model().objects.filter(is_active=True)
        if grupo:
            usuarios = usuarios.exclude(groups=grupo)
        self.fields["usuario"].queryset = usuarios.order_by("first_name", "username")

    def save(self):
        usuario = self.cleaned_data["usuario"]
        grupo, _ = Group.objects.get_or_create(name="Técnicos de TI")
        usuario.groups.add(grupo)
        return usuario


class RelatorioChamadosForm(BootstrapFormMixin, forms.Form):
    AGRUPAMENTO_CHOICES = [
        ("status", "Status"),
        ("tipo", "Tipo"),
        ("atendente", "Atendente"),
        ("setor", "Setor"),
        ("categoria", "Categoria"),
        ("prioridade", "Prioridade"),
    ]

    data_inicio = forms.DateField(
        label="Data inicial",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    data_fim = forms.DateField(
        label="Data final",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    status = forms.ChoiceField(
        label="Status",
        required=False,
        choices=[("", "Todos")] + list(Chamado.Status.choices),
    )
    tipo = forms.ChoiceField(
        label="Tipo",
        required=False,
        choices=[("", "Todos")] + list(Chamado.Tipo.choices),
    )
    prioridade = forms.ChoiceField(
        label="Prioridade",
        required=False,
        choices=[("", "Todas")] + list(Chamado.Prioridade.choices),
    )
    setor = forms.ModelChoiceField(
        label="Setor",
        required=False,
        queryset=Setor.objects.filter(ativo=True),
        empty_label="Todos",
    )
    categoria = forms.ModelChoiceField(
        label="Categoria",
        required=False,
        queryset=Categoria.objects.filter(ativo=True),
        empty_label="Todas",
    )
    atendente = forms.ModelChoiceField(
        label="Atendente",
        required=False,
        queryset=get_user_model().objects.none(),
        empty_label="Todos",
    )
    agrupamento = forms.ChoiceField(
        label="Agrupar por",
        required=False,
        choices=AGRUPAMENTO_CHOICES,
        initial="status",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        grupo = Group.objects.filter(name="Técnicos de TI").first()
        users = get_user_model().objects.filter(is_active=True)
        if grupo:
            users = users.filter(groups=grupo)
        else:
            users = users.filter(is_staff=True)
        self.fields["atendente"].queryset = users.order_by("first_name", "username")


class ArtigoConhecimentoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ArtigoConhecimento
        fields = [
            "titulo",
            "topico_ajuda",
            "resumo",
            "conteudo",
            "video_youtube_url",
            "imagem",
            "legenda_imagem",
            "publico",
            "ativo",
        ]
        widgets = {
            "conteudo": forms.Textarea(attrs={"rows": 10}),
            "resumo": forms.TextInput(attrs={"placeholder": "Resumo curto para listagens"}),
        }


class AvaliacaoChamadoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = AvaliacaoChamado
        fields = ["nota", "comentario"]
        widgets = {
            "comentario": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "nota": "Nota do atendimento",
            "comentario": "Comentário",
        }


class ServicoCatalogoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ServicoCatalogo
        fields = [
            "nome",
            "descricao",
            "topico_ajuda",
            "categoria",
            "tipo_chamado",
            "prioridade_padrao",
            "equipe_padrao",
            "aprovador_padrao",
            "requer_matricula",
            "requer_aprovacao",
            "instrucoes",
            "ativo",
        ]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 4}),
            "instrucoes": forms.Textarea(attrs={"rows": 4}),
        }


class CampoServicoCatalogoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = CampoServicoCatalogo
        fields = ["nome", "rotulo", "tipo", "opcoes", "obrigatorio", "ordem", "ativo"]
        widgets = {
            "opcoes": forms.Textarea(attrs={"rows": 4, "placeholder": "Uma opcao por linha"}),
        }


class SolicitacaoServicoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = SolicitacaoServico
        fields = ["matricula", "nome", "email", "setor", "telefone", "detalhes"]
        widgets = {
            "detalhes": forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, servico=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.servico = servico
        setores = Setor.objects.filter(ativo=True)
        if self.instance and self.instance.setor_id:
            setores = setores | Setor.objects.filter(pk=self.instance.setor_id)
        self.fields["setor"].queryset = setores.distinct()
        if servico and not servico.requer_matricula:
            self.fields["matricula"].required = False
        else:
            self.fields["matricula"].required = True
        self.campos_dinamicos = []
        campos_visuais = []
        if servico and servico.pk:
            campos_visuais = list(servico.campos.filter(ativo=True))
        campos_legados = getattr(servico, "campos_personalizados", None) or []
        for campo in campos_visuais:
            nome = campo.nome
            field_name = f"extra_{nome}"
            rotulo = campo.rotulo
            tipo = campo.tipo
            obrigatorio = campo.obrigatorio
            opcoes = campo.lista_opcoes
            self._adicionar_campo_dinamico(field_name, nome, rotulo, tipo, obrigatorio, opcoes)
        for campo in campos_legados:
            nome = str(campo.get("nome", "")).strip()
            if not nome:
                continue
            field_name = f"extra_{nome}"
            rotulo = campo.get("rotulo") or campo.get("label") or nome.replace("_", " ").title()
            tipo = campo.get("tipo", "texto")
            obrigatorio = bool(campo.get("obrigatorio", False))
            opcoes = campo.get("opcoes") or campo.get("choices") or []
            self._adicionar_campo_dinamico(field_name, nome, rotulo, tipo, obrigatorio, opcoes)

    def _adicionar_campo_dinamico(self, field_name, nome, rotulo, tipo, obrigatorio, opcoes):
        if tipo == "texto_longo":
            field = forms.CharField(label=rotulo, required=obrigatorio, widget=forms.Textarea(attrs={"rows": 4}))
        elif tipo == "numero":
            field = forms.DecimalField(label=rotulo, required=obrigatorio)
        elif tipo == "data":
            field = forms.DateField(label=rotulo, required=obrigatorio, widget=forms.DateInput(attrs={"type": "date"}))
        elif tipo == "email":
            field = forms.EmailField(label=rotulo, required=obrigatorio)
        elif tipo == "checkbox":
            field = forms.BooleanField(label=rotulo, required=False)
        elif tipo == "selecao":
            choices = [("", "Selecione")] + [(str(item), str(item)) for item in opcoes]
            field = forms.ChoiceField(label=rotulo, required=obrigatorio, choices=choices)
        else:
            field = forms.CharField(label=rotulo, required=obrigatorio)
        self.fields[field_name] = field
        self.campos_dinamicos.append((field_name, nome, rotulo))

    def save(self, commit=True):
        instance = super().save(commit=False)
        dados = {}
        for field_name, nome, rotulo in getattr(self, "campos_dinamicos", []):
            valor = self.cleaned_data.get(field_name)
            if hasattr(valor, "isoformat"):
                valor = valor.isoformat()
            dados[nome] = {"rotulo": rotulo, "valor": valor}
        instance.dados_personalizados = dados
        if commit:
            instance.save()
        return instance


class ProblemaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Problema
        fields = [
            "titulo",
            "chamado_principal",
            "chamados_relacionados",
            "responsavel",
            "status",
            "causa_raiz",
            "workaround",
            "solucao_definitiva",
        ]
        widgets = {
            "chamados_relacionados": forms.SelectMultiple(attrs={"size": 8}),
            "causa_raiz": forms.Textarea(attrs={"rows": 4}),
            "workaround": forms.Textarea(attrs={"rows": 4}),
            "solucao_definitiva": forms.Textarea(attrs={"rows": 4}),
        }


class MudancaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Mudanca
        fields = [
            "titulo",
            "chamado",
            "responsavel",
            "aprovador",
            "status",
            "risco",
            "impacto",
            "plano_execucao",
            "plano_rollback",
            "janela_inicio",
            "janela_fim",
            "validacao_pos_mudanca",
        ]
        widgets = {
            "impacto": forms.Textarea(attrs={"rows": 4}),
            "plano_execucao": forms.Textarea(attrs={"rows": 5}),
            "plano_rollback": forms.Textarea(attrs={"rows": 5}),
            "janela_inicio": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "janela_fim": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "validacao_pos_mudanca": forms.Textarea(attrs={"rows": 4}),
        }
