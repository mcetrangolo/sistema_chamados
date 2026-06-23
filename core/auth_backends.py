from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from .models import ConfiguracaoLDAP


class CaseInsensitiveModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        login = username or kwargs.get(UserModel.USERNAME_FIELD)
        if login is None or password is None:
            return None

        try:
            user = UserModel._default_manager.get(
                **{f"{UserModel.USERNAME_FIELD}__iexact": login}
            )
        except UserModel.DoesNotExist:
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None


class LDAPOpcionalBackend(ModelBackend):
    """Autentica no LDAP somente quando a integracao web estiver ativa."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        try:
            configuracao = ConfiguracaoLDAP.objects.filter(pk=1, ativo=True).first()
        except Exception:
            return None
        if not configuracao or not configuracao.servidor or not configuracao.base_dn:
            return None

        try:
            from ldap3 import Connection, Server
            from ldap3.utils.conv import escape_filter_chars

            servidor = Server(
                configuracao.servidor,
                port=configuracao.porta,
                use_ssl=configuracao.usar_ssl,
            )
            conexao = Connection(
                servidor,
                user=configuracao.usuario_bind,
                password=configuracao.obter_senha(),
                auto_bind=True,
            )
            filtro = (
                f"(&{configuracao.filtro_usuarios}"
                f"({configuracao.atributo_login}={escape_filter_chars(username)}))"
            )
            atributos = [
                configuracao.atributo_login,
                configuracao.atributo_nome,
                configuracao.atributo_sobrenome,
                configuracao.atributo_email,
            ]
            conexao.search(configuracao.base_dn, filtro, attributes=atributos, size_limit=2)
            if len(conexao.entries) != 1:
                conexao.unbind()
                return None
            entrada = conexao.entries[0]
            dn_usuario = entrada.entry_dn
            conexao.unbind()

            autenticacao = Connection(servidor, user=dn_usuario, password=password, auto_bind=True)
            autenticacao.unbind()
        except Exception:
            return None

        def valor(nome):
            atributo = getattr(entrada, nome, None)
            return str(atributo.value or "").strip() if atributo else ""

        User = get_user_model()
        login = valor(configuracao.atributo_login) or username
        usuario = User.objects.filter(username__iexact=login).first()
        if usuario is None:
            usuario = User(username=login.lower())
            usuario.set_unusable_password()
        usuario.first_name = valor(configuracao.atributo_nome)[:150]
        usuario.last_name = valor(configuracao.atributo_sobrenome)[:150]
        usuario.email = valor(configuracao.atributo_email)[:254]
        if configuracao.sincronizar_ativos:
            usuario.is_active = True
        usuario.save()
        return usuario if self.user_can_authenticate(usuario) else None
