from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("chamados", "0005_thread_anexos"),
    ]

    operations = [
        migrations.CreateModel(
            name="ArtigoConhecimento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(max_length=180)),
                ("slug", models.SlugField(blank=True, max_length=200, unique=True)),
                ("resumo", models.CharField(blank=True, max_length=250)),
                ("conteudo", models.TextField()),
                ("publico", models.BooleanField(default=True)),
                ("ativo", models.BooleanField(default=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("topico_ajuda", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="artigos", to="chamados.topicoajuda")),
            ],
            options={
                "verbose_name": "artigo da base de conhecimento",
                "verbose_name_plural": "artigos da base de conhecimento",
                "ordering": ["titulo"],
            },
        ),
        migrations.CreateModel(
            name="AvaliacaoChamado",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nota", models.PositiveSmallIntegerField(choices=[(1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")])),
                ("comentario", models.TextField(blank=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("chamado", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="avaliacao", to="chamados.chamado")),
            ],
            options={
                "verbose_name": "avaliação do chamado",
                "verbose_name_plural": "avaliações dos chamados",
            },
        ),
    ]
