"""Ingestão: snapshots → projeção SQLite. O banco é derivado; os blobs são a fonte."""
import pytest

from stf.db import abrir, criar_schema
from stf.ingest import ingerir_coleta
from stf.store import BlobStore, RegistroColeta

ABAS = ["casca", "informacoes", "partes", "andamentos", "decisoes", "sessao",
        "deslocamentos", "peticoes", "recursos", "pautas"]


def montar_coleta(tmp_path, fx, coleta_id, transformar=None, incidente=7514886):
    """Cria blobs + registro JSONL a partir dos fixtures, opcionalmente transformando o HTML."""
    bs = BlobStore(tmp_path / "blobs")
    reg = RegistroColeta(tmp_path / "coletas", coleta_id=coleta_id)
    for i, aba in enumerate(ABAS):
        raw = fx(aba)
        if transformar:
            raw = transformar(aba, raw)
        p = bs.gravar(raw, ext="html")
        reg.anotar({
            "incidente": incidente, "aba": aba,
            "url": f"https://portal.stf.jus.br/processos/aba{aba}.asp?incidente={incidente}",
            "fetched_at": f"2026-09-14T01:06:{50 + i:02d}+00:00", "http_status": 200,
            "sha256": p.stem, "bytes": len(raw), "raw_path": str(p), "content_type": "text/html",
        })
    return reg.caminho


@pytest.fixture
def db():
    con = abrir(":memory:")
    criar_schema(con)
    return con


def contar(con, sql):
    return con.execute(sql).fetchone()[0]


def test_ingestao_popula_todas_as_tabelas(db, tmp_path, fx):
    reg = montar_coleta(tmp_path, fx, "C1")
    ingerir_coleta(db, reg)
    assert contar(db, "select count(*) from coleta") == 1
    assert contar(db, "select count(*) from snapshot") == 10
    assert contar(db, "select count(*) from incidente") == 1
    assert contar(db, "select count(*) from parte") == 56
    assert contar(db, "select count(*) from andamento") == 407
    assert contar(db, "select count(*) from andamento where e_decisao=1") == 27
    assert contar(db, "select count(*) from andamento where e_pauta=1") == 1
    # 72 citações apontam para 57 documentos únicos (decisão e vista à PGR citam o mesmo PDF)
    assert contar(db, "select count(*) from documento") == 57
    assert contar(db, "select count(*) from andamento_documento") == 72
    assert contar(db, "select count(*) from peticao") == 113
    assert contar(db, "select count(*) from deslocamento") == 90
    assert contar(db, "select count(*) from tipo_andamento where explicacao_portal is not null") >= 1


def test_incidente_projetado_com_cabecalho_e_informacoes(db, tmp_path, fx):
    ingerir_coleta(db, montar_coleta(tmp_path, fx, "C1"))
    row = db.execute("select * from incidente where numero=7514886").fetchone()
    assert row["classe"] == "Pet" and row["numero_processo"] == 15556
    assert row["relator"] == "MIN. ANDRÉ MENDONÇA" and row["ultimo_incidente"] == "Pet-AgR-quarto"
    assert row["publicidade"] == "Público" and row["reu_preso"] == 1
    assert row["data_protocolo"] == "2026-02-27"
    assert "15198" in row["numeros_origem"]
    assert contar(db, "select count(*) from incidente_versao") == 1


def test_documento_e_unico_por_endpoint_e_id_mesmo_citado_em_duas_abas(db, tmp_path, fx):
    ingerir_coleta(db, montar_coleta(tmp_path, fx, "C1"))
    # o RTF do julgamento aparece em Andamentos e em Decisões; deve existir uma vez
    assert contar(db, "select count(*) from documento where endpoint='downloadTexto'") == 1
    row = db.execute("select * from documento where id_portal='15384501728'").fetchone()
    assert row["formato"] == "pdf" and row["titulo"] == "Certidão"
    assert row["url"].startswith("https://portal.stf.jus.br/processos/downloadPeca.asp?id=15384501728")


def test_reingestao_da_mesma_coleta_e_idempotente(db, tmp_path, fx):
    reg = montar_coleta(tmp_path, fx, "C1")
    ingerir_coleta(db, reg)
    ingerir_coleta(db, reg)
    assert contar(db, "select count(*) from coleta") == 1
    assert contar(db, "select count(*) from snapshot") == 10
    assert contar(db, "select count(*) from andamento") == 407
    assert contar(db, "select count(*) from parte") == 56


def _remover_10_andamentos_mais_recentes(aba, raw):
    if aba != "andamentos":
        return raw
    from selectolax.parser import HTMLParser
    t = HTMLParser(raw.decode("utf-8"))
    for item in t.css(".andamento-item")[:10]:
        item.decompose()
    return t.html.encode("utf-8")


def test_segunda_coleta_com_itens_novos_preserva_first_seen_e_avanca_last_seen(db, tmp_path, fx):
    antiga = montar_coleta(tmp_path / "a", fx, "C0", _remover_10_andamentos_mais_recentes)
    nova = montar_coleta(tmp_path / "b", fx, "C1")
    ingerir_coleta(db, antiga)
    assert contar(db, "select count(*) from andamento") == 397
    ingerir_coleta(db, nova)
    assert contar(db, "select count(*) from andamento") == 407
    snaps = {r["coleta_id"]: r["id"] for r in db.execute(
        "select id, coleta_id from snapshot where aba='andamentos'")}
    # os 397 antigos: vistos primeiro em C0, por último em C1
    assert contar(db, f"select count(*) from andamento where snapshot_first_seen={snaps['C0']} "
                      f"and snapshot_last_seen={snaps['C1']}") == 397
    # os 10 novos: vistos primeiro e por último em C1
    assert contar(db, f"select count(*) from andamento where snapshot_first_seen={snaps['C1']}") == 10


def test_fts_busca_sem_acento(db, tmp_path, fx):
    ingerir_coleta(db, montar_coleta(tmp_path, fx, "C1"))
    hits = db.execute(
        "select a.data, a.tipo from andamento_fts f join andamento a on a.id=f.rowid "
        "where andamento_fts match 'prisao preventiva' order by a.data").fetchall()
    assert len(hits) >= 1
    assert any(h["tipo"] == "Determinada a diligência" for h in hits)


def test_andamentos_mais_recentes_primeiro_e_com_posicao(db, tmp_path, fx):
    ingerir_coleta(db, montar_coleta(tmp_path, fx, "C1"))
    top = db.execute("select data, tipo, posicao from andamento order by posicao limit 1").fetchone()
    assert (top["data"], top["tipo"], top["posicao"]) == ("2026-09-11", "Remessa", 0)
