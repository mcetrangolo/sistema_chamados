from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chamados", "0009_sla_pausa"),
    ]

    operations = [
        migrations.CreateModel(
            name="AprovacaoSolicitacao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("origem", models.CharField(choices=[("catalogo", "Catálogo de serviços"), ("governanca", "Governança")], max_length=20)),
                ("governanca_id", models.PositiveIntegerField(blank=True, null=True)),
                ("titulo", models.CharField(max_length=180)),
                ("solicitante", models.CharField(max_length=150)),
                ("status", models.CharField(choices=[("pendente", "Pendente"), ("aprovada", "Aprovada"), ("rejeitada", "Rejeitada")], default="pendente", max_length=20)),
                ("observacao", models.TextField(blank=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("decidido_em", models.DateTimeField(blank=True, null=True)),
                ("aprovado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("solicitacao_servico", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="aprovacoes", to="chamados.solicitacaoservico")),
            ],
            options={
                "verbose_name": "aprovação de solicitação",
                "verbose_name_plural": "aprovações de solicitações",
                "ordering": ["-criado_em"],
            },
        ),
    ]
