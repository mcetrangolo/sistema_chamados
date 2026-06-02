from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("inventario", "0001_initial"),
        ("chamados", "0003_osticket_like"),
    ]

    operations = [
        migrations.AddField(
            model_name="chamado",
            name="ativo_rede",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="chamados", to="inventario.ativorede"),
        ),
    ]
