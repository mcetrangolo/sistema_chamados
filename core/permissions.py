from django.contrib.auth.models import Group


GRUPO_ADMIN = "Administradores"
GRUPO_SUPORTE_N2 = "Suporte N2"
GRUPO_SUPORTE_N1 = "Suporte N1"
GRUPO_TECNICOS = "Técnicos de TI"

PAPEL_ADMIN = "admin"
PAPEL_N2 = "n2"
PAPEL_N1 = "n1"
PAPEL_USUARIO = "usuario"

PAPEIS = [
    (PAPEL_ADMIN, "Administrador"),
    (PAPEL_N2, "Suporte N2"),
    (PAPEL_N1, "Suporte N1"),
    (PAPEL_USUARIO, "Usuário comum"),
]

DESCRICAO_PAPEIS = {
    PAPEL_ADMIN: "Acesso total ao sistema, permissões, configurações, backup, atualizações e todos os módulos.",
    PAPEL_N2: "Acesso a chamados, inventário, documentação, governança, contratos e relatórios; sem gestão do sistema.",
    PAPEL_N1: "Acesso operacional aos chamados, filas, respostas e base de conhecimento.",
    PAPEL_USUARIO: "Acesso básico ao próprio perfil e chamados internos permitidos.",
}


def usuario_em_grupo(usuario, nome):
    return bool(usuario and usuario.is_authenticated and usuario.groups.filter(name=nome).exists())


def usuario_e_admin(usuario):
    if not usuario or not usuario.is_authenticated:
        return False
    return usuario.is_superuser or usuario_em_grupo(usuario, GRUPO_ADMIN)


def usuario_e_suporte_n2(usuario):
    return usuario_e_admin(usuario) or usuario_em_grupo(usuario, GRUPO_SUPORTE_N2)


def usuario_e_suporte_n1(usuario):
    return usuario_e_suporte_n2(usuario) or usuario_em_grupo(usuario, GRUPO_SUPORTE_N1) or usuario_em_grupo(usuario, GRUPO_TECNICOS)


def pode_acessar_chamados(usuario):
    return bool(usuario and usuario.is_authenticated)


def pode_acessar_inventario(usuario):
    return usuario_e_suporte_n2(usuario)


def pode_acessar_sistema(usuario):
    return usuario_e_admin(usuario)


def papel_usuario(usuario):
    if usuario_e_admin(usuario):
        return PAPEL_ADMIN
    if usuario_em_grupo(usuario, GRUPO_SUPORTE_N2):
        return PAPEL_N2
    if usuario_em_grupo(usuario, GRUPO_SUPORTE_N1) or usuario_em_grupo(usuario, GRUPO_TECNICOS):
        return PAPEL_N1
    return PAPEL_USUARIO


def aplicar_papel(usuario, papel):
    grupos = {
        nome: Group.objects.get_or_create(name=nome)[0]
        for nome in [GRUPO_ADMIN, GRUPO_SUPORTE_N2, GRUPO_SUPORTE_N1, GRUPO_TECNICOS]
    }
    usuario.groups.remove(*grupos.values())
    usuario.is_staff = False
    usuario.is_superuser = False

    if papel == PAPEL_ADMIN:
        usuario.groups.add(grupos[GRUPO_ADMIN], grupos[GRUPO_TECNICOS])
        usuario.is_staff = True
        usuario.is_superuser = True
    elif papel == PAPEL_N2:
        usuario.groups.add(grupos[GRUPO_SUPORTE_N2], grupos[GRUPO_TECNICOS])
    elif papel == PAPEL_N1:
        usuario.groups.add(grupos[GRUPO_SUPORTE_N1], grupos[GRUPO_TECNICOS])

    return usuario
