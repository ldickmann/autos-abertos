"""Grafo de processos e entidades, e relatório de cruzamentos.

Nós: `processo:<Classe>/<numero>` e `entidade:<id>`.
Arestas (toda aresta carrega `fonte`, a proveniência):
- relacao       processo → processo   subtipo: justifica_prevencao | relacionado | autuado_a_partir
- parte_em      entidade → processo   papel (literal e normalizado), bloco
- representa    advogado → parte      incidente em que a representação aparece
- numero_origem processo → processo   fraco: o campo "Número de Origem" cita um número igual ao de
                                      outro processo do grafo, sem classe. Marcado `fraco: true`.
- cita_processo processo → processo   documentos do primeiro citam o segundo no texto (documento_ref_processo);
                                      o destino pode ser "externo" (citado, não coletado): `dados.externo`
- citado_em     entidade → processo   a entidade é citada em asserções extraídas de documentos do processo
- afirma_em     entidade → processo   asserções `alegacao_parte`/`fundamento_decisorio` atribuídas à entidade
- co_citacao    entidade — entidade   as duas aparecem na mesma asserção (coocorrência literal, com o trecho);
                                      nunca entre ministros/advogados; não é "envolvimento", é coocorrência
- relator_de    ministro → processo   campo Relator do cadastro
- votou_em      ministro → processo   voto registrado na sessão virtual (tipo de voto literal)

Nada aqui é inferido: cada aresta vem de um campo, andamento, documento/página ou asserção validada, com fonte.
Nós sem nenhuma aresta são removidos do grafo (continuam na base e na página de entidades).
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict

from .entidades import chave_ministro, chave_nome


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
    ents = con.execute(
        "SELECT e.id, e.tipo, e.chave, e.nome, e.natureza_provavel, e.origem, e.grupo, "
        "(SELECT COUNT(*) FROM assercao_entidade ae WHERE ae.entidade_id=e.id) AS n_assercoes, "
        "(SELECT COUNT(DISTINCT m.incidente) FROM entidade_mencao m WHERE m.entidade_id=e.id) AS n_processos, "
        "(SELECT json_group_array(DISTINCT m.papel) FROM entidade_mencao m WHERE m.entidade_id=e.id) AS papeis "
        "FROM entidade e ORDER BY e.id").fetchall()
    for e in ents:
        nodes.append({"id": f"entidade:{e['id']}", "tipo": "entidade", "rotulo": e["nome"],
                      "dados": {"nome": e["nome"], "subtipo": e["tipo"], "chave": e["chave"],
                                "natureza_provavel": e["natureza_provavel"], "origem": e["origem"], "grupo": e["grupo"],
                                "n_assercoes": e["n_assercoes"], "n_processos": e["n_processos"],
                                "papeis": json.loads(e["papeis"] or "[]")}})
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

    # citações em documentos: processo → processo citado (interno ou externo)
    ids_nos = {n["id"] for n in nodes}
    cit = con.execute(
        "SELECT d.incidente, r.classe, r.numero, COUNT(DISTINCT r.documento_id) n_docs, SUM(r.ocorrencias) n_oc, "
        "json_group_array(json_object('documento_id', r.documento_id, 'pagina', r.pagina)) fontes "
        "FROM documento_ref_processo r JOIN documento d ON d.id=r.documento_id GROUP BY d.incidente, r.classe, r.numero").fetchall()
    for r in cit:
        origem = por_incidente.get(r["incidente"])
        destino = f"processo:{r['classe']}/{r['numero']}"
        if origem is None or origem == destino:
            continue
        if destino not in ids_nos:
            nodes.append({"id": destino, "tipo": "processo", "rotulo": f"{r['classe']} {r['numero']}",
                          "dados": {"classe": r["classe"], "numero": r["numero"], "incidente": None,
                                    "status_resolucao": "citado", "coletado": False, "externo": True}})
            ids_nos.add(destino)
        edges.append({"origem": origem, "destino": destino, "tipo": "cita_processo",
                      "dados": {"n_docs": r["n_docs"], "n_ocorrencias": r["n_oc"], "externo": destino not in por_incidente.values(),
                                "fonte": {"documentos": json.loads(r["fontes"])[:25]}}})

    # asserções: entidade citada em processo; entidade que afirma; coocorrência entidade—entidade
    for r in con.execute(
            "SELECT ae.entidade_id, d.incidente, COUNT(*) n, "
            "json_group_array(json_object('assercao_id', a.id, 'documento_id', a.documento_id, 'pagina', a.pagina)) fontes "
            "FROM assercao_entidade ae JOIN assercao a ON a.id=ae.assercao_id JOIN documento d ON d.id=a.documento_id "
            "GROUP BY ae.entidade_id, d.incidente"):
        proc = por_incidente.get(r["incidente"])
        if proc:
            edges.append({"origem": f"entidade:{r['entidade_id']}", "destino": proc, "tipo": "citado_em",
                          "dados": {"n": r["n"], "fonte": {"assercoes": json.loads(r["fontes"])[:25]}}})
    chave_para_id = {e["chave"]: e["id"] for e in ents}
    afirma: dict[tuple[int, str, str], list] = defaultdict(list)
    for a in con.execute("SELECT a.id, a.documento_id, a.pagina, a.tipo_epistemico, a.atribuida_a, d.incidente "
                         "FROM assercao a JOIN documento d ON d.id=a.documento_id WHERE a.atribuida_a IS NOT NULL"):
        nome = a["atribuida_a"].strip()
        eid = chave_para_id.get(chave_ministro(nome)) or chave_para_id.get(chave_nome(nome))
        if eid is None:
            continue
        afirma[(eid, a["incidente"], a["tipo_epistemico"])].append({"assercao_id": a["id"], "documento_id": a["documento_id"], "pagina": a["pagina"]})
    for (eid, inc, tipo_ep), fontes in afirma.items():
        proc = por_incidente.get(inc)
        if proc:
            edges.append({"origem": f"entidade:{eid}", "destino": proc, "tipo": "afirma_em",
                          "dados": {"subtipo": tipo_ep, "n": len(fontes), "fonte": {"assercoes": fontes[:25]}}})
    excluidos = {e["id"] for e in ents if e["tipo"] in ("ministro", "advogado")}
    co: dict[tuple[int, int], list] = defaultdict(list)
    for r in con.execute("SELECT x.entidade_id a, y.entidade_id b, s.id assercao_id, s.documento_id, s.pagina "
                         "FROM assercao_entidade x JOIN assercao_entidade y ON y.assercao_id=x.assercao_id AND y.entidade_id>x.entidade_id "
                         "JOIN assercao s ON s.id=x.assercao_id"):
        if r["a"] in excluidos or r["b"] in excluidos:
            continue
        co[(r["a"], r["b"])].append({"assercao_id": r["assercao_id"], "documento_id": r["documento_id"], "pagina": r["pagina"]})
    for (a, b), fontes in co.items():
        edges.append({"origem": f"entidade:{a}", "destino": f"entidade:{b}", "tipo": "co_citacao",
                      "dados": {"n": len(fontes), "fonte": {"assercoes": fontes[:10]}}})

    # ministros: relator e votos
    for r in con.execute("SELECT p.classe, p.numero, i.relator, i.snapshot_last_seen FROM processo p JOIN incidente i ON i.numero=p.incidente_principal WHERE i.relator IS NOT NULL"):
        eid = chave_para_id.get(chave_ministro(r["relator"]))
        if eid:
            edges.append({"origem": f"entidade:{eid}", "destino": f"processo:{r['classe']}/{r['numero']}", "tipo": "relator_de",
                          "dados": {"fonte": {"snapshot": r["snapshot_last_seen"], "campo": "Relator"}}})
    for r in con.execute("SELECT v.ministro, v.tipo_voto, v.data, l.nome_lista, l.snapshot_last_seen, o.incidente_principal, o.identificacao "
                         "FROM voto v JOIN lista_julgamento l ON l.id=v.lista_id JOIN objeto_incidente o ON o.id=l.objeto_incidente_id"):
        eid = chave_para_id.get(chave_ministro(r["ministro"] or ""))
        proc = por_incidente.get(r["incidente_principal"])
        if eid and proc:
            edges.append({"origem": f"entidade:{eid}", "destino": proc, "tipo": "votou_em",
                          "dados": {"tipo_voto": r["tipo_voto"], "data": r["data"], "objeto": r["identificacao"], "lista": r["nome_lista"],
                                    "fonte": {"snapshot": r["snapshot_last_seen"], "campo": "sessão virtual"}}})

    # nós sem aresta saem do grafo (ficam na base e na página de entidades)
    grau: Counter = Counter()
    for e in edges:
        grau[e["origem"]] += 1
        grau[e["destino"]] += 1
    nodes = [n for n in nodes if grau[n["id"]] > 0 or (n["tipo"] == "processo" and not n["dados"].get("externo"))]
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


def atualizar_profundidade(con: sqlite3.Connection) -> int:
    """Persiste em `processo.profundidade` a distância até a semente calculada pelo grafo (só para quem tem incidente)."""
    n = 0
    with con:
        for no in construir_grafo(con)["nodes"]:
            if no["tipo"] == "processo" and no["dados"].get("profundidade") is not None and not no["dados"].get("externo"):
                con.execute("UPDATE processo SET profundidade=? WHERE classe=? AND numero=?",
                            (no["dados"]["profundidade"], no["dados"]["classe"], no["dados"]["numero"]))
                n += 1
    return n


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
    citados = [dict(r) for r in con.execute(
        "SELECT r.classe, r.numero, COUNT(DISTINCT r.documento_id) n_docs, COUNT(DISTINCT d.incidente) n_processos, "
        "EXISTS(SELECT 1 FROM processo p WHERE p.classe=r.classe AND p.numero=r.numero) AS interno "
        "FROM documento_ref_processo r JOIN documento d ON d.id=r.documento_id GROUP BY r.classe, r.numero "
        "HAVING n_processos > 1 OR n_docs >= 3 ORDER BY n_processos DESC, n_docs DESC")]
    dispositivos = [dict(r) for r in con.execute(
        "SELECT r.dispositivo, COUNT(DISTINCT r.documento_id) n_docs, COUNT(DISTINCT d.incidente) n_processos "
        "FROM documento_ref_dispositivo r JOIN documento d ON d.id=r.documento_id GROUP BY r.dispositivo "
        "HAVING n_processos > 1 ORDER BY n_processos DESC, n_docs DESC LIMIT 40")]
    relator_por_chave: dict[str, list[str]] = defaultdict(list)
    for r in con.execute("SELECT p.classe, p.numero, i.relator FROM processo p JOIN incidente i ON i.numero=p.incidente_principal WHERE i.relator IS NOT NULL"):
        relator_por_chave[chave_ministro(r["relator"])].append(f"{r['classe']} {r['numero']}")
    ministros = [{"nome": e["nome"], "relator_de": relator_por_chave.get(e["chave"], [])}
                 for e in con.execute("SELECT nome, chave FROM entidade WHERE tipo='ministro' ORDER BY nome")]
    return {"entidades_em_varios_processos": multi, "numero_origem_coincidencias": coincid, "relacoes": relacoes,
            "processos_citados_em_documentos": citados, "dispositivos_em_varios_processos": dispositivos, "ministros": ministros}


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
    linhas.append("== Processos citados no texto dos documentos (em mais de um processo, ou por 3+ documentos) ==")
    for x in c.get("processos_citados_em_documentos", []):
        linhas.append(f"  {x['classe']} {x['numero']}: {x['n_docs']} doc(s) em {x['n_processos']} processo(s){'' if x['interno'] else ' [externo, não coletado]'}")
    linhas.append("== Dispositivos legais citados em mais de um processo ==")
    for x in c.get("dispositivos_em_varios_processos", []):
        linhas.append(f"  {x['dispositivo']}: {x['n_docs']} doc(s) em {x['n_processos']} processo(s)")
    linhas.append("== Coincidências de 'Número de Origem' (número puro, sem classe; ligação fraca) ==")
    for x in c["numero_origem_coincidencias"]:
        linhas.append(f"  {x['processo']} cita {x['numero_citado']} → coincide com {', '.join(x['coincide_com'])}")
    if not c["numero_origem_coincidencias"]:
        linhas.append("  nenhuma")
    return "\n".join(linhas)
