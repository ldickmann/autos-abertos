"""Manifesto de integridade: o hash de cada cópia que a base guarda, com origem e data, para que qualquer pessoa
possa conferir que nada foi alterado desde a coleta.

- `gerar_manifesto(con)`: registros de coleta (JSONL, com sha256 do arquivo), snapshots do portal (URL, data, sha256, bytes),
  documentos baixados (URL, sha256, código de autenticação do STF) e um `raiz_sha256` do próprio manifesto, que é o valor
  a ancorar em carimbo de tempo externo.
- `verificar_blobs(con, blobs)`: recalcula o sha256 de cada blob local e compara com o registrado. Nenhuma tolerância.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import config


def _sha256_arquivo(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def gerar_manifesto(con: sqlite3.Connection, *, coletas: Path = config.COLETAS) -> dict:
    registros = []
    for p in sorted(Path(coletas).glob("*.jsonl")):
        registros.append({"id": p.stem, "arquivo": f"data/raw/coletas/{p.name}", "sha256": _sha256_arquivo(p),
                          "linhas": sum(1 for _ in p.open("rb"))})
    snapshots = [dict(r) for r in con.execute(
        "SELECT id, coleta_id, incidente, aba, url, fetched_at, http_status, sha256, bytes FROM snapshot ORDER BY id")]
    documentos = [dict(r) for r in con.execute(
        "SELECT d.id, d.incidente, d.titulo, d.url, d.formato, d.sha256, d.paginas, d.baixado_em, d.codigo_autenticacao, d.senha_autenticacao, "
        "p.classe || ' ' || p.numero AS processo FROM documento d LEFT JOIN processo p ON p.incidente_principal=d.incidente "
        "WHERE d.sha256 IS NOT NULL ORDER BY d.id")]
    corpo = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "como_conferir": "Baixe o arquivo pela URL de origem, calcule o SHA-256 e compare com o valor listado. Para documentos, o código e a senha de autenticação também podem ser conferidos em http://www.stf.jus.br/portal/autenticacao/autenticarDocumento.asp.",
        "totais": {"registros_de_coleta": len(registros), "snapshots": len(snapshots), "documentos": len(documentos)},
        "registros_de_coleta": registros,
        "snapshots": snapshots,
        "documentos": documentos,
    }
    canonico = json.dumps(corpo, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    corpo["raiz_sha256"] = hashlib.sha256(canonico).hexdigest()
    return corpo


def verificar_blobs(con: sqlite3.Connection, *, blobs: Path = config.BLOBS, raiz: Path = config.RAIZ) -> dict:
    """Confere cada blob referenciado (snapshots e documentos) contra o sha256 registrado."""
    ok = faltando = divergentes = 0
    problemas: list[dict] = []
    vistos: set[str] = set()
    for tabela, col_path in (("snapshot", "raw_path"), ("documento", "blob_path")):
        for r in con.execute(f"SELECT id, sha256, {col_path} AS caminho FROM {tabela} WHERE sha256 IS NOT NULL AND {col_path} IS NOT NULL"):
            if r["caminho"] in vistos:
                continue
            vistos.add(r["caminho"])
            p = Path(r["caminho"])
            if not p.is_absolute():
                p = raiz / p
            if not p.exists():
                faltando += 1
                problemas.append({"tabela": tabela, "id": r["id"], "problema": "arquivo ausente", "caminho": str(p)})
                continue
            real = _sha256_arquivo(p)
            if real != r["sha256"]:
                divergentes += 1
                problemas.append({"tabela": tabela, "id": r["id"], "problema": "sha256 diferente", "esperado": r["sha256"], "real": real})
            else:
                ok += 1
    return {"ok": ok, "faltando": faltando, "divergentes": divergentes, "problemas": problemas}
