from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("governanca", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="solicitacaogovernanca",
            name="chefia_imediata",
            field=models.CharField(
                blank=True,
                help_text="Nome da chefia que autoriza ou deverá validar a solicitação.",
                max_length=150,
                verbose_name="chefia imediata/autorizador",
            ),
        ),
        migrations.AddField(
            model_name="solicitacaogovernanca",
            name="termo_aceito_em",
            field=models.DateTimeField(blank=True, null=True, verbose_name="termo aceito em"),
        ),
        migrations.AddField(
            model_name="solicitacaogovernanca",
            name="termo_aceito_ip",
            field=models.GenericIPAddressField(blank=True, null=True, verbose_name="IP do aceite"),
        ),
        migrations.AddField(
            model_name="solicitacaogovernanca",
            name="termo_aceito_user_agent",
            field=models.CharField(blank=True, max_length=300, verbose_name="user-agent do aceite"),
        ),
        migrations.AddField(
            model_name="solicitacaogovernanca",
            name="termo_texto_aceito",
            field=models.TextField(blank=True, verbose_name="texto do termo aceito"),
        ),
        migrations.AddField(
            model_name="solicitacaogovernanca",
            name="termo_versao",
            field=models.CharField(blank=True, max_length=80, verbose_name="versão do termo aceito"),
        ),
        migrations.AddField(
            model_name="solicitacaogovernanca",
            name="tipo_solicitacao_rede",
            field=models.CharField(
                blank=True,
                choices=[
                    ("novo_acesso", "Novo acesso"),
                    ("troca_senha", "Troca de senha"),
                    ("alteracao_permissao", "Alteração de permissão de acesso"),
                ],
                max_length=30,
                verbose_name="tipo de solicitação",
            ),
        ),
        migrations.AddField(
            model_name="solicitacaogovernanca",
            name="usuario_rede_existente",
            field=models.CharField(
                blank=True,
                help_text="Preencha em caso de troca de senha ou alteração de permissão.",
                max_length=80,
                verbose_name="usuário de rede existente",
            ),
        ),
    ]
