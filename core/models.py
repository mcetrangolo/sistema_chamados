from django.conf import settings
from django.db import models


class ConfiguracaoInstitucional(models.Model):
    class TemaVisual(models.TextChoices):
        PERSONALIZADO = "personalizado", "Personalizado"
        CLEAN = "clean", "Clean"
        BLUE = "blue", "Blue"
        DARK = "dark", "Dark"
        RED = "red", "Red"
        GREEN = "green", "Green"
        CORPORATE = "corporate", "Corporate"

    PALETAS = {
        TemaVisual.CLEAN: {
            "cor_primaria": "#2563eb",
            "cor_secundaria": "#334155",
            "cor_fundo": "#f8fafc",
            "cor_texto": "#1f2937",
            "cor_menu_texto": "#1f2937",
        },
        TemaVisual.BLUE: {
            "cor_primaria": "#155eef",
            "cor_secundaria": "#0f3f9f",
            "cor_fundo": "#eef4ff",
            "cor_texto": "#172033",
            "cor_menu_texto": "#1f2937",
        },
        TemaVisual.DARK: {
            "cor_primaria": "#38bdf8",
            "cor_secundaria": "#020617",
            "cor_fundo": "#111827",
            "cor_texto": "#e5e7eb",
            "cor_menu_texto": "#111827",
        },
        TemaVisual.RED: {
            "cor_primaria": "#dc2626",
            "cor_secundaria": "#7f1d1d",
            "cor_fundo": "#fff5f5",
            "cor_texto": "#2f1720",
            "cor_menu_texto": "#2f1720",
        },
        TemaVisual.GREEN: {
            "cor_primaria": "#16875d",
            "cor_secundaria": "#14532d",
            "cor_fundo": "#f0fdf4",
            "cor_texto": "#14261c",
            "cor_menu_texto": "#14261c",
        },
        TemaVisual.CORPORATE: {
            "cor_primaria": "#0f766e",
            "cor_secundaria": "#1f2937",
            "cor_fundo": "#f3f6f8",
            "cor_texto": "#1f2937",
            "cor_menu_texto": "#1f2937",
        },
    }

    nome_instituicao = models.CharField(max_length=180, default="Sistema de Chamados")
    sigla = models.CharField(max_length=30, blank=True)
    cnpj = models.CharField("CNPJ", max_length=30, blank=True)
    endereco = models.CharField("endereço", max_length=250, blank=True)
    telefone = models.CharField(max_length=60, blank=True)
    email = models.EmailField(blank=True)
    site = models.URLField(blank=True)
    logo = models.ImageField(upload_to="institucional/logo/", blank=True)
    portal_rotulo = models.CharField(max_length=80, default="Service desk")
    portal_titulo = models.CharField(max_length=120, default="Abrir chamado de TI")
    portal_subtitulo = models.TextField(
        blank=True,
        default="Registre sua solicitacao para a equipe tecnica acompanhar, priorizar e documentar o atendimento.",
    )
    portal_texto_apoio = models.TextField(
        blank=True,
        default="Informe o setor correto, descreva mensagens de erro, equipamento afetado e impacto no trabalho.",
    )
    tema_visual = models.CharField(
        max_length=20,
        choices=TemaVisual.choices,
        default=TemaVisual.BLUE,
    )
    cor_primaria = models.CharField(max_length=20, default="#155eef")
    cor_secundaria = models.CharField(max_length=20, default="#0f172a")
    cor_fundo = models.CharField(max_length=20, default="#f4f7fb")
    cor_texto = models.CharField(max_length=20, default="#172033")
    cor_menu_texto = models.CharField(max_length=20, default="#1f2937")
    texto_rodape = models.CharField(max_length=180, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "configuração institucional"
        verbose_name_plural = "configurações institucionais"

    def __str__(self):
        return self.nome_instituicao

    def save(self, *args, **kwargs):
        self.pk = 1
        paleta = self.PALETAS.get(self.tema_visual)
        if paleta:
            self.cor_primaria = paleta["cor_primaria"]
            self.cor_secundaria = paleta["cor_secundaria"]
            self.cor_fundo = paleta["cor_fundo"]
            self.cor_texto = paleta["cor_texto"]
            self.cor_menu_texto = paleta["cor_menu_texto"]
        super().save(*args, **kwargs)

    @classmethod
    def atual(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class RegistroAuditoria(models.Model):
    class Acao(models.TextChoices):
        CRIACAO = "criacao", "Criacao"
        ALTERACAO = "alteracao", "Alteracao"
        EXCLUSAO = "exclusao", "Exclusao"
        LOGIN = "login", "Login"
        LOGOUT = "logout", "Logout"
        EXPORTACAO = "exportacao", "Exportacao"
        API = "api", "API"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_auditoria",
    )
    acao = models.CharField(max_length=20, choices=Acao.choices)
    app_label = models.CharField(max_length=80)
    modelo = models.CharField(max_length=120)
    objeto_id = models.CharField(max_length=80, blank=True)
    objeto = models.CharField(max_length=250, blank=True)
    caminho = models.CharField(max_length=250, blank=True)
    ip_origem = models.GenericIPAddressField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "registro de auditoria"
        verbose_name_plural = "registros de auditoria"

    def __str__(self):
        return f"{self.get_acao_display()} - {self.modelo} - {self.objeto}"


class ConfiguracaoBackup(models.Model):
    ativo = models.BooleanField(default=False)
    intervalo_horas = models.PositiveIntegerField(default=24)
    pasta_destino = models.CharField(max_length=500, blank=True)
    manter_ultimos = models.PositiveIntegerField(default=15)
    validar_automaticamente = models.BooleanField(default=True)
    ultima_execucao = models.DateTimeField(null=True, blank=True)
    proxima_execucao = models.DateTimeField(null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def atual(cls):
        objeto, _ = cls.objects.get_or_create(pk=1)
        return objeto


class RegistroBackup(models.Model):
    class Status(models.TextChoices):
        SUCESSO = "sucesso", "Sucesso"
        ERRO = "erro", "Erro"
        INVALIDO = "invalido", "Invalido"

    nome_arquivo = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices)
    tamanho_bytes = models.BigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True)
    destino = models.CharField(max_length=500, blank=True)
    mensagem = models.TextField(blank=True)
    validado_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]


