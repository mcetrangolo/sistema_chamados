from django.db import models


class SolicitacaoGovernanca(models.Model):
    class Tipo(models.TextChoices):
        USUARIO_ACESSO = "usuario_acesso", "Cadastro de usuário e acessos"
        WIFI_CORPORATIVO = "wifi_corporativo", "Acesso à internet Wi-Fi corporativa"

    class Status(models.TextChoices):
        RECEBIDA = "recebida", "Recebida"
        EM_ANALISE = "em_analise", "Em análise"
        ATENDIDA = "atendida", "Atendida"
        NEGADA = "negada", "Negada"

    protocolo = models.CharField(max_length=40, unique=True, editable=False)
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    matricula = models.CharField("matrícula", max_length=50)
    nome = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    setor = models.CharField(max_length=120)
    cargo = models.CharField(max_length=120, blank=True)
    telefone = models.CharField(max_length=50, blank=True)
    justificativa = models.TextField(blank=True)
    acessos_solicitados = models.TextField("acessos solicitados", blank=True)
    aparelhos = models.TextField(blank=True, help_text="Informe marca, modelo, patrimônio/serial e observações.")
    termo_ciencia = models.BooleanField("declaro ciência das responsabilidades", default=False)
    documento_caminho = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEBIDA)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "solicitação de governança"
        verbose_name_plural = "solicitações de governança"

    def __str__(self):
        return f"{self.protocolo} - {self.nome}"

    def save(self, *args, **kwargs):
        if not self.protocolo:
            from django.utils import timezone

            agora = timezone.now()
            self.protocolo = f"GOV-{agora:%Y%m%d-%H%M%S-%f}"
        super().save(*args, **kwargs)
