from datetime import datetime
import os
from pathlib import Path
import platform
from re import sub
import shutil
import subprocess
import sys
import urllib.request

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connections
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView, UpdateView

from .backup_utils import descriptografar_backup, sha256_arquivo, validar_backup_zip
from .forms import ConfiguracaoBackupForm, ConfiguracaoInstitucionalForm, ConfiguracaoLDAPForm, PerfilUsuarioForm
from .models import ConfiguracaoBackup, ConfiguracaoInstitucional, ConfiguracaoLDAP, Notificacao, RegistroAuditoria, RegistroBackup


class SuperuserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


class ConfiguracaoInstitucionalView(LoginRequiredMixin, UpdateView):
    model = ConfiguracaoInstitucional
    form_class = ConfiguracaoInstitucionalForm
    template_name = "core/configuracao_institucional.html"
    success_url = reverse_lazy("core:configuracao")

    def get_object(self, queryset=None):
        return ConfiguracaoInstitucional.atual()

    def form_valid(self, form):
        messages.success(self.request, "Configuração institucional atualizada com sucesso.")
        return super().form_valid(form)


class PerfilUsuarioView(LoginRequiredMixin, UpdateView):
    form_class = PerfilUsuarioForm
    template_name = "core/perfil_usuario.html"
    success_url = reverse_lazy("core:perfil")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Suas informações pessoais foram atualizadas.")
        return super().form_valid(form)


class AjudaSistemaView(LoginRequiredMixin, TemplateView):
    template_name = "core/ajuda.html"


class AuditoriaListView(LoginRequiredMixin, SuperuserRequiredMixin, TemplateView):
    template_name = "core/auditoria.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        registros = RegistroAuditoria.objects.select_related("usuario")
        q = self.request.GET.get("q", "").strip()
        if q:
            registros = registros.filter(modelo__icontains=q) | registros.filter(objeto__icontains=q)
        context["registros"] = registros[:200]
        context["q"] = q
        return context


class NotificacaoListView(LoginRequiredMixin, TemplateView):
    template_name = "core/notificacoes.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["notificacoes"] = self.request.user.notificacoes.all()[:200]
        return context


@login_required
def marcar_notificacao_lida(request, pk):
    notificacao = get_object_or_404(Notificacao, pk=pk, usuario=request.user)
    if request.method == "POST":
        notificacao.lida_em = timezone.now()
        notificacao.save(update_fields=["lida_em"])
    return redirect(notificacao.link or "core:notificacoes")


@login_required
def marcar_todas_notificacoes_lidas(request):
    if request.method == "POST":
        request.user.notificacoes.filter(lida_em__isnull=True).update(lida_em=timezone.now())
    return redirect("core:notificacoes")


