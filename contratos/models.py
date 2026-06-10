from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Fornecedor(models.Model):
    nome = models.CharField(max_length=180)
    cnpj = models.CharField("CNPJ", max_length=20, blank=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=40, blank=True)
    endereco = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "fornecedor"
        verbose_name_plural = "fornecedores"

    def __str__(self):
        return self.nome


class ContratoPublico(models.Model):
    class LeiRegencia(models.TextChoices):
        LEI_14133 = "14133", "Lei 14.133/2021"
        LEI_8666 = "8666", "Lei 8.666/1993"
        OUTRA = "outra", "Outra base legal"

    class Tipo(models.TextChoices):
        CONTINUADO = "continuado", "Servico continuado"
        ESCOPO = "escopo", "Escopo definido"
        FORNECIMENTO = "fornecimento", "Fornecimento"
        OBRA = "obra", "Obra/engenharia"
        TI = "ti", "Solucao de TIC"
        OUTRO = "outro", "Outro"

    class Status(models.TextChoices):
        VIGENTE = "vigente", "Vigente"
        A_VENCER = "a_vencer", "A vencer"
        VENCIDO = "vencido", "Vencido"
        ENCERRADO = "encerrado", "Encerrado"
        RESCINDIDO = "rescindido", "Rescindido"

    numero = models.CharField(max_length=60)
    ano = models.PositiveIntegerField(default=timezone.now().year)
    processo_administrativo = models.CharField(max_length=80, blank=True)
    objeto = models.TextField()
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, related_name="contratos")
    lei_regencia = models.CharField(max_length=20, choices=LeiRegencia.choices, default=LeiRegencia.LEI_14133)
    modalidade = models.CharField(max_length=120, blank=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.CONTINUADO)
    valor_global = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    data_assinatura = models.DateField(null=True, blank=True)
    data_inicio = models.DateField()
    data_fim = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.VIGENTE)
    gestor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="contratos_geridos",
        null=True,
        blank=True,
    )
    fiscal = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="contratos_fiscalizados",
        null=True,
        blank=True,
    )
    permite_prorrogacao = models.BooleanField(default=True)
    limite_prorrogacao_meses = models.PositiveIntegerField(
        default=120,
        help_text="Limite operacional cadastrado para controle interno. Confirme a base legal antes de formalizar.",
    )
    alerta_dias = models.PositiveIntegerField(default=90)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["data_fim", "numero"]
        unique_together = ("numero", "ano")
        verbose_name = "contrato publico"
        verbose_name_plural = "contratos publicos"

    def __str__(self):
        return f"{self.numero}/{self.ano} - {self.fornecedor}"

    def get_absolute_url(self):
        return reverse("contratos:detalhe", kwargs={"pk": self.pk})

    @property
    def dias_para_vencimento(self):
        return (self.data_fim - timezone.localdate()).days

    @property
    def vencido(self):
        return self.status not in {self.Status.ENCERRADO, self.Status.RESCINDIDO} and self.dias_para_vencimento < 0

    @property
    def em_alerta(self):
        return (
            self.status not in {self.Status.ENCERRADO, self.Status.RESCINDIDO}
            and 0 <= self.dias_para_vencimento <= self.alerta_dias
        )

    @property
    def status_operacional(self):
        if self.vencido:
            return self.Status.VENCIDO
        if self.em_alerta:
            return self.Status.A_VENCER
        return self.status

    @property
    def base_legal_resumo(self):
        if self.lei_regencia == self.LeiRegencia.LEI_14133:
            return "Controle operacional baseado na Lei 14.133/2021. Validar edital, termo contratual e parecer juridico."
        if self.lei_regencia == self.LeiRegencia.LEI_8666:
            return "Controle operacional baseado na Lei 8.666/1993. Usar apenas para contratos legados aplicaveis."
        return "Base legal informada manualmente. Validar com assessoria juridica."


class PedidoProrrogacao(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        SOLICITADO = "solicitado", "Solicitado"
        APROVADO = "aprovado", "Aprovado"
        REJEITADO = "rejeitado", "Rejeitado"
        FORMALIZADO = "formalizado", "Formalizado"

    contrato = models.ForeignKey(ContratoPublico, on_delete=models.CASCADE, related_name="prorrogacoes")
    solicitado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="pedidos_prorrogacao",
        null=True,
        blank=True,
    )
    solicitado_em = models.DateTimeField(auto_now_add=True)
    novo_fim = models.DateField("nova data final pretendida")
    justificativa = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SOLICITADO)
    decidido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="decisoes_prorrogacao",
        null=True,
        blank=True,
    )
    decidido_em = models.DateTimeField(null=True, blank=True)
    observacao_decisao = models.TextField(blank=True)

    class Meta:
        ordering = ["-solicitado_em"]
        verbose_name = "pedido de prorrogacao"
        verbose_name_plural = "pedidos de prorrogacao"

    def __str__(self):
        return f"{self.contrato} ate {self.novo_fim:%d/%m/%Y}"


class AditivoContrato(models.Model):
    class Tipo(models.TextChoices):
        PRAZO = "prazo", "Prazo"
        VALOR = "valor", "Valor"
        QUANTITATIVO = "quantitativo", "Quantitativo"
        REAJUSTE = "reajuste", "Reajuste"
        OUTRO = "outro", "Outro"

    contrato = models.ForeignKey(ContratoPublico, on_delete=models.CASCADE, related_name="aditivos")
    numero = models.CharField(max_length=60)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.PRAZO)
    data_assinatura = models.DateField()
    nova_data_fim = models.DateField(null=True, blank=True)
    valor_acrescimo = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    observacao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data_assinatura", "-criado_em"]
        verbose_name = "aditivo contratual"
        verbose_name_plural = "aditivos contratuais"

    def __str__(self):
        return f"{self.numero} - {self.get_tipo_display()}"


class AnexoContrato(models.Model):
    class Tipo(models.TextChoices):
        CONTRATO = "contrato", "Contrato assinado"
        EDITAL = "edital", "Edital"
        TERMO_REFERENCIA = "termo_referencia", "Termo de referencia"
        ADITIVO = "aditivo", "Aditivo"
        PARECER = "parecer", "Parecer juridico"
        PORTARIA = "portaria", "Portaria fiscal/gestor"
        FISCALIZACAO = "fiscalizacao", "Relatorio de fiscalizacao"
        OUTRO = "outro", "Outro"

    contrato = models.ForeignKey(ContratoPublico, on_delete=models.CASCADE, related_name="anexos")
    arquivo = models.FileField(upload_to="contratos/anexos/%Y/%m/")
    tipo = models.CharField(max_length=30, choices=Tipo.choices, default=Tipo.OUTRO)
    descricao = models.CharField(max_length=180, blank=True)
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "anexo de contrato"
        verbose_name_plural = "anexos de contratos"

    def __str__(self):
        return self.descricao or self.arquivo.name
