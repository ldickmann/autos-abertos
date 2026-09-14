"""Parser da casca: verImpressao.asp?imprimir=true&incidente=N.

A casca traz o cabeçalho do processo e o script que carrega as nove abas.
Não traz andamentos, partes nem documentos.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ._util import clean, text_of, tree


class CascaInvalida(ValueError):
    """HTML sem os marcadores mínimos de uma página de processo."""


@dataclass
class Casca:
    incidente: int
    classe: str
    numero_processo: int
    numero_unico: str | None
    relator: str | None
    relator_ultimo_incidente: str | None
    ultimo_incidente: str | None      # ex.: "Pet-AgR-quarto"
    publicidade: str | None           # literal do portal: "Público" | "Sigiloso"
    natureza: str | None              # ex.: "Criminal"
    reu_preso: bool
    tipo_tramitacao: str | None       # ex.: "Processo Eletrônico"
    meio: str | None                  # input#meio: "E" (eletrônico) | "F" (físico)
    peca: str | None                  # input#peca
    abas: dict[str, str] = field(default_factory=dict)  # nome → URL relativa

    @property
    def abas_ordem(self) -> list[str]:
        return list(self.abas)


_ABA_RE = re.compile(
    r"""(?:\$\.get\(|\.load\()\s*['"](?P<url>aba(?P<nome>[A-Za-z]+)\.asp\?[^'"]*)['"]"""
)
_ABA_NOMES = {
    "Partes": "partes", "Andamentos": "andamentos", "Informacoes": "informacoes",
    "Decisoes": "decisoes", "Sessao": "sessao", "Deslocamentos": "deslocamentos",
    "Peticoes": "peticoes", "Recursos": "recursos", "Pautas": "pautas",
}
_CLASSE_NUM_RE = re.compile(r"^\s*([A-Za-z]+)\s+(\d+)\s*$")
_NUM_UNICO_RE = re.compile(r"Número Único:\s*([\d.\-]+)")
_RELATOR_RE = re.compile(r"Relator\(a\):\s*(.+?)\s*(?:Relator\(a\) do último incidente:|$)")
_RELATOR_ULT_RE = re.compile(r"Relator\(a\) do último incidente:\s*(.+?)\s*\(([^)]+)\)")
_PUBLICIDADE_RE = re.compile(r"if\s*\(\s*'(Público|Sigiloso)'\s*==")


def _input_value(t, id_: str) -> str | None:
    n = t.css_first(f"input#{id_}")
    return n.attributes.get("value") if n is not None else None


def parse_casca(raw: bytes) -> Casca:
    t = tree(raw)
    inc = _input_value(t, "incidente")
    classe_num = _input_value(t, "classe-numero-processo")
    if not inc or not classe_num:
        raise CascaInvalida("input#incidente ou input#classe-numero-processo ausente")
    m = _CLASSE_NUM_RE.match(classe_num)
    if not m:
        raise CascaInvalida(f"classe/número em formato inesperado: {classe_num!r}")
    classe, numero = m.group(1), int(m.group(2))

    dados = t.css_first("#dados-processo")
    cabecalho = text_of(dados)
    # o texto do cabeçalho vem antes das abas; corta na primeira ocorrência de "Todos"
    cabecalho = cabecalho.split(" Todos ")[0] if " Todos " in cabecalho else cabecalho

    # flags conhecidas aparecem como texto curto no cabeçalho; sem inferência, só presença literal
    reu_preso = "Réu Preso" in cabecalho
    natureza = "Criminal" if "Criminal" in cabecalho else ("Cível" if "Cível" in cabecalho else None)
    tipo_tramitacao = "Processo Eletrônico" if "Processo Eletrônico" in cabecalho else (
        "Processo Físico" if "Processo Físico" in cabecalho else None)

    num_unico = (_NUM_UNICO_RE.search(cabecalho) or [None, None])[1]
    rel = _RELATOR_RE.search(cabecalho)
    rel_ult = _RELATOR_ULT_RE.search(cabecalho)

    scripts = "\n".join(s.text() for s in t.css("script"))
    abas: dict[str, str] = {}
    for mm in _ABA_RE.finditer(scripts):
        nome = _ABA_NOMES.get(mm.group("nome"))
        if nome and nome not in abas:
            url = mm.group("url")
            abas[nome] = url
    # o script concatena "&tema=' + num_tema" com num_tema = 'N'; normaliza para a URL efetiva
    if "sessao" in abas and abas["sessao"].endswith("&tema="):
        abas["sessao"] += "N"

    pub = _PUBLICIDADE_RE.search(scripts)

    return Casca(
        incidente=int(inc), classe=classe, numero_processo=numero, numero_unico=num_unico,
        relator=clean(rel.group(1)) if rel else None,
        relator_ultimo_incidente=clean(rel_ult.group(1)) if rel_ult else None,
        ultimo_incidente=clean(rel_ult.group(2)) if rel_ult else None,
        publicidade=pub.group(1) if pub else None,
        natureza=natureza, reu_preso=reu_preso, tipo_tramitacao=tipo_tramitacao,
        meio=_input_value(t, "meio"), peca=_input_value(t, "peca"), abas=abas,
    )