class Notificacao(models.Model):
    class Nivel(models.TextChoices):
        INFO = "info", "Informacao"
        SUCESSO = "sucesso", "Sucesso"
        ALERTA = "alerta", "Alerta"
        CRITICO = "critico", "Critico"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificacoes")
    titulo = models.CharField(max_length=180)
    mensagem = models.TextField()
    nivel = models.CharField(max_length=20, choices=Nivel.choices, default=Nivel.INFO)
    link = models.CharField(max_length=500, blank=True)
    chave = models.CharField(max_length=180, blank=True, db_index=True)
    lida_em = models.DateTimeField(null=True, blank=True)
    email_enviado_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        indexes = [models.Index(fields=["usuario", "lida_em", "criado_em"])]


class ConfiguracaoLDAP(models.Model):
    ativo = models.BooleanField(default=False)
    servidor = models.CharField(max_length=255, blank=True)
    porta = models.PositiveIntegerField(default=389)
    usar_ssl = models.BooleanField(default=False)
    usuario_bind = models.CharField(max_length=255, blank=True)
    senha_criptografada = models.TextField(blank=True, editable=False)
    base_dn = models.CharField(max_length=255, blank=True)
    filtro_usuarios = models.CharField(max_length=255, default="(objectClass=user)")
    filtro_computadores = models.CharField(max_length=255, default="(objectClass=computer)")
    atributo_login = models.CharField(max_length=80, default="sAMAccountName")
    atributo_nome = models.CharField(max_length=80, default="givenName")
    atributo_sobrenome = models.CharField(max_length=80, default="sn")
    atributo_email = models.CharField(max_length=80, default="mail")
    sincronizar_ativos = models.BooleanField(default=True)
    ultima_sincronizacao = models.DateTimeField(null=True, blank=True)
    ultima_mensagem = models.TextField(blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def atual(cls):
        objeto, _ = cls.objects.get_or_create(pk=1)
        return objeto

    def definir_senha(self, senha):
        if not senha:
            return
        import base64
        import hashlib
        from cryptography.fernet import Fernet

        chave = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
        self.senha_criptografada = Fernet(chave).encrypt(senha.encode()).decode()

    def obter_senha(self):
        if not self.senha_criptografada:
            return ""
        import base64
        import hashlib
        from cryptography.fernet import Fernet

        chave = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
        return Fernet(chave).decrypt(self.senha_criptografada.encode()).decode()
