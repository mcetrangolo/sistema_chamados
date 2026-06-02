from django.core.management.base import BaseCommand, CommandError

from inventario.models import CredencialSNMP
from inventario.services import consultar_snmp_basico


class Command(BaseCommand):
    help = "Testa uma consulta SNMP basica em um ativo de rede."

    def add_arguments(self, parser):
        parser.add_argument("ip", help="IP do switch, roteador, impressora ou outro ativo SNMP.")
        parser.add_argument(
            "--credencial",
            help="Nome da credencial SNMP cadastrada. Se omitido, usa a primeira credencial ativa.",
        )
        parser.add_argument(
            "--community",
            help="Community SNMP v1/v2c para teste rapido, sem depender de cadastro previo.",
        )

    def handle(self, *args, **options):
        community = options.get("community")
        credencial_nome = options.get("credencial")

        if not community:
            credenciais = CredencialSNMP.objects.filter(ativo=True)
            if credencial_nome:
                credenciais = credenciais.filter(nome=credencial_nome)
            credencial = credenciais.first()
            if not credencial:
                raise CommandError("Informe --community ou cadastre uma credencial SNMP ativa.")
            if credencial.versao == CredencialSNMP.Versao.V3:
                raise CommandError("O teste automatico atual usa SNMP v1/v2c. Use uma credencial community.")
            community = credencial.community

        dados = consultar_snmp_basico(options["ip"], community)
        if not dados:
            raise CommandError("Nao houve resposta SNMP. Verifique IP, community, porta 161/UDP e ACL do equipamento.")

        self.stdout.write(self.style.SUCCESS("Consulta SNMP realizada com sucesso."))
        self.stdout.write(f"Hostname: {dados.get('hostname') or '-'}")
        self.stdout.write(f"Descricao: {dados.get('descricao') or '-'}")
