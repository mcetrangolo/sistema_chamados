from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from chamados.models import AprovacaoSolicitacao, Chamado

from .models import SolicitacaoGovernanca


class GovernancaAprovacaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser(
            username="admin-governanca",
            email="admin-governanca@example.com",
            password="senha-teste",
        )

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

    def criar_solicitacao_com_aprovacao(self):
        solicitacao = SolicitacaoGovernanca.objects.create(
            tipo=SolicitacaoGovernanca.Tipo.USUARIO_ACESSO,
            matricula="456",
            nome="Carlos Souza",
            email="carlos@example.com",
            setor="TI",
            cargo="Técnico",
            tipo_solicitacao_rede=SolicitacaoGovernanca.TipoSolicitacaoRede.NOVO_ACESSO,
            acessos_solicitados="Conta de rede",
            termo_ciencia=True,
        )
        aprovacao = AprovacaoSolicitacao.objects.create(
            origem=AprovacaoSolicitacao.Origem.GOVERNANCA,
            governanca_id=solicitacao.pk,
            titulo="Aprovar governança",
            solicitante=solicitacao.nome,
        )
        return solicitacao, aprovacao

    def test_solicitacao_de_rede_cria_aprovacao_sem_chamado(self):
        response = self.client.post(reverse("governanca:usuario_acesso"), self.dados_usuario_acesso())

        self.assertRedirects(response, reverse("governanca:portal"), fetch_redirect_response=False)
        self.assertEqual(SolicitacaoGovernanca.objects.count(), 1)
        self.assertEqual(AprovacaoSolicitacao.objects.count(), 1)
        self.assertEqual(Chamado.objects.count(), 0)
        aprovacao = AprovacaoSolicitacao.objects.get()
        self.assertEqual(aprovacao.origem, AprovacaoSolicitacao.Origem.GOVERNANCA)
        self.assertEqual(aprovacao.status, AprovacaoSolicitacao.Status.PENDENTE)

    def test_aprovar_governanca_converte_em_chamado(self):
        solicitacao, aprovacao = self.criar_solicitacao_com_aprovacao()
        self.client.force_login(self.admin)

        response = self.client.post(reverse("chamados:decidir_aprovacao", kwargs={"pk": aprovacao.pk, "decisao": "aprovar"}))

        self.assertRedirects(response, reverse("chamados:aprovacoes"))
        aprovacao.refresh_from_db()
        solicitacao.refresh_from_db()
        self.assertEqual(aprovacao.status, AprovacaoSolicitacao.Status.APROVADA)
        self.assertEqual(solicitacao.status, SolicitacaoGovernanca.Status.EM_ANALISE)
        self.assertEqual(Chamado.objects.count(), 1)

    def test_rejeitar_governanca_marca_solicitacao_como_negada(self):
        solicitacao, aprovacao = self.criar_solicitacao_com_aprovacao()
        self.client.force_login(self.admin)

        response = self.client.post(reverse("chamados:decidir_aprovacao", kwargs={"pk": aprovacao.pk, "decisao": "rejeitar"}))

        self.assertRedirects(response, reverse("chamados:aprovacoes"))
        aprovacao.refresh_from_db()
        solicitacao.refresh_from_db()
        self.assertEqual(aprovacao.status, AprovacaoSolicitacao.Status.REJEITADA)
        self.assertEqual(solicitacao.status, SolicitacaoGovernanca.Status.NEGADA)
        self.assertEqual(Chamado.objects.count(), 0)

    def test_lista_de_governanca_exibe_acoes_de_aprovacao(self):
        _, aprovacao = self.criar_solicitacao_com_aprovacao()
        self.client.force_login(self.admin)

        response = self.client.get(reverse("governanca:solicitacoes"))

        self.assertContains(response, reverse("chamados:decidir_aprovacao", kwargs={"pk": aprovacao.pk, "decisao": "aprovar"}))
        self.assertContains(response, "Aprovar")
        self.assertContains(response, "Rejeitar")
        self.assertContains(response, reverse("governanca:solicitacoes"))

    def test_consulta_publica_localiza_protocolo_governanca(self):
        solicitacao, _ = self.criar_solicitacao_com_aprovacao()

        response = self.client.post(
            reverse("chamados:portal_consultar"),
            {"numero": solicitacao.protocolo, "email": solicitacao.email},
        )

        self.assertContains(response, solicitacao.protocolo)
        self.assertContains(response, "Solicitação de governança")
        self.assertContains(response, "Recebida")
