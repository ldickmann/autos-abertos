"""Fontes externas oficiais ligadas ao caso (Banco Central, Senado, TCU…): captura educada com hash e histórico.

A lista curada fica em `stf/curadoria/fontes_externas.json`: cada fonte tem órgão, URL, por que importa e se deve ser
capturada (páginas de terceiros só de referência, como enciclopédias, não são copiadas). Cada captura vira um blob
(conteúdo nomeado pelo sha256) e uma linha em `fonte_externa_snapshot`, append-only: dá para ver se a página mudou
ou sumiu entre uma captura e outra. Mesmo cliente educado da coleta do STF: uma requisição por vez, intervalo, backoff.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .coleta import ClienteEducado, _ext
from .store import BlobStore, caminho_relativo

_PATH = Path(__file__).parent / "curadoria" / "fontes_externas.json"
REGISTRO = config.DATA / "raw" / "externas.jsonl"   # registro append-only, versionado; a tabela é projeção dele


def fontes_curadas() -> list[dict]:
    return json.loads(_PATH.read_text("utf-8"))["fontes"]


def _registrar(registro: Path | None, linha: dict) -> None:
    if registro is None:
        return
    registro.parent.mkdir(parents=True, exist_ok=True)
    with registro.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")


def _inserir(con: sqlite3.Connection, linha: dict) -> None:
    con.execute("INSERT INTO fonte_externa_snapshot (fonte_id, url, fetched_at, http_status, sha256, bytes, content_type, raw_path) VALUES (?,?,?,?,?,?,?,?)",
                (linha["fonte_id"], linha["url"], linha["fetched_at"], linha.get("http_status"), linha.get("sha256"), linha.get("bytes"),
                 linha.get("content_type"), linha.get("raw_path")))


def reingerir_externas(con: sqlite3.Connection, registro: Path = REGISTRO) -> int:
    """Refaz a tabela a partir do registro JSONL (usado por `reconstruir`)."""
    with con:
        con.execute("DELETE FROM fonte_externa_snapshot")
        n = 0
        if registro.exists():
            for linha in registro.read_text("utf-8").splitlines():
                if linha.strip():
                    _inserir(con, json.loads(linha)); n += 1
    return n


def capturar_fontes(con: sqlite3.Connection, fontes: list[dict], *, cliente: ClienteEducado | None = None,
                    blobs: Path = config.BLOBS, raiz: Path = config.RAIZ, registro: Path | None = None) -> dict:
    c = cliente or ClienteEducado(teto=len(fontes) * 3 + 3)
    bs = BlobStore(blobs)
    res = {"capturadas": 0, "erros": 0, "puladas": 0}
    for f in fontes:
        if not f.get("capturar", False):
            res["puladas"] += 1
            continue
        agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
        r = c.get(f["url"], aba=f"externa:{f['id']}")
        if r is None or r.status_code != 200 or not r.content:
            res["erros"] += 1
            linha = {"fonte_id": f["id"], "url": f["url"], "fetched_at": agora, "http_status": r.status_code if r is not None else None}
        else:
            p = bs.gravar(r.content, ext=_ext(r.headers.get("content-type"), f["url"]))
            linha = {"fonte_id": f["id"], "url": f["url"], "fetched_at": agora, "http_status": r.status_code, "sha256": p.stem.split(".")[0],
                     "bytes": len(r.content), "content_type": r.headers.get("content-type"), "raw_path": caminho_relativo(p, raiz)}
            res["capturadas"] += 1
        _inserir(con, linha)
        con.commit()
        _registrar(registro, linha)
    return res


def exportar_fontes(con: sqlite3.Connection, fontes: list[dict]) -> list[dict]:
    out = []
    for f in fontes:
        hist = [dict(r) for r in con.execute(
            "SELECT id, fetched_at, http_status, sha256, bytes, content_type FROM fonte_externa_snapshot WHERE fonte_id=? ORDER BY id", (f["id"],))]
        ultima = hist[-1] if hist else None
        hashes = [h["sha256"] for h in hist if h["sha256"]]
        out.append({**f, "capturar": bool(f.get("capturar", False)), "ultima": ultima, "historico": hist,
                    "mudou": len(set(hashes)) > 1, "versoes_distintas": len(set(hashes))})
    return out
