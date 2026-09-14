"""Armazenamento append-only: blobs por sha256 e registro de coleta em JSONL."""
import hashlib
import json

import pytest

from stf.store import BlobStore, RegistroColeta


def test_blob_e_gravado_pelo_sha256_e_nunca_sobrescrito(tmp_path):
    bs = BlobStore(tmp_path / "blobs")
    data = b"<html>a</html>"
    p1 = bs.gravar(data, ext="html")
    assert p1.name == hashlib.sha256(data).hexdigest() + ".html"
    assert p1.read_bytes() == data
    # gravar de novo o mesmo conteúdo é no-op, não erro (dedup por conteúdo)
    assert bs.gravar(data, ext="html") == p1
    # conteúdo diferente com o mesmo nome não pode acontecer; corrompe → erro
    p1.write_bytes(b"corrompido")
    with pytest.raises(RuntimeError):
        bs.gravar(data, ext="html")


def test_registro_de_coleta_e_jsonl_append_only(tmp_path):
    reg = RegistroColeta(tmp_path / "coletas", coleta_id="20260914T000000Z-7514886")
    reg.anotar({"aba": "casca", "http_status": 200, "sha256": "x"})
    reg.anotar({"aba": "partes", "http_status": 200, "sha256": "y"})
    linhas = [json.loads(l) for l in reg.caminho.read_text("utf-8").splitlines()]
    assert [l["aba"] for l in linhas] == ["casca", "partes"]
    assert all(l["coleta_id"] == "20260914T000000Z-7514886" for l in linhas)
    assert RegistroColeta.ler(reg.caminho) == linhas


def test_caminho_relativo_dentro_e_fora_da_raiz(tmp_path):
    from pathlib import Path
    from stf.store import caminho_relativo, resolver_raw
    raiz = tmp_path / "proj"
    dentro = raiz / "data" / "raw" / "blobs" / "abc.html"
    dentro.parent.mkdir(parents=True)
    dentro.write_bytes(b"x")
    assert caminho_relativo(dentro, raiz) == "data/raw/blobs/abc.html"
    assert resolver_raw("data/raw/blobs/abc.html", raiz) == raiz / "data/raw/blobs/abc.html"
    fora = tmp_path / "outro.html"
    assert Path(caminho_relativo(fora, raiz)).is_absolute()
    assert resolver_raw(str(fora), raiz) == fora
