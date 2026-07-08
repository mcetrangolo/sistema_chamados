from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from core.permissions import GRUPO_SUPORTE_N1

from .models import DEFAULT_BPMN_XML, DiagramaBPMN


class ProcessosBPMNTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin = user_model.objects.create_superuser(
            username="admin-processos",
            email="admin-processos@example.com",
            password="senha-teste",
        )
        cls.n1 = user_model.objects.create_user(
            username="n1-processos",
            email="n1-processos@example.com",
            password="senha-teste",
        )
        cls.n1.groups.add(Group.objects.create(name=GRUPO_SUPORTE_N1))

    def test_admin_cria_diagrama_bpmn(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("processos:novo"),
            {
                "titulo": "Fluxo de governança",
                "descricao": "Processo de acesso à rede.",
                "xml": DEFAULT_BPMN_XML,
                "ativo": "on",
                "exibir_portal": "on",
            },
        )

        diagrama = DiagramaBPMN.objects.get()
        self.assertRedirects(response, diagrama.get_absolute_url())
        self.assertEqual(diagrama.criado_por, self.admin)
        self.assertTrue(diagrama.exibir_portal)
        self.assertIn("<bpmn:definitions", diagrama.xml)

    def test_diagrama_tem_pagina_propria_e_exportacao(self):
        diagrama = DiagramaBPMN.objects.create(titulo="Atendimento", xml=DEFAULT_BPMN_XML)
        self.client.force_login(self.admin)

        response = self.client.get(diagrama.get_absolute_url())
        export_response = self.client.get(reverse("processos:exportar", args=[diagrama.pk]))

        self.assertContains(response, "Atendimento")
        self.assertEqual(export_response.status_code, 200)
        self.assertEqual(export_response["Content-Type"], "application/xml; charset=utf-8")
        self.assertIn(b"<bpmn:definitions", export_response.content)

    def test_editor_tem_zoom_cores_importacao_e_exportacao(self):
        diagrama = DiagramaBPMN.objects.create(titulo="Editor BPMN", xml=DEFAULT_BPMN_XML)
        self.client.force_login(self.admin)

        response = self.client.get(reverse("processos:editar", args=[diagrama.pk]))

        self.assertContains(response, 'id="bpmn-zoom-in"')
        self.assertContains(response, 'id="bpmn-zoom-out"')
        self.assertContains(response, 'id="bpmn-fit"')
        self.assertContains(response, 'id="bpmn-fullscreen"')
        self.assertContains(response, 'id="bpmn-fill-color"')
        self.assertContains(response, 'id="bpmn-stroke-color"')
        self.assertContains(response, 'id="bpmn-import"')
        self.assertContains(response, 'id="bpmn-download"')

    def test_usuario_n1_nao_acessa_processos(self):
        self.client.force_login(self.n1)

        response = self.client.get(reverse("processos:lista"))

        self.assertEqual(response.status_code, 403)

    def test_portal_exibe_apenas_diagramas_ativos_e_publicos(self):
        publico = DiagramaBPMN.objects.create(
            titulo="Fluxo público",
            xml=DEFAULT_BPMN_XML,
            ativo=True,
            exibir_portal=True,
        )
        DiagramaBPMN.objects.create(
            titulo="Fluxo interno",
            xml=DEFAULT_BPMN_XML,
            ativo=True,
            exibir_portal=False,
        )
        DiagramaBPMN.objects.create(
            titulo="Fluxo inativo",
            xml=DEFAULT_BPMN_XML,
            ativo=False,
            exibir_portal=True,
        )

        response = self.client.get(reverse("processos_publicos:lista"))
        detail_response = self.client.get(reverse("processos_publicos:detalhe", args=[publico.pk]))

        self.assertContains(response, "Fluxo público")
        self.assertNotContains(response, "Fluxo interno")
        self.assertNotContains(response, "Fluxo inativo")
        self.assertContains(detail_response, "Fluxo público")

    def test_portal_nao_abre_diagrama_interno(self):
        interno = DiagramaBPMN.objects.create(
            titulo="Fluxo interno",
            xml=DEFAULT_BPMN_XML,
            ativo=True,
            exibir_portal=False,
        )

        response = self.client.get(reverse("processos_publicos:detalhe", args=[interno.pk]))

        self.assertEqual(response.status_code, 404)

    def test_portal_nao_abre_diagrama_inativo(self):
        inativo = DiagramaBPMN.objects.create(
            titulo="Fluxo inativo",
            xml=DEFAULT_BPMN_XML,
            ativo=False,
            exibir_portal=True,
        )

        response = self.client.get(reverse("processos_publicos:detalhe", args=[inativo.pk]))

        self.assertEqual(response.status_code, 404)

    def test_admin_exclui_diagrama_bpmn(self):
        diagrama = DiagramaBPMN.objects.create(titulo="Excluir BPMN", xml=DEFAULT_BPMN_XML)
        self.client.force_login(self.admin)

        response = self.client.post(reverse("processos:excluir", args=[diagrama.pk]))

        self.assertRedirects(response, reverse("processos:lista"))
        self.assertFalse(DiagramaBPMN.objects.filter(pk=diagrama.pk).exists())
