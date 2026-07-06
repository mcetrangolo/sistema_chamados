from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from .permissions import GRUPO_SUPORTE_N1, GRUPO_SUPORTE_N2
from .views import ControleServicosView


class AjudaSistemaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.usuario = user_model.objects.create_user(username="atendente", password="senha-teste")
        cls.administrador = user_model.objects.create_superuser(
            username="administrador",
            email="admin@example.com",
            password="senha-teste",
        )

    def test_exige_autenticacao(self):
        response = self.client.get(reverse("core:ajuda"))

        self.assertRedirects(response, f"{reverse('login')}?next={reverse('core:ajuda')}")

    def test_usuario_autenticado_acessa_ajuda_e_os_dois_menus(self):
        self.client.force_login(self.usuario)

        response = self.client.get(reverse("core:ajuda"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ajuda do sistema")
        self.assertContains(response, "Guia operacional para uso")
        self.assertContains(response, "Como usar esta central")
        self.assertContains(response, "Perfis e permiss")
        self.assertContains(response, reverse("core:ajuda"), count=2)
        self.assertNotContains(response, reverse("core:atualizacoes"))

    def test_administrador_recebe_atalhos_operacionais(self):
        self.client.force_login(self.administrador)

        response = self.client.get(reverse("core:ajuda"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Atualiza")
        self.assertContains(response, reverse("core:atualizacoes"))
        self.assertContains(response, reverse("inventario:agente_config"))


class ControleServicosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.administrador = get_user_model().objects.create_superuser(
            username="admin-servicos",
            email="admin-servicos@example.com",
            password="senha-teste",
        )

    @patch.object(ControleServicosView, "_agendar_reinicio_container", return_value=(True, ""))
    @patch.object(ControleServicosView, "_reinicio_interno_disponivel", return_value=True)
    def test_reinicio_interno_do_container_e_agendado(self, _reinicio_disponivel, _agendar):
        self.client.force_login(self.administrador)

        response = self.client.post(
            reverse("core:servicos"),
            {"acao": "reiniciar_servicos", "confirmacao": "REINICIAR"},
        )

        self.assertRedirects(response, reverse("core:servicos"), fetch_redirect_response=False)
        self.assertIn("Reinicio interno", self.client.session["ultimo_resultado_servicos"])
        _agendar.assert_called_once_with()


class UsuariosPermissoesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin = user_model.objects.create_superuser(
            username="admin-permissoes",
            email="admin-permissoes@example.com",
            password="senha-teste",
        )
        cls.usuario = user_model.objects.create_user(
            username="usuario-comum",
            email="usuario-comum@example.com",
            password="senha-teste",
        )
        cls.n1 = user_model.objects.create_user(username="suporte-n1", password="senha-teste")
        Group.objects.create(name=GRUPO_SUPORTE_N1).user_set.add(cls.n1)
        cls.n2 = user_model.objects.create_user(username="suporte-n2", password="senha-teste")
        Group.objects.create(name=GRUPO_SUPORTE_N2).user_set.add(cls.n2)

    def test_admin_acessa_tela_de_usuarios(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("core:usuarios"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Usuários e permissões")
        self.assertContains(response, "Suporte N2")

    def test_usuario_comum_nao_acessa_tela_de_usuarios(self):
        self.client.force_login(self.usuario)

        response = self.client.get(reverse("core:usuarios"), follow=True)

        self.assertRedirects(response, reverse("chamados:painel"))

    def test_n1_nao_acessa_inventario(self):
        self.client.force_login(self.n1)

        response = self.client.get(reverse("inventario:painel"), follow=True)

        self.assertRedirects(response, reverse("chamados:painel"))

    def test_n2_acessa_inventario(self):
        self.client.force_login(self.n2)

        response = self.client.get(reverse("inventario:painel"))

        self.assertEqual(response.status_code, 200)
