from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chamados", "0003_osticket_like"),
    ]

    operations = [
        migrations.CreateModel(
            name="CredencialSNMP",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=100, unique=True)),
                ("versao", models.CharField(choices=[("1", "v1"), ("2c", "v2c"), ("3", "v3")], default="2c", max_length=5)),
                ("community", models.CharField(blank=True, max_length=120)),
                ("usuario", models.CharField(blank=True, max_length=120)),
                ("ativo", models.BooleanField(default=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
            ],
            options={"verbose_name": "credencial SNMP", "verbose_name_plural": "credenciais SNMP", "ordering": ["nome"]},
        ),
        migrations.CreateModel(
            name="TipoAtivo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=80, unique=True)),
                ("ativo", models.BooleanField(default=True)),
            ],
            options={"verbose_name": "tipo de ativo", "verbose_name_plural": "tipos de ativo", "ordering": ["nome"]},
        ),
        migrations.CreateModel(
            name="FaixaRede",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=100)),
                ("cidr", models.CharField(help_text="Exemplo: 192.168.0.0/24", max_length=50, verbose_name="CIDR")),
                ("ativa", models.BooleanField(default=True)),
                ("credencial_snmp", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="faixas", to="inventario.credencialsnmp")),
            ],
            options={"verbose_name": "faixa de rede", "verbose_name_plural": "faixas de rede", "ordering": ["nome"]},
        ),
        migrations.CreateModel(
            name="AtivoRede",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=150)),
                ("ip", models.GenericIPAddressField(blank=True, null=True, verbose_name="IP")),
                ("mac", models.CharField(blank=True, max_length=30, verbose_name="MAC")),
                ("hostname", models.CharField(blank=True, max_length=150)),
                ("fabricante", models.CharField(blank=True, max_length=120)),
                ("modelo", models.CharField(blank=True, max_length=120)),
                ("numero_serie", models.CharField(blank=True, max_length=120, verbose_name="número de série")),
                ("sistema_operacional", models.CharField(blank=True, max_length=150)),
                ("localizacao", models.CharField(blank=True, max_length=150)),
                ("responsavel", models.CharField(blank=True, max_length=150)),
                ("funcao", models.CharField(blank=True, max_length=150, verbose_name="função")),
                ("status", models.CharField(choices=[("online", "Online"), ("offline", "Offline"), ("desconhecido", "Desconhecido"), ("manutencao", "Em manutenção"), ("desativado", "Desativado")], default="desconhecido", max_length=20)),
                ("origem", models.CharField(choices=[("manual", "Manual"), ("snmp", "SNMP"), ("ad", "Active Directory"), ("importacao", "Importação")], default="manual", max_length=20)),
                ("observacoes", models.TextField(blank=True, verbose_name="observações")),
                ("ultima_coleta_em", models.DateTimeField(blank=True, null=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("setor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ativos_rede", to="chamados.setor")),
                ("tipo", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ativos", to="inventario.tipoativo")),
            ],
            options={"verbose_name": "ativo de rede", "verbose_name_plural": "ativos de rede", "ordering": ["nome"]},
        ),
        migrations.CreateModel(
            name="InterfaceRede",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=120)),
                ("descricao", models.CharField(blank=True, max_length=250)),
                ("mac", models.CharField(blank=True, max_length=30, verbose_name="MAC")),
                ("ip", models.GenericIPAddressField(blank=True, null=True, verbose_name="IP")),
                ("velocidade", models.CharField(blank=True, max_length=80)),
                ("status", models.CharField(blank=True, max_length=80)),
                ("ativo", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interfaces", to="inventario.ativorede")),
            ],
            options={"verbose_name": "interface de rede", "verbose_name_plural": "interfaces de rede", "ordering": ["nome"]},
        ),
        migrations.CreateModel(
            name="OcorrenciaAtivo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("manutencao", "Manutenção"), ("incidente", "Incidente"), ("alteracao", "Alteração"), ("observacao", "Observação")], default="observacao", max_length=20)),
                ("titulo", models.CharField(max_length=150)),
                ("descricao", models.TextField()),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("ativo", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ocorrencias", to="inventario.ativorede")),
                ("registrado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "ocorrência do ativo", "verbose_name_plural": "ocorrências dos ativos", "ordering": ["-criado_em"]},
        ),
        migrations.CreateModel(
            name="VarreduraRede",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("agendada", "Agendada"), ("em_execucao", "Em execução"), ("concluida", "Concluída"), ("erro", "Erro")], default="agendada", max_length=20)),
                ("mensagem", models.TextField(blank=True)),
                ("ativos_encontrados", models.PositiveIntegerField(default=0)),
                ("iniciado_em", models.DateTimeField(auto_now_add=True)),
                ("concluido_em", models.DateTimeField(blank=True, null=True)),
                ("faixa", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="varreduras", to="inventario.faixarede")),
                ("iniciado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "varredura de rede", "verbose_name_plural": "varreduras de rede", "ordering": ["-iniciado_em"]},
        ),
    ]
