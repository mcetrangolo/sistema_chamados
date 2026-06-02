import datetime
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chamados", "0008_catalogo_servicos"),
    ]

    operations = [
        migrations.AddField(
            model_name="chamado",
            name="sla_pausado_em",
            field=models.DateTimeField(blank=True, null=True, verbose_name="SLA pausado em"),
        ),
        migrations.AddField(
            model_name="chamado",
            name="sla_pausado_total",
            field=models.DurationField(default=datetime.timedelta, verbose_name="tempo total de pausa do SLA"),
        ),
    ]
