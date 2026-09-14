"""Mapa do caso em texto: tudo o que a base tem, numa listagem determinística, para quem mantém a base (e para o
modelo que a analisa) enxergar o conjunto e achar o que falta. Não é narrativa: são contagens, listas e lacunas.

Gera docs/MAPA-DO-CASO.md a partir da base (`python -m stf mapa`). Regenerado a cada exportação.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone

from .decisoes import ROTULO_RESULTADO
from .funcoes import funcao_de
from .grafo import construir_grafo


def _linha_tabela(cols: list) -> str:
    return "| " + " | ".join(str(c) for c in cols) + " |"


def gerar_mapa(con: sqlite3.Connection, *, semente: int) -> str:
    q = con.execute
    L: list[str] = []
    L.append("# Mapa do caso (gerado)")
    L.append("")
    L.append(f"Gerado em {datetime.now(timezone.utc).isoformat(timespec='minutes')} por `python -m stf mapa`. Listagem determinística da base; "
             "sem interpretação. Use para achar lacunas: o que ainda não foi coletado, extraído ou ligado.")
    L.append("")

    # ---- processos
    L.append("## Processos")
    L.append("")
    L.append(_linha_tabela(["processo", "incidente", "publicidade", "relator", "profundidade", "andamentos", "partes", "docs (com texto)", "asserções", "decisões (itens)", "coletado em"]))
    L.append(_linha_tabela(["---"] * 11))
    for p in q("SELECT p.classe, p.numero, p.incidente_principal inc, p.status, p.profundidade, i.publicidade, i.relator "
               "FROM processo p LEFT JOIN incidente i ON i.numero=p.incidente_principal ORDER BY p.profundidade, p.classe, p.numero"):
        inc = p["inc"]
        if inc is None or p["relator"] is None:
            L.append(_linha_tabela([f"{p['classe']} {p['numero']}", inc or "—", "—", "—", p["profundidade"], "—", "—", "—", "—", "—", f"não coletado ({p['status']})"]))
            continue
        n_and = q("SELECT COUNT(*) FROM andamento WHERE incidente=?", (inc,)).fetchone()[0]
        n_par = q("SELECT COUNT(*) FROM parte WHERE incidente=? AND e_placeholder=0", (inc,)).fetchone()[0]
        n_doc, n_txt = q("SELECT COUNT(*), SUM(tem_camada_texto IS 1) FROM documento WHERE incidente=?", (inc,)).fetchone()
        n_ass = q("SELECT COUNT(*) FROM assercao a JOIN documento d ON d.id=a.documento_id WHERE d.incidente=?", (inc,)).fetchone()[0]
        n_dec = q("SELECT COUNT(*) FROM decisao_item i JOIN documento d ON d.id=i.documento_id WHERE d.incidente=?", (inc,)).fetchone()[0]
        col = q("SELECT MAX(fetched_at) FROM snapshot WHERE incidente=?", (inc,)).fetchone()[0]
        L.append(_linha_tabela([f"{p['classe']} {p['numero']}" + (" (semente)" if inc == semente else ""), inc, p["publicidade"], p["relator"], p["profundidade"],
                                n_and, n_par, f"{n_doc} ({n_txt or 0})", n_ass, n_dec, (col or "")[:10]]))
    L.append("")

    # ---- relações declaradas
    L.append("## Relações declaradas nos andamentos")
    L.append("")
    for r in q("SELECT p.classe||' '||p.numero origem, r.classe_destino||' '||r.numero_destino destino, r.tipo, a.data "
               "FROM processo_relacao r JOIN processo p ON p.incidente_principal=r.incidente_origem LEFT JOIN andamento a ON a.id=r.fonte_andamento_id ORDER BY 1, 3, 2"):
        L.append(f"- {r['origem']} —{r['tipo']}→ {r['destino']} ({r['data']})")
    L.append("")

    # ---- grafo: contagens e hubs
    g = construir_grafo(con)
    grau: Counter = Counter()
    for e in g["edges"]:
        grau[e["origem"]] += 1; grau[e["destino"]] += 1
    L.append("## Grafo (uso interno)")
    L.append("")
    L.append(f"{len(g['nodes'])} nós, {len(g['edges'])} arestas. Por tipo de aresta: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(e['tipo'] for e in g['edges']).items())) + ".")
    L.append("")
    L.append("Entidades mais ligadas (grau, grupo curado, papéis, asserções que a citam):")
    L.append("")
    ents = sorted((n for n in g["nodes"] if n["tipo"] == "entidade"), key=lambda n: -grau[n["id"]])[:30]
    for n in ents:
        d = n["dados"]
        L.append(f"- {n['rotulo']} — grau {grau[n['id']]}, {d.get('subtipo')}{', ' + d['grupo'] if d.get('grupo') else ''}, papéis {d.get('papeis') or '—'}, {d.get('n_assercoes', 0)} asserções, origem {d.get('origem')}")
    L.append("")
    externos = sorted((n for n in g["nodes"] if n["tipo"] == "processo" and n["dados"].get("externo")), key=lambda n: -grau[n["id"]])
    L.append(f"Processos citados nos documentos e não coletados ({len(externos)}), por número de ligações: " + ", ".join(f"{n['rotulo']} ({grau[n['id']]})" for n in externos[:25]) + ".")
    L.append("")

    # ---- documentos por função e por processo
    L.append("## Documentos por função")
    L.append("")
    cont: dict = defaultdict(Counter)
    for d in q("SELECT d.incidente, d.titulo, EXISTS(SELECT 1 FROM andamento_documento ad JOIN andamento a ON a.id=ad.andamento_id WHERE ad.documento_id=d.id AND a.e_decisao=1) dec FROM documento d"):
        cont[d["incidente"]][funcao_de(d["titulo"], bool(d["dec"]))] += 1
    proc_de = {r["incidente_principal"]: f"{r['classe']} {r['numero']}" for r in q("SELECT classe, numero, incidente_principal FROM processo")}
    for inc, c in sorted(cont.items(), key=lambda x: -sum(x[1].values())):
        L.append(f"- {proc_de.get(inc, inc)}: " + ", ".join(f"{k} {v}" for k, v in c.most_common()))
    L.append("")

    # ---- decisões
    L.append("## Decisões: itens pedido → resultado")
    L.append("")
    tot = Counter(r[0] for r in q("SELECT resultado FROM decisao_item"))
    L.append("Total por resultado: " + ", ".join(f"{ROTULO_RESULTADO.get(k, k)} {v}" for k, v in tot.most_common()) + ".")
    L.append("")
    L.append("Quem mais pediu (campo literal `quem_pediu`, top 12):")
    for k, v in Counter(r[0] for r in q("SELECT quem_pediu FROM decisao_item WHERE quem_pediu IS NOT NULL")).most_common(12):
        L.append(f"- {k}: {v}")
    L.append("")
    L.append("Linha do tempo das decisões com resultado deferido/indeferido/referendado (data, processo, resultado, pedido):")
    L.append("")
    for r in q("SELECT COALESCE(i.data, (SELECT MIN(a.data) FROM andamento_documento ad JOIN andamento a ON a.id=ad.andamento_id WHERE ad.documento_id=d.id)) dt, "
               "d.incidente, i.resultado, i.pedido, i.documento_id, i.pagina FROM decisao_item i JOIN documento d ON d.id=i.documento_id "
               "WHERE i.resultado IN ('deferido','indeferido','parcialmente_deferido','referendado','negado_seguimento','nao_conhecido') ORDER BY dt, i.documento_id, i.id"):
        L.append(f"- {r['dt']} · {proc_de.get(r['incidente'], r['incidente'])} · {r['resultado']} · {r['pedido'][:140]} (doc {r['documento_id']} p. {r['pagina']})")
    L.append("")

    # ---- asserções
    L.append("## Asserções")
    L.append("")
    L.append("Por tipo: " + ", ".join(f"{k} {v}" for k, v in q("SELECT tipo_epistemico, COUNT(*) FROM assercao GROUP BY 1")) + ".")
    L.append("Quem mais afirma (`atribuida_a`, top 12): " + ", ".join(f"{k} {v}" for k, v in Counter(r[0] for r in q("SELECT atribuida_a FROM assercao WHERE atribuida_a IS NOT NULL")).most_common(12)) + ".")
    L.append("")

    # ---- referências
    L.append("## Referências nos documentos")
    L.append("")
    L.append("Dispositivos legais mais citados: " + ", ".join(f"{r[0]} ({r[1]} docs)" for r in q(
        "SELECT dispositivo, COUNT(DISTINCT documento_id) n FROM documento_ref_dispositivo GROUP BY 1 ORDER BY n DESC LIMIT 15")) + ".")
    L.append("")

    # ---- lacunas
    L.append("## Lacunas conhecidas")
    L.append("")
    lac = []
    for r in q("SELECT classe, numero, status FROM processo WHERE incidente_principal IS NULL OR incidente_principal NOT IN (SELECT numero FROM incidente)"):
        lac.append(f"processo {r['classe']} {r['numero']} resolvido mas não coletado ({r['status']})")
    n = q("SELECT COUNT(*) FROM documento WHERE sha256 IS NULL").fetchone()[0]
    if n: lac.append(f"{n} documento(s) sem download")
    n = q("SELECT COUNT(*) FROM documento WHERE sha256 IS NOT NULL AND (tem_camada_texto=0 OR tem_camada_texto IS NULL)").fetchone()[0]
    if n: lac.append(f"{n} documento(s) sem camada de texto (OCR pendente)")
    n = q("SELECT COUNT(*) FROM documento d WHERE d.sha256 IS NOT NULL AND d.tem_camada_texto=1 AND NOT EXISTS (SELECT 1 FROM extracao e WHERE e.documento_id=d.id AND e.prompt_version LIKE 'extracao_v1%' AND e.status='ok')").fetchone()[0]
    if n: lac.append(f"{n} documento(s) sem extração de asserções válida")
    n = q("SELECT COUNT(*) FROM incidente WHERE publicidade LIKE 'Sigil%'").fetchone()[0]
    if n: lac.append(f"{n} processo(s) sigiloso(s): o portal só devolve cabeçalho e andamentos genéricos")
    lac.append(f"{len(externos)} processo(s) citados em documentos e não coletados (a maioria são precedentes; os que importam ao caso aparecem no topo da lista acima)")
    try:
        props = json.loads((__import__('stf.config', fromlist=['DATA']).DATA / "curadoria" / "aliases-propostos.json").read_text("utf-8"))["propostas"]
        lac.append(f"{len(props)} proposta(s) de alias de entidade aguardando decisão humana (data/curadoria/aliases-propostos.json)")
    except (OSError, KeyError, ValueError):
        pass
    for x in lac:
        L.append(f"- {x}")
    L.append("")
    return "\n".join(L) + "\n"
