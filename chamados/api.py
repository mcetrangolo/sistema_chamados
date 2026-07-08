from django.db.models import Q
from django.views.decorators.http import require_http_methods

from core.api import api_error, api_success, json_body
from core.audit import registrar_evento
from core.models import RegistroAuditoria
from core.permissions import usuario_e_suporte_n1, usuario_e_suporte_n2

from .models import Categoria, Chamado, Setor
from .services import registrar_chamado_aberto


def _exigir_suporte(request):
    if not request.user.is_authenticated:
        return api_error("AUTH_REQUIRED", "Autenticacao obrigatoria.", status=401)
    if not usuario_e_suporte_n1(request.user):
        return api_error("FORBIDDEN", "Perfil sem permissao para acessar chamados via API.", status=403)
    return None


def chamado_payload(chamado):
    return {
        "id": chamado.pk,
        "numero": chamado.numero,
        "titulo": chamado.descricao[:80],
        "descricao": chamado.descricao,
        "solicitante": chamado.nome_solicitante,
        "email": chamado.email,
        "telefone": chamado.telefone,
        "setor": chamado.setor.nome if chamado.setor_id else "",
        "categoria": chamado.categoria.nome if chamado.categoria_id else "",
        "tipo": chamado.tipo,
        "prioridade": chamado.prioridade,
        "status": chamado.status,
        "tecnico": (
            chamado.tecnico_responsavel.get_full_name()
            or chamado.tecnico_responsavel.username
            if chamado.tecnico_responsavel_id
            else ""
        ),
        "ativo_id": chamado.ativo_rede_id,
        "criado_em": chamado.criado_em.isoformat() if chamado.criado_em else None,
        "atualizado_em": chamado.atualizado_em.isoformat() if chamado.atualizado_em else None,
        "encerrado_em": chamado.concluido_em.isoformat() if chamado.concluido_em else None,
    }


def filtrar_chamados_visiveis_api(usuario, queryset):
    if usuario_e_suporte_n2(usuario):
        return queryset
    return queryset.exclude(numero__startswith="GOV-")


@require_http_methods(["GET", "POST"])
def chamados_collection(request):
    erro = _exigir_suporte(request)
    if erro:
        return erro

    if request.method == "POST":
        return criar_chamado_api(request)

    chamados = Chamado.objects.select_related(
        "setor", "categoria", "tecnico_responsavel"
    ).order_by("-criado_em")
    chamados = filtrar_chamados_visiveis_api(request.user, chamados)
    q = request.GET.get("q", "").strip()
    if q:
        chamados = chamados.filter(
            Q(numero__icontains=q)
            | Q(nome_solicitante__icontains=q)
            | Q(email__icontains=q)
            | Q(descricao__icontains=q)
        )
    if request.GET.get("status"):
        chamados = chamados.filter(status=request.GET["status"])
    if request.GET.get("prioridade"):
        chamados = chamados.filter(prioridade=request.GET["prioridade"])
    limite = min(int(request.GET.get("limit", "50") or 50), 200)
    dados = [chamado_payload(chamado) for chamado in chamados[:limite]]
    registrar_evento(
        RegistroAuditoria.Acao.API,
        "Chamado",
        objeto=f"Listagem API ({len(dados)} itens)",
        usuario=request.user,
        caminho=request.path,
    )
    return api_success(dados, count=len(dados))


def criar_chamado_api(request):
    dados = json_body(request)
    if dados is None:
        return api_error("INVALID_JSON", "JSON invalido.", status=400)

    obrigatorios = ["nome_solicitante", "setor_id", "categoria_id", "descricao"]
    faltantes = [campo for campo in obrigatorios if not dados.get(campo)]
    if faltantes:
        return api_error(
            "VALIDATION_ERROR",
            "Campos obrigatorios nao informados.",
            status=400,
            details={"fields": faltantes},
        )

    try:
        setor = Setor.objects.get(pk=dados["setor_id"])
        categoria = Categoria.objects.get(pk=dados["categoria_id"])
    except (Setor.DoesNotExist, Categoria.DoesNotExist):
        return api_error("VALIDATION_ERROR", "Setor ou categoria invalido.", status=400)

    chamado = Chamado.objects.create(
        nome_solicitante=str(dados["nome_solicitante"])[:150],
        email=str(dados.get("email", ""))[:254],
        telefone=str(dados.get("telefone", ""))[:40],
        setor=setor,
        categoria=categoria,
        descricao=str(dados["descricao"]),
        tipo=dados.get("tipo") or Chamado.Tipo.INCIDENTE,
        prioridade=dados.get("prioridade") or Chamado.Prioridade.MEDIA,
        origem=Chamado.Origem.INTERNO,
        solicitante=request.user,
    )
    registrar_chamado_aberto(chamado, request.user, "Chamado aberto pela API interna.")
    registrar_evento(
        RegistroAuditoria.Acao.API,
        "Chamado",
        objeto=f"Criacao API {chamado.numero}",
        usuario=request.user,
        objeto_id=chamado.pk,
        caminho=request.path,
    )
    return api_success(chamado_payload(chamado), status=201)


@require_http_methods(["GET"])
def chamado_detail(request, pk):
    erro = _exigir_suporte(request)
    if erro:
        return erro
    try:
        chamado = filtrar_chamados_visiveis_api(
            request.user,
            Chamado.objects.select_related(
            "setor", "categoria", "tecnico_responsavel"
            ),
        ).get(pk=pk)
    except Chamado.DoesNotExist:
        return api_error("NOT_FOUND", "Chamado nao encontrado.", status=404)
    return api_success(chamado_payload(chamado))
