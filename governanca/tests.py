from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from chamados.models import AprovacaoSolicitacao, Chamado
from core.permissions import GRUPO_SUPORTE_N1

from .models import SolicitacaoGovernanca


class GovernancaChamadoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin = user_model.objects.create_superuser(
            username="admin-governanca",
            email="admin-governanca@example.com",
            password="senha-teste",
        )
        cls.n1 = user_model.objects.create_user(
            username="suporte-n1",
            email="suporte-n1@example.com",
            password="senha-teste",
        )
        cls.n1.groups.add(Group.objects.create(name=GRUPO_SUPORTE_N1))

    def dados_usuario_acesso(self):
        return {
            "matricula": "123",
            "nome": "Maria Silva",
            "email": "maria@example.com",
            "setor": "Administrativo",
            "cargo": "Analista",
            "telefone": "1111-1111",
            "tipo_solicitacao_rede": SolicitacaoGovernanca.TipoSolicitacaoRede.NOVO_ACESSO,
            "usuario_rede_existente": "",
            "acessos_solicitados": "Conta de rede e pasta compartilhada",
            "chefia_imediata": "João Gestor",
            "justificativa": "Novo vínculo institucional.",
            "termo_ciencia": "on",
        }

    def abrir_chamado_gov(self):
        self.client.post(reverse("governanca:usuario_acesso"), self.dados_usuario_acesso())
        return Chamado.objects.get(numero__startswith="GOV-")

    def test_solicitacao_de_rede_cria_chamado_gov_sem_aprovacao(self):
        response = self.client.post(reverse("governanca:usuario_acesso"), self.dados_usuario_acesso())

        self.assertRedirects(response, reverse("governanca:portal"), fetch_redirect_response=False)
        self.assertEqual(SolicitacaoGovernanca.objects.count(), 1)
        self.assertEqual(AprovacaoSolicitacao.objects.count(), 0)
        self.assertEqual(Chamado.objects.count(), 1)
        solicitacao = SolicitacaoGovernanca.objects.get()
        chamado = Chamado.objects.get()
        self.assertEqual(chamado.numero, solicitacao.protocolo)
        self.assertTrue(chamado.numero.startswith("GOV-"))
        self.assertEqual(chamado.status, Chamado.Status.ABERTO)
        self.assertEqual(solicitacao.status, SolicitacaoGovernanca.Status.EM_ANALISE)

    def test_consulta_publica_localiza_chamado_gov(self):
        chamado = self.abrir_chamado_gov()

        response = self.client.post(
            reverse("chamados:portal_consultar"),
            {"numero": chamado.numero, "email": chamado.email},
        )

        self.assertContains(response, chamado.numero)
        self.assertContains(response, chamado.nome_solicitante)
        self.assertContains(response, chamado.get_status_display())

    def test_lista_de_governanca_exibe_chamados_gov_para_admin(self):
        chamado = self.abrir_chamado_gov()
        self.client.force_login(self.admin)

        response = self.client.get(reverse("governanca:solicitacoes"))

        self.assertContains(response, chamado.numero)
        self.assertContains(response, chamado.get_absolute_url())
        self.assertContains(response, "Tramitar")
        self.assertNotContains(response, "Aprovar")

    def test_usuario_n1_nao_enxerga_gov_na_fila_de_chamados(self):
        chamado = self.abrir_chamado_gov()
        client = Client()
        client.force_login(self.n1)

        response = client.get(reverse("chamados:lista"), {"q": chamado.numero})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhum chamado encontrado")
        self.assertNotContains(response, chamado.get_absolute_url())
