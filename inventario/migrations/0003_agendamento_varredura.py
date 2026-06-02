from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("inventario", "0002_metodo_descoberta"),
    ]

    operations = [
        migrations.CreateModel(
            name="AgendamentoVarredura",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=120)),
                ("metodo", models.CharField(choices=[("ping", "Ping / ICMP"), ("dns", "DNS reverso"), ("tcp", "TCP / portas"), ("snmp", "SNMP"), ("ad", "Active Directory"), ("winrm", "WinRM / WMI"), ("csv", "Importação CSV"), ("manual", "Cadastro manual")], max_length=20)),
                ("portas", models.CharField(blank=True, max_length=120)),
                ("intervalo_horas", models.PositiveIntegerField(default=24)),
                ("ativo", models.BooleanField(default=True)),
                ("ultima_execucao", models.DateTimeField(blank=True, null=True)),
                ("proxima_execucao", models.DateTimeField(blank=True, null=True)),
                ("faixa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="agendamentos", to="inventario.faixarede")),
            ],
            options={
                "verbose_name": "agendamento de varredura",
                "verbose_name_plural": "agendamentos de varredura",
                "ordering": ["nome"],
            },
        ),
    ]
