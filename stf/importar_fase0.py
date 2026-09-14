"""Registra os snapshots brutos da Fase 0 (recon/, data/raw/7514886/) como uma coleta.

Os arquivos da Fase 0 foram gravados com .meta.json ao lado (url, fetched_at, sha256,
status). Aqui eles são copiados para o BlobStore (endereçado por sha256) e ganham um
registro JSONL igual ao das coletas normais, para que o banco e o `diff` os tratem
como a primeira observação do incidente. Os originais não são tocados.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import config
from .store import BlobStore, RegistroColeta, caminho_relativo, sha256

RAW_FASE0 = config.DATA / "raw" / "7514886"
INCIDENTE = 7514886


def _meta(path: Path) -> dict:
    return json.loads(path.read_text("utf-8"))


def importar(*, blobs: Path = config.BLOBS, coletas: Path = config.COLETAS) -> Path:
    bs = BlobStore(blobs)
    entradas: list[tuple[str, Path, dict]] = []

    casca = sorted(RAW_FASE0.glob("*_ua-ident_verImpressao.html"))[0]
    entradas.append(("casca", casca, _meta(casca.with_suffix(".meta.json"))))
    for html in sorted((RAW_FASE0 / "abas").glob("*.html")):
        aba = html.stem.split("_", 1)[1]
        entradas.append((aba, html, _meta(html.with_suffix(".meta.json"))))
    for pdf in sorted((RAW_FASE0 / "docs").glob("*.pdf")):
        entradas.append(("documento", pdf, _meta(Path(str(pdf) + ".meta.json"))))

    # id da coleta = timestamp da casca (primeira requisição a /processos)
    coleta_id = f"{entradas[0][2]['fetched_at'][:19].replace('-', '').replace(':', '')}Z-{INCIDENTE}"
    reg = RegistroColeta(coletas, coleta_id)
    if reg.caminho.exists():
        return reg.caminho
    for aba, path, meta in entradas:
        data = path.read_bytes()
        digest = sha256(data)
        if digest != meta["sha256"]:
            raise RuntimeError(f"arquivo da Fase 0 não confere com o meta: {path}")
        p = bs.gravar(data, ext=path.suffix.lstrip("."))
        url = meta.get("url") or meta["link"]["abs"]   # o meta do PDF da Fase 0 guarda o link em `link.abs`
        reg.anotar({
            "incidente": INCIDENTE, "aba": aba, "url": url, "url_final": meta.get("final_url"),
            "fetched_at": meta["fetched_at"], "http_status": meta["http_status"], "sha256": digest,
            "bytes": len(data), "raw_path": caminho_relativo(p, config.RAIZ), "content_type": meta.get("content_type") or meta.get("response_headers", {}).get("content-type"),
            "user_agent": meta.get("request_headers", {}).get("User-Agent") or meta.get("ua"),
            "origem": "fase0", "arquivo_original": caminho_relativo(path, config.RAIZ),
        })
    return reg.caminho
