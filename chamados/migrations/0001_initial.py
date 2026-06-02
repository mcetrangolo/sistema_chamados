# Generated manually for the initial chamados module.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Categoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=120, unique=True)),
                ("ativo", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "categoria",
                "verbose_name_plural": "categorias",
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="Setor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=120, unique=True)),
                ("ativo", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "setor",
                "verbose_name_plural": "setores",
                "ordering": ["nome"],
            },
        ),
        migrations.CreateModel(
            name="Chamado",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("numero", models.CharField(editable=False, max_length=30, unique=True)),
                ("nome_solicitante", models.CharField(max_length=150)),
                ("telefone", models.CharField(blank=True, max_length=40, verbose_name="telefone ou ramal")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="e-mail")),
                ("prioridade", models.CharField(choices=[("baixa", "Baixa"), ("media", "Média"), ("alta", "Alta"), ("critica", "Crítica")], default="media", max_length=20)),
                ("descricao", models.TextField(verbose_name="descrição do problema")),
                ("status", models.CharField(choices=[("aberto", "Aberto"), ("em_analise", "Em análise"), ("em_atendimento", "Em atendimento"), ("aguardando_usuario", "Aguardando usuário"), ("aguardando_fornecedor", "Aguardando fornecedor"), ("resolvido", "Resolvido"), ("encerrado", "Encerrado"), ("cancelado", "Cancelado")], default="aberto", max_length=30)),
                ("solucao_aplicada", models.TextField(blank=True, verbose_name="solução aplicada")),
                ("observacoes_internas", models.TextField(blank=True, verbose_name="observações internas")),
                ("criado_em", models.DateTimeField(auto_now_add=True, verbose_name="data e hora de abertura")),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("concluido_em", models.DateTimeField(blank=True, null=True, verbose_name="data de conclusão")),
                ("arquivado", models.BooleanField(default=False)),
                ("categoria", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="chamados", to="chamados.categoria")),
                ("setor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="chamados", to="chamados.setor")),
                ("solicitante", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="chamados_solicitados", to=settings.AUTH_USER_MODEL)),
                ("tecnico_responsavel", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="chamados_atribuidos", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "chamado",
                "verbose_name_plural": "chamados",
                "ordering": ["-criado_em"],
            },
        ),
        migrations.CreateModel(
            name="HistoricoChamado",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("aberto", "Aberto"), ("em_analise", "Em análise"), ("em_atendimento", "Em atendimento"), ("aguardando_usuario", "Aguardando usuário"), ("aguardando_fornecedor", "Aguardando fornecedor"), ("resolvido", "Resolvido"), ("encerrado", "Encerrado"), ("cancelado", "Cancelado")], max_length=30)),
                ("comentario", models.TextField(blank=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("chamado", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="historico", to="chamados.chamado")),
                ("usuario", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "histórico do chamado",
                "verbose_name_plural": "históricos dos chamados",
                "ordering": ["-criado_em"],
            },
        ),
        migrations.CreateModel(
            name="AnexoChamado",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("arquivo", models.FileField(upload_to="chamados/anexos/%Y/%m/")),
                ("descricao", models.CharField(blank=True, max_length=150)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("chamado", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="anexos", to="chamados.chamado")),
                ("enviado_por", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "anexo do chamado",
                "verbose_name_plural": "anexos dos chamados",
                "ordering": ["-criado_em"],
            },
        ),
    ]
