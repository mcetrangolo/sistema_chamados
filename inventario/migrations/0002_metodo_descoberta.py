from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventario", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MetodoDescoberta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(choices=[("ping", "Ping / ICMP"), ("dns", "DNS reverso"), ("tcp", "TCP / portas"), ("snmp", "SNMP"), ("ad", "Active Directory"), ("winrm", "WinRM / WMI"), ("csv", "Importação CSV"), ("manual", "Cadastro manual")], max_length=20, unique=True)),
                ("nome", models.CharField(max_length=100)),
                ("descricao", models.TextField(blank=True)),
                ("ativo", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "método de descoberta",
                "verbose_name_plural": "métodos de descoberta",
                "ordering": ["nome"],
            },
        ),
        migrations.AddField(
            model_name="varredurarede",
            name="metodo",
            field=models.CharField(choices=[("ping", "Ping / ICMP"), ("dns", "DNS reverso"), ("tcp", "TCP / portas"), ("snmp", "SNMP"), ("ad", "Active Directory"), ("winrm", "WinRM / WMI"), ("csv", "Importação CSV"), ("manual", "Cadastro manual")], default="snmp", max_length=20),
        ),
        migrations.AddField(
            model_name="varredurarede",
            name="portas",
            field=models.CharField(blank=True, help_text="Portas usadas em varredura TCP. Exemplo: 22,80,443,3389", max_length=120),
        ),
    ]
