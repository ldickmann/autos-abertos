"""Cronologia do caso: o que aconteceu, quando e segundo quem, juntando três fontes num fio só.

- registro do portal: andamentos das categorias decisão, julgamento, recurso, distribuição e encerramento;
- o que os documentos dizem: asserções cujo trecho literal traz exatamente uma data (stf/datas.py), com o tipo
  epistêmico e a quem a afirmação é atribuída;
- decisões: itens pedido → resultado com data.

Datas anteriores a 2025 são marcadas como "referência" (jurisprudência e legislação citadas), não como evento do caso.
"""

from __future__ import annotations

import sqlite3

from .linha_tempo import categoria_de

INICIO_DO_CASO = "2025-01-01"
CATEGORIAS_PORTAL = {"decisao", "julgamento", "recurso", "distribuicao", "encerramento"}


def cronologia(con: sqlite3.Connection) -> dict:
    proc = {r["incidente_principal"]: f"{r['classe']} {r['numero']}" for r in con.execute("SELECT classe, numero, incidente_principal FROM processo WHERE incidente_principal IS NOT NULL")}
    eventos: list[dict] = []
    for a in con.execute("SELECT id, incidente, data, tipo, descricao, e_decisao, e_pauta FROM andamento"):
        cat = categoria_de(a["tipo"], a["e_decisao"], a["e_pauta"])
        if cat not in CATEGORIAS_PORTAL or a["incidente"] not in proc:
            continue
        eventos.append({"data": a["data"], "fonte": "portal", "tipo": "andamento", "categoria": cat, "processo": proc[a["incidente"]], "incidente": a["incidente"],
                        "texto": a["tipo"] + (f" — {a['descricao']}" if a["descricao"] else ""), "andamento_id": a["id"], "contexto": "caso"})
    for r in con.execute(
            "SELECT d.data, d.literal, a.id, a.tipo_epistemico, a.atribuida_a, a.texto, a.trecho_fonte, a.pagina, a.documento_id, doc.incidente, doc.titulo "
            "FROM assercao_data d JOIN assercao a ON a.id=d.assercao_id JOIN documento doc ON doc.id=a.documento_id WHERE d.n_datas=1"):
        if r["incidente"] not in proc:
            continue
        eventos.append({"data": r["data"], "fonte": "documento", "tipo": "assercao", "tipo_epistemico": r["tipo_epistemico"], "atribuida_a": r["atribuida_a"],
                        "processo": proc[r["incidente"]], "incidente": r["incidente"], "texto": r["texto"], "trecho_fonte": r["trecho_fonte"], "literal": r["literal"],
                        "documento_id": r["documento_id"], "titulo_documento": r["titulo"], "pagina": r["pagina"], "assercao_id": r["id"],
                        "contexto": "caso" if r["data"] >= INICIO_DO_CASO else "referencia"})
    for r in con.execute(
            "SELECT i.id, i.data, i.pedido, i.quem_pediu, i.resultado, i.decisao, i.quem_decidiu, i.pagina, i.documento_id, d.incidente, d.titulo "
            "FROM decisao_item i JOIN documento d ON d.id=i.documento_id WHERE i.data IS NOT NULL"):
        if r["incidente"] not in proc:
            continue
        eventos.append({"data": r["data"], "fonte": "documento", "tipo": "decisao", "resultado": r["resultado"], "processo": proc[r["incidente"]], "incidente": r["incidente"],
                        "texto": f"{r['pedido']} → {r['decisao']}", "quem_pediu": r["quem_pediu"], "quem_decidiu": r["quem_decidiu"],
                        "documento_id": r["documento_id"], "titulo_documento": r["titulo"], "pagina": r["pagina"], "decisao_id": r["id"],
                        "contexto": "caso" if r["data"] >= INICIO_DO_CASO else "referencia"})
    eventos.sort(key=lambda e: (e["data"], e["fonte"], e["tipo"]))
    return {"inicio_do_caso": INICIO_DO_CASO, "total": len(eventos), "por_fonte": {"portal": sum(e["fonte"] == "portal" for e in eventos), "documento": sum(e["fonte"] == "documento" for e in eventos)},
            "eventos": eventos}
