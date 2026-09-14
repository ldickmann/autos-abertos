"""Função de cada documento, derivada do título literal do portal (stf/curadoria/funcoes_documento.json)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .entidades import normalizar

_CFG = json.loads((Path(__file__).parent / "curadoria" / "funcoes_documento.json").read_text("utf-8"))
_PADROES = [(c["funcao"], [re.compile(p) for p in c["padroes"]]) for c in _CFG["padroes"]]
ROTULOS: dict[str, str] = _CFG["rotulos"]


def funcao_de(titulo: str | None, e_decisao: bool = False) -> str:
    """Um despacho marcado como decisão pelo portal é 'decisao'; o resto segue os padrões do título."""
    t = normalizar(titulo or "")
    for funcao, padroes in _PADROES:
        if any(p.search(t) for p in padroes):
            return "decisao" if funcao == "despacho" and e_decisao else funcao
    return "outro"
