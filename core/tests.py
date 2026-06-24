from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

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
        self.assertContains(response, "Manual operacional da area interna")
        self.assertContains(response, "nao e destinada aos usuarios finais")
        self.assertContains(response, reverse("core:ajuda"), count=2)
        self.assertNotContains(response, ">Verificar atualizacoes<")

    def test_administrador_recebe_atalhos_operacionais(self):
        self.client.force_login(self.administrador)

        response = self.client.get(reverse("core:ajuda"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verificar atualizacoes")
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
