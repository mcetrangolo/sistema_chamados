from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("chamados", "0007_artigo_midias"),
    ]

    operations = [
        migrations.CreateModel(
            name="ServicoCatalogo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=150, unique=True)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("descricao", models.TextField(blank=True)),
                ("prioridade_padrao", models.CharField(choices=[("baixa", "Baixa"), ("media", "Média"), ("alta", "Alta"), ("critica", "Crítica")], default="media", max_length=20)),
                ("requer_matricula", models.BooleanField(default=True)),
                ("requer_aprovacao", models.BooleanField(default=False)),
                ("instrucoes", models.TextField(blank=True)),
                ("ativo", models.BooleanField(default=True)),
                ("categoria", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="servicos", to="chamados.categoria")),
                ("topico_ajuda", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="servicos", to="chamados.topicoajuda")),
            ],
            options={
                "verbose_name": "serviço do catálogo",
                "verbose_name_plural": "serviços do catálogo",
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="SolicitacaoServico",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("protocolo", models.CharField(editable=False, max_length=40, unique=True)),
                ("matricula", models.CharField(blank=True, max_length=50, verbose_name="matrícula")),
                ("nome", models.CharField(max_length=150)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("telefone", models.CharField(blank=True, max_length=50)),
                ("detalhes", models.TextField()),
                ("status", models.CharField(choices=[("recebida", "Recebida"), ("convertida", "Convertida em chamado"), ("cancelada", "Cancelada")], default="recebida", max_length=20)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("chamado", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="solicitacao_servico", to="chamados.chamado")),
                ("servico", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="solicitacoes", to="chamados.servicocatalogo")),
                ("setor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="solicitacoes_servico", to="chamados.setor")),
            ],
            options={
                "verbose_name": "solicitação de serviço",
                "verbose_name_plural": "solicitações de serviço",
                "ordering": ["-criado_em"],
            },
        ),
    ]
