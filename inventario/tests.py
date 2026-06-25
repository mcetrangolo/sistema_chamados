import json

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import AtivoRede, RegistroColetaAgente, TipoAtivo


class ColetaAgenteTests(TestCase):
    endpoint = "inventario:agente_coleta"

    @override_settings(INVENTARIO_AGENT_TOKEN="token-correto")
    def test_token_correto_atualiza_inventario_e_data_da_coleta(self):
        response = self.client.post(
            reverse(self.endpoint),
            data=json.dumps(
                {
                    "hostname": "PC-TESTE",
                    "ip": "192.168.10.25",
                    "mac": "00:11:22:33:44:55",
                    "sistema_operacional": "Windows 11",
                    "versao_agente": "1.4.0",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer token-correto",
        )

        self.assertEqual(response.status_code, 200)
        ativo = AtivoRede.objects.get(hostname="PC-TESTE")
        self.assertEqual(ativo.origem, AtivoRede.Origem.AGENTE)
        self.assertIsNotNone(ativo.ultima_coleta_em)
        self.assertTrue(RegistroColetaAgente.objects.filter(ativo=ativo, status="sucesso").exists())

    @override_settings(INVENTARIO_AGENT_TOKEN="token-correto")
    def test_token_incorreto_e_rejeitado_com_diagnostico(self):
        response = self.client.post(
            reverse(self.endpoint),
            data=json.dumps({"hostname": "PC-NEGADO"}),
            content_type="application/json",
            HTTP_X_AGENT_TOKEN="token-incorreto",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(AtivoRede.objects.filter(hostname="PC-NEGADO").exists())
        self.assertTrue(RegistroColetaAgente.objects.filter(status="rejeitada").exists())

    @override_settings(INVENTARIO_AGENT_TOKEN="token-correto")
    def test_agente_consulta_solicitacao_pendente(self):
        tipo = TipoAtivo.objects.create(nome="Computador")
        ativo = AtivoRede.objects.create(
            nome="PC-SOLICITADO",
            hostname="PC-SOLICITADO",
            origem=AtivoRede.Origem.AGENTE,
            tipo=tipo,
        )
        ativo.coleta_solicitada_em = ativo.atualizado_em
        ativo.save(update_fields=["coleta_solicitada_em"])

        response = self.client.get(
            reverse("inventario:agente_coleta_solicitada"),
            {"hostname": "pc-solicitado"},
            HTTP_AUTHORIZATION="Bearer token-correto",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["coleta_solicitada"])

    @override_settings(INVENTARIO_AGENT_TOKEN="token-correto")
    def test_consulta_de_solicitacao_rejeita_token_incorreto(self):
        response = self.client.get(
            reverse("inventario:agente_coleta_solicitada"),
            {"hostname": "PC-NEGADO"},
            HTTP_AUTHORIZATION="Bearer token-incorreto",
        )

        self.assertEqual(response.status_code, 403)
