from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.urls import reverse
from urllib.parse import quote
import re

from chamados.models import Setor


class TipoAtivo(models.Model):
    nome = models.CharField(max_length=80, unique=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "tipo de ativo"
        verbose_name_plural = "tipos de ativo"

    def __str__(self):
        return self.nome


class CredencialSNMP(models.Model):
    class Versao(models.TextChoices):
        V1 = "1", "v1"
        V2C = "2c", "v2c"
        V3 = "3", "v3"

    nome = models.CharField(max_length=100, unique=True)
    versao = models.CharField(max_length=5, choices=Versao.choices, default=Versao.V2C)
    community = models.CharField(max_length=120, blank=True)
    usuario = models.CharField(max_length=120, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "credencial SNMP"
        verbose_name_plural = "credenciais SNMP"

    def __str__(self):
        return self.nome


class FaixaRede(models.Model):
    nome = models.CharField(max_length=100)
    cidr = models.CharField("CIDR", max_length=50, help_text="Exemplo: 192.168.0.0/24")
    credencial_snmp = models.ForeignKey(
        CredencialSNMP,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="faixas",
    )
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "faixa de rede"
        verbose_name_plural = "faixas de rede"

    def __str__(self):
        return f"{self.nome} ({self.cidr})"


class MetodoDescoberta(models.Model):
    class Codigo(models.TextChoices):
        AUTO = "auto", "Automático"
        PING = "ping", "Ping / ICMP"
        DNS = "dns", "DNS reverso"
        TCP = "tcp", "TCP / portas"
        SNMP = "snmp", "SNMP"
        AD = "ad", "Active Directory"
        WINRM = "winrm", "WinRM / WMI"
        CSV = "csv", "Importação CSV"
        MANUAL = "manual", "Cadastro manual"

    codigo = models.CharField(max_length=20, choices=Codigo.choices, unique=True)
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "método de descoberta"
        verbose_name_plural = "métodos de descoberta"

    def __str__(self):
        return self.nome


class AtivoRede(models.Model):
    class Status(models.TextChoices):
        ONLINE = "online", "Online"
        OFFLINE = "offline", "Offline"
        DESCONHECIDO = "desconhecido", "Desconhecido"
        MANUTENCAO = "manutencao", "Em manutenção"
        DESATIVADO = "desativado", "Desativado"

    class Origem(models.TextChoices):
        MANUAL = "manual", "Manual"
        SNMP = "snmp", "SNMP"
        AD = "ad", "Active Directory"
        AGENTE = "agente", "Agente"
        IMPORTACAO = "importacao", "Importação"

    class CicloVida(models.TextChoices):
        ESTOQUE = "estoque", "Em estoque"
        EM_USO = "em_uso", "Em uso"
        MANUTENCAO = "manutencao", "Em manutencao"
        EMPRESTADO = "emprestado", "Emprestado"
        BAIXADO = "baixado", "Baixado"
        DESCARTADO = "descartado", "Descartado"

    nome = models.CharField(max_length=150)
    tipo = models.ForeignKey(TipoAtivo, on_delete=models.PROTECT, related_name="ativos")
    setor = models.ForeignKey(
        Setor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ativos_rede",
    )
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    mac = models.CharField("MAC", max_length=30, blank=True)
    hostname = models.CharField(max_length=150, blank=True)
    fabricante = models.CharField(max_length=120, blank=True)
    modelo = models.CharField(max_length=120, blank=True)
    numero_serie = models.CharField("número de série", max_length=120, blank=True)
    patrimonio = models.CharField(max_length=80, blank=True, db_index=True)
    sistema_operacional = models.CharField(max_length=150, blank=True)
    arquitetura = models.CharField(max_length=40, blank=True)
    processador = models.CharField(max_length=180, blank=True)
    memoria_total_gb = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    disco_total_gb = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    office = models.CharField(max_length=180, blank=True)
    softwares_instalados = models.TextField(blank=True)
    usuario_logado = models.CharField(max_length=150, blank=True)
    dominio = models.CharField(max_length=150, blank=True)
    localizacao = models.CharField(max_length=150, blank=True)
    responsavel = models.CharField(max_length=150, blank=True)
    funcao = models.CharField("função", max_length=150, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DESCONHECIDO)
    ciclo_vida = models.CharField(max_length=20, choices=CicloVida.choices, default=CicloVida.EM_USO)
    data_aquisicao = models.DateField(null=True, blank=True)
    garantia_ate = models.DateField(null=True, blank=True)
    data_baixa = models.DateField(null=True, blank=True)
    motivo_baixa = models.TextField(blank=True)
    origem = models.CharField(max_length=20, choices=Origem.choices, default=Origem.MANUAL)
    observacoes = models.TextField("observações", blank=True)
    ultima_coleta_em = models.DateTimeField(null=True, blank=True)
    coleta_solicitada_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "ativo de rede"
        verbose_name_plural = "ativos de rede"

    def __str__(self):
        return self.nome

    def get_absolute_url(self):
        return reverse("inventario:ativo_detalhe", kwargs={"pk": self.pk})


class RelacionamentoAtivo(models.Model):
    class Tipo(models.TextChoices):
        DEPENDE_DE = "depende_de", "Depende de"
        CONECTADO_A = "conectado_a", "Conectado a"
        HOSPEDA = "hospeda", "Hospeda"
        USA_SERVICO = "usa_servico", "Usa servico"
        IMPACTA = "impacta", "Impacta"

    origem = models.ForeignKey(AtivoRede, on_delete=models.CASCADE, related_name="relacoes_origem")
    destino = models.ForeignKey(AtivoRede, on_delete=models.CASCADE, related_name="relacoes_destino")
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.DEPENDE_DE)
    descricao = models.CharField(max_length=250, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["origem__nome", "destino__nome"]
        verbose_name = "relacionamento de ativo"
        verbose_name_plural = "relacionamentos de ativos"

    def __str__(self):
        return f"{self.origem} {self.get_tipo_display()} {self.destino}"


class IntegracaoExterna(models.Model):
    class Tipo(models.TextChoices):
        LINK = "link", "Link externo"
        IFRAME = "iframe", "Iframe embutido"

    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.LINK)
    url_template = models.CharField(
        max_length=600,
        help_text="Use variaveis como {{ ip }}, {{ hostname }}, {{ nome }}, {{ patrimonio }} ou campos externos.",
    )
    abrir_em_nova_aba = models.BooleanField(default=True)
    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["ordem", "nome"]
        verbose_name = "integracao externa"
        verbose_name_plural = "integracoes externas"

    def __str__(self):
        return self.nome

    def renderizar_url(self, ativo):
        variaveis = {
            "id": ativo.pk,
            "nome": ativo.nome,
            "ip": ativo.ip or "",
            "hostname": ativo.hostname,
            "patrimonio": ativo.patrimonio,
            "mac": ativo.mac,
            "serial": ativo.numero_serie,
            "numero_serie": ativo.numero_serie,
            "tipo": str(ativo.tipo or ""),
            "setor": str(ativo.setor or ""),
            "responsavel": ativo.responsavel,
        }
        variaveis.update({campo.chave: campo.valor for campo in ativo.campos_externos.all()})

        def substituir(match):
            chave = match.group(1).strip()
            return quote(str(variaveis.get(chave, "")), safe="")

        return re.sub(r"\{\{\s*([\w.-]+)\s*\}\}", substituir, self.url_template)


class CampoExternoAtivo(models.Model):
    ativo = models.ForeignKey(AtivoRede, on_delete=models.CASCADE, related_name="campos_externos")
    chave = models.SlugField(max_length=80)
    valor = models.CharField(max_length=250)
    descricao = models.CharField(max_length=180, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["chave"]
        unique_together = ("ativo", "chave")
        verbose_name = "campo externo do ativo"
        verbose_name_plural = "campos externos dos ativos"

    def __str__(self):
        return f"{self.ativo} - {self.chave}"


class RegistroAcessoIntegracao(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    ativo = models.ForeignKey(AtivoRede, on_delete=models.CASCADE, related_name="acessos_integracoes")
    integracao = models.ForeignKey(IntegracaoExterna, on_delete=models.CASCADE, related_name="acessos")
    url_gerada = models.CharField(max_length=800)
    modo = models.CharField(max_length=20, blank=True)
    ip_origem = models.GenericIPAddressField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "acesso a integracao"
        verbose_name_plural = "acessos a integracoes"


class LicencaSoftware(models.Model):
    class Status(models.TextChoices):
        ATIVA = "ativa", "Ativa"
        A_VENCER = "a_vencer", "A vencer"
        VENCIDA = "vencida", "Vencida"
        SUSPENSA = "suspensa", "Suspensa"

    nome = models.CharField(max_length=180)
    fabricante = models.CharField(max_length=120, blank=True)
    chave = models.CharField(max_length=180, blank=True)
    quantidade_total = models.PositiveIntegerField(default=1)
    validade = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ATIVA)
    ativos = models.ManyToManyField(AtivoRede, related_name="licencas", blank=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome", "fabricante"]
        verbose_name = "licenca de software"
        verbose_name_plural = "licencas de software"

    def __str__(self):
        return self.nome

    @property
    def quantidade_em_uso(self):
        return self.ativos.exclude(status=AtivoRede.Status.DESATIVADO).count()

    @property
    def saldo(self):
        return self.quantidade_total - self.quantidade_em_uso


class AnexoLicencaSoftware(models.Model):
    licenca = models.ForeignKey(LicencaSoftware, on_delete=models.CASCADE, related_name="anexos")
    arquivo = models.FileField(upload_to="licencas/anexos/%Y/%m/")
    descricao = models.CharField(max_length=180, blank=True)
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "anexo de licenca"
        verbose_name_plural = "anexos de licencas"

    def __str__(self):
        return self.descricao or self.arquivo.name


class HistoricoAlteracaoAtivo(models.Model):
    ativo = models.ForeignKey(AtivoRede, on_delete=models.CASCADE, related_name="historico_alteracoes")
    campo = models.CharField(max_length=120)
    valor_anterior = models.TextField(blank=True)
    valor_novo = models.TextField(blank=True)
    origem = models.CharField(max_length=80, default="sistema")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "historico de alteracao do ativo"
        verbose_name_plural = "historicos de alteracoes dos ativos"

    def __str__(self):
        return f"{self.ativo} - {self.campo}"


class MovimentacaoAtivo(models.Model):
    ativo = models.ForeignKey(AtivoRede, on_delete=models.CASCADE, related_name="movimentacoes")
    setor_origem = models.ForeignKey(
        Setor, on_delete=models.SET_NULL, null=True, blank=True, related_name="movimentacoes_origem"
    )
    setor_destino = models.ForeignKey(
        Setor, on_delete=models.SET_NULL, null=True, blank=True, related_name="movimentacoes_destino"
    )
    local_origem = models.CharField(max_length=150, blank=True)
    local_destino = models.CharField(max_length=150, blank=True)
    responsavel_origem = models.CharField(max_length=150, blank=True)
    responsavel_destino = models.CharField(max_length=150, blank=True)
    ciclo_anterior = models.CharField(max_length=20, choices=AtivoRede.CicloVida.choices)
    ciclo_novo = models.CharField(max_length=20, choices=AtivoRede.CicloVida.choices)
    motivo = models.TextField()
    movimentado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]


class TermoResponsabilidadeAtivo(models.Model):
    class Tipo(models.TextChoices):
        ENTREGA = "entrega", "Entrega"
        DEVOLUCAO = "devolucao", "Devolucao"
        EMPRESTIMO = "emprestimo", "Emprestimo"

    ativo = models.ForeignKey(AtivoRede, on_delete=models.CASCADE, related_name="termos_responsabilidade")
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    responsavel = models.CharField(max_length=180)
    matricula = models.CharField(max_length=80, blank=True)
    setor = models.ForeignKey(Setor, on_delete=models.SET_NULL, null=True, blank=True)
    finalidade = models.TextField(blank=True)
    texto_termo = models.TextField()
    data_evento = models.DateField()
    assinatura_nome = models.CharField(max_length=180, blank=True)
    aceite_em = models.DateTimeField(null=True, blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]


class RegistroColetaAgente(models.Model):
    class Status(models.TextChoices):
        SUCESSO = "sucesso", "Sucesso"
        ERRO = "erro", "Erro"
        REJEITADA = "rejeitada", "Rejeitada"

    ativo = models.ForeignKey(
        AtivoRede, on_delete=models.CASCADE, null=True, blank=True, related_name="registros_coleta"
    )
    hostname = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    mensagem = models.CharField(max_length=500, blank=True)
    ip_origem = models.GenericIPAddressField(null=True, blank=True)
    versao_agente = models.CharField(max_length=40, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        indexes = [models.Index(fields=["status", "criado_em"])]


class SondaRemota(models.Model):
    nome = models.CharField(max_length=120, unique=True)
    localidade = models.CharField(max_length=180, blank=True)
    descricao = models.TextField(blank=True)
    faixas = models.ManyToManyField(FaixaRede, related_name="sondas", blank=True)
    token_hash = models.CharField(max_length=256, editable=False)
    token_prefixo = models.CharField(max_length=12, blank=True, editable=False)
    ativa = models.BooleanField(default=True)
    ultima_comunicacao_em = models.DateTimeField(null=True, blank=True)
    ultima_mensagem = models.CharField(max_length=500, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome"]

    def definir_token(self, token):
        self.token_hash = make_password(token)
        self.token_prefixo = token[:8]

    def verificar_token(self, token):
        return bool(self.token_hash and check_password(token, self.token_hash))

    def __str__(self):
        return self.nome


class ExecucaoSonda(models.Model):
    class Status(models.TextChoices):
        SUCESSO = "sucesso", "Sucesso"
        ERRO = "erro", "Erro"

    sonda = models.ForeignKey(SondaRemota, on_delete=models.CASCADE, related_name="execucoes")
    status = models.CharField(max_length=20, choices=Status.choices)
    ativos_encontrados = models.PositiveIntegerField(default=0)
    mensagem = models.CharField(max_length=500, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]


class InterfaceRede(models.Model):
    ativo = models.ForeignKey(AtivoRede, on_delete=models.CASCADE, related_name="interfaces")
    nome = models.CharField(max_length=120)
    descricao = models.CharField(max_length=250, blank=True)
    mac = models.CharField("MAC", max_length=30, blank=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    velocidade = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "interface de rede"
        verbose_name_plural = "interfaces de rede"

    def __str__(self):
        return f"{self.ativo} - {self.nome}"


class VarreduraRede(models.Model):
    class Status(models.TextChoices):
        AGENDADA = "agendada", "Agendada"
        EM_EXECUCAO = "em_execucao", "Em execução"
        CONCLUIDA = "concluida", "Concluída"
        ERRO = "erro", "Erro"

    faixa = models.ForeignKey(FaixaRede, on_delete=models.PROTECT, related_name="varreduras")
    metodo = models.CharField(
        max_length=20,
        choices=MetodoDescoberta.Codigo.choices,
        default=MetodoDescoberta.Codigo.AUTO,
    )
    iniciado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AGENDADA)
    mensagem = models.TextField(blank=True)
    ativos_encontrados = models.PositiveIntegerField(default=0)
    portas = models.CharField(
        max_length=120,
        blank=True,
        help_text="Portas usadas em varredura TCP. Exemplo: 22,80,443,3389",
    )
    iniciado_em = models.DateTimeField(auto_now_add=True)
    concluido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-iniciado_em"]
        verbose_name = "varredura de rede"
        verbose_name_plural = "varreduras de rede"

    def __str__(self):
        return f"{self.faixa} - {self.get_status_display()}"


class AgendamentoVarredura(models.Model):
    nome = models.CharField(max_length=120)
    faixa = models.ForeignKey(FaixaRede, on_delete=models.CASCADE, related_name="agendamentos")
    metodo = models.CharField(max_length=20, choices=MetodoDescoberta.Codigo.choices)
    portas = models.CharField(max_length=120, blank=True)
    intervalo_horas = models.PositiveIntegerField(default=24)
    ativo = models.BooleanField(default=True)
    ultima_execucao = models.DateTimeField(null=True, blank=True)
    proxima_execucao = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "agendamento de varredura"
        verbose_name_plural = "agendamentos de varredura"

    def __str__(self):
        return self.nome


class OcorrenciaAtivo(models.Model):
    class Tipo(models.TextChoices):
        MANUTENCAO = "manutencao", "Manutenção"
        INCIDENTE = "incidente", "Incidente"
        ALTERACAO = "alteracao", "Alteração"
        OBSERVACAO = "observacao", "Observação"

    ativo = models.ForeignKey(AtivoRede, on_delete=models.CASCADE, related_name="ocorrencias")
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.OBSERVACAO)
    titulo = models.CharField(max_length=150)
    descricao = models.TextField()
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "ocorrência do ativo"
        verbose_name_plural = "ocorrências dos ativos"

    def __str__(self):
        return self.titulo
