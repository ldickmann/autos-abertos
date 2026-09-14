"""Grafo de processos e entidades, e relatório de cruzamentos.

Nós: `processo:<Classe>/<numero>` e `entidade:<id>`.
Arestas (toda aresta carrega `fonte`, a proveniência):
- relacao       processo → processo   subtipo: justifica_prevencao | relacionado | autuado_a_partir
- parte_em      entidade → processo   papel (literal e normalizado), bloco
- representa    advogado → parte      incidente em que a representação aparece
- numero_origem processo → processo   fraco: o campo "Número de Origem" cita um número igual ao de
                                      outro processo do grafo, sem classe. Marcado `fraco: true`.

Nada aqui é inferido: cada aresta vem de um campo ou andamento do portal, com snapshot.
"""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict


def _no_processo(row) -> dict:
    return {
        "id": f"processo:{row['classe']}/{row['numero']}", "tipo": "processo",
        "rotulo": f"{row['classe']} {row['numero']}",
        "dados": {
            "classe": row["classe"], "numero": row["numero"], "incidente": row["incidente_principal"],
            "status_resolucao": row["status"], "profundidade": row["profundidade"],
            "relator": row["relator"], "assuntos": json.loads(row["assuntos"]) if row["assuntos"] else [],
            "publicidade": row["publicidade"], "natureza": row["natureza"], "data_protocolo": row["data_protocolo"],
            "coletado": row["relator"] is not None,
        },
    }


def construir_grafo(con: sqlite3.Connection) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []

    processos = con.execute(
        "SELECT p.classe, p.numero, p.incidente_principal, p.status, p.profundidade, "
        "i.relator, i.assuntos, i.publicidade, i.natureza, i.data_protocolo "
        "FROM processo p LEFT JOIN incidente i ON i.numero = p.incidente_principal ORDER BY p.classe, p.numero").fetchall()
    por_incidente = {r["incidente_principal"]: f"processo:{r['classe']}/{r['numero']}" for r in processos if r["incidente_principal"]}
    por_numero: dict[int, list[str]] = defaultdict(list)
    for r in processos:
        nodes.append(_no_processo(r))
        por_numero[r["numero"]].append(f"processo:{r['classe']}/{r['numero']}")

    # relações entre processos
    for r in con.execute(
            "SELECT r.incidente_origem, r.classe_destino, r.numero_destino, r.tipo, r.snapshot_first_seen, "
            "a.data, a.tipo AS andamento_tipo FROM processo_relacao r LEFT JOIN andamento a ON a.id = r.fonte_andamento_id"):
        origem = por_incidente.get(r["incidente_origem"])
        if origem is None:
            continue
        destino = f"processo:{r['classe_destino']}/{r['numero_destino']}"
        if not any(n["id"] == destino for n in nodes):
            nodes.append({"id": destino, "tipo": "processo", "rotulo": f"{r['classe_destino']} {r['numero_destino']}",
                          "dados": {"classe": r["classe_destino"], "numero": r["numero_destino"], "incidente": None,
                                    "status_resolucao": "nao_resolvido", "coletado": False}})
        edges.append({"origem": origem, "destino": destino, "tipo": "relacao",
                      "dados": {"subtipo": r["tipo"], "fonte": {"snapshot": r["snapshot_first_seen"],
                                                                "andamento": f"{r['data']} {r['andamento_tipo']}"}}})

    # entidades e menções
    ents = con.execute("SELECT id, tipo, chave, nome, natureza_provavel FROM entidade ORDER BY id").fetchall()
    for e in ents:
        nodes.append({"id": f"entidade:{e['id']}", "tipo": "entidade", "rotulo": e["nome"],
                      "dados": {"nome": e["nome"], "subtipo": e["tipo"], "chave": e["chave"],
                                "natureza_provavel": e["natureza_provavel"]}})
    mencoes = con.execute(
        "SELECT m.entidade_id, m.incidente, m.papel_portal, m.papel, m.bloco, p.snapshot_first_seen, p.id AS parte_id "
        "FROM entidade_mencao m JOIN parte p ON p.id = m.parte_id ORDER BY m.incidente, m.bloco, p.posicao").fetchall()
    for m in mencoes:
        proc = por_incidente.get(m["incidente"])
        if proc is None:
            continue
        edges.append({"origem": f"entidade:{m['entidade_id']}", "destino": proc, "tipo": "parte_em",
                      "dados": {"papel": m["papel"], "papel_portal": m["papel_portal"], "bloco": m["bloco"],
                                "fonte": {"snapshot": m["snapshot_first_seen"], "parte_id": m["parte_id"]}}})

    # representação: bloco de advogados representa o bloco não-advogado imediatamente anterior, no mesmo incidente
    por_inc_bloco: dict[int, dict[int, list]] = defaultdict(lambda: defaultdict(list))
    for m in mencoes:
        por_inc_bloco[m["incidente"]][m["bloco"]].append(m)
    for inc, blocos in por_inc_bloco.items():
        ordem = sorted(blocos)
        for i, b in enumerate(ordem):
            advs = [m for m in blocos[b] if m["papel"] == "advogado"]
            if not advs:
                continue
            representados: list = []
            for bb in reversed(ordem[:i]):
                nao_adv = [m for m in blocos[bb] if m["papel"] != "advogado"]
                if nao_adv:
                    representados = nao_adv
                    break
            for a in advs:
                for r in representados:
                    edges.append({"origem": f"entidade:{a['entidade_id']}", "destino": f"entidade:{r['entidade_id']}",
                                  "tipo": "representa", "dados": {"incidente": inc, "processo": por_incidente.get(inc),
                                                                  "fonte": {"snapshot": a["snapshot_first_seen"], "parte_id": a["parte_id"]}}})

    # número de origem: coincidência de número puro com outro processo do grafo (fraco)
    for r in con.execute("SELECT p.classe, p.numero, i.numeros_origem, i.snapshot_last_seen FROM processo p "
                         "JOIN incidente i ON i.numero = p.incidente_principal WHERE i.numeros_origem IS NOT NULL"):
        origem = f"processo:{r['classe']}/{r['numero']}"
        for n in json.loads(r["numeros_origem"]):
            if not n.isdigit() or len(n) > 7:
                continue
            for destino in por_numero.get(int(n), []):
                if destino != origem:
                    edges.append({"origem": origem, "destino": destino, "tipo": "numero_origem",
                                  "dados": {"fraco": True, "numero_citado": n,
                                            "fonte": {"snapshot": r["snapshot_last_seen"], "campo": "Número de Origem"}}})
    # profundidade = distância (em arestas `relacao`, sem direção) até a semente mais próxima
    adj: dict[str, set[str]] = defaultdict(set)
    for e in edges:
        if e["tipo"] == "relacao":
            adj[e["origem"]].add(e["destino"]); adj[e["destino"]].add(e["origem"])
    dist: dict[str, int] = {}
    fila = [n["id"] for n in nodes if n["tipo"] == "processo" and n["dados"].get("status_resolucao") == "semente"]
    for s in fila:
        dist[s] = 0
    while fila:
        atual = fila.pop(0)
        for viz in adj[atual]:
            if viz not in dist:
                dist[viz] = dist[atual] + 1
                fila.append(viz)
    for n in nodes:
        if n["tipo"] == "processo":
            n["dados"]["profundidade"] = dist.get(n["id"])
    return {"nodes": nodes, "edges": edges}