class ConfiguracaoLDAPView(LoginRequiredMixin, SuperuserRequiredMixin, TemplateView):
    template_name = "core/ldap.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        configuracao = ConfiguracaoLDAP.atual()
        context["configuracao"] = configuracao
        context["form"] = kwargs.get("form") or ConfiguracaoLDAPForm(instance=configuracao)
        return context

    def post(self, request, *args, **kwargs):
        acao = request.POST.get("acao", "salvar")
        configuracao = ConfiguracaoLDAP.atual()
        if acao == "salvar":
            form = ConfiguracaoLDAPForm(request.POST, instance=configuracao)
            if form.is_valid():
                form.save()
                messages.success(request, "Configuracao LDAP atualizada.")
                return redirect("core:ldap")
            return self.render_to_response(self.get_context_data(form=form))
        try:
            conexao = self._conectar(configuracao)
            if acao == "testar":
                conexao.unbind()
                messages.success(request, "Conexao LDAP realizada com sucesso.")
            elif acao == "sincronizar":
                total = self._sincronizar(conexao, configuracao)
                configuracao.ultima_sincronizacao = timezone.now()
                configuracao.ultima_mensagem = f"{total} usuario(s) sincronizados."
                configuracao.save(update_fields=["ultima_sincronizacao", "ultima_mensagem", "atualizado_em"])
                messages.success(request, configuracao.ultima_mensagem)
        except Exception as exc:
            configuracao.ultima_mensagem = str(exc)
            configuracao.save(update_fields=["ultima_mensagem", "atualizado_em"])
            messages.error(request, f"Falha LDAP: {exc}")
        return redirect("core:ldap")

    def _conectar(self, configuracao):
        if not configuracao.ativo:
            raise ValueError("Ative a integracao LDAP antes de testar.")
        from ldap3 import ALL, Connection, Server

        servidor = Server(
            configuracao.servidor,
            port=configuracao.porta,
            use_ssl=configuracao.usar_ssl,
            get_info=ALL,
        )
        return Connection(
            servidor,
            user=configuracao.usuario_bind,
            password=configuracao.obter_senha(),
            auto_bind=True,
        )

    def _sincronizar(self, conexao, configuracao):
        atributos = [
            configuracao.atributo_login,
            configuracao.atributo_nome,
            configuracao.atributo_sobrenome,
            configuracao.atributo_email,
        ]
        conexao.search(configuracao.base_dn, configuracao.filtro_usuarios, attributes=atributos)
        total = 0
        User = get_user_model()
        for entrada in conexao.entries:
            def valor(nome):
                atributo = getattr(entrada, nome, None)
                return str(atributo.value or "").strip() if atributo else ""

            login = valor(configuracao.atributo_login)
            if not login:
                continue
            usuario = User.objects.filter(username__iexact=login).first()
            criado = usuario is None
            if criado:
                usuario = User(username=login.lower())
                usuario.set_unusable_password()
            usuario.first_name = valor(configuracao.atributo_nome)[:150]
            usuario.last_name = valor(configuracao.atributo_sobrenome)[:150]
            usuario.email = valor(configuracao.atributo_email)[:254]
            if configuracao.sincronizar_ativos:
                usuario.is_active = True
            usuario.save()
            total += 1
        conexao.unbind()
        return total


