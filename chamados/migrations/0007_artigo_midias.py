from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chamados", "0006_conhecimento_avaliacao"),
    ]

    operations = [
        migrations.AddField(
            model_name="artigoconhecimento",
            name="video_youtube_url",
            field=models.URLField(blank=True, verbose_name="vídeo do YouTube"),
        ),
        migrations.AddField(
            model_name="artigoconhecimento",
            name="imagem",
            field=models.ImageField(blank=True, upload_to="conhecimento/imagens/%Y/%m/"),
        ),
        migrations.AddField(
            model_name="artigoconhecimento",
            name="legenda_imagem",
            field=models.CharField(blank=True, max_length=180),
        ),
    ]
