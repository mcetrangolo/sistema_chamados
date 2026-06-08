from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone


class Setor(models.Model):
    nome = models.CharField(max_length=120, unique=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "setor"
        verbose_name_plural = "setores"

    def __str__(self):
        return self.nome


class Categoria(models.Model):
    nome = models.CharField(max_length=120, unique=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "categoria"
        verbose_name_plural = "categorias"

    def __str__(self):
        return self.nome


class TopicoAjuda(models.Model):
    nome = models.CharField(max_length=150, unique=True)
    descricao = models.TextField(blank=True)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="topicos_ajuda",
    )
    prioridade_padrao = models.CharField(
        max_length=20,
        choices=[
            ("baixa", "Baixa"),
            ("media", "Média"),
            ("alta", "Alta"),
            ("critica", "Crítica"),
        ],
        default="media",
    )
    atendente_padrao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="topicos_ajuda_padrao",
        null=True,
        blank=True,
    )
    sla_horas = models.PositiveIntegerField(
        "SLA em horas",
        default=48,
        help_text="Prazo esperado para resolução dos chamados deste tópico.",
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "tópico de ajuda"
        verbose_name_plural = "tópicos de ajuda"

    def __str__(self):
        return self.nome


class Chamado(models.Model):
    class Tipo(models.TextChoices):
        INCIDENTE = "incidente", "Incidente"
        REQUISICAO = "requisicao", "Requisição de serviço"
        PROBLEMA = "problema", "Problema"
        MUDANCA = "mudanca", "Mudança"

    class Origem(models.TextChoices):
        PORTAL = "portal", "Portal"
        INTERNO = "interno", "Interno"
        EMAIL = "email", "E-mail"
        TELEFONE = "telefone", "Telefone"

    class Status(models.TextChoices):
        ABERTO = "aberto", "Aberto"
        EM_ANALISE = "em_analise", "Em análise"
        EM_ATENDIMENTO = "em_atendimento", "Em atendimento"
        AGUARDANDO_USUARIO = "aguardando_usuario", "Aguardando usuário"
        AGUARDANDO_FORNECEDOR = "aguardando_fornecedor", "Aguardando fornecedor"
        RESOLVIDO = "resolvido", "Resolvido"
        ENCERRADO = "encerrado", "Encerrado"
        CANCELADO = "cancelado", "Cancelado"

    class Prioridade(models.TextChoices):
        BAIXA = "baixa", "Baixa"
        MEDIA = "media", "Média"
        ALTA = "alta", "Alta"
        CRITICA = "critica", "Crítica"

    class Impacto(models.TextChoices):
        BAIXO = "baixo", "Baixo"
        MEDIO = "medio", "Médio"
        ALTO = "alto", "Alto"

    class Urgencia(models.TextChoices):
        BAIXA = "baixa", "Baixa"
        MEDIA = "media", "Média"
        ALTA = "alta", "Alta"

    numero = models.CharField(max_length=30, unique=True, editable=False)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.INCIDENTE)
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="chamados_solicitados",
        null=True,
        blank=True,
    )
    nome_solicitante = models.CharField(max_length=150)
    setor = models.ForeignKey(Setor, on_delete=models.PROTECT, related_name="chamados")
    telefone = models.CharField("telefone ou ramal", max_length=40, blank=True)
    email = models.EmailField("e-mail", blank=True)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="chamados"
    )
    topico_ajuda = models.ForeignKey(
        TopicoAjuda,
        on_delete=models.PROTECT,
        related_name="chamados",
        null=True,
        blank=True,
    )
    ativo_rede = models.ForeignKey(
        "inventario.AtivoRede",
        on_delete=models.SET_NULL,
        related_name="chamados",
        null=True,
        blank=True,
    )
    prioridade = models.CharField(
        max_length=20, choices=Prioridade.choices, default=Prioridade.MEDIA
    )
    impacto = models.CharField(max_length=20, choices=Impacto.choices, default=Impacto.MEDIO)
    urgencia = models.CharField(max_length=20, choices=Urgencia.choices, default=Urgencia.MEDIA)
    descricao = models.TextField("descrição do problema")
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.ABERTO)
    origem = models.CharField(max_length=20, choices=Origem.choices, default=Origem.PORTAL)
    tecnico_responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="chamados_atribuidos",
        null=True,
        blank=True,
    )
    solucao_aplicada = models.TextField("solução aplicada", blank=True)
    observacoes_internas = models.TextField("observações internas", blank=True)
    criado_em = models.DateTimeField("data e hora de abertura", auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    primeira_resposta_em = models.DateTimeField("primeira resposta", null=True, blank=True)
    concluido_em = models.DateTimeField("data de conclusão", null=True, blank=True)
    vencimento_em = models.DateTimeField("vencimento SLA", null=True, blank=True)
    sla_pausado_em = models.DateTimeField("SLA pausado em", null=True, blank=True)
    sla_pausado_total = models.DurationField("tempo total de pausa do SLA", default=timezone.timedelta)
    arquivado = models.BooleanField(default=False)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "chamado"
        verbose_name_plural = "chamados"

    def __str__(self):
        return f"{self.numero} - {self.nome_solicitante}"

    def get_absolute_url(self):
        return reverse("chamados:detalhe", kwargs={"pk": self.pk})

    def clean(self):
        if self.status in {self.Status.RESOLVIDO, self.Status.ENCERRADO}:
            if not self.solucao_aplicada.strip():
                raise ValidationError(
                    {"solucao_aplicada": "Informe a solução aplicada para concluir o chamado."}
                )

    def prioridade_por_impacto_urgencia(self):
        matriz = {
            (self.Impacto.ALTO, self.Urgencia.ALTA): self.Prioridade.CRITICA,
            (self.Impacto.ALTO, self.Urgencia.MEDIA): self.Prioridade.ALTA,
            (self.Impacto.ALTO, self.Urgencia.BAIXA): self.Prioridade.MEDIA,
            (self.Impacto.MEDIO, self.Urgencia.ALTA): self.Prioridade.ALTA,
            (self.Impacto.MEDIO, self.Urgencia.MEDIA): self.Prioridade.MEDIA,
            (self.Impacto.MEDIO, self.Urgencia.BAIXA): self.Prioridade.BAIXA,
            (self.Impacto.BAIXO, self.Urgencia.ALTA): self.Prioridade.MEDIA,
            (self.Impacto.BAIXO, self.Urgencia.MEDIA): self.Prioridade.BAIXA,
            (self.Impacto.BAIXO, self.Urgencia.BAIXA): self.Prioridade.BAIXA,
        }
        return matriz.get((self.impacto, self.urgencia), self.Prioridade.MEDIA)

    def save(self, *args, **kwargs):
        status_anterior = None
        if self.pk:
            status_anterior = Chamado.objects.filter(pk=self.pk).values_list("status", flat=True).first()

        if not self.numero:
            agora = timezone.now()
            self.numero = f"CH-{agora:%Y%m%d-%H%M%S-%f}"

        if self.topico_ajuda:
            if not self.categoria_id:
                self.categoria = self.topico_ajuda.categoria
            if not self.tecnico_responsavel_id and self.topico_ajuda.atendente_padrao_id:
                self.tecnico_responsavel = self.topico_ajuda.atendente_padrao
            if not self.vencimento_em and self.topico_ajuda.sla_horas:
                self.vencimento_em = timezone.now() + timezone.timedelta(
                    hours=self.topico_ajuda.sla_horas
                )

        if self.status in {self.Status.RESOLVIDO, self.Status.ENCERRADO} and not self.concluido_em:
            self.concluido_em = timezone.now()
        if self.status not in {self.Status.RESOLVIDO, self.Status.ENCERRADO}:
            self.concluido_em = None

        status_pausa = {self.Status.AGUARDANDO_USUARIO, self.Status.AGUARDANDO_FORNECEDOR}
        if self.status in status_pausa and not self.sla_pausado_em:
            self.sla_pausado_em = timezone.now()
        elif status_anterior in status_pausa and self.status not in status_pausa and self.sla_pausado_em:
            pausa = timezone.now() - self.sla_pausado_em
            self.sla_pausado_total = (self.sla_pausado_total or timezone.timedelta()) + pausa
            if self.vencimento_em:
                self.vencimento_em = self.vencimento_em + pausa
            self.sla_pausado_em = None

        super().save(*args, **kwargs)

    @property
    def atrasado(self):
        if not self.vencimento_em:
            return False
        if self.status in {self.Status.RESOLVIDO, self.Status.ENCERRADO, self.Status.CANCELADO}:
            return False
        if self.sla_pausado_em:
            return False
        return self.vencimento_em < timezone.now()


class HistoricoChamado(models.Model):
    chamado = models.ForeignKey(
        Chamado, on_delete=models.CASCADE, related_name="historico"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=30, choices=Chamado.Status.choices)
    comentario = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "histórico do chamado"
        verbose_name_plural = "históricos dos chamados"

    def __str__(self):
        return f"{self.chamado.numero} - {self.get_status_display()}"


class AnexoChamado(models.Model):
    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name="anexos")
    arquivo = models.FileField(upload_to="chamados/anexos/%Y/%m/")
    descricao = models.CharField(max_length=150, blank=True)
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    nome_enviado_por = models.CharField(max_length=150, blank=True)
    publico = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "anexo do chamado"
        verbose_name_plural = "anexos dos chamados"

    def __str__(self):
        return self.descricao or self.arquivo.name