class BackupConfiguracaoView(LoginRequiredMixin, SuperuserRequiredMixin, TemplateView):
    template_name = "core/backup.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pasta = self._pasta_backups()

        arquivos = []
        for caminho in sorted(pasta.glob("*"), key=lambda item: item.stat().st_mtime, reverse=True):
            if not (caminho.name.lower().endswith(".zip") or caminho.name.lower().endswith(".zip.enc")):
                continue
            stat = caminho.stat()
            arquivos.append(
                {
                    "nome": caminho.name,
                    "tamanho_mb": stat.st_size / 1024 / 1024,
                    "modificado_em": datetime.fromtimestamp(stat.st_mtime),
                    "tipo": "SQLite/media",
                    "restauravel": True,
                }
            )

        context["backups"] = arquivos
        context["backups_sqlite"] = [item for item in arquivos if item["restauravel"]]
        context["configuracao_backup"] = ConfiguracaoBackup.atual()
        context["configuracao_backup_form"] = ConfiguracaoBackupForm(instance=context["configuracao_backup"])
        context["historico_backups"] = RegistroBackup.objects.all()[:50]
        return context

    def post(self, request, *args, **kwargs):
        acao = request.POST.get("acao")

        if acao == "apagar":
            return self._apagar_backup(request)

        if acao == "criar":
            call_command("backup_local")
            messages.success(request, "Backup criado com sucesso.")
            return redirect("core:backup")

        if acao == "salvar_configuracao":
            form = ConfiguracaoBackupForm(request.POST, instance=ConfiguracaoBackup.atual())
            if form.is_valid():
                configuracao = form.save(commit=False)
                if configuracao.ativo and not configuracao.proxima_execucao:
                    configuracao.proxima_execucao = timezone.now()
                configuracao.save()
                messages.success(request, "Agendamento de backup atualizado.")
            else:
                messages.error(request, "Revise a configuracao do backup.")
            return redirect("core:backup")

        if acao == "validar":
            caminho = self._resolver_backup_existente(request.POST.get("backup", ""), extensoes=(".zip", ".enc"))
            if not caminho:
                messages.error(request, "Backup nao encontrado.")
                return redirect("core:backup")
            temporario = None
            try:
                arquivo_zip, temporario = descriptografar_backup(caminho)
                validar_backup_zip(arquivo_zip)
                RegistroBackup.objects.create(
                    nome_arquivo=caminho.name,
                    status=RegistroBackup.Status.SUCESSO,
                    tamanho_bytes=caminho.stat().st_size,
                    sha256=sha256_arquivo(caminho),
                    destino=str(caminho),
                    mensagem="Validacao manual concluida.",
                    validado_em=timezone.now(),
                )
                messages.success(request, "Backup valido: ZIP, CRC e banco SQLite verificados.")
            except Exception as exc:
                RegistroBackup.objects.create(
                    nome_arquivo=caminho.name,
                    status=RegistroBackup.Status.INVALIDO,
                    destino=str(caminho),
                    mensagem=str(exc),
                )
                messages.error(request, f"Backup invalido: {exc}")
            finally:
                if temporario:
                    arquivo_zip.unlink(missing_ok=True)
            return redirect("core:backup")

        if acao == "restaurar":
            return self._restaurar_backup(request)

        messages.error(request, "Ação inválida.")
        return redirect("core:backup")

    def _pasta_backups(self):
        pasta = settings.BASE_DIR / "backups"
        pasta.mkdir(exist_ok=True)
        return pasta.resolve()

    def _resolver_backup_existente(self, nome, extensoes=(".zip",)):
        pasta = self._pasta_backups()
        caminho = (pasta / Path(nome).name).resolve()
        if not str(caminho).startswith(str(pasta)):
            return None
        if not any(caminho.name.lower().endswith(extensao) for extensao in extensoes):
            return None
        if not caminho.exists():
            return None
        return caminho

    def _salvar_upload_backup(self, arquivo):
        if not arquivo:
            return None
        nome_original = Path(arquivo.name).name
        if not (nome_original.lower().endswith(".zip") or nome_original.lower().endswith(".zip.enc")):
            raise CommandError("Envie um arquivo de backup .zip ou .zip.enc.")

        nome_limpo = sub(r"[^A-Za-z0-9_.-]", "_", nome_original)
        destino = self._pasta_backups() / f"restore_upload_{timezone.now():%Y%m%d_%H%M%S}_{nome_limpo}"
        with destino.open("wb") as saida:
            for parte in arquivo.chunks():
                saida.write(parte)
        return destino

    def _restaurar_backup(self, request):
        confirmacao = request.POST.get("confirmacao", "").strip()
        origem = request.POST.get("origem", "existente")

        if confirmacao != "RESTAURAR":
            messages.error(request, "Digite RESTAURAR para confirmar a restauração.")
            return redirect("core:backup")

        try:
            if origem == "upload":
                caminho = self._salvar_upload_backup(request.FILES.get("arquivo_backup"))
                if not caminho:
                    messages.error(request, "Selecione um arquivo .zip do seu computador.")
                    return redirect("core:backup")
            else:
                caminho = self._resolver_backup_existente(request.POST.get("backup", ""), extensoes=(".zip", ".enc"))
                if not caminho:
                    messages.error(request, "Backup inválido ou não encontrado.")
                    return redirect("core:backup")

            arquivo_zip, temporario = descriptografar_backup(caminho)
            validar_backup_zip(arquivo_zip)
            connections.close_all()
            call_command("restaurar_backup_local", str(arquivo_zip), confirmar=True)
            connections.close_all()
            if temporario:
                arquivo_zip.unlink(missing_ok=True)
        except CommandError as exc:
            messages.error(request, str(exc))
            return redirect("core:backup")

        return HttpResponse(
            """
            <!doctype html>
            <html lang="pt-br">
            <head>
              <meta charset="utf-8">
              <title>Backup restaurado</title>
              <style>
                body { font-family: Arial, sans-serif; background: #f4f7fb; color: #111827; padding: 40px; }
                .box { background: #fff; border: 1px solid #d9e2ec; border-radius: 8px; max-width: 720px; padding: 24px; }
                code { background: #eef2f7; border-radius: 4px; padding: 2px 5px; }
              </style>
            </head>
            <body>
              <div class="box">
                <h1>Backup restaurado com sucesso</h1>
                <p>A base SQLite e os arquivos de mídia foram restaurados.</p>
                <p><strong>Agora reinicie o servidor da aplicação</strong> antes de continuar usando o sistema.</p>
                <p>Se estiver usando o servidor local, pare com <code>Ctrl + C</code> e rode novamente <code>python manage.py runserver 0.0.0.0:8000</code>.</p>
              </div>
            </body>
            </html>
            """
        )

    def _apagar_backup(self, request):
        nome = request.POST.get("backup", "")
        confirmacao = request.POST.get("confirmacao_apagar", "").strip()
        if confirmacao != "APAGAR":
            messages.error(request, "Digite APAGAR para confirmar a exclusão do backup.")
            return redirect("core:backup")

        caminho = self._resolver_backup_existente(nome)
        if not caminho:
            messages.error(request, "Backup inválido ou não encontrado.")
            return redirect("core:backup")

        caminho.unlink()
        messages.success(request, f"Backup {caminho.name} apagado com sucesso.")
        return redirect("core:backup")


