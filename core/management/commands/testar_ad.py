from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Testa conexao e busca basica no Active Directory configurado no .env."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limite",
            type=int,
            default=5,
            help="Quantidade maxima de objetos exibidos no teste.",
        )

    def handle(self, *args, **options):
        obrigatorios = {
            "AD_SERVER": settings.AD_SERVER,
            "AD_USER": settings.AD_USER,
            "AD_PASSWORD": settings.AD_PASSWORD,
            "AD_BASE_DN": settings.AD_BASE_DN,
        }
        faltando = [nome for nome, valor in obrigatorios.items() if not valor]
        if faltando:
            raise CommandError(f"Configure no .env: {', '.join(faltando)}.")

        try:
            from ldap3 import ALL, Connection, Server
        except Exception as exc:
            raise CommandError("Biblioteca ldap3 nao esta instalada.") from exc

        server = Server(settings.AD_SERVER, get_info=ALL)
        conn = Connection(server, user=settings.AD_USER, password=settings.AD_PASSWORD, auto_bind=True)
        try:
            conn.search(
                settings.AD_BASE_DN,
                settings.AD_COMPUTERS_FILTER,
                attributes=["cn", "dNSHostName", "operatingSystem"],
                size_limit=options["limite"],
            )
            self.stdout.write(self.style.SUCCESS("Conexao com Active Directory realizada com sucesso."))
            self.stdout.write(f"Objetos encontrados no teste: {len(conn.entries)}")
            for entry in conn.entries:
                cn = getattr(entry, "cn", "")
                hostname = getattr(entry, "dNSHostName", "")
                so = getattr(entry, "operatingSystem", "")
                self.stdout.write(f"- {cn} {hostname} {so}".strip())
        finally:
            conn.unbind()
