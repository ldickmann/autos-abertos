"""CLI: python -m stf <comando> [args]

  coletar <incidente>          coleta educada (casca + abas) e ingere no banco
  importar-fase0               registra os snapshots brutos da Fase 0 como uma coleta
  ingerir <registro.jsonl>     projeta uma coleta já gravada no banco
  reconstruir                  apaga a projeção e reingere todas as coletas (prova que os blobs são a fonte)
  diff <coleta_a> <coleta_b>   compara duas coletas (ids ou caminhos de registro)
  buscar "<termos>"            busca FTS5 em andamentos
  status                       contagens do banco
  expandir <incidente>         resolve processos relacionados e coleta cada um por completo (--profundidade, --teto)
  entidades                    (re)constrói entidades canônicas a partir das partes
  grafo                        imprime a lista de arestas e grava data/grafo.json
  cruzamentos                  o que se repete entre processos (entidades, relações, números de origem)
  sessao <incidente>|--todos   coleta só os JSONs de sessão virtual (objetos incidente, listas, votos)
  baixar-docs [--incidente N]  baixa documentos ainda não baixados (cache por sha256) e extrai o texto
  acervo <pacote.7z|.zip> --url U --incidente N --pasta P   registra peças do acervo público do STF como documentos
  ingerir-fluxos <dataset.json>   valida o dataset curado de fluxos financeiros (trechos por página) e carrega em fluxo_*
  fluxos                        resumo dos fluxos carregados (fontes, atores, totais por par)
  extrair-texto                texto por página, chunks e código de autenticação dos documentos baixados
  buscar-docs "<termos>"       busca FTS5 no texto dos documentos, com página
  sessoes                      listas de julgamento virtual e votos por ministro
  extrair-assercoes            Fase 4: LLM sobre documentos (--documentos 1,2,3 | --limite N | --dry-run | --modelo)
  assercoes [--documento N]    lista asserções com tipo epistêmico, página e trecho-fonte
  exportar [--saida DIR]       JSON estático para a interface (padrão: web/public/data), semente 7514886
  preparar-extracao            Fase 4 pelo Claude Code: grava data/extracao/entradas/<id>.entrada.md + MANIFEST.json
  ingerir-extracao             lê data/extracao/respostas/<id>.json, valida e persiste (mesma validação da API)
  preparar-decisoes            entradas para pedidos/resultados por decisão (data/extracao/decisoes/entradas)
  ingerir-decisoes             lê data/extracao/decisoes/respostas/<id>.json, valida e persiste em decisao_item
  legislativo                  consulta as APIs de dados abertos do Senado e da Câmara (stf/curadoria/legislativo.json)
  capturar-externas            copia (com hash) as fontes oficiais externas de stf/curadoria/fontes_externas.json
  vigiar                       recoleta cada processo, compara com a cópia anterior e registra em CHANGELOG-PORTAL.md
  verificar                    recalcula o sha256 de cada blob local e compara com o registrado
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
import sys
from pathlib import Path

from . import config
from .db import abrir, apagar_projecao, criar_schema
from .diff import diff_coletas, formatar_diff
from .ingest import ingerir_coleta, resumo


def _registro(ref: str) -> Path:
    p = Path(ref)
    if p.exists():
        return p
    p = config.COLETAS / f"{ref}.jsonl"
    if p.exists():
        return p
    sys.exit(f"coleta não encontrada: {ref}")


def _con():
    config.DATA.mkdir(parents=True, exist_ok=True)
    con = abrir(config.BANCO)
    criar_schema(con)
    return con


def cmd_coletar(args):
    from .coleta import coletar_incidente
    reg = coletar_incidente(args.incidente)
    print(f"registro: {reg}")
    r = ingerir_coleta(_con(), reg)
    print("ingerido:", json.dumps(r, ensure_ascii=False))


def cmd_importar_fase0(args):
    from .importar_fase0 import importar
    reg = importar()
    print(f"registro: {reg}")
    r = ingerir_coleta(_con(), reg)
    print("ingerido:", json.dumps(r, ensure_ascii=False))


def cmd_ingerir(args):
    r = ingerir_coleta(_con(), _registro(args.registro))
    print(json.dumps(r, ensure_ascii=False))


def cmd_reconstruir(args):
    from .documentos import extrair_texto
    from .entidades import construir_entidades
    from .referencias import construir_referencias
    from .grafo import atualizar_profundidade
    con = _con()
    apagar_projecao(con)
    criar_schema(con)
    for reg in sorted(config.COLETAS.glob("*.jsonl")):
        r = ingerir_coleta(con, reg)
        print(f"{reg.name}: {json.dumps(r, ensure_ascii=False)}")
    print("texto:", json.dumps(extrair_texto(con, log=lambda s: None), ensure_ascii=False))
    print("entidades:", json.dumps(construir_entidades(con), ensure_ascii=False))
    print("referencias:", json.dumps(construir_referencias(con), ensure_ascii=False))
    print("profundidade:", atualizar_profundidade(con), "processos")
    from .externas import reingerir_externas
    print("fontes externas:", reingerir_externas(con), "capturas reingeridas do registro")
    from .legislativo import reingerir_legislativo
    print("legislativo:", reingerir_legislativo(con), "matérias reingeridas do registro")


def cmd_diff(args):
    print(formatar_diff(diff_coletas(_registro(args.a), _registro(args.b))))


def cmd_buscar(args):
    con = _con()
    rows = con.execute(
        "SELECT a.incidente, a.data, a.tipo, snippet(andamento_fts, 0, '[', ']', '…', 12) AS trecho, "
        "a.snapshot_first_seen, a.e_decisao "
        "FROM andamento_fts JOIN andamento a ON a.id = andamento_fts.rowid "
        "WHERE andamento_fts MATCH ? ORDER BY a.data DESC LIMIT ?", (args.termos, args.limite)).fetchall()
    for r in rows:
        flag = " [decisão]" if r["e_decisao"] else ""
        print(f"{r['data']} | {r['tipo']}{flag} | {r['trecho']}  (snapshot {r['snapshot_first_seen']})")
    print(f"{len(rows)} resultado(s)")


def cmd_expandir(args):
    from .coleta import ClienteEducado
    from .entidades import construir_entidades
    from .expandir import expandir
    con = _con()
    rel = expandir(con, args.incidente, profundidade=args.profundidade, cliente=ClienteEducado(teto=args.teto))
    print(json.dumps({k: v for k, v in rel.__dict__.items()}, ensure_ascii=False, indent=2, default=str))
    print("entidades:", json.dumps(construir_entidades(con), ensure_ascii=False))


def cmd_referencias(args):
    from .referencias import construir_referencias, contagem_por_diploma, resumo_dispositivos
    con = _con()
    criar_schema(con)
    print(json.dumps(construir_referencias(con), ensure_ascii=False))
    print("por diploma:", dict(contagem_por_diploma(con).most_common()))
    for d in resumo_dispositivos(con)[:args.top]:
        print(f"  {d['dispositivo']:32s} {len(d['documentos']):3d} doc(s)  {d['ocorrencias']:3d} ocorrência(s)")


def cmd_aliases_propor(args):
    from .aliases import propor_aliases
    con = _con()
    props = propor_aliases(con)
    saida = config.DATA / "curadoria" / "aliases-propostos.json"
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps({"gerado_em": datetime.now(timezone.utc).isoformat(), "limiar": 0.9, "propostas": props},
                                ensure_ascii=False, indent=1), "utf-8")
    print(f"{len(props)} proposta(s) → {saida}")
    for x in props[:args.top]:
        print(f"  {x['similaridade']:.3f}  {x['a']['nome']}  ~  {x['b']['nome']}{'  [pessoas]' if x['pessoas'] else ''}")


def cmd_entidades(args):
    from .entidades import construir_entidades
    print(json.dumps(construir_entidades(_con()), ensure_ascii=False))


def cmd_grafo(args):
    from .grafo import construir_grafo, formatar_arestas
    g = construir_grafo(_con())
    saida = config.DATA / "grafo.json"
    saida.write_text(json.dumps(g, ensure_ascii=False, indent=1), "utf-8")
    print(formatar_arestas(g))
    print(f"\ngravado: {saida}")


def cmd_cruzamentos(args):
    from .grafo import cruzamentos, formatar_cruzamentos
    print(formatar_cruzamentos(cruzamentos(_con())))


def cmd_sessao(args):
    from .coleta import ClienteEducado, coletar_sessao_virtual
    con = _con()
    incs = [r[0] for r in con.execute("SELECT numero FROM incidente ORDER BY numero")] if args.todos else [args.incidente]
    cliente = ClienteEducado(teto=10 * max(1, len(incs)))
    for inc in incs:
        reg = coletar_sessao_virtual(inc, cliente=cliente)
        print(json.dumps(ingerir_coleta(con, reg), ensure_ascii=False))


def cmd_baixar_docs(args):
    from .documentos import baixar_documentos, extrair_texto
    con = _con()
    print(json.dumps(baixar_documentos(con, incidente=args.incidente, teto=args.teto), ensure_ascii=False))
    print("texto:", json.dumps(extrair_texto(con), ensure_ascii=False))


def cmd_extrair_texto(args):
    from .documentos import extrair_texto
    print(json.dumps(extrair_texto(_con()), ensure_ascii=False))


def cmd_buscar_docs(args):
    con = _con()
    rows = con.execute(
        "SELECT d.incidente, d.endpoint, d.id_portal, d.titulo, p.pagina, "
        "snippet(documento_fts, 0, '[', ']', '…', 14) AS trecho "
        "FROM documento_fts JOIN documento_pagina p ON p.rowid = documento_fts.rowid JOIN documento d ON d.id = p.documento_id "
        "WHERE documento_fts MATCH ? ORDER BY rank LIMIT ?", (args.termos, args.limite)).fetchall()
    for r in rows:
        print(f"inc {r['incidente']} | {r['titulo']} ({r['endpoint']}/{r['id_portal']}) p.{r['pagina']} | {r['trecho']}")
    print(f"{len(rows)} resultado(s)")


def cmd_sessoes(args):
    con = _con()
    for l in con.execute("SELECT l.*, o.identificacao, o.incidente_principal FROM lista_julgamento l "
                         "JOIN objeto_incidente o ON o.id = l.objeto_incidente_id ORDER BY l.data_inicio"):
        print(f"{l['identificacao']} (inc {l['incidente_principal']}) | lista {l['nome_lista']} | {l['colegiado']} "
              f"{l['data_inicio']}→{l['data_fim']} | relator {l['relator']} | julgado={l['julgado']} | resultado={l['resultado']}")
        for v in con.execute("SELECT ministro, tipo_voto, data FROM voto WHERE lista_id=? ORDER BY ordem", (l["id"],)):
            print(f"    {v['data']} {v['ministro']}: {v['tipo_voto']}")


def cmd_extrair_assercoes(args):
    from .semantica import MODELO_PADRAO, PROMPT_TEXTO, PROMPT_VERSION, estimar_tokens, extrair_assercoes
    con = _con()
    docs = [int(x) for x in args.documentos.split(",")] if args.documentos else None
    est = estimar_tokens(con, docs)
    print(f"prompt_version={PROMPT_VERSION} modelo={args.modelo or MODELO_PADRAO}")
    print("estimativa:", json.dumps(est, ensure_ascii=False))
    if args.dry_run:
        print("--- prompt ---"); print(PROMPT_TEXTO)
        return
    import os
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        sys.exit("sem credencial: defina ANTHROPIC_API_KEY (ou use `ant auth login`) antes de rodar a extração")
    from .semantica import ClienteAnthropic
    cliente = ClienteAnthropic(modelo=args.modelo or MODELO_PADRAO, effort=args.effort)
    r = extrair_assercoes(con, cliente, documentos=docs, limite=args.limite)
    print(json.dumps(r, ensure_ascii=False))


def cmd_assercoes(args):
    con = _con()
    sql = ("SELECT a.id, a.documento_id, d.titulo, d.incidente, a.pagina, a.tipo_epistemico, a.texto, a.trecho_fonte, a.atribuida_a "
           "FROM assercao a JOIN documento d ON d.id=a.documento_id")
    params: list = []
    if args.documento:
        sql += " WHERE a.documento_id=?"; params.append(args.documento)
    sql += " ORDER BY a.documento_id, a.pagina, a.id"
    for r in con.execute(sql, params):
        print(f"#{r['id']} doc {r['documento_id']} ({r['titulo']}, inc {r['incidente']}) p.{r['pagina']} [{r['tipo_epistemico']}]"
              + (f" atribuída a {r['atribuida_a']}" if r["atribuida_a"] else ""))
        print(f"    {r['texto']}")
        print(f"    fonte: \"{r['trecho_fonte'][:160]}\"")


def cmd_preparar_extracao(args):
    from .semantica import preparar_entradas
    docs = [int(x) for x in args.documentos.split(",")] if args.documentos else None
    saida = config.DATA / "extracao" / "entradas"
    print(json.dumps(preparar_entradas(_con(), saida, documentos=docs, limite=args.limite, modelo=args.modelo), ensure_ascii=False), "→", saida)


def cmd_ingerir_extracao(args):
    from .semantica import ClienteArquivo, extrair_assercoes
    docs = [int(x) for x in args.documentos.split(",")] if args.documentos else None
    from .datas import construir_datas
    con = _con()
    criar_schema(con)
    cliente = ClienteArquivo(config.DATA / "extracao" / "respostas", modelo=args.modelo)
    print(json.dumps(extrair_assercoes(con, cliente, documentos=docs, log=print), ensure_ascii=False))
    print("datas:", json.dumps(construir_datas(con), ensure_ascii=False))


def cmd_preparar_decisoes(args):
    from .decisoes import preparar_entradas
    docs = [int(x) for x in args.documentos.split(",")] if args.documentos else None
    saida = config.DATA / "extracao" / "decisoes" / "entradas"
    print(json.dumps(preparar_entradas(_con(), saida, documentos=docs, modelo=args.modelo), ensure_ascii=False), "→", saida)


def cmd_ingerir_decisoes(args):
    from .decisoes import ingerir_decisoes
    from .semantica import ClienteArquivo
    docs = [int(x) for x in args.documentos.split(",")] if args.documentos else None
    con = _con()
    criar_schema(con)
    cliente = ClienteArquivo(config.DATA / "extracao" / "decisoes" / "respostas", modelo=args.modelo)
    print(json.dumps(ingerir_decisoes(con, cliente, documentos=docs, log=print), ensure_ascii=False))


def cmd_legislativo(args):
    from .legislativo import CONSULTAS, REGISTRO, consultar
    con = _con()
    criar_schema(con)
    print(json.dumps(consultar(con, CONSULTAS, registro=REGISTRO), ensure_ascii=False))


def cmd_capturar_externas(args):
    from .externas import REGISTRO, capturar_fontes, fontes_curadas
    con = _con()
    criar_schema(con)
    print(json.dumps(capturar_fontes(con, fontes_curadas(), registro=REGISTRO), ensure_ascii=False))


def cmd_vigiar(args):
    from .vigiar import registrar, vigiar
    incs = [int(x) for x in args.incidentes.split(",")] if args.incidentes else None
    rel = vigiar(_con(), incidentes=incs)
    registrar(rel)
    print(json.dumps([{"processo": r["processo"], **r["resumo"]} for r in rel], ensure_ascii=False))


def cmd_acervo(args):
    from .acervo import registrar_acervo
    from .documentos import extrair_texto
    con = _con()
    r = registrar_acervo(con, arquivo=Path(args.pacote), url=args.url, incidente=args.incidente, pasta=args.pasta,
                         fetched_at=args.fetched_at, user_agent=args.user_agent)
    print(json.dumps(r, ensure_ascii=False))
    print(json.dumps(extrair_texto(con), ensure_ascii=False))


def cmd_ingerir_fluxos(args):
    from .fluxos_carga import ingerir_fluxos
    print(json.dumps(ingerir_fluxos(_con(), Path(args.arquivo)), ensure_ascii=False))


def cmd_fluxos(args):
    con = _con()
    for r in con.execute("SELECT tipo, identificador, orgao, documento_id, carregado_em FROM fluxo_fonte"):
        print("fonte:", dict(r))
    print("atores:", con.execute("SELECT COUNT(*) FROM fluxo_ator").fetchone()[0],
          "comunicações:", con.execute("SELECT COUNT(*) FROM fluxo_comunicacao").fetchone()[0],
          "transações:", con.execute("SELECT COUNT(*) FROM fluxo_transacao").fetchone()[0])
    print("maiores pares (origem → destino, soma em R$, natureza individual/agregado):")
    for r in con.execute(
            "SELECT o.nome, d.nome, SUM(t.valor_centavos), COUNT(*) FROM fluxo_transacao t "
            "LEFT JOIN fluxo_ator o ON o.id=t.origem_ator_id LEFT JOIN fluxo_ator d ON d.id=t.destino_ator_id "
            "WHERE t.natureza != 'resumo_tipo' GROUP BY 1,2 ORDER BY 3 DESC LIMIT 15"):
        print(f"  {r[0] or '(não informado)'} → {r[1] or '(não informado)'}: R$ {r[2]/100:,.2f} ({r[3]})")


def cmd_verificar(args):
    from .integridade import verificar_blobs
    r = verificar_blobs(_con())
    print(json.dumps({k: v for k, v in r.items() if k != "problemas"}, ensure_ascii=False))
    for x in r["problemas"][:50]:
        print("  ", json.dumps(x, ensure_ascii=False))
    raise SystemExit(0 if not r["problemas"] else 1)


def cmd_mapa(args):
    from .mapa import gerar_mapa
    saida = config.RAIZ / "docs" / "MAPA-DO-CASO.md"
    saida.parent.mkdir(exist_ok=True)
    saida.write_text(gerar_mapa(_con(), semente=args.semente), "utf-8")
    print("mapa →", saida)


def cmd_exportar(args):
    from .exportar import exportar
    from .mapa import gerar_mapa
    saida = Path(args.saida) if args.saida else config.RAIZ / "web" / "public" / "data"
    con = _con()
    print(json.dumps(exportar(con, saida, semente=args.semente), ensure_ascii=False), "→", saida)
    mapa = config.RAIZ / "docs" / "MAPA-DO-CASO.md"
    mapa.parent.mkdir(exist_ok=True)
    mapa.write_text(gerar_mapa(con, semente=args.semente), "utf-8")
    print("mapa →", mapa)
    from .integridade import gerar_manifesto
    man = gerar_manifesto(con)
    (saida / "integridade.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), "utf-8")
    (config.RAIZ / "INTEGRIDADE.sha256").write_text(f"{man['raiz_sha256']}  integridade.json  gerado_em={man['gerado_em']}\n", "utf-8", newline="\n")
    print("integridade →", saida / "integridade.json", "| raiz", man["raiz_sha256"][:16] + "…")


def cmd_status(args):
    con = _con()
    print(json.dumps(resumo(con), ensure_ascii=False, indent=2))
    for r in con.execute("SELECT id, incidente, ingerida_em FROM coleta ORDER BY id"):
        print(f"  coleta {r['id']}  incidente {r['incidente']}  ingerida {r['ingerida_em'][:19]}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="stf", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("coletar"); p.add_argument("incidente", type=int); p.set_defaults(f=cmd_coletar)
    p = sub.add_parser("importar-fase0"); p.set_defaults(f=cmd_importar_fase0)
    p = sub.add_parser("ingerir"); p.add_argument("registro"); p.set_defaults(f=cmd_ingerir)
    p = sub.add_parser("reconstruir"); p.set_defaults(f=cmd_reconstruir)
    p = sub.add_parser("diff"); p.add_argument("a"); p.add_argument("b"); p.set_defaults(f=cmd_diff)
    p = sub.add_parser("buscar"); p.add_argument("termos"); p.add_argument("--limite", type=int, default=20); p.set_defaults(f=cmd_buscar)
    p = sub.add_parser("status"); p.set_defaults(f=cmd_status)
    p = sub.add_parser("expandir"); p.add_argument("incidente", type=int)
    p.add_argument("--profundidade", type=int, default=1); p.add_argument("--teto", type=int, default=config.TETO_REQUISICOES_POR_EXPANSAO)
    p.set_defaults(f=cmd_expandir)
    p = sub.add_parser("referencias"); p.add_argument("--top", type=int, default=20); p.set_defaults(f=cmd_referencias)
    p = sub.add_parser("aliases-propor"); p.add_argument("--top", type=int, default=15); p.set_defaults(f=cmd_aliases_propor)
    p = sub.add_parser("entidades"); p.set_defaults(f=cmd_entidades)
    p = sub.add_parser("grafo"); p.set_defaults(f=cmd_grafo)
    p = sub.add_parser("cruzamentos"); p.set_defaults(f=cmd_cruzamentos)
    p = sub.add_parser("sessao"); p.add_argument("incidente", type=int, nargs="?"); p.add_argument("--todos", action="store_true"); p.set_defaults(f=cmd_sessao)
    p = sub.add_parser("baixar-docs"); p.add_argument("--incidente", type=int); p.add_argument("--teto", type=int); p.set_defaults(f=cmd_baixar_docs)
    p = sub.add_parser("extrair-texto"); p.set_defaults(f=cmd_extrair_texto)
    p = sub.add_parser("buscar-docs"); p.add_argument("termos"); p.add_argument("--limite", type=int, default=20); p.set_defaults(f=cmd_buscar_docs)
    p = sub.add_parser("sessoes"); p.set_defaults(f=cmd_sessoes)
    p = sub.add_parser("extrair-assercoes"); p.add_argument("--documentos"); p.add_argument("--limite", type=int)
    p.add_argument("--dry-run", action="store_true"); p.add_argument("--modelo"); p.add_argument("--effort", default="high")
    p.set_defaults(f=cmd_extrair_assercoes)
    p = sub.add_parser("assercoes"); p.add_argument("--documento", type=int); p.set_defaults(f=cmd_assercoes)
    p = sub.add_parser("legislativo"); p.set_defaults(f=cmd_legislativo)
    p = sub.add_parser("capturar-externas"); p.set_defaults(f=cmd_capturar_externas)
    p = sub.add_parser("vigiar"); p.add_argument("--incidentes"); p.set_defaults(f=cmd_vigiar)
    p = sub.add_parser("acervo"); p.add_argument("pacote"); p.add_argument("--url", required=True)
    p.add_argument("--incidente", type=int, required=True); p.add_argument("--pasta", required=True)
    p.add_argument("--fetched-at", dest="fetched_at"); p.add_argument("--user-agent", dest="user_agent"); p.set_defaults(f=cmd_acervo)
    p = sub.add_parser("ingerir-fluxos"); p.add_argument("arquivo"); p.set_defaults(f=cmd_ingerir_fluxos)
    p = sub.add_parser("fluxos"); p.set_defaults(f=cmd_fluxos)
    p = sub.add_parser("verificar"); p.set_defaults(f=cmd_verificar)
    p = sub.add_parser("mapa"); p.add_argument("--semente", type=int, default=7514886); p.set_defaults(f=cmd_mapa)
    p = sub.add_parser("exportar"); p.add_argument("--saida"); p.add_argument("--semente", type=int, default=7514886); p.set_defaults(f=cmd_exportar)
    p = sub.add_parser("preparar-extracao"); p.add_argument("--documentos"); p.add_argument("--limite", type=int)
    p.add_argument("--modelo", default="claude-code/claude-opus-5"); p.set_defaults(f=cmd_preparar_extracao)
    p = sub.add_parser("ingerir-extracao"); p.add_argument("--documentos"); p.add_argument("--modelo", default="claude-code/claude-opus-5")
    p.set_defaults(f=cmd_ingerir_extracao)
    p = sub.add_parser("preparar-decisoes"); p.add_argument("--documentos"); p.add_argument("--modelo", default="claude-code/claude-opus-5")
    p.set_defaults(f=cmd_preparar_decisoes)
    p = sub.add_parser("ingerir-decisoes"); p.add_argument("--documentos"); p.add_argument("--modelo", default="claude-code/claude-opus-5")
    p.set_defaults(f=cmd_ingerir_decisoes)
    args = ap.parse_args(argv)
    args.f(args)


if __name__ == "__main__":
    main()
