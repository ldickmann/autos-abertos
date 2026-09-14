"""CLI: python -m stf <comando> [args]

  coletar <incidente>          coleta educada (casca + abas) e ingere no banco
  importar-fase0               registra os snapshots brutos da Fase 0 como uma coleta
  ingerir <registro.jsonl>     projeta uma coleta já gravada no banco
  reconstruir                  apaga a projeção e reingere todas as coletas (prova que os blobs são a fonte)
  diff <coleta_a> <coleta_b>   compara duas coletas (ids ou caminhos de registro)
  buscar "<termos>"            busca FTS5 em andamentos
  status                       contagens do banco
"""

from __future__ import annotations

import argparse
import json
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
    con = _con()
    apagar_projecao(con)
    criar_schema(con)
    for reg in sorted(config.COLETAS.glob("*.jsonl")):
        r = ingerir_coleta(con, reg)
        print(f"{reg.name}: {json.dumps(r, ensure_ascii=False)}")


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
    args = ap.parse_args(argv)
    args.f(args)


if __name__ == "__main__":
    main()
