"""Parser de abaDeslocamentos.asp?incidente=N."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ._util import clean, data_iso, text_of, tree

_ENVIADO_RE = re.compile(r"Enviado por\s+(.+?)\s+em\s+(\d{2}/\d{2}/\d{4})")
_GUIA_RE = re.compile(r"Guia\s+(\S+)")
_RECEBIDO_RE = re.compile(r"Recebido em\s+(\d{2}/\d{2}/\d{4})")


@dataclass
class Deslocamento:
    posicao: int
    destino: str
    enviado_por: str | None
    data_envio: str | None
    guia: str | None
    recebido_em: str | None


def parse_deslocamentos(raw: bytes) -> list[Deslocamento]:
    if not raw.strip():
        return []
    t = tree(raw)
    out: list[Deslocamento] = []
    for pos, row in enumerate(t.css(".lista-dados")):
        # o ícone <i class="processo-detalhes-bold fas ..."> também carrega a classe; só o span tem texto
        destino = text_of(row.css_first("span.processo-detalhes-bold"))
        enviado_por = data_envio = guia = recebido = None
        for s in row.css(".processo-detalhes"):
            txt = clean(s.text())
            if (m := _ENVIADO_RE.search(txt)):
                enviado_por, data_envio = clean(m.group(1)), data_iso(m.group(2))
            elif (m := _GUIA_RE.search(txt)):
                guia = m.group(1)
            elif (m := _RECEBIDO_RE.search(txt)):
                recebido = data_iso(m.group(1))
        out.append(Deslocamento(
            posicao=pos, destino=destino, enviado_por=enviado_por,
            data_envio=data_envio, guia=guia, recebido_em=recebido,
        ))
    return out
