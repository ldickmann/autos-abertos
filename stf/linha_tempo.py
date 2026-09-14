"""Linha do tempo unificada: todos os andamentos de todos os processos coletados, numa ordenação só.

A categoria de cada andamento vem de `stf/curadoria/categorias_andamento.json` (padrões sobre o nome do tipo,
curados e versionados). O tipo literal do portal é sempre preservado ao lado; a categoria só serve para filtrar.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from .entidades import normalizar

_PATH = Path(__file__).parent / "curadoria" / "categorias_andamento.json"
_CFG = json.loads(_PATH.read_text("utf-8"))
_PADROES = [(c["categoria"], [re.compile(p) for p in c["padroes"]]) for c in _CFG["padroes"]]
ORDEM = _CFG["ordem"]
ROTULOS = _CFG["rotulos"]


def categoria_de(tipo: str, e_decisao: int = 0, e_pauta: int = 0) -> str:
    if e_decisao:
        return "decisao"
    if e_pauta:
        return "julgamento"
    t = normalizar(tipo)
    for categoria, padroes in _PADROES:
        if any(p.search(t) for p in padroes):
            return categoria
    return "outro"


def linha_tempo_unificada(con: sqlite3.Connection) -> list[dict]:
    rotulo = {r["incidente_principal"]: f"{r['classe']} {r['numero']}" for r in
              con.execute("SELECT classe, numero, incidente_principal FROM processo WHERE incidente_principal IS NOT NULL")}
    docs: dict[int, list] = {}
    for r in con.execute("SELECT ad.andamento_id, d.id, ad.rotulo, d.sha256 IS NOT NULL AS baixado, d.paginas FROM andamento_documento ad JOIN documento d ON d.id=ad.documento_id"):
        docs.setdefault(r["andamento_id"], []).append({"id": r["id"], "rotulo": r["rotulo"], "baixado": bool(r["baixado"]), "paginas": r["paginas"]})
    pet: dict[int, dict] = {}
    for r in con.execute("SELECT ap.andamento_id, p.numero, p.recebido_por, p.data_peticionamento FROM andamento_peticao ap JOIN peticao p ON p.id=ap.peticao_id"):
        pet[r["andamento_id"]] = {"numero": r["numero"], "recebido_por": r["recebido_por"], "data_peticionamento": r["data_peticionamento"]}
    n_ass: dict[int, int] = {}
    for r in con.execute("SELECT ad.andamento_id, COUNT(*) n FROM andamento_documento ad JOIN assercao a ON a.documento_id=ad.documento_id GROUP BY ad.andamento_id"):
        n_ass[r["andamento_id"]] = r["n"]
    eventos = []
    for a in con.execute("SELECT id, incidente, hash_natural, data, tipo, descricao, e_decisao, e_pauta, e_recurso, snapshot_first_seen "
                         "FROM andamento ORDER BY data, incidente, posicao DESC"):
        if a["incidente"] not in rotulo:
            continue
        eventos.append({
            "andamento_id": a["id"], "incidente": a["incidente"], "processo": rotulo[a["incidente"]], "data": a["data"],
            "tipo": a["tipo"], "categoria": categoria_de(a["tipo"], a["e_decisao"], a["e_pauta"]),
            "descricao": a["descricao"], "e_decisao": bool(a["e_decisao"]), "e_pauta": bool(a["e_pauta"]), "e_recurso": bool(a["e_recurso"]),
            "documentos": docs.get(a["id"], []), "peticao": pet.get(a["id"]), "assercoes": n_ass.get(a["id"], 0),
            "hash": a["hash_natural"], "snapshot": a["snapshot_first_seen"],
        })
    return eventos
