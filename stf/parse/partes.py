"""Parser de abaPartes.asp?incidente=N.

Estrutura: blocos `.processo-partes`, cada um com pares `.detalhe-parte` (papel)
/ `.nome-parte` (nome). O portal coloca a parte em um bloco e seus advogados no
bloco seguinte. O índice do bloco é preservado para permitir essa ligação sem
inferência.

`papel` é um mapeamento fixo do literal do portal; nunca é deduzido do nome
ou do conteúdo do processo (restrição 5).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ._util import clean, tree

PAPEIS: dict[str, str] = {
    "REQTE.(S)": "requerente",
    "REQDO.(A/S)": "requerido",
    "ADV.(A/S)": "advogado",
    "AUT. POL.": "autoridade_policial",
    "INTDO.(A/S)": "interessado",
    "PROC.(A/S)(ES)": "procurador",
    "AGTE.(S)": "agravante",
    "AGDO.(A/S)": "agravado",
    "PACTE.(S)": "paciente",
    "IMPTE.(S)": "impetrante",
    "COATOR(A/S)(ES)": "coator",
    "AM. CURIAE.": "amicus_curiae",
    "RECTE.(S)": "recorrente",
    "RECDO.(A/S)": "recorrido",
    "EMBTE.(S)": "embargante",
    "EMBDO.(A/S)": "embargado",
    "AUTOR(A/S)(ES)": "autor",
    "RÉU(É)(S)": "reu",
    "DENUNCIADO(A/S)": "denunciado",
    "INVEST.(A/S)": "investigado",
}

PLACEHOLDERS = {"SEM REPRESENTAÇÃO NOS AUTOS", "SOB SIGILO"}

# formatos vistos no portal: 317282/SP, 30814/A/MT, 141073A/RS, "32957 A/PB", 5922-A/AP, 01875/A/DF
_OAB_UMA = r"\d+\s?-?\s?[A-Z]?(?:/[A-Z])?/[A-Z]{2}"
_OAB_RE = re.compile(rf"^(?P<nome>.*?)\s*\((?P<oabs>(?:{_OAB_UMA}(?:,\s*)?)+)\)\s*$")


@dataclass
class Parte:
    papel_portal: str
    papel: str            # normalizado pela tabela PAPEIS; "desconhecido:<literal>" se não mapeado
    nome: str
    oab: list[str] = field(default_factory=list)
    bloco: int = 0
    posicao: int = 0
    e_placeholder: bool = False


def _separa_oab(nome_bruto: str) -> tuple[str, list[str]]:
    m = _OAB_RE.match(nome_bruto)
    if not m:
        return nome_bruto, []
    return clean(m.group("nome")), [clean(x) for x in m.group("oabs").split(",")]


def parse_partes(raw: bytes) -> list[Parte]:
    t = tree(raw)
    # #todas-partes tem a lista completa; #partes-resumidas (depois) é um resumo
    # "X E OUTRO(A/S)" que reutiliza a classe .processo-partes e não é parte.
    raiz = t.css_first("#todas-partes")
    if raiz is None:
        raise ValueError("aba Partes sem #todas-partes: estrutura do portal mudou")
    out: list[Parte] = []
    for bloco, blk in enumerate(raiz.css(".processo-partes")):
        papeis = [clean(x.text()) for x in blk.css(".detalhe-parte")]
        nomes = [clean(x.text()) for x in blk.css(".nome-parte")]
        if len(papeis) != len(nomes):
            raise ValueError(f"bloco {bloco}: {len(papeis)} papéis para {len(nomes)} nomes")
        for papel_portal, nome_bruto in zip(papeis, nomes):
            nome, oab = _separa_oab(nome_bruto)
            out.append(Parte(
                papel_portal=papel_portal,
                papel=PAPEIS.get(papel_portal, f"desconhecido:{papel_portal}"),
                nome=nome, oab=oab, bloco=bloco, posicao=len(out),
                e_placeholder=nome in PLACEHOLDERS,
            ))
    return out