def formatar_arestas(g: dict) -> str:
    linhas = [f"{len(g['nodes'])} nós, {len(g['edges'])} arestas"]
    rotulo = {n["id"]: n["rotulo"] for n in g["nodes"]}
    for e in g["edges"]:
        sub = e["dados"].get("subtipo") or e["dados"].get("papel_portal") or ("fraco" if e["dados"].get("fraco") else "")
        extra = f" [{rotulo[e['origem']]} → {rotulo[e['destino']]}]" if e["tipo"] != "relacao" else ""
        linhas.append(f"{e['origem']} --{e['tipo']}{':' + sub if sub else ''}--> {e['destino']}{extra}")
    return "\n".join(linhas)


def cruzamentos(con: sqlite3.Connection) -> dict:
    """O que se repete entre processos. Só fatos do portal, agrupados."""
    proc_de = {r["incidente_principal"]: f"{r['classe']} {r['numero']}" for r in
               con.execute("SELECT classe, numero, incidente_principal FROM processo WHERE incidente_principal IS NOT NULL")}
    multi = []
    for e in con.execute("SELECT id, nome, tipo FROM entidade ORDER BY nome"):
        ms = con.execute("SELECT DISTINCT incidente, papel_portal FROM entidade_mencao WHERE entidade_id=? ORDER BY incidente",
                         (e["id"],)).fetchall()
        incs = sorted({m["incidente"] for m in ms})
        if len(incs) > 1:
            multi.append({"nome": e["nome"], "tipo": e["tipo"],
                          "processos": [{"processo": proc_de.get(i, str(i)), "incidente": i,
                                         "papeis": sorted({m["papel_portal"] for m in ms if m["incidente"] == i})} for i in incs]})

    coincid = []
    por_numero = defaultdict(list)
    for r in con.execute("SELECT classe, numero FROM processo"):
        por_numero[r["numero"]].append(f"{r['classe']} {r['numero']}")
    for r in con.execute("SELECT p.classe, p.numero, i.numeros_origem FROM processo p JOIN incidente i ON i.numero=p.incidente_principal"):
        for n in json.loads(r["numeros_origem"] or "[]"):
            if n.isdigit() and len(n) <= 7 and int(n) in por_numero:
                alvo = [x for x in por_numero[int(n)] if x != f"{r['classe']} {r['numero']}"]
                if alvo:
                    coincid.append({"processo": f"{r['classe']} {r['numero']}", "numero_citado": n, "coincide_com": alvo})

    relacoes = [dict(r) for r in con.execute(
        "SELECT p.classe || ' ' || p.numero AS origem, r.classe_destino || ' ' || r.numero_destino AS destino, r.tipo "
        "FROM processo_relacao r JOIN processo p ON p.incidente_principal = r.incidente_origem ORDER BY 1, 3, 2")]
    return {"entidades_em_varios_processos": multi, "numero_origem_coincidencias": coincid, "relacoes": relacoes}


def formatar_cruzamentos(c: dict) -> str:
    linhas = ["== Entidades presentes em mais de um processo =="]
    for e in c["entidades_em_varios_processos"]:
        linhas.append(f"  {e['nome']} ({e['tipo']}) — {len(e['processos'])} processos")
        for p in e["processos"]:
            linhas.append(f"      {p['processo']} (incidente {p['incidente']}): {', '.join(p['papeis'])}")
    if not c["entidades_em_varios_processos"]:
        linhas.append("  nenhuma")
    linhas.append("== Relações declaradas nos andamentos ==")
    for r in c["relacoes"]:
        linhas.append(f"  {r['origem']} --{r['tipo']}--> {r['destino']}")
    linhas.append("== Coincidências de 'Número de Origem' (número puro, sem classe; ligação fraca) ==")
    for x in c["numero_origem_coincidencias"]:
        linhas.append(f"  {x['processo']} cita {x['numero_citado']} → coincide com {', '.join(x['coincide_com'])}")
    if not c["numero_origem_coincidencias"]:
        linhas.append("  nenhuma")
    return "\n".join(linhas)
