from django.db.models import Q
from django.views.decorators.http import require_http_methods

from core.api import api_error, api_success
from core.audit import registrar_evento
from core.models import RegistroAuditoria
from core.permissions import usuario_e_suporte_n2

from .models import AtivoRede


def _exigir_inventario(request):
    if not request.user.is_authenticated:
        return api_error("AUTH_REQUIRED", "Autenticacao obrigatoria.", status=401)
    if not usuario_e_suporte_n2(request.user):
        return api_error("FORBIDDEN", "Perfil sem permissao para acessar inventario via API.", status=403)
    return None


def ativo_payload(ativo):
    return {
        "id": ativo.pk,
        "nome": ativo.nome,
        "tipo": ativo.tipo.nome if ativo.tipo_id else "",
        "setor": ativo.setor.nome if ativo.setor_id else "",
        "hostname": ativo.hostname,
        "ip": str(ativo.ip or ""),
        "mac": ativo.mac,
        "fabricante": ativo.fabricante,
        "modelo": ativo.modelo,
        "numero_serie": ativo.numero_serie,
        "patrimonio": ativo.patrimonio,
        "sistema_operacional": ativo.sistema_operacional,
        "usuario_logado": ativo.usuario_logado,
        "status": ativo.status,
        "ciclo_vida": ativo.ciclo_vida,
        "origem": ativo.origem,
        "ultima_coleta_em": ativo.ultima_coleta_em.isoformat() if ativo.ultima_coleta_em else None,
        "atualizado_em": ativo.atualizado_em.isoformat() if ativo.atualizado_em else None,
    }


@require_http_methods(["GET"])
def ativos_collection(request):
    erro = _exigir_inventario(request)
    if erro:
        return erro

    ativos = AtivoRede.objects.select_related("tipo", "setor").order_by("nome")
    q = request.GET.get("q", "").strip()
    if q:
        ativos = ativos.filter(
            Q(nome__icontains=q)
            | Q(hostname__icontains=q)
            | Q(ip__icontains=q)
            | Q(mac__icontains=q)
            | Q(numero_serie__icontains=q)
            | Q(patrimonio__icontains=q)
        )
    if request.GET.get("status"):
        ativos = ativos.filter(status=request.GET["status"])
    if request.GET.get("tipo_id"):
        ativos = ativos.filter(tipo_id=request.GET["tipo_id"])
    limite = min(int(request.GET.get("limit", "50") or 50), 200)
    dados = [ativo_payload(ativo) for ativo in ativos[:limite]]
    registrar_evento(
        RegistroAuditoria.Acao.API,
        "AtivoRede",
        objeto=f"Listagem API ({len(dados)} itens)",
        usuario=request.user,
        caminho=request.path,
    )
    return api_success(dados, count=len(dados))


@require_http_methods(["GET"])
def ativo_detail(request, pk):
    erro = _exigir_inventario(request)
    if erro:
        return erro
    try:
        ativo = AtivoRede.objects.select_related("tipo", "setor").get(pk=pk)
    except AtivoRede.DoesNotExist:
        return api_error("NOT_FOUND", "Ativo nao encontrado.", status=404)
    return api_success(ativo_payload(ativo))
