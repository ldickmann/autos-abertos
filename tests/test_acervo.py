"""Peças do acervo público do STF (docspublicos/SharePoint) entram no pipeline como coleta de documentos."""
import json
from pathlib import Path

import py7zr

from stf.acervo import registrar_acervo
from stf.db import abrir, criar_schema
from stf.store import sha256

PDF = Path(__file__).parent / "fixtures" / "docs" / "despacho_15389657076.pdf"
URL_7Z = "https://docspublicos.stf.jus.br/processos-publicos/Pet16704-pt3/Pet16704-pt3.7z"


def _arquivo_7z(tmp_path: Path) -> Path:
    p = tmp_path / "Pet16704-pt3.7z"
    with py7zr.SevenZipFile(p, "w") as z:
        z.write(PDF, "Pet15645/00001 Peticao inicial - Peticao inicial_e75aa603.pdf")
        z.write(PDF, "Pet15645/00004 Certidao - Certidao de distribuicao de processo_0cb05b15.pdf")
    return p


def test_registrar_acervo_cria_documentos_com_blob_e_registro(tmp_path):
    con = abrir(":memory:"); criar_schema(con)
    arq = _arquivo_7z(tmp_path)
    res = registrar_acervo(con, arquivo=arq, url=URL_7Z, incidente=7526458, pasta="Pet15645",
                           blobs=tmp_path / "blobs", coletas=tmp_path / "coletas", raiz=tmp_path,
                           fetched_at="2026-09-14T21:39:00+00:00", user_agent="Mozilla/5.0 (teste)")
    assert res["documentos"] == 2

    docs = con.execute("SELECT * FROM documento WHERE incidente=7526458 ORDER BY id_portal").fetchall()
    assert [d["endpoint"] for d in docs] == ["docspublicos", "docspublicos"]
    assert docs[0]["id_portal"] == "Pet15645/00001_e75aa603"
    assert docs[0]["titulo"] == "Peticao inicial - Peticao inicial"
    assert docs[0]["formato"] == "pdf" and docs[0]["sha256"] == sha256(PDF.read_bytes())
    assert Path(tmp_path / docs[0]["blob_path"]).exists()
    assert docs[0]["url"].startswith(URL_7Z + "#")            # localização dentro do pacote publicado
    assert docs[0]["http_status"] == 200 and docs[0]["snapshot_download"] is not None

    # o pacote inteiro também é um snapshot, com o mesmo sha256 do arquivo baixado
    pacote = con.execute("SELECT * FROM snapshot WHERE aba='acervo'").fetchone()
    assert pacote["sha256"] == sha256(arq.read_bytes()) and pacote["url"] == URL_7Z

    # registro JSONL reingerível: uma linha do pacote + uma por peça, com o UA usado (a exceção fica escrita)
    registros = [json.loads(l) for l in (tmp_path / "coletas" / f"{res['coleta']}.jsonl").read_text("utf-8").splitlines()]
    assert [r["aba"] for r in registros] == ["acervo", "documento", "documento"]
    assert all(r["user_agent"] == "Mozilla/5.0 (teste)" for r in registros)
    assert res["coleta"].endswith("-documentos-acervo-7526458")


def test_registrar_acervo_e_idempotente(tmp_path):
    con = abrir(":memory:"); criar_schema(con)
    arq = _arquivo_7z(tmp_path)
    kw = dict(url=URL_7Z, incidente=7526458, pasta="Pet15645", blobs=tmp_path / "blobs",
              coletas=tmp_path / "coletas", raiz=tmp_path, fetched_at="2026-09-14T21:39:00+00:00", user_agent="ua")
    registrar_acervo(con, arquivo=arq, **kw)
    registrar_acervo(con, arquivo=arq, **{**kw, "fetched_at": "2026-09-14T22:00:00+00:00"})
    assert con.execute("SELECT COUNT(*) FROM documento").fetchone()[0] == 2


def test_registro_do_acervo_e_reingerivel_pela_projecao_normal(tmp_path):
    from stf.ingest import ingerir_coleta
    con = abrir(":memory:"); criar_schema(con)
    arq = _arquivo_7z(tmp_path)
    res = registrar_acervo(con, arquivo=arq, url=URL_7Z, incidente=7526458, pasta="Pet15645",
                           blobs=tmp_path / "blobs", coletas=tmp_path / "coletas", raiz=tmp_path,
                           fetched_at="2026-09-14T21:39:00+00:00", user_agent="ua")
    antes = [tuple(r) for r in con.execute("SELECT endpoint, id_portal, titulo, sha256, blob_path, incidente FROM documento ORDER BY id_portal")]

    con2 = abrir(":memory:"); criar_schema(con2)
    ingerir_coleta(con2, tmp_path / "coletas" / f"{res['coleta']}.jsonl")
    depois = [tuple(r) for r in con2.execute("SELECT endpoint, id_portal, titulo, sha256, blob_path, incidente FROM documento ORDER BY id_portal")]
    assert depois == antes
    assert con2.execute("SELECT COUNT(*) FROM snapshot WHERE aba='acervo'").fetchone()[0] == 1
