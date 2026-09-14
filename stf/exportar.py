"""Exporta a projeção para JSON estático consumido pela interface (Fase 5).

Cada item exportado carrega `snapshot` = {id, fetched_at, sha256, url}: é o "dados coletados em"
e o ponteiro para o blob bruto. Nada é resumido nem reescrito aqui.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .grafo import construir_grafo, cruzamentos

STATUS_PROCESSUAL = {
    "requerente": "requerente", "requerido": "requerido", "advogado": "advogado", "investigado": "investigado",
    "interessado": "interessado", "autoridade_policial": "autoridade policial", "procurador": "procurador",
    "autor": "autor", "reu": "réu", "denunciado": "denunciado", "agravante": "agravante", "agravado": "agravado",
    "paciente": "paciente", "impetrante": "impetrante", "coator": "autoridade coatora", "amicus_curiae": "amicus curiae",
    "recorrente": "recorrente", "recorrido": "recorrido", "embargante": "embargante", "embargado": "embargado",
}


def _snap(con, sid: int | None, cache: dict) -> dict | None:
    if sid is None:
        return None
    if sid not in cache:
        r = con.execute("SELECT id, fetched_at, sha256, url, aba FROM snapshot WHERE id=?", (sid,)).fetchone()
        cache[sid] = dict(r) if r else None
    return cache[sid]


def _escrever(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), "utf-8")


def exportar(con: sqlite3.Connection, saida: Path, *, semente: int) -> dict:
    saida = Path(saida)
    cache: dict = {}
    processos = [dict(r) for r in con.execute(
        "SELECT p.classe, p.numero, p.incidente_principal AS incidente, p.status, i.* FROM processo p "
        "LEFT JOIN incidente i ON i.numero = p.incidente_principal ORDER BY p.classe, p.numero")]
    lista_processos = []
    coletado_em: dict[str, str] = {}
    docs_exportados = 0

    for p in processos:
        inc = p["incidente"]
        if inc is None or p["relator"] is None:
            lista_processos.append({"classe": p["classe"], "numero": p["numero"], "incidente": inc, "coletado": False})
            continue
        cab = {k: p[k] for k in ("classe", "numero", "incidente", "numero_unico", "relator", "relator_ultimo_incidente",
                                  "ultimo_incidente", "publicidade", "natureza", "reu_preso", "tipo_tramitacao",
                                  "data_protocolo", "orgao_origem", "origem", "descricao_procedencia")}
        cab["numero_processo"] = p["numero_processo"]
        cab["assuntos"] = json.loads(p["assuntos"] or "[]")
        cab["numeros_origem"] = json.loads(p["numeros_origem"] or "[]")
        cab["snapshot"] = _snap(con, p["snapshot_last_seen"], cache)
        coletado_em[str(inc)] = (cab["snapshot"] or {}).get("fetched_at")

        partes = []
        for r in con.execute(
                "SELECT pa.*, m.entidade_id FROM parte pa LEFT JOIN entidade_mencao m ON m.parte_id = pa.id "
                "WHERE pa.incidente=? ORDER BY pa.posicao", (inc,)):
            partes.append({"id": r["id"], "nome": r["nome"], "papel_portal": r["papel_portal"], "papel": r["papel"],
                           "status_processual": STATUS_PROCESSUAL.get(r["papel"], r["papel"]), "oab": json.loads(r["oab"]),
                           "bloco": r["bloco"], "e_placeholder": bool(r["e_placeholder"]), "entidade_id": r["entidade_id"],
                           "snapshot": _snap(con, r["snapshot_last_seen"], cache)})

        assercoes_doc: dict[int, list] = {}
        contagem = {"fato_processual": 0, "alegacao_parte": 0, "fundamento_decisorio": 0}
        for a in con.execute(
                "SELECT a.id, a.documento_id, a.pagina, a.tipo_epistemico, a.texto, a.trecho_fonte, a.atribuida_a FROM assercao a "
                "JOIN documento d ON d.id = a.documento_id WHERE d.incidente=? ORDER BY a.documento_id, a.pagina, a.id", (inc,)):
            assercoes_doc.setdefault(a["documento_id"], []).append({
                "id": a["id"], "pagina": a["pagina"], "tipo_epistemico": a["tipo_epistemico"], "texto": a["texto"],
                "trecho_fonte": a["trecho_fonte"], "atribuida_a": a["atribuida_a"]})
            contagem[a["tipo_epistemico"]] += 1
        docs_por_andamento: dict[int, list] = {}
        for r in con.execute(
                "SELECT ad.andamento_id, ad.rotulo, d.id, d.formato, d.url, d.sha256, d.paginas, d.tem_camada_texto, d.codigo_autenticacao "
                "FROM andamento_documento ad JOIN documento d ON d.id = ad.documento_id JOIN andamento a ON a.id = ad.andamento_id "
                "WHERE a.incidente=?", (inc,)):
            docs_por_andamento.setdefault(r["andamento_id"], []).append({
                "id": r["id"], "rotulo": r["rotulo"], "formato": r["formato"], "url": r["url"], "baixado": r["sha256"] is not None,
                "paginas": r["paginas"], "tem_texto": bool(r["tem_camada_texto"]), "codigo_autenticacao": r["codigo_autenticacao"],
                "assercoes": assercoes_doc.get(r["id"], [])})
        andamentos = []
        for r in con.execute("SELECT * FROM andamento WHERE incidente=? ORDER BY posicao", (inc,)):
            andamentos.append({"id": r["id"], "data": r["data"], "tipo": r["tipo"], "descricao": r["descricao"],
                               "e_decisao": bool(r["e_decisao"]), "e_pauta": bool(r["e_pauta"]),
                               "documentos": docs_por_andamento.get(r["id"], []),
                               "snapshot": _snap(con, r["snapshot_last_seen"], cache), "hash": r["hash_natural"][:12]})
        peticoes = [{"numero": r["numero"], "data_peticionamento": r["data_peticionamento"], "recebido_em": r["recebido_em"],
                     "recebido_por": r["recebido_por"], "snapshot": _snap(con, r["snapshot_last_seen"], cache)}
                    for r in con.execute("SELECT * FROM peticao WHERE incidente=? ORDER BY posicao", (inc,))]
        deslocamentos = [{"destino": r["destino"], "enviado_por": r["enviado_por"], "data_envio": r["data_envio"], "guia": r["guia"],
                          "recebido_em": r["recebido_em"], "snapshot": _snap(con, r["snapshot_last_seen"], cache)}
                         for r in con.execute("SELECT * FROM deslocamento WHERE incidente=? ORDER BY posicao", (inc,))]
        relacoes = [{"tipo": r["tipo"], "classe": r["classe_destino"], "numero": r["numero_destino"],
                     "fonte_andamento_id": r["fonte_andamento_id"], "snapshot": _snap(con, r["snapshot_first_seen"], cache)}
                    for r in con.execute("SELECT * FROM processo_relacao WHERE incidente_origem=?", (inc,))]
        sessoes = []
        for l in con.execute("SELECT l.*, o.identificacao, o.identificacao_completa, o.tipo AS tipo_objeto FROM lista_julgamento l "
                             "JOIN objeto_incidente o ON o.id = l.objeto_incidente_id WHERE o.incidente_principal=? ORDER BY l.data_inicio", (inc,)):
            votos = [dict(v) for v in con.execute("SELECT ordem, ministro, data, tipo_voto, acompanhando, antecipado FROM voto WHERE lista_id=? ORDER BY ordem", (l["id"],))]
            sessoes.append({"objeto": l["identificacao"], "objeto_completo": l["identificacao_completa"], "tipo_objeto": l["tipo_objeto"],
                            "lista": l["nome_lista"], "julgado": l["julgado"], "relator": l["relator"], "tipo_lista": l["tipo_lista"],
                            "colegiado": l["colegiado"], "data_inicio": l["data_inicio"], "data_fim": l["data_fim"],
                            "texto_decisao": l["texto_decisao"], "resultado": l["resultado"], "votos": votos,
                            "snapshot": _snap(con, l["snapshot_last_seen"], cache)})
        tipos = {r["nome"]: r["explicacao_portal"] for r in con.execute(
            "SELECT DISTINCT t.nome, t.explicacao_portal FROM tipo_andamento t JOIN andamento a ON a.tipo = t.nome WHERE a.incidente=?", (inc,))}
        _escrever(saida / "processo" / f"{inc}.json", {
            "cabecalho": cab, "partes": partes, "andamentos": andamentos, "peticoes": peticoes, "deslocamentos": deslocamentos,
            "relacoes": relacoes, "sessoes": sessoes, "explicacoes_portal": tipos, "contagem_assercoes": contagem,
        })
        lista_processos.append({"classe": p["classe"], "numero": p["numero"], "incidente": inc, "coletado": True,
                                "publicidade": p["publicidade"], "relator": p["relator"], "assuntos": cab["assuntos"],
                                "data_protocolo": p["data_protocolo"], "status": p["status"],
                                "contagens": {"partes": len(partes), "andamentos": len(andamentos), "peticoes": len(peticoes),
                                              "deslocamentos": len(deslocamentos), "documentos": sum(len(v) for v in docs_por_andamento.values())},
                                "coletado_em": coletado_em[str(inc)]})

    # documentos com texto
    assercoes_por_doc: dict[int, list] = {}
    for a in con.execute("SELECT a.*, (SELECT json_group_array(json_object('entidade_id', ae.entidade_id, 'nome', ae.nome_literal, 'tipo', ae.tipo_citado)) "
                         "FROM assercao_entidade ae WHERE ae.assercao_id=a.id) AS ents FROM assercao a ORDER BY a.documento_id, a.pagina, a.id"):
        assercoes_por_doc.setdefault(a["documento_id"], []).append({
            "id": a["id"], "pagina": a["pagina"], "tipo_epistemico": a["tipo_epistemico"], "texto": a["texto"],
            "trecho_fonte": a["trecho_fonte"], "atribuida_a": a["atribuida_a"], "entidades": json.loads(a["ents"] or "[]"),
            "modelo": a["modelo"], "prompt_version": a["prompt_version"]})
    todas_assercoes = []
    for d in con.execute("SELECT * FROM documento WHERE sha256 IS NOT NULL ORDER BY id"):
        paginas = [{"n": r["pagina"], "texto": r["texto"]} for r in con.execute(
            "SELECT pagina, texto FROM documento_pagina WHERE documento_id=? ORDER BY pagina", (d["id"],))]
        chunks = [dict(r) for r in con.execute(
            "SELECT ordem, pagina_inicio, pagina_fim, secao, texto FROM documento_chunk WHERE documento_id=? ORDER BY ordem", (d["id"],))]
        andamentos_ref = [dict(r) for r in con.execute(
            "SELECT a.id, a.data, a.tipo, a.incidente FROM andamento_documento ad JOIN andamento a ON a.id=ad.andamento_id WHERE ad.documento_id=?", (d["id"],))]
        meta_doc = {"id": d["id"], "incidente": d["incidente"], "endpoint": d["endpoint"], "id_portal": d["id_portal"], "formato": d["formato"],
                    "url": d["url"], "titulo": d["titulo"], "sha256": d["sha256"], "paginas": d["paginas"], "tem_texto": bool(d["tem_camada_texto"]),
                    "precisa_ocr": bool(d["precisa_ocr"]), "codigo_autenticacao": d["codigo_autenticacao"],
                    "senha_autenticacao": d["senha_autenticacao"], "baixado_em": d["baixado_em"],
                    "snapshot": _snap(con, d["snapshot_download"], cache), "andamentos": andamentos_ref}
        _escrever(saida / "documento" / f"{d['id']}.json",
                  {"meta": meta_doc, "paginas": paginas, "chunks": chunks, "assercoes": assercoes_por_doc.get(d["id"], [])})
        for a in assercoes_por_doc.get(d["id"], []):
            todas_assercoes.append({**a, "documento": {k: meta_doc[k] for k in ("id", "incidente", "titulo", "url", "codigo_autenticacao")},
                                    "data_andamento": andamentos_ref[0]["data"] if andamentos_ref else None})
        docs_exportados += 1
    _escrever(saida / "assercoes.json", todas_assercoes)

    # entidades
    ents = []
    for e in con.execute("SELECT * FROM entidade ORDER BY nome"):
        mencoes = [dict(m) for m in con.execute(
            "SELECT m.incidente, m.papel_portal, m.papel, p.classe || ' ' || p.numero AS processo FROM entidade_mencao m "
            "LEFT JOIN processo p ON p.incidente_principal = m.incidente WHERE m.entidade_id=? ORDER BY m.incidente", (e["id"],))]
        for m in mencoes:
            m["status_processual"] = STATUS_PROCESSUAL.get(m["papel"], m["papel"])
        n_ass = con.execute("SELECT COUNT(*) FROM assercao_entidade WHERE entidade_id=?", (e["id"],)).fetchone()[0]
        ents.append({"id": e["id"], "nome": e["nome"], "tipo": e["tipo"], "chave": e["chave"], "natureza_provavel": e["natureza_provavel"],
                     "origem": e["origem"], "status_padrao": "terceiro mencionado" if e["origem"] == "documento" else None,
                     "mencoes": mencoes, "assercoes": n_ass})
    _escrever(saida / "entidades.json", ents)

    # índice de busca: andamentos + chunks de documentos
    busca = []
    for r in con.execute("SELECT a.id, a.incidente, a.data, a.tipo, a.descricao, a.e_decisao FROM andamento a"):
        busca.append({"tipo": "andamento", "id": r["id"], "incidente": r["incidente"], "data": r["data"], "titulo": r["tipo"],
                      "texto": r["descricao"], "decisao": bool(r["e_decisao"])})
    for r in con.execute("SELECT c.id, c.documento_id, d.incidente, d.titulo, c.pagina_inicio, c.secao, c.texto FROM documento_chunk c JOIN documento d ON d.id=c.documento_id"):
        busca.append({"tipo": "documento", "id": r["id"], "documento_id": r["documento_id"], "incidente": r["incidente"],
                      "titulo": r["titulo"], "pagina": r["pagina_inicio"], "secao": r["secao"], "texto": r["texto"]})
    _escrever(saida / "busca.json", busca)

    _escrever(saida / "grafo.json", construir_grafo(con))
    _escrever(saida / "cruzamentos.json", cruzamentos(con))
    _escrever(saida / "processos.json", lista_processos)
    coletas = [dict(r) for r in con.execute("SELECT id, incidente, ingerida_em FROM coleta ORDER BY id")]
    _escrever(saida / "meta.json", {
        "gerado_em": datetime.now(timezone.utc).isoformat(), "semente": semente, "coletado_em": coletado_em, "coletas": coletas,
        "contagens": {"processos": len([p for p in lista_processos if p["coletado"]]), "documentos": docs_exportados,
                      "entidades": len(ents), "assercoes": len(todas_assercoes), "busca": len(busca)},
        "tipos_epistemicos": {
            "fato_processual": "Evento verificável nos autos: uma decisão, um prazo, uma juntada. Diz o que aconteceu no processo.",
            "alegacao_parte": "Afirmação que o documento atribui a uma parte, órgão ou pessoa. O sistema registra que foi alegado, não que é verdade.",
            "fundamento_decisorio": "Razão que o julgador declara adotar ao decidir: a prova que aponta, a norma que invoca, o raciocínio que segue.",
        },
    })
    return {"processos": len([p for p in lista_processos if p["coletado"]]), "documentos": docs_exportados,
            "entidades": len(ents), "busca": len(busca), "assercoes": len(todas_assercoes)}
