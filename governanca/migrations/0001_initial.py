from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SolicitacaoGovernanca",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("protocolo", models.CharField(editable=False, max_length=40, unique=True)),
                ("tipo", models.CharField(choices=[("usuario_acesso", "Cadastro de usuário e acessos"), ("wifi_corporativo", "Acesso à internet Wi-Fi corporativa")], max_length=30)),
                ("matricula", models.CharField(max_length=50, verbose_name="matrícula")),
                ("nome", models.CharField(max_length=150)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("setor", models.CharField(max_length=120)),
                ("cargo", models.CharField(blank=True, max_length=120)),
                ("telefone", models.CharField(blank=True, max_length=50)),
                ("justificativa", models.TextField(blank=True)),
                ("acessos_solicitados", models.TextField(blank=True, verbose_name="acessos solicitados")),
                ("aparelhos", models.TextField(blank=True, help_text="Informe marca, modelo, patrimônio/serial e observações.")),
                ("termo_ciencia", models.BooleanField(default=False, verbose_name="declaro ciência das responsabilidades")),
                ("documento_caminho", models.CharField(blank=True, max_length=500)),
                ("status", models.CharField(choices=[("recebida", "Recebida"), ("em_analise", "Em análise"), ("atendida", "Atendida"), ("negada", "Negada")], default="recebida", max_length=20)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "solicitação de governança",
                "verbose_name_plural": "solicitações de governança",
                "ordering": ["-criado_em"],
            },
        ),
    ]
