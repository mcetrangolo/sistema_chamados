from django.db import migrations
from django.utils.text import slugify


ARTIGOS = [
    (
        "Atendimento e chamados",
        "Uso do portal de chamados",
        "Como abrir um chamado corretamente",
        "Informacoes essenciais para registrar uma solicitacao com clareza.",
        """Para agilizar o atendimento, informe o maximo de detalhes relevantes no chamado.

Inclua sempre:
- Nome do solicitante, setor e telefone/ramal.
- Equipamento afetado, quando houver.
- Mensagem de erro completa ou print da tela.
- Quando o problema comecou.
- Se afeta apenas voce, um setor ou todos os usuarios.
- Impacto no trabalho e urgencia percebida.

Evite descricoes muito genericas como "nao funciona". Prefira explicar o que voce tentou fazer, o que aconteceu e o que esperava que acontecesse.""",
    ),
    (
        "Atendimento e chamados",
        "Uso do portal de chamados",
        "Como consultar o andamento do chamado",
        "Acompanhe o chamado usando protocolo e e-mail informado na abertura.",
        """Para consultar um chamado, acesse a area de consulta do portal e informe:

- Numero/protocolo do chamado.
- E-mail usado na abertura.

Na consulta voce pode acompanhar respostas, enviar novas informacoes e verificar o status atual. Guarde o numero do chamado ate a conclusao do atendimento.""",
    ),
    (
        "Computadores e equipamentos",
        "Identificacao do equipamento",
        "Como identificar o nome do computador",
        "Passos simples para localizar o nome do computador no Windows.",
        """O nome do computador ajuda a equipe de TI a localizar o equipamento no inventario.

No Windows:
1. Pressione as teclas Windows + R.
2. Digite cmd e pressione Enter.
3. No prompt, digite hostname e pressione Enter.
4. Informe o nome exibido no chamado.

Tambem e possivel verificar em Configuracoes > Sistema > Sobre.""",
    ),
    (
        "Computadores e equipamentos",
        "Identificacao do equipamento",
        "Como verificar o IP da maquina",
        "Use o comando ipconfig para informar o endereco IP ao suporte.",
        """O endereco IP ajuda a diagnosticar problemas de rede e identificar o equipamento.

No Windows:
1. Pressione Windows + R.
2. Digite cmd e pressione Enter.
3. Digite ipconfig e pressione Enter.
4. Procure o campo Endereco IPv4.

Informe esse IP no chamado quando o problema envolver rede, internet, impressoras ou acesso a sistemas.""",
    ),
    (
        "Rede e internet",
        "Problemas de conectividade",
        "O que fazer quando a internet estiver lenta",
        "Verificacoes iniciais antes de abrir um chamado de lentidao.",
        """Antes de abrir o chamado, se possivel verifique:

- Se outros sites ou sistemas tambem estao lentos.
- Se outros usuarios do mesmo setor estao com o mesmo problema.
- Se o computador esta conectado via cabo ou Wi-Fi.
- Se reiniciar o navegador resolve.
- Se ha downloads, atualizacoes ou videos consumindo a conexao.

Ao abrir o chamado, informe horario aproximado, setor, equipamento afetado e se o problema e geral ou isolado.""",
    ),
    (
        "Impressoras",
        "Problemas de impressao",
        "O que fazer quando a impressora nao imprime",
        "Checklist basico para problemas comuns de impressao.",
        """Verifique estes pontos antes de abrir o chamado:

- A impressora esta ligada?
- Ha papel e toner/tinta?
- Alguma luz de erro esta acesa?
- A impressora correta esta selecionada no computador?
- Existe documento parado na fila de impressao?
- Outros usuarios conseguem imprimir?

Ao abrir o chamado, informe o nome ou local da impressora, mensagem de erro e se o problema afeta apenas voce ou todo o setor.""",
    ),
    (
        "Seguranca da informacao",
        "Senhas e phishing",
        "Boas praticas de seguranca de senha",
        "Cuidados essenciais para proteger contas e sistemas.",
        """Boas praticas recomendadas:

- Nao compartilhe sua senha com colegas.
- Nao anote senhas em locais visiveis.
- Use senhas diferentes para sistemas diferentes.
- Evite datas de nascimento, nomes e sequencias simples.
- Troque a senha se suspeitar que alguem teve acesso.
- Bloqueie a tela ao se afastar do computador.

A equipe de TI nunca deve pedir sua senha completa.""",
    ),
    (
        "Seguranca da informacao",
        "Senhas e phishing",
        "Como reconhecer e-mails falsos ou phishing",
        "Sinais de alerta para mensagens suspeitas.",
        """Desconfie de e-mails que tenham:

- Urgencia exagerada ou ameacas.
- Links encurtados ou dominios estranhos.
- Erros de portugues ou formatacao incomum.
- Anexos inesperados.
- Pedido de senha, codigo ou dados pessoais.
- Remetente parecido, mas nao identico ao oficial.

Na duvida, nao clique em links nem abra anexos. Encaminhe a mensagem para a equipe de TI ou abra um chamado informando o ocorrido.""",
    ),
    (
        "Softwares e sistemas",
        "Instalacao de software",
        "Como solicitar instalacao de software",
        "Informacoes necessarias para avaliar instalacao e licenciamento.",
        """Ao solicitar instalacao de software, informe:

- Nome do software.
- Versao desejada, se houver.
- Finalidade de uso.
- Equipamento onde deve ser instalado.
- Usuario responsavel.
- Se ja existe licenca ou contrato.
- Urgencia e prazo desejado.

A instalacao pode depender de licenciamento, compatibilidade, autorizacao da chefia e politicas de seguranca.""",
    ),
    (
        "Arquivos e backup",
        "Backup e restauracao",
        "Como solicitar restauracao de arquivo",
        "Dados necessarios para tentar recuperar arquivos perdidos.",
        """Para solicitar restauracao de arquivo, informe:

- Caminho completo da pasta ou sistema.
- Nome do arquivo, se lembrar.
- Data aproximada em que o arquivo existia.
- Data/hora em que percebeu a perda.
- Se o arquivo foi apagado, sobrescrito ou corrompido.

Quanto mais precisa for a informacao, maior a chance de localizar a versao correta no backup.""",
    ),
]


