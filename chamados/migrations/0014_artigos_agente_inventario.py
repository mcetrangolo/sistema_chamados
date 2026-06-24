from django.db import migrations


def criar_artigos_agente(apps, schema_editor):
    Categoria = apps.get_model("chamados", "Categoria")
    TopicoAjuda = apps.get_model("chamados", "TopicoAjuda")
    ArtigoConhecimento = apps.get_model("chamados", "ArtigoConhecimento")

    categoria, _ = Categoria.objects.get_or_create(nome="Computador", defaults={"ativo": True})
    topico, _ = TopicoAjuda.objects.get_or_create(
        nome="Agente de inventario",
        defaults={
            "categoria": categoria,
            "prioridade_padrao": "media",
            "sla_horas": 48,
            "ativo": True,
        },
    )
    ArtigoConhecimento.objects.get_or_create(
        titulo="Instalacao do agente de inventario no Windows",
        defaults={
            "slug": "instalacao-do-agente-de-inventario-no-windows",
            "topico_ajuda": topico,
            "resumo": "Como baixar, instalar, configurar e remover o agente Windows.",
            "conteudo": (
                "Acesse Inventario > Configurar agente e baixe o instalador Windows. "
                "Execute como administrador, informe o endereco do servidor, por exemplo http://IP-DO-SERVIDOR:8000, "
                "e confirme a instalacao. O agente registra tarefas agendadas para coleta ao iniciar o Windows e a cada 6 horas. "
                "Para remover, use Painel de Controle > Programas e Recursos ou Menu Iniciar > Sistema Chamados Agent > Desinstalar agente."
            ),
            "publico": True,
            "ativo": True,
        },
    )
    ArtigoConhecimento.objects.get_or_create(
        titulo="Instalacao do agente de inventario no Linux",
        defaults={
            "slug": "instalacao-do-agente-de-inventario-no-linux",
            "topico_ajuda": topico,
            "resumo": "Como instalar o agente Linux em Debian, Ubuntu, Proxmox e servidores similares.",
            "conteudo": (
                "Acesse Inventario > Configurar agente e baixe o agente Linux. No servidor Linux, execute chmod +x sistema-chamados-agent-linux.sh "
                "e depois sudo ./sistema-chamados-agent-linux.sh. Informe a URL do servidor quando solicitado. "
                "O instalador cria servico e timer do systemd para executar a coleta periodicamente. "
                "Funciona em maquinas Debian/Ubuntu e pode ser usado em servidores Proxmox, VMs e hosts Linux com acesso HTTP ao sistema."
            ),
            "publico": True,
            "ativo": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("chamados", "0013_chamado_aprovacao_necessaria_chamado_aprovado_em_and_more"),
    ]

    operations = [
        migrations.RunPython(criar_artigos_agente, migrations.RunPython.noop),
    ]
