from django.conf import settings
from django.db import models
from django.urls import reverse


class DocumentoInfra(models.Model):
    class Tipo(models.TextChoices):
        TOPOLOGIA = "topologia", "Topologia"
        REDE = "rede", "Rede"
        CREDENCIAL = "credencial", "Credenciais e acessos"
        SERVIDOR = "servidor", "Servidor"
        SISTEMA = "sistema", "Sistema"
        PROCEDIMENTO = "procedimento", "Procedimento"
        OUTRO = "outro", "Outro"

    class Criticidade(models.TextChoices):
        BAIXA = "baixa", "Baixa"
        MEDIA = "media", "Média"
        ALTA = "alta", "Alta"
        CRITICA = "critica", "Crítica"

    titulo = models.CharField(max_length=180)
    tipo = models.CharField(max_length=30, choices=Tipo.choices, default=Tipo.TOPOLOGIA)
    criticidade = models.CharField(max_length=20, choices=Criticidade.choices, default=Criticidade.MEDIA)
    localizacao = models.CharField("localização/unidade", max_length=180, blank=True)
    resumo = models.TextField(blank=True)
    conteudo = models.TextField("documentação técnica", blank=True)
    conteudo_restrito = models.TextField(
        "informações restritas",
        blank=True,
        help_text="Use para senhas, chaves, configurações sensíveis e observações de acesso.",
    )
    usuarios_autorizados = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="documentos_infra_autorizados",
        help_text="Superusuários sempre possuem acesso. Demais usuários precisam estar nesta lista.",
    )
    ativo = models.BooleanField(default=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_infra_criados",
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_infra_atualizados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["tipo", "titulo"]
        verbose_name = "documentação de infraestrutura"
        verbose_name_plural = "documentações de infraestrutura"

    def __str__(self):
        return self.titulo

    def get_absolute_url(self):
        return reverse("documentacao:detalhe", kwargs={"pk": self.pk})


class AnexoDocumentoInfra(models.Model):
    documento = models.ForeignKey(DocumentoInfra, on_delete=models.CASCADE, related_name="anexos")
    arquivo = models.FileField(upload_to="documentacao_infra/anexos/%Y/%m/")
    descricao = models.CharField(max_length=180, blank=True)
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "anexo de documentação de infraestrutura"
        verbose_name_plural = "anexos de documentação de infraestrutura"

    def __str__(self):
        return self.descricao or self.arquivo.name


class AcessoDocumentoInfra(models.Model):
    class Acao(models.TextChoices):
        VISUALIZACAO = "visualizacao", "Visualização"
        CRIACAO = "criacao", "Criação"
        EDICAO = "edicao", "Edição"
        ANEXO = "anexo", "Anexo"

    documento = models.ForeignKey(DocumentoInfra, on_delete=models.CASCADE, related_name="logs_acesso")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    acao = models.CharField(max_length=20, choices=Acao.choices)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "log de acesso à documentação"
        verbose_name_plural = "logs de acesso à documentação"

    def __str__(self):
        return f"{self.documento} - {self.get_acao_display()}"

# Create your models here.
