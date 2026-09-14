"""Entidades canônicas, derivadas deterministicamente das partes.

Chave de identidade:
- advogado com OAB: `oab:<primeiro número/UF>` (a OAB identifica a pessoa; o nome pode variar)
- qualquer outro: `nome:<nome normalizado>` (maiúsculas, sem acentos, espaços colapsados)

Limitação declarada: duas pessoas com o mesmo nome exato e sem OAB viram uma entidade.
A tabela `entidade_mencao` preserva cada ocorrência (parte, incidente, papel), então a
interface consegue mostrar todas as menções e o leitor decide.

`natureza_provavel` só é preenchida quando o nome traz sufixo societário explícito
(LTDA, S.A., S/A, EIRELI, ME, EPP, "SOCIEDADE"). Nunca é deduzida de outra forma.
Não há inferência sobre conduta, caráter ou intenção (restrição 5).
"""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from collections import Counter

_SUFIXOS_PJ = re.compile(r"\b(LTDA\.?|S\.?A\.?|S/A|EIRELI|EPP|ME|SOCIEDADE|PARTICIPACOES|PARTICIPAÇÕES|EMPREENDIMENTOS|CONSULTORIA|HOLDING)\b", re.I)


def normalizar(nome: str) -> str:
    s = unicodedata.normalize("NFKD", nome)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s).strip().upper()


def chave_de(papel: str, nome: str, oab: list[str]) -> tuple[str, str]:
    if papel == "advogado" and oab:
        return "advogado", f"oab:{oab[0]}"
    return ("advogado" if papel == "advogado" else "parte"), f"nome:{normalizar(nome)}"


def natureza_provavel(nome: str) -> str | None:
    return "pessoa_juridica" if _SUFIXOS_PJ.search(nome) else None


def construir_entidades(con: sqlite3.Connection) -> dict:
    """Recria entidade + entidade_mencao a partir de `parte`. Idempotente (é projeção da projeção)."""
    partes = con.execute(
        "SELECT id, incidente, papel_portal, papel, nome, oab, bloco, e_placeholder FROM parte ORDER BY id").fetchall()
    grupos: dict[tuple[str, str], list] = {}
    for p in partes:
        if p["e_placeholder"]:
            continue
        tipo, chave = chave_de(p["papel"], p["nome"], json.loads(p["oab"]))
        grupos.setdefault((tipo, chave), []).append(p)

    with con:
        con.execute("DELETE FROM entidade_mencao")
        con.execute("DELETE FROM entidade")
        for (tipo, chave), ps in grupos.items():
            nome = Counter(p["nome"] for p in ps).most_common(1)[0][0]
            cur = con.execute("INSERT INTO entidade (tipo, chave, nome, natureza_provavel) VALUES (?,?,?,?)",
                              (tipo, chave, nome, natureza_provavel(nome)))
            eid = cur.lastrowid
            con.executemany(
                "INSERT INTO entidade_mencao (entidade_id, parte_id, incidente, papel_portal, papel, bloco) VALUES (?,?,?,?,?,?)",
                [(eid, p["id"], p["incidente"], p["papel_portal"], p["papel"], p["bloco"]) for p in ps])
    return {"entidades": len(grupos), "mencoes": sum(len(v) for v in grupos.values())}
