from django import template
from django.utils import timezone


register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def prioridade_badge(prioridade):
    return {
        "baixa": "text-bg-secondary",
        "media": "text-bg-info",
        "alta": "text-bg-warning",
        "critica": "text-bg-danger",
    }.get(prioridade, "text-bg-light")


@register.filter
def status_badge(status):
    return {
        "aberto": "text-bg-primary",
        "em_analise": "text-bg-info",
        "em_atendimento": "text-bg-warning",
        "aguardando_aprovacao": "text-bg-warning",
        "aguardando_usuario": "text-bg-secondary",
        "aguardando_fornecedor": "text-bg-secondary",
        "resolvido": "text-bg-success",
        "encerrado": "text-bg-dark",
        "cancelado": "text-bg-light",
    }.get(status, "text-bg-light")


@register.filter
def sla_estado(chamado):
    if not chamado.vencimento_em:
        return "Sem SLA"
    if chamado.status in {"resolvido", "encerrado", "cancelado"}:
        return "Concluido"
    if chamado.sla_pausado_em:
        return "Pausado"
    agora = timezone.now()
    if chamado.vencimento_em < agora:
        return "Vencido"
    if chamado.vencimento_em <= agora + timezone.timedelta(hours=4):
        return "A vencer"
    return "No prazo"


@register.filter
def sla_badge(chamado):
    return {
        "Sem SLA": "text-bg-light",
        "Concluido": "text-bg-success",
        "Pausado": "text-bg-secondary",
        "Vencido": "text-bg-danger",
        "A vencer": "text-bg-warning",
        "No prazo": "text-bg-success",
    }.get(sla_estado(chamado), "text-bg-light")
