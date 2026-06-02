from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ConfiguracaoInstitucional",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome_instituicao", models.CharField(default="Sistema de Chamados", max_length=180)),
                ("sigla", models.CharField(blank=True, max_length=30)),
                ("cnpj", models.CharField(blank=True, max_length=30, verbose_name="CNPJ")),
                ("endereco", models.CharField(blank=True, max_length=250, verbose_name="endereço")),
                ("telefone", models.CharField(blank=True, max_length=60)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("site", models.URLField(blank=True)),
                ("logo", models.ImageField(blank=True, upload_to="institucional/logo/")),
                ("cor_primaria", models.CharField(default="#155eef", max_length=20)),
                ("cor_secundaria", models.CharField(default="#0f172a", max_length=20)),
                ("cor_fundo", models.CharField(default="#f4f7fb", max_length=20)),
                ("texto_rodape", models.CharField(blank=True, max_length=180)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "configuração institucional",
                "verbose_name_plural": "configurações institucionais",
            },
        ),
    ]
