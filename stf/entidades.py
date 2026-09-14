"""Entidades canônicas, derivadas deterministicamente das partes, do cadastro do portal e das citações em documentos.

Chave de identidade:
- advogado com OAB: `oab:<primeiro número/UF>` (a OAB identifica a pessoa; o nome pode variar)
- ministro: `ministro:<nome normalizado sem prefixo MIN./Ministro(a) e sem sufixo "(relator)">`.
  O portal escreve "MIN. ANDRÉ MENDONÇA", os documentos "Ministro André Mendonça (relator)": é a mesma entidade.
- qualquer outro: `nome:<nome normalizado>` (maiúsculas, sem acentos, espaços colapsados)

Limitação declarada: duas pessoas com o mesmo nome exato e sem OAB viram uma entidade.
A tabela `entidade_mencao` preserva cada ocorrência (parte, incidente, papel), então a
interface consegue mostrar todas as menções e o leitor decide.

`natureza_provavel` só é preenchida quando o nome traz sufixo societário explícito
(LTDA, S.A., S/A, EIRELI, ME, EPP, "SOCIEDADE"). Nunca é deduzida de outra forma.
`grupo` vem de `stf/curadoria/grupos.json`: lista curada de padrões de órgãos (Polícia Federal,
Ministério Público, STF…), versionada com o código e marcada como curadoria na interface.
Não há inferência sobre conduta, caráter ou intenção (restrição 5).
"""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from collections import Counter
from pathlib import Path

_SUFIXOS_PJ = re.compile(r"\b(LTDA\.?|S\.?A\.?|S/A|EIRELI|EPP|ME|SOCIEDADE|PARTICIPACOES|PARTICIPAÇÕES|EMPREENDIMENTOS|CONSULTORIA|HOLDING)\b", re.I)
_PREFIXO_MINISTRO = re.compile(r"^\s*(?:MIN\.?|MINISTR[OA])\s+", re.I)
_SUFIXO_MINISTRO = re.compile(r"\s*\((?:relator[a]?|revisor[a]?|presidente)\)\s*$", re.I)
_GRUPOS_PATH = Path(__file__).parent / "curadoria" / "grupos.json"


def normalizar(nome: str) -> str:
    s = unicodedata.normalize("NFKD", nome)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s).strip().upper()


def nome_ministro(nome: str) -> str:
    """'MIN. ANDRÉ MENDONÇA' → 'ANDRÉ MENDONÇA'; 'Ministro Dias Toffoli (relator)' → 'Dias Toffoli'. Preserva acentos."""
    return _SUFIXO_MINISTRO.sub("", _PREFIXO_MINISTRO.sub("", nome)).strip()


def chave_ministro(nome: str) -> str:
    return f"ministro:{normalizar(nome_ministro(nome))}"


def chave_de(papel: str, nome: str, oab: list[str]) -> tuple[str, str]:
    if papel == "advogado" and oab:
        return "advogado", f"oab:{oab[0]}"
    return ("advogado" if papel == "advogado" else "parte"), f"nome:{normalizar(nome)}"


def natureza_provavel(nome: str) -> str | None:
    return "pessoa_juridica" if _SUFIXOS_PJ.search(nome) else None


def _carregar_grupos() -> list[tuple[str, list[re.Pattern]]]:
    dados = json.loads(_GRUPOS_PATH.read_text("utf-8"))
    return [(g["grupo"], [re.compile(p) for p in g["padroes"]]) for g in dados["grupos"]]


_GRUPOS = _carregar_grupos()


def grupo_de(nome: str) -> str | None:
    """Primeiro grupo curado cujo padrão casa com o nome normalizado; None se nenhum."""
    n = normalizar(nome)
    for grupo, padroes in _GRUPOS:
        if any(p.search(n) for p in padroes):
            return grupo
    return None


def construir_entidades(con: sqlite3.Connection) -> dict:
    """Recria entidade + entidade_mencao a partir de `parte`, e os ministros a partir do cadastro do portal. Idempotente."""
    partes = con.execute(
        "SELECT id, incidente, papel_portal, papel, nome, oab, bloco, e_placeholder FROM parte ORDER BY id").fetchall()
    grupos: dict[tuple[str, str], list] = {}
    for p in partes:
        if p["e_placeholder"]:
            continue
        tipo, chave = chave_de(p["papel"], p["nome"], json.loads(p["oab"]))
        grupos.setdefault((tipo, chave), []).append(p)

    ministros: Counter = Counter()
    for sql in ("SELECT relator AS n FROM incidente", "SELECT relator_ultimo_incidente AS n FROM incidente",
                "SELECT relator AS n FROM lista_julgamento", "SELECT ministro AS n FROM voto"):
        for r in con.execute(sql):
            if r["n"]:
                ministros[nome_ministro(r["n"])] += 1

    with con:
        con.execute("DELETE FROM entidade_mencao")
        # entidades vindas de documentos (Fase 4) têm asserções ligadas; ficam. As de partes/portal são recriadas.
        con.execute("DELETE FROM entidade WHERE origem IN ('partes', 'portal') AND id NOT IN (SELECT entidade_id FROM assercao_entidade)")
        for (tipo, chave), ps in grupos.items():
            nome = Counter(p["nome"] for p in ps).most_common(1)[0][0]
            con.execute(
                "INSERT INTO entidade (tipo, chave, nome, natureza_provavel, origem, grupo) VALUES (?,?,?,?,'partes',?) "
                "ON CONFLICT(chave) DO UPDATE SET tipo=excluded.tipo, nome=excluded.nome, natureza_provavel=excluded.natureza_provavel, "
                "origem='partes', grupo=excluded.grupo",
                (tipo, chave, nome, natureza_provavel(nome), grupo_de(nome)))
            eid = con.execute("SELECT id FROM entidade WHERE chave=?", (chave,)).fetchone()["id"]
            con.executemany(
                "INSERT INTO entidade_mencao (entidade_id, parte_id, incidente, papel_portal, papel, bloco) VALUES (?,?,?,?,?,?)",
                [(eid, p["id"], p["incidente"], p["papel_portal"], p["papel"], p["bloco"]) for p in ps])
        for nome in ministros:
            con.execute(
                "INSERT INTO entidade (tipo, chave, nome, natureza_provavel, origem, grupo) VALUES ('ministro',?,?,NULL,'portal','Supremo Tribunal Federal') "
                "ON CONFLICT(chave) DO UPDATE SET tipo='ministro', nome=excluded.nome, origem='portal', grupo=excluded.grupo",
                (chave_ministro(nome), nome))
        # grupo curado também para entidades vindas de documentos (o nome literal fica; só o rótulo de grupo é derivado)
        for e in con.execute("SELECT id, nome FROM entidade WHERE origem='documento'").fetchall():
            con.execute("UPDATE entidade SET grupo=? WHERE id=?", (grupo_de(e["nome"]), e["id"]))
    return {"entidades": len(grupos), "mencoes": sum(len(v) for v in grupos.values()), "ministros": len(ministros)}
