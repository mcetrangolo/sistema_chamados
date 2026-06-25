from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse


class AtendentesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin = user_model.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="senha-teste",
        )
        cls.usuario = user_model.objects.create_user(
            username="usuario",
            email="usuario@example.com",
            password="senha-teste",
        )
        cls.atendente = user_model.objects.create_user(
            username="atendente",
            email="atendente@example.com",
            password="senha-teste",
        )
        cls.grupo = Group.objects.create(name="Técnicos de TI")
        cls.atendente.groups.add(cls.grupo)

    def test_adiciona_usuario_existente_como_atendente(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse("chamados:tecnico_adicionar"), {"usuario": self.usuario.pk})

        self.assertRedirects(response, reverse("chamados:tecnicos"))
        self.assertTrue(self.usuario.groups.filter(name="Técnicos de TI").exists())

    def test_remover_atendente_nao_desativa_usuario(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse("chamados:tecnico_desativar", args=[self.atendente.pk]))

        self.assertRedirects(response, reverse("chamados:tecnicos"))
        self.atendente.refresh_from_db()
        self.assertTrue(self.atendente.is_active)
        self.assertFalse(self.atendente.groups.filter(name="Técnicos de TI").exists())

    def test_usuario_comum_nao_acessa_gestao_de_atendentes(self):
        self.client.force_login(self.usuario)

        response = self.client.get(reverse("chamados:tecnicos"))

        self.assertEqual(response.status_code, 403)
