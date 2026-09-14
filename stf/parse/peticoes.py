"""Parser de abaPeticoes.asp?incidente=N."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ._util import clean, data_iso, datahora_iso, text_of, tree

_PETICIONADO_RE = re.compile(r"Peticionado em\s+(\d{2}/\d{2}/\d{4})")
_RECEBIDO_RE = re.compile(r"Recebido em\s+(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})\s+por\s+(.+)$")


@dataclass
class Peticao:
    posicao: int
    numero: str                    # "114945/2026"
    data_peticionamento: str | None
    recebido_em: str | None        # ISO datetime
    recebido_por: str | None


def parse_peticoes(raw: bytes) -> list[Peticao]:
    if not raw.strip():
        return []
    t = tree(raw)
    out: list[Peticao] = []
    for pos, row in enumerate(t.css(".lista-dados")):
        numero = text_of(row.css_first(".processo-detalhes-bold"))
        detalhes = [clean(s.text()) for s in row.css(".processo-detalhes")]
        pet = rec = None
        for d in detalhes:
            if (m := _PETICIONADO_RE.search(d)):
                pet = data_iso(m.group(1))
            if (m := _RECEBIDO_RE.search(d)):
                rec = (datahora_iso(m.group(1)), clean(m.group(2)))
        out.append(Peticao(
            posicao=pos, numero=numero, data_peticionamento=pet,
            recebido_em=rec[0] if rec else None, recebido_por=rec[1] if rec else None,
        ))
    return out
