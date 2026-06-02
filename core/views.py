from datetime import datetime
from pathlib import Path
from re import sub

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connections
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView, UpdateView

from .forms import ConfiguracaoInstitucionalForm
from .models import ConfiguracaoInstitucional


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


class BackupConfiguracaoView(LoginRequiredMixin, TemplateView):
    template_name = "core/backup.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pasta = self._pasta_backups()

        arquivos = []
        for caminho in sorted(pasta.glob("*"), key=lambda item: item.stat().st_mtime, reverse=True):
            if caminho.suffix.lower() not in {".zip", ".dump"}:
                continue
            stat = caminho.stat()
            arquivos.append(
                {
                    "nome": caminho.name,
                    "tamanho_mb": stat.st_size / 1024 / 1024,
                    "modificado_em": datetime.fromtimestamp(stat.st_mtime),
                    "tipo": "SQLite/media" if caminho.suffix.lower() == ".zip" else "PostgreSQL",
                    "restauravel": caminho.suffix.lower() == ".zip",
                }
            )

        context["backups"] = arquivos
        context["backups_sqlite"] = [item for item in arquivos if item["restauravel"]]
        context["usa_sqlite"] = settings.DATABASES["default"]["ENGINE"].endswith("sqlite3")
        return context

    def post(self, request, *args, **kwargs):
        acao = request.POST.get("acao")

        if acao == "apagar":
            return self._apagar_backup(request)

        if not settings.DATABASES["default"]["ENGINE"].endswith("sqlite3"):
            messages.error(
                request,
                "Backup e restauração pela interface estão disponíveis apenas para SQLite. Em PostgreSQL, use os scripts Docker.",
            )
            return redirect("core:backup")

        if acao == "criar":
            call_command("backup_local")
            messages.success(request, "Backup criado com sucesso.")
            return redirect("core:backup")

        if acao == "restaurar":
            return self._restaurar_backup(request)

        messages.error(request, "Ação inválida.")
        return redirect("core:backup")

    def _pasta_backups(self):
        pasta = settings.BASE_DIR / "backups"
        pasta.mkdir(exist_ok=True)
        return pasta.resolve()

    def _resolver_backup_existente(self, nome, extensoes=(".zip", ".dump")):
        pasta = self._pasta_backups()
        caminho = (pasta / Path(nome).name).resolve()
        if not str(caminho).startswith(str(pasta)):
            return None
        if caminho.suffix.lower() not in extensoes:
            return None
        if not caminho.exists():
            return None
        return caminho

    def _salvar_upload_backup(self, arquivo):
        if not arquivo:
            return None
        nome_original = Path(arquivo.name).name
        if not nome_original.lower().endswith(".zip"):
            raise CommandError("Envie um arquivo de backup .zip.")

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
                caminho = self._resolver_backup_existente(request.POST.get("backup", ""), extensoes=(".zip",))
                if not caminho:
                    messages.error(request, "Backup inválido ou não encontrado.")
                    return redirect("core:backup")

            connections.close_all()
            call_command("restaurar_backup_local", str(caminho), confirmar=True)
            connections.close_all()
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


@login_required
def baixar_backup(request, nome):
    pasta = (settings.BASE_DIR / "backups").resolve()
    caminho = (pasta / Path(nome).name).resolve()
    if not str(caminho).startswith(str(pasta)) or caminho.suffix.lower() not in {".zip", ".dump"}:
        raise Http404("Backup não encontrado.")
    if not caminho.exists():
        raise Http404("Backup não encontrado.")
    return FileResponse(caminho.open("rb"), as_attachment=True, filename=caminho.name)
