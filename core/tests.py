from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from .permissions import GRUPO_SUPORTE_N1, GRUPO_SUPORTE_N2


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
        self.assertContains(response, reverse("core:usuario_senha", kwargs={"pk": self.usuario.pk}))
        self.assertContains(response, reverse("core:usuario_status", kwargs={"pk": self.usuario.pk}))
        self.assertContains(response, reverse("core:usuario_excluir", kwargs={"pk": self.usuario.pk}))

    def test_admin_altera_senha_de_outro_usuario(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("core:usuario_senha", kwargs={"pk": self.usuario.pk}),
            {"new_password1": "nova-senha-forte-123", "new_password2": "nova-senha-forte-123"},
        )

        self.assertRedirects(response, reverse("core:usuarios"))
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("nova-senha-forte-123"))

    def test_admin_exclui_usuario_sem_vinculos(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse("core:usuario_excluir", kwargs={"pk": self.usuario.pk}))

        self.assertRedirects(response, reverse("core:usuarios"))
        self.assertFalse(get_user_model().objects.filter(pk=self.usuario.pk).exists())

    def test_admin_nao_exclui_proprio_usuario(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse("core:usuario_excluir", kwargs={"pk": self.admin.pk}))

        self.assertRedirects(response, reverse("core:usuarios"))
        self.assertTrue(get_user_model().objects.filter(pk=self.admin.pk).exists())

    def test_admin_desativa_usuario(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("core:usuario_status", kwargs={"pk": self.usuario.pk}),
            {"acao": "desativar"},
        )

        self.assertRedirects(response, reverse("core:usuarios"))
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.is_active)

    def test_admin_ativa_usuario(self):
        self.usuario.is_active = False
        self.usuario.save(update_fields=["is_active"])
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("core:usuario_status", kwargs={"pk": self.usuario.pk}),
            {"acao": "ativar"},
        )

        self.assertRedirects(response, reverse("core:usuarios"))
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.is_active)

    def test_admin_nao_desativa_proprio_usuario(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("core:usuario_status", kwargs={"pk": self.admin.pk}),
            {"acao": "desativar"},
        )

        self.assertRedirects(response, reverse("core:usuarios"))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

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
