"""Exportação dos fluxos financeiros para o site (fluxos.json) e para planilha (fluxos.csv).

O JSON leva tudo o que está nas tabelas fluxo_* menos `fluxo_bem.identificacao` (placas, chassis, livros de
cartório), e já traz o grafo pré-agregado: um nó por ator (com totais de entrada e saída) e uma aresta por
par origem→destino somando as transações. Comunicações sem transação (escrituras cujo texto não diz quem
pagou a quem) viram arestas não dirigidas entre os titulares, com o valor comunicado.
"""

from __future__ import annotations

import csv
import io
import sqlite3
from collections import defaultdict


def _rows(con: sqlite3.Connection, sql: str, args=()) -> list[dict]:
    return [dict(r) for r in con.execute(sql, args)]


def exportar_fluxos(con: sqlite3.Connection) -> dict:
    fontes = _rows(con, """
        SELECT f.id, f.tipo, f.identificador, f.orgao, f.destinatario, f.emitido_em, f.incidente, f.curadoria_path, f.curadoria_sha256,
               f.carregado_em, d.id AS documento_id, d.titulo AS documento_titulo, d.paginas AS documento_paginas, d.sha256 AS documento_sha256,
               i.classe, i.numero_processo
        FROM fluxo_fonte f JOIN documento d ON d.id=f.documento_id LEFT JOIN incidente i ON i.numero=f.incidente ORDER BY f.id""")
    for f in fontes:
        f["documento"] = {"id": f.pop("documento_id"), "titulo": f.pop("documento_titulo"), "paginas": f.pop("documento_paginas"),
                          "sha256": f.pop("documento_sha256")}
        classe, numero = f.pop("classe"), f.pop("numero_processo")
        f["processo"] = f"{classe} {numero}" if classe else None
    doc_por_fonte = {f["id"]: f["documento"]["id"] for f in fontes}

    atores = _rows(con, "SELECT id, chave, nome, tipo, documento_mascarado, atividade, entidade_id FROM fluxo_ator ORDER BY id")
    por_id = {a["id"]: a for a in atores}
    for a in atores:
        a["totais"] = {"entradas_centavos": 0, "saidas_centavos": 0, "n_transacoes": 0}
        a["papeis"] = sorted({r[0] for r in con.execute("SELECT papel FROM fluxo_participacao WHERE ator_id=?", (a["id"],))})

    comunicacoes = _rows(con, """
        SELECT id, fonte_id, secao, numero, titular_ator_id, segmento, comunicante, local, periodo_inicio, periodo_fim, valor_centavos,
               creditos_centavos, debitos_centavos, informacoes, consideracoes, pagina_inicio, pagina_fim
        FROM fluxo_comunicacao ORDER BY fonte_id, secao, numero""")
    for c in comunicacoes:
        c["participacoes"] = _rows(con, "SELECT ator_id, papel FROM fluxo_participacao WHERE comunicacao_id=? ORDER BY papel, ator_id", (c["id"],))
        c["bens"] = _rows(con, "SELECT id, tipo, descricao, valor_centavos, valor_referencia_centavos, data_negocio FROM fluxo_bem WHERE comunicacao_id=? ORDER BY id", (c["id"],))
        c["ocorrencias"] = _rows(con, "SELECT norma, codigo, descricao FROM fluxo_ocorrencia WHERE comunicacao_id=? ORDER BY id", (c["id"],))
        c["documento_id"] = doc_por_fonte.get(c["fonte_id"])
    com_por_id = {c["id"]: c for c in comunicacoes}

    transacoes = _rows(con, """
        SELECT id, comunicacao_id, origem_ator_id, destino_ator_id, valor_centavos, data, periodo_inicio, periodo_fim, tipo, natureza, quantidade,
               bem_id, descricao, pagina, trecho_fonte
        FROM fluxo_transacao ORDER BY comunicacao_id, id""")
    for t in transacoes:
        t["documento_id"] = com_por_id[t["comunicacao_id"]]["documento_id"]
        t["secao"] = com_por_id[t["comunicacao_id"]]["secao"]
        if t["natureza"] != "resumo_tipo":   # resumos por tipo repetem os agregados; não contam duas vezes
            if t["origem_ator_id"] in por_id:
                por_id[t["origem_ator_id"]]["totais"]["saidas_centavos"] += t["valor_centavos"]
                por_id[t["origem_ator_id"]]["totais"]["n_transacoes"] += 1
            if t["destino_ator_id"] in por_id:
                por_id[t["destino_ator_id"]]["totais"]["entradas_centavos"] += t["valor_centavos"]
                por_id[t["destino_ator_id"]]["totais"]["n_transacoes"] += 1

    # grafo: arestas dirigidas por par (sem resumos por tipo), + não dirigidas para escrituras sem direção
    pares: dict[tuple, dict] = {}
    for t in transacoes:
        if t["natureza"] == "resumo_tipo" or t["origem_ator_id"] is None or t["destino_ator_id"] is None:
            continue
        k = (t["origem_ator_id"], t["destino_ator_id"])
        e = pares.setdefault(k, {"origem": k[0], "destino": k[1], "dirigida": True, "valor_centavos": 0, "n": 0, "transacoes": [],
                                 "naturezas": set(), "tipos": set(), "secoes": set()})
        e["valor_centavos"] += t["valor_centavos"]; e["n"] += 1; e["transacoes"].append(t["id"])
        e["naturezas"].add(t["natureza"]); e["tipos"].add(t["tipo"]); e["secoes"].add(t["secao"])
    arestas = []
    for e in pares.values():
        arestas.append({**e, "naturezas": sorted(e["naturezas"]), "tipos": sorted(e["tipos"]), "secoes": sorted(e["secoes"])})
    com_transacao = {t["comunicacao_id"] for t in transacoes}
    for c in comunicacoes:
        if c["id"] in com_transacao or not c["valor_centavos"]:
            continue
        titulares = [p["ator_id"] for p in c["participacoes"] if p["papel"] in ("titular", "vendedor")]
        titulares = sorted(set(titulares))
        if len(titulares) < 2:
            continue
        ancora = c["titular_ator_id"] if c["titular_ator_id"] in titulares else titulares[0]
        for outro in titulares:
            if outro == ancora:
                continue
            arestas.append({"origem": ancora, "destino": outro, "dirigida": False, "valor_centavos": c["valor_centavos"], "n": 1,
                            "transacoes": [], "comunicacao_id": c["id"], "naturezas": ["escritura"], "tipos": ["escritura_sem_direcao"],
                            "secoes": [c["secao"]]})
    ligados = {e["origem"] for e in arestas} | {e["destino"] for e in arestas}
    nos = [{"id": a["id"], "nome": a["nome"], "tipo": a["tipo"], "totais": a["totais"], "entidade_id": a["entidade_id"]}
           for a in atores if a["id"] in ligados]

    resumo = {
        "atores": len(atores), "comunicacoes": len(comunicacoes), "transacoes": len(transacoes),
        "individuais": sum(1 for t in transacoes if t["natureza"] == "individual"),
        "agregadas": sum(1 for t in transacoes if t["natureza"] == "agregado"),
        "por_secao": {s: sum(1 for c in comunicacoes if c["secao"] == s) for s in ("suspeita", "automatica", "especie")},
    }
    return {"fontes": fontes, "atores": atores, "comunicacoes": comunicacoes, "transacoes": transacoes,
            "grafo": {"nos": nos, "arestas": arestas}, "resumo": resumo}


