"""Acervo público do STF: pacotes `.7z`/`.zip` publicados em docspublicos.stf.jus.br com as peças de
processos cujo sigilo foi levantado (notícia de 14/09/2026). Cada pacote vira um snapshot (aba `acervo`)
e cada peça dentro dele vira um `documento` com endpoint `docspublicos`, no mesmo registro JSONL que
`ingerir` e `reconstruir` já entendem — os blobs continuam sendo a fonte.

O CDN rejeita o User-Agent identificado do projeto; o UA efetivamente usado fica gravado em cada linha.
"""

from __future__ import annotations

import io
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .documentos import registrar_download
from .store import BlobStore, RegistroColeta, caminho_relativo, sha256

RE_NOME_PECA = re.compile(r"^(?P<seq>\d{5}) (?P<titulo>.+?)_(?P<hash>[0-9a-f]{8})\.(?P<ext>pdf|rtf)$", re.I)


def _listar(arquivo: Path) -> list[tuple[str, bytes]]:
    """(caminho dentro do pacote, bytes) de cada arquivo, em ordem de nome."""
    data = arquivo.read_bytes()
    if arquivo.suffix.lower() == ".7z":
        import tempfile
        import py7zr
        with tempfile.TemporaryDirectory() as tmp, py7zr.SevenZipFile(io.BytesIO(data)) as z:
            z.extractall(tmp)
            return sorted((p.relative_to(tmp).as_posix(), p.read_bytes()) for p in Path(tmp).rglob("*") if p.is_file())
    import zipfile
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return sorted((i.filename, z.read(i)) for i in z.infolist() if not i.is_dir())


def registrar_acervo(con: sqlite3.Connection, *, arquivo: Path, url: str, incidente: int, pasta: str,
                     blobs: Path = config.BLOBS, coletas: Path = config.COLETAS, raiz: Path = config.RAIZ,
                     fetched_at: str | None = None, user_agent: str | None = None) -> dict:
    """Registra um pacote do acervo e as peças da `pasta` (ex.: "Pet15645") como documentos do `incidente`."""
    fetched_at = fetched_at or datetime.now(timezone.utc).isoformat()
    bs = BlobStore(blobs)
    pacote = arquivo.read_bytes()
    p_pacote = bs.gravar(pacote, ext=arquivo.suffix.lstrip("."))
    coleta_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-documentos-acervo-{incidente}"
    reg = RegistroColeta(coletas, coleta_id)
    base = {"incidente": incidente, "fetched_at": fetched_at, "http_status": 200, "user_agent": user_agent,
            "content_type": "application/x-7z-compressed" if arquivo.suffix.lower() == ".7z" else "application/zip"}
    linha_pacote = {**base, "aba": "acervo", "url": url, "sha256": sha256(pacote), "bytes": len(pacote),
                    "raw_path": caminho_relativo(p_pacote, raiz)}
    reg.anotar(linha_pacote)
    with con:
        con.execute("INSERT OR IGNORE INTO coleta (id, incidente, registro_path, ingerida_em) VALUES (?,?,?,?)",
                    (coleta_id, incidente, str(reg.caminho), datetime.now(timezone.utc).isoformat()))
        con.execute(
            "INSERT OR IGNORE INTO snapshot (coleta_id, incidente, aba, url, fetched_at, http_status, sha256, bytes, raw_path, content_type) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (coleta_id, incidente, "acervo", url, fetched_at, 200, linha_pacote["sha256"], len(pacote),
             linha_pacote["raw_path"], base["content_type"]))
        n = 0
        for caminho, data in _listar(arquivo):
            if not caminho.startswith(pasta.rstrip("/") + "/"):
                continue
            m = RE_NOME_PECA.match(Path(caminho).name)
            if not m:
                continue
            ext = m["ext"].lower()
            p = bs.gravar(data, ext=ext)
            digest = sha256(data)
            id_portal = f"{pasta}/{m['seq']}_{m['hash']}"
            url_peca = f"{url}#{caminho}"
            linha = {**base, "aba": "documento", "url": url_peca, "url_final": url_peca, "sha256": digest,
                     "bytes": len(data), "raw_path": caminho_relativo(p, raiz),
                     "content_type": "application/pdf" if ext == "pdf" else "application/rtf",
                     "endpoint": "docspublicos", "id_portal": id_portal, "formato_real": ext, "titulo": m["titulo"]}
            reg.anotar(linha)
            cur = con.execute(
                "INSERT OR IGNORE INTO snapshot (coleta_id, incidente, aba, url, fetched_at, http_status, sha256, bytes, raw_path, content_type) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (coleta_id, incidente, "documento", url_peca, fetched_at, 200, digest, len(data), linha["raw_path"], linha["content_type"]))
            sid = cur.lastrowid if cur.rowcount else None
            registrar_download(con, "docspublicos", id_portal, digest, linha["raw_path"], 200, fetched_at, sid, ext,
                               incidente=incidente, url=url_peca)
            con.execute("UPDATE documento SET titulo=COALESCE(titulo, ?) WHERE endpoint='docspublicos' AND id_portal=?",
                        (m["titulo"], id_portal))
            n += 1
    return {"coleta": coleta_id, "documentos": n, "pacote_sha256": linha_pacote["sha256"]}
