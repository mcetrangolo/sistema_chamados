from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

from chamados.models import ArtigoConhecimento, Categoria, RespostaPronta, ServicoCatalogo, Setor, TopicoAjuda
from inventario.models import CredencialSNMP, MetodoDescoberta, TipoAtivo
from core.models import ConfiguracaoInstitucional


class Command(BaseCommand):
    help = "Cria categorias iniciais e um setor padrão para o módulo de chamados."

    def handle(self, *args, **options):
        ConfiguracaoInstitucional.atual()

        categorias = [
            "Computador",
            "Impressora",
            "Internet",
            "Rede",
            "Sistema",
            "E-mail",
            "Telefonia",
            "Acesso de usuário",
            "Instalação de software",
            "Manutenção preventiva",
            "Outros",
        ]

        categorias_criadas = {}
        for nome in categorias:
            categoria, _ = Categoria.objects.get_or_create(nome=nome)
            categorias_criadas[nome] = categoria

        Setor.objects.get_or_create(nome="TI")
        Group.objects.get_or_create(name="Técnicos de TI")

        topicos = [
            ("Problema com computador", "Computador", "media", 48),
            ("Impressora ou scanner", "Impressora", "media", 48),
            ("Internet ou rede", "Rede", "alta", 24),
            ("Acesso de usuário", "Acesso de usuário", "alta", 24),
            ("Sistema corporativo", "Sistema", "alta", 24),
            ("Outros atendimentos", "Outros", "media", 72),
        ]
        for nome, categoria_nome, prioridade, sla in topicos:
            TopicoAjuda.objects.get_or_create(
                nome=nome,
                defaults={
                    "categoria": categorias_criadas[categoria_nome],
                    "prioridade_padrao": prioridade,
                    "sla_horas": sla,
                },
            )

        RespostaPronta.objects.get_or_create(
            titulo="Solicitar mais informações",
            defaults={
                "conteudo": "Olá. Para avançarmos com o atendimento, poderia enviar mais detalhes sobre o problema, incluindo mensagem de erro, equipamento afetado e horário em que ocorreu?"
            },
        )
        RespostaPronta.objects.get_or_create(
            titulo="Chamado resolvido",
            defaults={
                "conteudo": "Olá. O atendimento foi concluído e a solução aplicada está registrada no chamado. Caso o problema volte a ocorrer, abra um novo chamado informando este número como referência."
            },
        )

        ArtigoConhecimento.objects.get_or_create(
            titulo="Como abrir um chamado eficiente",
            defaults={
                "resumo": "Informações que ajudam a equipe de TI a atender mais rápido.",
                "conteudo": "Descreva o problema com clareza, informe mensagens de erro, equipamento afetado, setor, telefone para contato e desde quando o problema ocorre.",
                "publico": True,
                "ativo": True,
            },
        )

        servicos = [
            ("Novo usuário de rede", "Acesso de usuário", "Solicitação para criação de usuário de rede e acessos iniciais.", "alta"),
            ("Troca de senha", "Acesso de usuário", "Solicitação de apoio para troca ou redefinição de senha.", "media"),
            ("Instalação de software", "Instalação de software", "Solicitação de instalação ou atualização de software autorizado.", "media"),
            ("Acesso à internet/Wi-Fi", "Internet", "Solicitação de acesso à internet ou Wi-Fi corporativo.", "media"),
            ("Manutenção de computador", "Computador", "Solicitação de avaliação ou manutenção em computador/notebook.", "media"),
        ]
        for nome, categoria_nome, descricao, prioridade in servicos:
            ServicoCatalogo.objects.get_or_create(
                nome=nome,
                defaults={
                    "categoria": categorias_criadas[categoria_nome],
                    "descricao": descricao,
                    "prioridade_padrao": prioridade,
                    "requer_matricula": True,
                },
            )
        ArtigoConhecimento.objects.get_or_create(
            titulo="Quando usar prioridade crítica",
            defaults={
                "resumo": "Critérios para classificar corretamente a urgência de um chamado.",
                "conteudo": "Use prioridade crítica quando houver paralisação de serviço essencial, impacto em vários usuários ou interrupção de atividade institucional importante.",
                "publico": True,
                "ativo": True,
            },
        )

        for tipo in [
            "Switch",
            "Roteador",
            "Access Point",
            "Firewall",
            "Impressora",
            "Servidor",
            "Computador",
            "Notebook",
            "Dispositivo de rede",
            "Dispositivo desconhecido",
            "Servidor ou serviço de rede",
            "Dispositivo importado",
            "Dispositivo manual",
        ]:
            TipoAtivo.objects.get_or_create(nome=tipo)

        CredencialSNMP.objects.get_or_create(
            nome="SNMP público v2c",
            defaults={
                "versao": CredencialSNMP.Versao.V2C,
                "community": "public",
            },
        )

        metodos = {
            MetodoDescoberta.Codigo.PING: ("Ping / ICMP", "Detecta hosts ativos por resposta ICMP."),
            MetodoDescoberta.Codigo.DNS: ("DNS reverso", "Tenta identificar hostnames a partir dos IPs."),
            MetodoDescoberta.Codigo.TCP: ("TCP / portas", "Detecta serviços expostos em portas informadas."),
            MetodoDescoberta.Codigo.SNMP: ("SNMP", "Consulta dispositivos gerenciáveis como switches, roteadores e impressoras."),
            MetodoDescoberta.Codigo.AD: ("Active Directory", "Sincroniza computadores e informações do domínio."),
            MetodoDescoberta.Codigo.WINRM: ("WinRM / WMI", "Consulta máquinas Windows autorizadas."),
            MetodoDescoberta.Codigo.CSV: ("Importação CSV", "Importa ativos a partir de planilhas."),
            MetodoDescoberta.Codigo.MANUAL: ("Cadastro manual", "Registro manual de ativos."),
        }
        for codigo, (nome, descricao) in metodos.items():
            MetodoDescoberta.objects.get_or_create(
                codigo=codigo,
                defaults={"nome": nome, "descricao": descricao},
            )

        self.stdout.write(self.style.SUCCESS("Dados iniciais criados com sucesso."))
