from pathlib import Path
import textwrap

from django.conf import settings


def pdf_escape(texto):
    return str(texto).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def montar_stream_pagina(linhas):
    comandos = ["BT", "/F1 10 Tf", "45 800 Td", "13 TL"]
    for linha in linhas:
        comandos.append(f"({pdf_escape(linha)}) Tj")
        comandos.append("T*")
    comandos.append("ET")
    return "\n".join(comandos).encode("latin-1", "replace")


def montar_pdf(linhas):
    paginas = [linhas[indice : indice + 58] for indice in range(0, len(linhas), 58)] or [[]]
    primeira_pagina_id = 4
    primeira_stream_id = primeira_pagina_id + len(paginas)
    kids = [f"{primeira_pagina_id + indice} 0 R" for indice in range(len(paginas))]
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(paginas)} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for indice in range(len(paginas)):
        stream_id = primeira_stream_id + indice
        objetos.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {stream_id} 0 R >>".encode()
        )
    for pagina in paginas:
        stream = montar_stream_pagina(pagina)
        objetos.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for indice, objeto in enumerate(objetos, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{indice} 0 obj\n".encode())
        pdf.extend(objeto)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer << /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(pdf)


def quebrar(label, valor):
    linhas = []
    texto = str(valor or "-")
    for parte in textwrap.wrap(texto, width=88) or ["-"]:
        prefixo = f"{label}: " if not linhas else " " * (len(label) + 2)
        linhas.append(prefixo + parte)
    return linhas


def gerar_documento_solicitacao(solicitacao):
    destino = Path(settings.GOVERNANCA_DOCUMENT_ROOT)
    destino.mkdir(parents=True, exist_ok=True)
    nome_arquivo = f"{solicitacao.protocolo}.pdf"
    caminho = destino / nome_arquivo

    linhas = [
        "SOLICITACAO DE GOVERNANCA DE ACESSO",
        f"Protocolo: {solicitacao.protocolo}",
        f"Tipo: {solicitacao.get_tipo_display()}",
        f"Data: {solicitacao.criado_em:%d/%m/%Y %H:%M}",
        "",
        "DADOS DO SOLICITANTE",
    ]
    for label, valor in [
        ("Matricula", solicitacao.matricula),
        ("Nome", solicitacao.nome),
        ("E-mail", solicitacao.email),
        ("Setor", solicitacao.setor),
        ("Cargo", solicitacao.cargo),
        ("Telefone", solicitacao.telefone),
    ]:
        linhas.extend(quebrar(label, valor))

    linhas.extend(["", "SOLICITACAO"])
    if solicitacao.tipo_solicitacao_rede:
        linhas.extend(quebrar("Tipo", solicitacao.get_tipo_solicitacao_rede_display()))
    if solicitacao.usuario_rede_existente:
        linhas.extend(quebrar("Usuario existente", solicitacao.usuario_rede_existente))
    if solicitacao.chefia_imediata:
        linhas.extend(quebrar("Chefia/autorizador", solicitacao.chefia_imediata))
    if solicitacao.acessos_solicitados:
        linhas.extend(quebrar("Acessos", solicitacao.acessos_solicitados))
    if solicitacao.aparelhos:
        linhas.extend(quebrar("Aparelhos", solicitacao.aparelhos))
    linhas.extend(quebrar("Justificativa", solicitacao.justificativa))

    linhas.extend(
        [
            "",
            "TERMO DE CIENCIA",
            f"Versao: {solicitacao.termo_versao or '-'}",
            f"Aceito em: {solicitacao.termo_aceito_em:%d/%m/%Y %H:%M:%S}" if solicitacao.termo_aceito_em else "Aceito em: -",
            f"IP do aceite: {solicitacao.termo_aceito_ip or '-'}",
            f"User-agent: {solicitacao.termo_aceito_user_agent or '-'}",
            "",
            f"Ciencia registrada: {'SIM' if solicitacao.termo_ciencia else 'NAO'}",
            "",
        ]
    )
    for paragrafo in (solicitacao.termo_texto_aceito or "").splitlines():
        linhas.extend(textwrap.wrap(paragrafo, width=88) or [""])

    caminho.write_bytes(montar_pdf(linhas))
    return str(caminho)
