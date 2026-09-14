"""Parser de abaAndamentos.asp, abaDecisoes.asp, abaPautas.asp e abaRecursos.asp.

As quatro abas usam a mesma estrutura `.andamento-item`. A aba Decisões é um
subconjunto exato da aba Andamentos (verificado na Fase 0: 27/27).

Ordem: o portal exibe do mais recente (posição 0) ao mais antigo. Não existe
campo de ordem no HTML; `posicao` é a posição na lista servida.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urljoin, urlparse

from ._util import clean, data_iso, text_of, tree

BASE_PROCESSOS = "https://portal.stf.jus.br/processos/"

_ENDPOINT_RE = re.compile(r"^(?P<endpoint>[A-Za-z]+)\.asp$")
_FORMATO_POR_EXT = {".pdf": "pdf", "pdf": "pdf", "rtf": "rtf", ".rtf": "rtf"}


@dataclass(frozen=True)
class LinkDocumento:
    rotulo: str
    endpoint: str      # downloadPeca | downloadTexto | <outro>
    id_portal: str
    formato: str       # pdf | rtf | <ext literal>
    url: str           # absoluta


@dataclass
class Andamento:
    posicao: int
    data: str          # ISO
    tipo: str
    descricao: str
    documentos: list[LinkDocumento] = field(default_factory=list)
    explicacao_portal: str | None = None


def _link(a) -> LinkDocumento:
    href = a.attributes.get("href", "")
    url = urljoin(BASE_PROCESSOS, href)
    p = urlparse(url)
    m = _ENDPOINT_RE.match(p.path.rsplit("/", 1)[-1])
    endpoint = m.group("endpoint") if m else p.path
    q = {k: v[0] for k, v in parse_qs(p.query).items()}
    ext = q.get("ext", "")
    return LinkDocumento(
        rotulo=clean(a.text()), endpoint=endpoint, id_portal=q.get("id", ""),
        formato=_FORMATO_POR_EXT.get(ext.lower(), ext.lower().lstrip(".")), url=url,
    )


def parse_andamentos(raw: bytes) -> list[Andamento]:
    if not raw.strip():
        return []
    t = tree(raw)
    out: list[Andamento] = []
    for pos, item in enumerate(t.css(".andamento-item")):
        data = text_of(item.css_first(".andamento-data"))
        tipo = text_of(item.css_first(".andamento-nome"))
        desc = text_of(item.css_first(".col-md-9.p-0"))
        docs = [_link(a) for a in item.css(".andamento-docs a[href]")]
        hint = text_of(item.css_first(".hint-msg")) or None
        out.append(Andamento(
            posicao=pos, data=data_iso(data), tipo=tipo, descricao=desc,
            documentos=docs, explicacao_portal=hint,
        ))
    return out