class AtualizacaoSistemaView(LoginRequiredMixin, SuperuserRequiredMixin, TemplateView):
    template_name = "core/atualizacoes.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["git_info"] = self._git_info()
        context["diagnostico_atualizacao"] = self._diagnostico(request=self.request)
        context["ultimo_resultado"] = self.request.session.pop("ultimo_resultado_atualizacao", "")
        context["deploy_info"] = self._deploy_info()
        context["comando_servidor"] = "cd /opt/sistema-chamados && bash scripts/deploy_linux.sh"
        return context

    def post(self, request, *args, **kwargs):
        acao = request.POST.get("acao")
        if acao == "verificar":
            return self._verificar(request)
        if acao == "atualizar":
            return self._atualizar(request)
        messages.error(request, "Ação inválida.")
        return redirect("core:atualizacoes")

    def _git_disponivel(self):
        return bool(shutil.which("git")) and (settings.BASE_DIR / ".git").exists()

    def _deploy_info(self):
        script = settings.BASE_DIR / "scripts" / "deploy_linux.sh"
        bash = shutil.which("bash")
        docker_compose = ""
        if shutil.which("docker"):
            codigo, _ = self._rodar(["docker", "compose", "version"], timeout=15)
            if codigo == 0:
                docker_compose = "docker compose"
        if not docker_compose and shutil.which("docker-compose"):
            docker_compose = "docker-compose"

        sistema_linux = platform.system().lower() == "linux"
        pode_usar_script = bool(sistema_linux and bash and script.exists() and docker_compose)
        return {
            "script": script,
            "script_existe": script.exists(),
            "bash": bash or "",
            "sistema_linux": sistema_linux,
            "docker_compose": docker_compose,
            "modo": "deploy_script" if pode_usar_script else "fallback",
            "pode_usar_script": pode_usar_script,
        }

    def _rodar(self, comando, timeout=120, env=None):
        try:
            resultado = subprocess.run(
                comando,
                cwd=settings.BASE_DIR,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=env,
            )
        except FileNotFoundError:
            return 127, f"Comando nao encontrado: {comando[0]}"
        except subprocess.TimeoutExpired as exc:
            saida_timeout = "\n".join(
                parte.decode("utf-8", "replace") if isinstance(parte, bytes) else str(parte)
                for parte in [exc.stdout, exc.stderr]
                if parte
            )
            return 124, f"Tempo limite excedido ao executar: {' '.join(comando)}\n{saida_timeout}".strip()
        except Exception as exc:
            return 1, str(exc)
        saida = "\n".join(
            parte.strip()
            for parte in [resultado.stdout, resultado.stderr]
            if parte and parte.strip()
        )
        return resultado.returncode, saida

    def _testar_url(self, url, timeout=5):
        try:
            requisicao = urllib.request.Request(url, headers={"User-Agent": "SistemaChamadosAtualizador/1.0"})
            with urllib.request.urlopen(requisicao, timeout=timeout) as resposta:
                return True, f"HTTP {resposta.status}"
        except Exception as exc:
            return False, str(exc)

    def _diagnostico(self, request):
        github_ok, github_msg = self._testar_url("https://github.com", timeout=5)
        host = request.get_host()
        origem = request.headers.get("Origin") or request.headers.get("Referer") or ""
        return {
            "host": host,
            "origem": origem,
            "allowed_hosts": ", ".join(settings.ALLOWED_HOSTS) or "-",
            "csrf_trusted_origins": ", ".join(settings.CSRF_TRUSTED_ORIGINS) or "-",
            "git_binario": shutil.which("git") or "",
            "git_pasta": (settings.BASE_DIR / ".git").exists(),
            "deploy_script": (settings.BASE_DIR / "scripts" / "deploy_linux.sh").exists(),
            "github_ok": github_ok,
            "github_msg": github_msg,
        }

    def _git_texto(self, *args):
        codigo, saida = self._rodar(["git", *args], timeout=30)
        return saida.strip() if codigo == 0 else ""

    def _git_info(self):
        if not self._git_disponivel():
            return {
                "disponivel": False,
                "mensagem": "Esta instalação não possui a pasta .git. Em Docker, atualize pelo terminal do servidor.",
            }

        branch = self._git_texto("branch", "--show-current") or "main"
        status = self._git_texto("status", "--short")
        atras = self._git_texto("rev-list", "--count", f"HEAD..origin/{branch}") or "0"
        return {
            "disponivel": True,
            "branch": branch,
            "commit": self._git_texto("rev-parse", "--short", "HEAD"),
            "commit_data": self._git_texto("log", "-1", "--format=%ci"),
            "remote": self._git_texto("remote", "get-url", "origin"),
            "status": status,
            "limpo": not bool(status),
            "atualizacoes_pendentes": atras,
        }

    def _verificar(self, request):
        if not self._git_disponivel():
            messages.error(request, "Esta instalação não pode verificar atualizações pela tela. Verifique se Git está instalado e se a pasta .git existe.")
            return redirect("core:atualizacoes")

        codigo, saida = self._rodar(["git", "fetch", "--prune"], timeout=120)
        request.session["ultimo_resultado_atualizacao"] = saida or "git fetch executado sem saída."
        if codigo == 0:
            messages.success(request, "Verificação concluída.")
        else:
            messages.error(request, "Não foi possível verificar atualizações.")
        return redirect("core:atualizacoes")

    def _atualizar(self, request):
        if request.POST.get("confirmacao", "").strip() != "ATUALIZAR":
            messages.error(request, "Digite ATUALIZAR para confirmar.")
            return redirect("core:atualizacoes")

        if not self._git_disponivel():
            messages.error(request, "Esta instalação não pode ser atualizada pela tela. Use o terminal do servidor.")
            return redirect("core:atualizacoes")

        info = self._git_info()
        if not info.get("limpo"):
            messages.error(request, "Existem alterações locais não commitadas. Atualização bloqueada para evitar perda de dados.")
            return redirect("core:atualizacoes")

        saidas = []
        try:
            if settings.DATABASES["default"]["ENGINE"].endswith("sqlite3"):
                call_command("backup_local")
                saidas.append("Backup local criado antes da atualizacao.")

            deploy_info = self._deploy_info()
            if deploy_info["pode_usar_script"]:
                comando = ["bash", "scripts/deploy_linux.sh"]
                ambiente = os.environ.copy()
                ambiente["PROJECT_DIR"] = str(settings.BASE_DIR)
                codigo, saida = self._rodar(comando, timeout=900, env=ambiente)
                saidas.append(f"$ {' '.join(comando)}\n{saida or '(sem saida)'}")
                request.session["ultimo_resultado_atualizacao"] = "\n\n".join(saidas)
                if codigo == 0:
                    messages.success(request, "Atualizacao concluida pelo script scripts/deploy_linux.sh.")
                else:
                    messages.error(request, "Atualizacao pelo script falhou. Veja o resultado na tela.")
                return redirect("core:atualizacoes")

            for comando in [
                ["git", "fetch", "--prune"],
                ["git", "pull", "--ff-only"],
            ]:
                codigo, saida = self._rodar(comando, timeout=180)
                saidas.append(f"$ {' '.join(comando)}\n{saida or '(sem saída)'}")
                if codigo != 0:
                    request.session["ultimo_resultado_atualizacao"] = "\n\n".join(saidas)
                    messages.error(request, "Atualização interrompida. Veja o resultado na tela.")
                    return redirect("core:atualizacoes")

            call_command("migrate", interactive=False)
            saidas.append("Migrations aplicadas.")
            call_command("collectstatic", interactive=False, verbosity=0)
            saidas.append("Arquivos estáticos coletados.")
        except Exception as exc:
            saidas.append(f"Erro: {exc}")
            request.session["ultimo_resultado_atualizacao"] = "\n\n".join(saidas)
            messages.error(request, "Atualização falhou.")
            return redirect("core:atualizacoes")

        request.session["ultimo_resultado_atualizacao"] = "\n\n".join(saidas)
        messages.success(request, "Atualização concluída. Reinicie o serviço se estiver em produção.")
        return redirect("core:atualizacoes")