def slug_unico(ArtigoConhecimento, titulo):
    base = slugify(titulo)[:180] or "artigo"
    slug = base
    contador = 2
    while ArtigoConhecimento.objects.filter(slug=slug).exists():
        slug = f"{base}-{contador}"
        contador += 1
    return slug


def criar_artigos(apps, schema_editor):
    Categoria = apps.get_model("chamados", "Categoria")
    TopicoAjuda = apps.get_model("chamados", "TopicoAjuda")
    ArtigoConhecimento = apps.get_model("chamados", "ArtigoConhecimento")

    for categoria_nome, topico_nome, titulo, resumo, conteudo in ARTIGOS:
        categoria, _ = Categoria.objects.get_or_create(nome=categoria_nome, defaults={"ativo": True})
        topico, _ = TopicoAjuda.objects.get_or_create(
            nome=topico_nome,
            defaults={
                "categoria": categoria,
                "prioridade_padrao": "media",
                "sla_horas": 48,
                "ativo": True,
            },
        )
        if topico.categoria_id != categoria.id:
            topico.categoria = categoria
            topico.save(update_fields=["categoria"])

        artigo = ArtigoConhecimento.objects.filter(titulo=titulo).first()
        if artigo:
            artigo.topico_ajuda = topico
            artigo.resumo = resumo
            artigo.conteudo = conteudo
            artigo.publico = True
            artigo.ativo = True
            if not artigo.slug:
                artigo.slug = slug_unico(ArtigoConhecimento, titulo)
            artigo.save()
        else:
            ArtigoConhecimento.objects.create(
                titulo=titulo,
                slug=slug_unico(ArtigoConhecimento, titulo),
                topico_ajuda=topico,
                resumo=resumo,
                conteudo=conteudo,
                publico=True,
                ativo=True,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("chamados", "0015_mudanca_problema_camposervicocatalogo"),
    ]

    operations = [
        migrations.RunPython(criar_artigos, migrations.RunPython.noop),
    ]
