"""Status da Fase 4: quantos documentos têm extração válida e o que falta, por lote.

Uso: python scripts/extracao_status.py [--lotes]   (a partir da raiz do projeto)
"""

import json
import pathlib
import sqlite3
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
con = sqlite3.connect(RAIZ / "data" / "stf.sqlite")
feitos = {r[0] for r in con.execute("SELECT documento_id FROM extracao WHERE status='ok'")}
total = con.execute("SELECT COUNT(*) FROM documento WHERE sha256 IS NOT NULL AND tem_camada_texto=1").fetchone()[0]
assercoes = con.execute("SELECT COUNT(*) FROM assercao").fetchone()[0]
por_tipo = dict(con.execute("SELECT tipo_epistemico, COUNT(*) FROM assercao GROUP BY 1").fetchall())
print(f"extraídos: {len(feitos)}/{total} documentos | asserções: {assercoes} {por_tipo}")

entradas = RAIZ / "data" / "extracao" / "entradas"
if (entradas / "LOTES.json").exists() and (entradas / "MANIFEST.json").exists():
    lotes = json.loads((entradas / "LOTES.json").read_text("utf-8"))
    m = {x["id"]: x for x in json.loads((entradas / "MANIFEST.json").read_text("utf-8"))["documentos"]}
    for n, l in enumerate(lotes):
        faltam = [i for i in l if i not in feitos]
        if faltam:
            chars = sum(m[i]["chars"] for i in faltam if i in m)
            print(f"  lote {n:02d}: faltam {len(faltam):3d} doc(s), {chars:6d} chars → {faltam if len(faltam) <= 12 or '--lotes' in sys.argv else str(faltam[:12]) + '…'}")
pend_sem_lote = sorted({r[0] for r in con.execute(
    "SELECT id FROM documento WHERE sha256 IS NOT NULL AND tem_camada_texto=1")} - feitos - {i for l in lotes for i in l} if 'lotes' in dir() else set())
if pend_sem_lote:
    print("  fora dos lotes (ex.: doc 55):", pend_sem_lote)
