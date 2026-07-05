import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from core.permissions import GRUPO_TECNICOS

from .models import Categoria, Chamado, ComentarioChamado, HistoricoChamado, Setor


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


class FluxoChamadoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.tecnico = user_model.objects.create_user(
            username="tecnico",
            email="tecnico@example.com",
            password="senha-teste",
        )
        cls.setor = Setor.objects.create(nome="TI")
        cls.categoria = Categoria.objects.create(nome="Suporte")

    def criar_chamado(self, **kwargs):
        dados = {
            "nome_solicitante": "Usuario Teste",
            "email": "usuario@example.com",
            "setor": self.setor,
            "categoria": self.categoria,
            "descricao": "Preciso de atendimento.",
        }
        dados.update(kwargs)
        return Chamado.objects.create(**dados)

    def test_atribuir_chamado_para_mim_altera_status_e_registra_historico(self):
        chamado = self.criar_chamado()
        self.client.force_login(self.tecnico)

        response = self.client.post(reverse("chamados:atribuir_mim", args=[chamado.pk]))

        self.assertRedirects(response, chamado.get_absolute_url())
        chamado.refresh_from_db()
        self.assertEqual(chamado.tecnico_responsavel, self.tecnico)
        self.assertEqual(chamado.status, Chamado.Status.EM_ATENDIMENTO)
        self.assertTrue(
            HistoricoChamado.objects.filter(
                chamado=chamado,
                usuario=self.tecnico,
                comentario="Chamado atribuido ao atendente logado.",
            ).exists()
        )

    def test_resolver_rapido_registra_solucao_comentario_e_primeira_resposta(self):
        chamado = self.criar_chamado()
        self.client.force_login(self.tecnico)

        response = self.client.post(
            reverse("chamados:resolver_rapido", args=[chamado.pk]),
            {"solucao_aplicada": "Reiniciado o servico."},
        )

        self.assertRedirects(response, chamado.get_absolute_url())
        chamado.refresh_from_db()
        self.assertEqual(chamado.status, Chamado.Status.RESOLVIDO)
        self.assertEqual(chamado.solucao_aplicada, "Reiniciado o servico.")
        self.assertIsNotNone(chamado.primeira_resposta_em)
        self.assertTrue(
            ComentarioChamado.objects.filter(
                chamado=chamado,
                autor=self.tecnico,
                mensagem="Reiniciado o servico.",
                publico=True,
            ).exists()
        )

    def test_reabrir_chamado_pelo_portal_retorna_para_atendimento(self):
        chamado = self.criar_chamado(
            status=Chamado.Status.RESOLVIDO,
            solucao_aplicada="Resolvido inicialmente.",
        )

        response = self.client.post(
            reverse("chamados:portal_reabrir", args=[chamado.pk]),
            {
                "email_confirmacao": chamado.email,
                "motivo": "O problema voltou.",
            },
        )

        self.assertRedirects(response, reverse("chamados:portal_consultar"))
        chamado.refresh_from_db()
        self.assertEqual(chamado.status, Chamado.Status.EM_ATENDIMENTO)
        self.assertTrue(
            ComentarioChamado.objects.filter(
                chamado=chamado,
                mensagem="Solicitacao de reabertura: O problema voltou.",
                publico=True,
            ).exists()
        )


class ChamadosApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.tecnico = user_model.objects.create_user(
            username="api-tecnico",
            email="api-tecnico@example.com",
            password="senha-teste",
        )
        cls.tecnico.groups.add(Group.objects.create(name=GRUPO_TECNICOS))
        cls.setor = Setor.objects.create(nome="API TI")
        cls.categoria = Categoria.objects.create(nome="API Suporte")
        cls.chamado = Chamado.objects.create(
            nome_solicitante="Usuario API",
            email="api@example.com",
            setor=cls.setor,
            categoria=cls.categoria,
            descricao="Chamado criado para teste de API.",
        )

    def test_api_lista_chamados_com_resposta_padronizada(self):
        self.client.force_login(self.tecnico)

        response = self.client.get("/api/v1/chamados/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"][0]["numero"], self.chamado.numero)

    def test_api_cria_chamado(self):
        self.client.force_login(self.tecnico)

        response = self.client.post(
            "/api/v1/chamados/",
            data=json.dumps({
                "nome_solicitante": "Novo API",
                "email": "novo@example.com",
                "setor_id": self.setor.pk,
                "categoria_id": self.categoria.pk,
                "descricao": "Solicitacao via API.",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertTrue(Chamado.objects.filter(numero=payload["data"]["numero"]).exists())
