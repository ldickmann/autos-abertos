"""Fonte de verdade do projeto: blobs endereçados por conteúdo + registro de coleta.

- `BlobStore`: cada resposta HTTP é gravada em `blobs/<sha256>.<ext>`. Gravar o
  mesmo conteúdo duas vezes é no-op. Um arquivo existente cujo conteúdo não bate
  com o nome é corrupção e levanta erro. Nunca sobrescreve.
- `RegistroColeta`: um JSONL por coleta, uma linha por requisição, só append.

O SQLite é uma projeção derivada disso e pode ser reconstruído do zero.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def caminho_relativo(p: Path, raiz: Path) -> str:
    """Caminho relativo à raiz do projeto quando possível (registros portáveis); senão absoluto."""
    try:
        return Path(p).resolve().relative_to(Path(raiz).resolve()).as_posix()
    except ValueError:
        return str(p)


def resolver_raw(raw_path: str, raiz: Path) -> Path:
    p = Path(raw_path)
    return p if p.is_absolute() else Path(raiz) / p


class BlobStore:
    def __init__(self, raiz: Path):
        self.raiz = Path(raiz)
        self.raiz.mkdir(parents=True, exist_ok=True)

    def caminho(self, digest: str, ext: str) -> Path:
        return self.raiz / f"{digest}.{ext.lstrip('.')}"

    def gravar(self, data: bytes, *, ext: str) -> Path:
        digest = sha256(data)
        p = self.caminho(digest, ext)
        if p.exists():
            if sha256(p.read_bytes()) != digest:
                raise RuntimeError(f"blob corrompido: {p} não confere com o sha256 do nome")
            return p
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(p)  # atômico no mesmo volume; nunca sobrescreve um blob íntegro
        return p

    def ler(self, digest: str, ext: str) -> bytes:
        p = self.caminho(digest, ext)
        data = p.read_bytes()
        if sha256(data) != digest:
            raise RuntimeError(f"blob corrompido: {p}")
        return data


class RegistroColeta:
    def __init__(self, raiz: Path, coleta_id: str):
        self.raiz = Path(raiz)
        self.raiz.mkdir(parents=True, exist_ok=True)
        self.coleta_id = coleta_id
        self.caminho = self.raiz / f"{coleta_id}.jsonl"

    def anotar(self, registro: dict) -> None:
        linha = {"coleta_id": self.coleta_id, **registro}
        with self.caminho.open("a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False, default=str) + "\n")

    @staticmethod
    def ler(caminho: Path) -> list[dict]:
        return [json.loads(l) for l in Path(caminho).read_text("utf-8").splitlines() if l.strip()]