class ComentarioChamado(models.Model):
    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name="comentarios")
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    nome_autor = models.CharField(max_length=150, blank=True)
    email_autor = models.EmailField(blank=True)
    mensagem = models.TextField()
    publico = models.BooleanField(
        default=True,
        help_text="Comentários públicos aparecem para o solicitante no portal.",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em"]
        verbose_name = "comentário do chamado"
        verbose_name_plural = "comentários dos chamados"

    def __str__(self):
        return f"{self.chamado.numero} - {self.nome_autor or self.autor or 'Portal'}"


class RespostaPronta(models.Model):
    titulo = models.CharField(max_length=150, unique=True)
    conteudo = models.TextField()
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["titulo"]
        verbose_name = "resposta pronta"
        verbose_name_plural = "respostas prontas"

    def __str__(self):
        return self.titulo


class TarefaChamado(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        EM_ANDAMENTO = "em_andamento", "Em andamento"
        CONCLUIDA = "concluida", "Concluída"

    chamado = models.ForeignKey(Chamado, on_delete=models.CASCADE, related_name="tarefas")
    titulo = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tarefas_chamado",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    prazo = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["status", "prazo", "titulo"]
        verbose_name = "tarefa do chamado"
        verbose_name_plural = "tarefas dos chamados"

    def __str__(self):
        return self.titulo


class ArtigoConhecimento(models.Model):
    titulo = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    topico_ajuda = models.ForeignKey(
        TopicoAjuda,
        on_delete=models.SET_NULL,
        related_name="artigos",
        null=True,
        blank=True,
    )
    resumo = models.CharField(max_length=250, blank=True)
    conteudo = models.TextField()
    video_youtube_url = models.URLField("vídeo do YouTube", blank=True)
    imagem = models.ImageField(upload_to="conhecimento/imagens/%Y/%m/", blank=True)
    legenda_imagem = models.CharField(max_length=180, blank=True)
    publico = models.BooleanField(default=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["titulo"]
        verbose_name = "artigo da base de conhecimento"
        verbose_name_plural = "artigos da base de conhecimento"

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.titulo)[:180]
            slug = base_slug
            contador = 2
            while ArtigoConhecimento.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{contador}"
                contador += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("chamados:artigo_detalhe", kwargs={"slug": self.slug})

    @property
    def youtube_embed_url(self):
        if not self.video_youtube_url:
            return ""
        url = self.video_youtube_url.strip()
        if "youtu.be/" in url:
            video_id = url.split("youtu.be/", 1)[1].split("?", 1)[0].split("/", 1)[0]
            return f"https://www.youtube.com/embed/{video_id}"
        if "watch?v=" in url:
            video_id = url.split("watch?v=", 1)[1].split("&", 1)[0]
            return f"https://www.youtube.com/embed/{video_id}"
        if "/embed/" in url:
            return url
        return ""


class AvaliacaoChamado(models.Model):
    chamado = models.OneToOneField(Chamado, on_delete=models.CASCADE, related_name="avaliacao")
    nota = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comentario = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "avaliação do chamado"
        verbose_name_plural = "avaliações dos chamados"

    def __str__(self):
        return f"{self.chamado.numero} - {self.nota}/5"


class ServicoCatalogo(models.Model):
    nome = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    descricao = models.TextField(blank=True)
    topico_ajuda = models.ForeignKey(
        TopicoAjuda,
        on_delete=models.SET_NULL,
        related_name="servicos",
        null=True,
        blank=True,
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="servicos",
    )
    tipo_chamado = models.CharField(
        max_length=20,
        choices=Chamado.Tipo.choices,
        default=Chamado.Tipo.REQUISICAO,
    )
    prioridade_padrao = models.CharField(
        max_length=20,
        choices=Chamado.Prioridade.choices,
        default=Chamado.Prioridade.MEDIA,
    )
    requer_matricula = models.BooleanField(default=True)
    requer_aprovacao = models.BooleanField(default=False)
    instrucoes = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "serviço do catálogo"
        verbose_name_plural = "serviços do catálogo"

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.nome)[:160]
            slug = base_slug
            contador = 2
            while ServicoCatalogo.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{contador}"
                contador += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("chamados:catalogo_solicitar", kwargs={"slug": self.slug})


class SolicitacaoServico(models.Model):
    class Status(models.TextChoices):
        RECEBIDA = "recebida", "Recebida"
        CONVERTIDA = "convertida", "Convertida em chamado"
        CANCELADA = "cancelada", "Cancelada"

    protocolo = models.CharField(max_length=40, unique=True, editable=False)
    servico = models.ForeignKey(ServicoCatalogo, on_delete=models.PROTECT, related_name="solicitacoes")
    chamado = models.OneToOneField(
        Chamado,
        on_delete=models.SET_NULL,
        related_name="solicitacao_servico",
        null=True,
        blank=True,
    )
    matricula = models.CharField("matrícula", max_length=50, blank=True)
    nome = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    setor = models.ForeignKey(Setor, on_delete=models.PROTECT, related_name="solicitacoes_servico")
    telefone = models.CharField(max_length=50, blank=True)
    detalhes = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEBIDA)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "solicitação de serviço"
        verbose_name_plural = "solicitações de serviço"

    def __str__(self):
        return f"{self.protocolo} - {self.servico}"

    def save(self, *args, **kwargs):
        if not self.protocolo:
            agora = timezone.now()
            self.protocolo = f"SRV-{agora:%Y%m%d-%H%M%S-%f}"
        super().save(*args, **kwargs)


class AprovacaoSolicitacao(models.Model):
    class Origem(models.TextChoices):
        CATALOGO = "catalogo", "Catálogo de serviços"
        GOVERNANCA = "governanca", "Governança"

    class Status(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        APROVADA = "aprovada", "Aprovada"
        REJEITADA = "rejeitada", "Rejeitada"

    origem = models.CharField(max_length=20, choices=Origem.choices)
    solicitacao_servico = models.ForeignKey(
        SolicitacaoServico,
        on_delete=models.CASCADE,
        related_name="aprovacoes",
        null=True,
        blank=True,
    )
    governanca_id = models.PositiveIntegerField(null=True, blank=True)
    titulo = models.CharField(max_length=180)
    solicitante = models.CharField(max_length=150)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    aprovado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    observacao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    decidido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "aprovação de solicitação"
        verbose_name_plural = "aprovações de solicitações"

    def __str__(self):
        return f"{self.titulo} - {self.get_status_display()}"
