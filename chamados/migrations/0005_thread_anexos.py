from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chamados", "0004_chamado_ativo_rede"),
    ]

    operations = [
        migrations.AlterField(
            model_name="anexochamado",
            name="enviado_por",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="anexochamado",
            name="nome_enviado_por",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name="anexochamado",
            name="publico",
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name="ComentarioChamado",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome_autor", models.CharField(blank=True, max_length=150)),
                ("email_autor", models.EmailField(blank=True, max_length=254)),
                ("mensagem", models.TextField()),
                ("publico", models.BooleanField(default=True, help_text="Comentários públicos aparecem para o solicitante no portal.")),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("autor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("chamado", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comentarios", to="chamados.chamado")),
            ],
            options={
                "verbose_name": "comentário do chamado",
                "verbose_name_plural": "comentários dos chamados",
                "ordering": ["criado_em"],
            },
        ),
    ]