def fluxos_csv(con: sqlite3.Connection) -> str:
    """Uma linha por transação, com página e trecho, para planilha/pandas. Valores em reais com ponto decimal."""
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["fonte", "comunicacao", "secao", "origem", "destino", "valor_reais", "data", "periodo_inicio", "periodo_fim", "tipo", "natureza",
                "quantidade", "pagina", "trecho", "descricao", "origem_documento", "destino_documento", "documento_id"])
    for r in con.execute("""
        SELECT f.identificador, c.numero, c.secao, o.nome AS origem, d.nome AS destino, t.valor_centavos, t.data, t.periodo_inicio, t.periodo_fim,
               t.tipo, t.natureza, t.quantidade, t.pagina, t.trecho_fonte, t.descricao, o.documento_mascarado AS od, d.documento_mascarado AS dd,
               f.documento_id
        FROM fluxo_transacao t JOIN fluxo_comunicacao c ON c.id=t.comunicacao_id JOIN fluxo_fonte f ON f.id=c.fonte_id
        LEFT JOIN fluxo_ator o ON o.id=t.origem_ator_id LEFT JOIN fluxo_ator d ON d.id=t.destino_ator_id
        ORDER BY c.secao, c.numero, t.id"""):
        r = dict(r)
        w.writerow([r["identificador"], r["numero"], r["secao"], r["origem"], r["destino"], f"{r['valor_centavos'] / 100:.2f}", r["data"],
                    r["periodo_inicio"], r["periodo_fim"], r["tipo"], r["natureza"], r["quantidade"], r["pagina"], r["trecho_fonte"],
                    r["descricao"], r["od"], r["dd"], r["documento_id"]])
    return out.getvalue()
