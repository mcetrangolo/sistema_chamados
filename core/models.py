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
        },
        TemaVisual.BLUE: {
            "cor_primaria": "#155eef",
            "cor_secundaria": "#0f3f9f",
            "cor_fundo": "#eef4ff",
        },
        TemaVisual.DARK: {
            "cor_primaria": "#38bdf8",
            "cor_secundaria": "#020617",
            "cor_fundo": "#111827",
        },
        TemaVisual.RED: {
            "cor_primaria": "#dc2626",
            "cor_secundaria": "#7f1d1d",
            "cor_fundo": "#fff5f5",
        },
        TemaVisual.GREEN: {
            "cor_primaria": "#16875d",
            "cor_secundaria": "#14532d",
            "cor_fundo": "#f0fdf4",
        },
        TemaVisual.CORPORATE: {
            "cor_primaria": "#0f766e",
            "cor_secundaria": "#1f2937",
            "cor_fundo": "#f3f6f8",
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
    tema_visual = models.CharField(
        max_length=20,
        choices=TemaVisual.choices,
        default=TemaVisual.BLUE,
    )
    cor_primaria = models.CharField(max_length=20, default="#155eef")
    cor_secundaria = models.CharField(max_length=20, default="#0f172a")
    cor_fundo = models.CharField(max_length=20, default="#f4f7fb")
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
        super().save(*args, **kwargs)

    @classmethod
    def atual(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
