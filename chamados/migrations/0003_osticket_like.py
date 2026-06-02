from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chamados", "0002_public_chamados"),
    ]

    operations = [
        migrations.CreateModel(
            name="RespostaPronta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(max_length=150, unique=True)),
                ("conteudo", models.TextField()),
                ("ativo", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "resposta pronta",
                "verbose_name_plural": "respostas prontas",
                "ordering": ["titulo"],
            },
        ),
        migrations.CreateModel(
            name="TopicoAjuda",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=150, unique=True)),
                ("descricao", models.TextField(blank=True)),
                ("prioridade_padrao", models.CharField(choices=[("baixa", "Baixa"), ("media", "Média"), ("alta", "Alta"), ("critica", "Crítica")], default="media", max_length=20)),
                ("sla_horas", models.PositiveIntegerField(default=48, help_text="Prazo esperado para resolução dos chamados deste tópico.", verbose_name="SLA em horas")),
                ("ativo", models.BooleanField(default=True)),
                ("atendente_padrao", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="topicos_ajuda_padrao", to=settings.AUTH_USER_MODEL)),
                ("categoria", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="topicos_ajuda", to="chamados.categoria")),
            ],
            options={
                "verbose_name": "tópico de ajuda",
                "verbose_name_plural": "tópicos de ajuda",
                "ordering": ["nome"],
            },
        ),
        migrations.AddField(
            model_name="chamado",
            name="origem",
            field=models.CharField(choices=[("portal", "Portal"), ("interno", "Interno"), ("email", "E-mail"), ("telefone", "Telefone")], default="portal", max_length=20),
        ),
        migrations.AddField(
            model_name="chamado",
            name="vencimento_em",
            field=models.DateTimeField(blank=True, null=True, verbose_name="vencimento SLA"),
        ),
        migrations.AddField(
            model_name="chamado",
            name="topico_ajuda",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="chamados", to="chamados.topicoajuda"),
        ),
        migrations.CreateModel(
            name="TarefaChamado",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(max_length=150)),
                ("descricao", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("pendente", "Pendente"), ("em_andamento", "Em andamento"), ("concluida", "Concluída")], default="pendente", max_length=20)),
                ("prazo", models.DateTimeField(blank=True, null=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("chamado", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tarefas", to="chamados.chamado")),
                ("responsavel", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="tarefas_chamado", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "tarefa do chamado",
                "verbose_name_plural": "tarefas dos chamados",
                "ordering": ["status", "prazo", "titulo"],
            },
        ),
    ]
