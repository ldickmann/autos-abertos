"""Aliases de entidades: chave canônica por normalização forte + lista curada + propostas para revisão humana.

- `normalizar_chave`: maiúsculas, sem acentos, sem pontuação, hífen e barra viram espaço, "S.A."/"S/A" viram "SA".
  Faz "KING PARTICIPAÇÕES LTDA." e "KING PARTICIPACOES LTDA" caírem na mesma chave por regra, sem julgamento.
- `canonizar`: aplica `stf/curadoria/aliases.json` (curado, com motivo) sobre uma chave já normalizada.
- `propor_aliases`: pares de nomes parecidos (difflib ≥ 0,9) que ainda são entidades distintas, para alguém decidir.
  Nunca funde nada sozinho: pessoas com nomes parecidos podem ser pessoas diferentes.
"""

from __future__ import annotations

import difflib
import itertools
import json
import re
import sqlite3
import unicodedata
from pathlib import Path

_PATH = Path(__file__).parent / "curadoria" / "aliases.json"
_PONTUACAO = re.compile(r"[.,;:'\"()\[\]{}«»“”‘’—–]")
_SEPARADORES = re.compile(r"[-/]")
_SA = re.compile(r"\bS\s?A\b")


def normalizar_chave(nome: str) -> str:
    s = unicodedata.normalize("NFKD", nome)
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).upper()
    s = _SEPARADORES.sub(" ", _PONTUACAO.sub("", s))
    s = re.sub(r"\s+", " ", s).strip()
    return _SA.sub("SA", s)


def _carregar() -> dict[str, dict]:
    dados = json.loads(_PATH.read_text("utf-8"))
    return {a["de"]: a for a in dados["aliases"]}


_ALIASES = _carregar()


def canonizar(chave: str) -> str:
    """Segue a lista curada (com proteção contra ciclos)."""
    vistos = set()
    while chave in _ALIASES and chave not in vistos:
        vistos.add(chave)
        chave = _ALIASES[chave]["para"]
    return chave


def motivo_alias(chave: str) -> str | None:
    return _ALIASES[chave]["motivo"] if chave in _ALIASES else None


def propor_aliases(con: sqlite3.Connection, limiar: float = 0.9, minimo: int = 12) -> list[dict]:
    """Pares de entidades distintas com nomes parecidos. Advogados ficam de fora (a OAB já identifica)."""
    ents = [dict(r) for r in con.execute("SELECT id, tipo, chave, nome, origem FROM entidade WHERE tipo != 'advogado' ORDER BY id")]
    for e in ents:
        e["norm"] = normalizar_chave(e["nome"])
    propostas = []
    for a, b in itertools.combinations(ents, 2):
        if len(a["norm"]) < minimo or len(b["norm"]) < minimo or a["norm"] == b["norm"]:
            continue
        r = difflib.SequenceMatcher(None, a["norm"], b["norm"]).ratio()
        ta, tb = a["norm"].split(), b["norm"].split()
        # nome contido: mesmo primeiro e último nome, e um é subsequência do outro ("DANIEL VORCARO" ⊂ "DANIEL BUENO VORCARO")
        contido = len(ta) >= 2 and len(tb) >= 2 and ta[0] == tb[0] and ta[-1] == tb[-1] and (set(ta) <= set(tb) or set(tb) <= set(ta))
        if r < limiar and not contido:
            continue
        propostas.append({
            "similaridade": round(r, 3), "motivo": "nome contido" if contido and r < limiar else "parecido",
            "a": {"id": a["id"], "nome": a["nome"], "chave": a["chave"], "tipo": a["tipo"], "origem": a["origem"]},
            "b": {"id": b["id"], "nome": b["nome"], "chave": b["chave"], "tipo": b["tipo"], "origem": b["origem"]},
            "pessoas": a["tipo"] in ("pessoa", "parte") and b["tipo"] in ("pessoa", "parte"),
            "decisao": None,
        })
    propostas.sort(key=lambda p: -p["similaridade"])
    return propostas