class ControleServicosView(LoginRequiredMixin, SuperuserRequiredMixin, TemplateView):
    template_name = "core/controle_servicos.html"

    ACOES = {
        "reiniciar_servicos": {
            "titulo": "Reiniciar servicos",
            "confirmacao": "REINICIAR",
        },
        "parar_servicos": {
            "titulo": "Parar servicos",
            "confirmacao": "PARAR",
        },
        "reboot_servidor": {
            "titulo": "Reiniciar servidor",
            "confirmacao": "REBOOT",
            "power_action": True,
        },
        "desligar_servidor": {
            "titulo": "Desligar servidor",
            "confirmacao": "DESLIGAR",
            "power_action": True,
        },
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["acoes"] = self.ACOES
        context["ultimo_resultado"] = self.request.session.pop("ultimo_resultado_servicos", "")
        context["power_actions_habilitadas"] = self._power_actions_habilitadas()
        context["docker_disponivel"] = bool(self._docker_compose_command("ps"))
        context["reinicio_interno"] = self._reinicio_interno_disponivel()
        context["reinicio_disponivel"] = context["docker_disponivel"] or context["reinicio_interno"]
        return context

    def post(self, request, *args, **kwargs):
        acao_id = request.POST.get("acao", "")
        acao = self.ACOES.get(acao_id)
        if not acao:
            messages.error(request, "Acao invalida.")
            return redirect("core:servicos")

        if request.POST.get("confirmacao", "").strip().upper() != acao["confirmacao"]:
            messages.error(request, f"Digite {acao['confirmacao']} para confirmar.")
            return redirect("core:servicos")

        if acao.get("power_action") and not self._power_actions_habilitadas():
            messages.error(
                request,
                "Reboot/desligamento do servidor esta bloqueado. Defina ALLOW_SERVER_POWER_ACTIONS=True no .env para habilitar.",
            )
            return redirect("core:servicos")

        if acao_id == "reiniciar_servicos" and self._reinicio_interno_disponivel():
            agendado, erro = self._agendar_reinicio_container()
            if not agendado:
                messages.error(request, f"Nao foi possivel agendar o reinicio: {erro}")
                return redirect("core:servicos")
            request.session["ultimo_resultado_servicos"] = (
                "Reinicio interno do container agendado. A aplicacao voltara em alguns segundos."
            )
            messages.success(request, "Reinicio da aplicacao agendado com sucesso.")
            return redirect("core:servicos")

        comando = self._comando_para_acao(acao_id)
        if not comando:
            messages.error(request, "Nao foi possivel encontrar um comando compativel neste ambiente.")
            return redirect("core:servicos")

        codigo, saida = self._rodar(comando, timeout=60)
        request.session["ultimo_resultado_servicos"] = f"$ {' '.join(comando)}\n{saida or '(sem saida)'}"
        if codigo == 0:
            messages.success(request, f"{acao['titulo']} solicitado com sucesso.")
        else:
            messages.error(request, f"{acao['titulo']} falhou. Veja o resultado na tela.")
        return redirect("core:servicos")

    def _power_actions_habilitadas(self):
        return os.getenv("ALLOW_SERVER_POWER_ACTIONS", "False").lower() in {"1", "true", "yes", "on"}

    def _docker_compose_command(self, subcomando):
        if shutil.which("docker"):
            return ["docker", "compose", subcomando]
        if shutil.which("docker-compose"):
            return ["docker-compose", subcomando]
        return None

    def _reinicio_interno_disponivel(self):
        return platform.system().lower() == "linux" and Path("/.dockerenv").exists()

    def _agendar_reinicio_container(self):
        codigo = "import os, signal, time; time.sleep(3); os.kill(1, signal.SIGTERM)"
        try:
            subprocess.Popen(
                [sys.executable, "-c", codigo],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                start_new_session=True,
            )
        except Exception as exc:
            return False, str(exc)
        return True, ""

    def _comando_para_acao(self, acao_id):
        if acao_id in {"reiniciar_servicos", "parar_servicos"}:
            subcomando = "restart" if acao_id == "reiniciar_servicos" else "down"
            return self._docker_compose_command(subcomando)

        sistema = platform.system().lower()
        if acao_id == "reboot_servidor":
            return ["shutdown", "/r", "/t", "5"] if sistema == "windows" else ["sudo", "systemctl", "reboot"]
        if acao_id == "desligar_servidor":
            return ["shutdown", "/s", "/t", "5"] if sistema == "windows" else ["sudo", "systemctl", "poweroff"]
        return None

    def _rodar(self, comando, timeout=60):
        try:
            resultado = subprocess.run(
                comando,
                cwd=settings.BASE_DIR,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except Exception as exc:
            return 1, str(exc)

        saida = "\n".join(
            parte.strip()
            for parte in [resultado.stdout, resultado.stderr]
            if parte and parte.strip()
        )
        return resultado.returncode, saida


@login_required
@user_passes_test(lambda user: user.is_superuser)
def baixar_backup(request, nome):
    pasta = (settings.BASE_DIR / "backups").resolve()
    caminho = (pasta / Path(nome).name).resolve()
    if not str(caminho).startswith(str(pasta)) or not (
        caminho.name.lower().endswith(".zip") or caminho.name.lower().endswith(".zip.enc")
    ):
        raise Http404("Backup não encontrado.")
    if not caminho.exists():
        raise Http404("Backup não encontrado.")
    return FileResponse(caminho.open("rb"), as_attachment=True, filename=caminho.name)
