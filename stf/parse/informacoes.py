"""Parser de abaInformacoes.asp?incidente=N."""

from __future__ import annotations

from dataclasses import dataclass, field

from ._util import clean, data_iso, text_of, tree


@dataclass
class Informacoes:
    assuntos: list[str] = field(default_factory=list)
    data_protocolo: str | None = None       # ISO
    orgao_origem: str | None = None
    origem: str | None = None
    numeros_origem: list[str] = field(default_factory=list)
    descricao_procedencia: str | None = None
    volumes: int | None = None
    folhas: int | None = None


def _pares_rotulo_valor(t) -> dict[str, str]:
    """Os campos vêm como sequência de divs irmãs: rótulo (processo-detalhes-bold,
    terminado em ':') seguido do valor. Monta o dicionário pela ordem."""
    pares: dict[str, str] = {}
    rotulo: str | None = None
    for d in t.css(".processo-informacoes div"):
        txt = clean(d.text())
        if not txt:
            continue
        # só folhas: ignora contêineres (cujo texto é a concatenação dos filhos).
        # selectolax: node.css() inclui o próprio nó, por isso olha os filhos diretos.
        if any(c.tag == "div" for c in d.iter()):
            continue
        if txt.endswith(":"):
            rotulo = txt[:-1]
        elif rotulo is not None:
            pares[rotulo] = txt
            rotulo = None
    return pares


def _int_ou_none(txt: str) -> int | None:
    txt = clean(txt)
    return int(txt) if txt.isdigit() else None


def parse_informacoes(raw: bytes) -> Informacoes:
    t = tree(raw)
    pares = _pares_rotulo_valor(t)
    numeros = [clean(n) for n in pares.get("Número de Origem", "").split(",")]
    numeros = [n for n in numeros if n]
    dp = pares.get("Data de Protocolo")

    quadros = {}
    for q in t.css(".processo-quadro"):
        quadros[text_of(q.css_first(".rotulo"))] = text_of(q.css_first(".numero"))

    return Informacoes(
        assuntos=[clean(li.text()) for li in t.css(".informacoes__assunto li") if clean(li.text())],
        data_protocolo=data_iso(dp) if dp else None,
        orgao_origem=pares.get("Órgão de Origem"),
        origem=pares.get("Origem"),
        numeros_origem=numeros,
        descricao_procedencia=text_of(t.css_first("#descricao-procedencia")) or None,
        volumes=_int_ou_none(quadros.get("Volumes", "")),
        folhas=_int_ou_none(quadros.get("Folhas", "")),
    )
