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

    class TipoSolicitacaoRede(models.TextChoices):
        NOVO_ACESSO = "novo_acesso", "Novo acesso"
        TROCA_SENHA = "troca_senha", "Troca de senha"
        ALTERACAO_PERMISSAO = "alteracao_permissao", "Alteração de permissão de acesso"

    protocolo = models.CharField(max_length=40, unique=True, editable=False)
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    matricula = models.CharField("matrícula", max_length=50)
    nome = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    setor = models.CharField(max_length=120)
    cargo = models.CharField(max_length=120, blank=True)
    telefone = models.CharField(max_length=50, blank=True)
    tipo_solicitacao_rede = models.CharField(
        "tipo de solicitação",
        max_length=30,
        choices=TipoSolicitacaoRede.choices,
        blank=True,
    )
    usuario_rede_existente = models.CharField(
        "usuário de rede existente",
        max_length=80,
        blank=True,
        help_text="Preencha em caso de troca de senha ou alteração de permissão.",
    )
    chefia_imediata = models.CharField(
        "chefia imediata/autorizador",
        max_length=150,
        blank=True,
        help_text="Nome da chefia que autoriza ou deverá validar a solicitação.",
    )
    justificativa = models.TextField(blank=True)
    acessos_solicitados = models.TextField("acessos solicitados", blank=True)
    aparelhos = models.TextField(blank=True, help_text="Informe marca, modelo, patrimônio/serial e observações.")
    termo_ciencia = models.BooleanField("declaro ciência das responsabilidades", default=False)
    termo_versao = models.CharField("versão do termo aceito", max_length=80, blank=True)
    termo_texto_aceito = models.TextField("texto do termo aceito", blank=True)
    termo_aceito_em = models.DateTimeField("termo aceito em", null=True, blank=True)
    termo_aceito_ip = models.GenericIPAddressField("IP do aceite", null=True, blank=True)
    termo_aceito_user_agent = models.CharField("user-agent do aceite", max_length=300, blank=True)
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
