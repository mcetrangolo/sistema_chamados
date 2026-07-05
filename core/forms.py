from django import forms
from django.contrib.auth import get_user_model

from .models import ConfiguracaoBackup, ConfiguracaoInstitucional, ConfiguracaoLDAP
from .permissions import PAPEIS, aplicar_papel, papel_usuario


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
            "cor_texto",
            "cor_menu_texto",
            "texto_rodape",
        ]
        widgets = {
            "cor_primaria": forms.TextInput(attrs={"type": "color"}),
            "cor_secundaria": forms.TextInput(attrs={"type": "color"}),
            "cor_fundo": forms.TextInput(attrs={"type": "color"}),
            "cor_texto": forms.TextInput(attrs={"type": "color"}),
            "cor_menu_texto": forms.TextInput(attrs={"type": "color"}),
            "portal_subtitulo": forms.Textarea(attrs={"rows": 3}),
            "portal_texto_apoio": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "tema_visual": "Escolha Personalizado para liberar o uso manual das cores abaixo.",
        }
        labels = {
            "cor_primaria": "Cor primaria",
            "cor_secundaria": "Cor secundaria",
            "cor_fundo": "Cor de fundo",
            "cor_texto": "Cor da fonte",
            "cor_menu_texto": "Cor da fonte do menu lateral",
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


class UsuarioSistemaForm(BootstrapFormMixin, forms.ModelForm):
    papel = forms.ChoiceField(label="Perfil de acesso", choices=PAPEIS)

    class Meta:
        model = get_user_model()
        fields = ["first_name", "last_name", "email", "is_active", "papel"]
        labels = {
            "first_name": "Nome",
            "last_name": "Sobrenome",
            "email": "E-mail",
            "is_active": "Usuário ativo",
        }

    def __init__(self, *args, **kwargs):
        self.usuario_logado = kwargs.pop("usuario_logado", None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["papel"].initial = papel_usuario(self.instance)

    def clean(self):
        cleaned_data = super().clean()
        if self.instance == self.usuario_logado:
            if not cleaned_data.get("is_active", True):
                self.add_error("is_active", "Nao e possivel desativar o proprio usuario logado.")
            if cleaned_data.get("papel") != "admin":
                self.add_error("papel", "Nao e possivel remover o proprio perfil de administrador.")
        return cleaned_data

    def save(self, commit=True):
        usuario = super().save(commit=False)
        aplicar_papel(usuario, self.cleaned_data["papel"])
        if commit:
            usuario.save()
            self.save_m2m()
        return usuario


class ConfiguracaoBackupForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ConfiguracaoBackup
        fields = ["ativo", "intervalo_horas", "pasta_destino", "manter_ultimos", "validar_automaticamente"]
        help_texts = {
            "pasta_destino": "Pasta local, compartilhamento de rede montado ou caminho acessivel pelo servidor.",
        }


class ConfiguracaoLDAPForm(BootstrapFormMixin, forms.ModelForm):
    senha = forms.CharField(
        label="Senha do usuario de bind",
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Deixe em branco para manter a senha atual.",
    )

    class Meta:
        model = ConfiguracaoLDAP
        fields = [
            "ativo", "servidor", "porta", "usar_ssl", "usuario_bind", "senha", "base_dn",
            "filtro_usuarios", "filtro_computadores", "atributo_login", "atributo_nome", "atributo_sobrenome",
            "atributo_email", "sincronizar_ativos",
        ]

    def save(self, commit=True):
        objeto = super().save(commit=False)
        objeto.definir_senha(self.cleaned_data.get("senha"))
        if commit:
            objeto.save()
        return objeto
