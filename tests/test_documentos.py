"""Fase 3: download com cache por sha256, texto por página, código de autenticação, chunking."""
from pathlib import Path

import pytest

from stf.coleta import ClienteEducado
from stf.db import abrir, criar_schema
from stf.documentos import (baixar_documentos, chunkar, codigo_autenticacao, extrair_paginas_pdf,
                            extrair_texto, rtf_para_texto)
from stf.ingest import ingerir_coleta
from tests.portal_falso import PortalFalso
from tests.test_ingest import montar_coleta

PDF = Path(__file__).parent / "fixtures" / "docs" / "despacho_15389657076.pdf"


def test_extrai_paginas_do_pdf_com_texto():
    paginas = extrair_paginas_pdf(PDF.read_bytes())
    assert len(paginas) == 2
    assert "DESPACHO" in paginas[1] and "Procuradoria-Geral da República" in paginas[1]
    assert "SOB SIGILO" in paginas[0]   # espaços preservados


def test_codigo_de_autenticacao_do_rodape():
    paginas = extrair_paginas_pdf(PDF.read_bytes())
    assert codigo_autenticacao("\n".join(paginas)) == ("5457-8466-98B0-B5A3", "5FA0-988C-2B24-C76D")
    assert codigo_autenticacao("sem rodapé") is None


def test_rtf_vira_texto():
    rtf = rb"{\rtf1\ansi\deff0 {\fonttbl {\f0 Times;}} \f0\fs24 Decis\'e3o: por unanimidade.\par Segundo.\par }"
    txt = rtf_para_texto(rtf)
    assert "Decisão: por unanimidade." in txt and "Segundo." in txt


def test_chunkar_respeita_paginas_e_paragrafos_numerados():
    paginas = [
        "PET 1 / DF\nDECISÃO:\n1. Primeiro parágrafo, curto.\n2. Segundo parágrafo, " + "x" * 200,
        "3. Terceiro parágrafo continua na página dois.\nAnte o exposto, defiro.\nBrasília, 1 de janeiro.",
    ]
    chunks = chunkar(paginas, max_chars=180)
    assert chunks[0]["pagina_inicio"] == 1 and chunks[-1]["pagina_fim"] == 2
    assert all(c["chars"] <= 180 or "\n" not in c["texto"] for c in chunks)
    assert any(c["texto"].startswith("3. Terceiro") and c["pagina_inicio"] == 2 for c in chunks)
    assert [c["ordem"] for c in chunks] == list(range(len(chunks)))
    assert any(c["secao"] == "DECISÃO" for c in chunks)


class Relogio:
    t = 0.0
    def monotonic(self): return self.t
    def sleep(self, s): self.t += s


@pytest.fixture
def banco(tmp_path, fx):
    con = abrir(":memory:"); criar_schema(con)
    ingerir_coleta(con, montar_coleta(tmp_path, fx, "C1"))
    portal = PortalFalso({("Pet", 15556): 7514886})
    rel = Relogio()
    cliente = ClienteEducado(transport=portal.transporte(), relogio=rel.monotonic, dormir=rel.sleep, teto=500)
    return con, portal, cliente, tmp_path


def test_baixa_documentos_com_cache_e_proveniencia(banco):
    con, portal, cliente, tmp = banco
    r = baixar_documentos(con, cliente=cliente, blobs=tmp / "blobs", coletas=tmp / "coletas", log=lambda s: None)
    assert r["baixados"] == 57 and r["erros"] == 0
    assert con.execute("select count(*) from documento where sha256 is not null").fetchone()[0] == 57
    assert con.execute("select count(*) from snapshot where aba='documento'").fetchone()[0] == 57
    rtf = con.execute("select * from documento where formato='rtf'").fetchone()
    assert rtf["blob_path"].endswith(".rtf") and rtf["http_status"] == 200
    n = len(portal.requisicoes)
    r2 = baixar_documentos(con, cliente=cliente, blobs=tmp / "blobs", coletas=tmp / "coletas", log=lambda s: None)
    assert r2["baixados"] == 0 and len(portal.requisicoes) == n   # cache: nada rebaixado


def test_extrai_texto_por_pagina_e_marca_camada_de_texto(banco):
    con, portal, cliente, tmp = banco
    baixar_documentos(con, cliente=cliente, blobs=tmp / "blobs", coletas=tmp / "coletas", log=lambda s: None)
    r = extrair_texto(con)
    assert r["extraidos"] == 57 and r["sem_camada_texto"] == 0
    doc = con.execute("select * from documento where id_portal='15389657076'").fetchone()
    assert doc["paginas"] == 2 and doc["tem_camada_texto"] == 1
    assert doc["codigo_autenticacao"] == "5457-8466-98B0-B5A3" and doc["senha_autenticacao"] == "5FA0-988C-2B24-C76D"
    pags = con.execute("select pagina, chars from documento_pagina where documento_id=? order by pagina", (doc["id"],)).fetchall()
    assert [p["pagina"] for p in pags] == [1, 2] and all(p["chars"] > 100 for p in pags)
    assert con.execute("select count(*) from documento_chunk where documento_id=?", (doc["id"],)).fetchone()[0] >= 2
    hit = con.execute("select documento_id, pagina from documento_fts join documento_pagina p on p.rowid=documento_fts.rowid "
                      "where documento_fts match 'procuradoria geral' limit 1").fetchone()
    assert hit["pagina"] == 2
    # idempotente
    assert extrair_texto(con)["extraidos"] == 0


def test_reconstruir_preserva_downloads_a_partir_dos_registros(banco, fx):
    from stf.db import apagar_projecao
    con, portal, cliente, tmp = banco
    baixar_documentos(con, cliente=cliente, blobs=tmp / "blobs", coletas=tmp / "coletas", log=lambda s: None)
    apagar_projecao(con); criar_schema(con)
    for reg in sorted((tmp / "coletas").glob("*.jsonl")):
        ingerir_coleta(con, reg)
    assert con.execute("select count(*) from documento where sha256 is not null").fetchone()[0] == 57


def test_rodada_de_documentos_com_varios_incidentes_e_ingerida(tmp_path, fx):
    """O registro de uma rodada de download mistura incidentes; a ingestão não pode exigir um só."""
    from stf.db import apagar_projecao
    con = abrir(":memory:"); criar_schema(con)
    ingerir_coleta(con, montar_coleta(tmp_path / "a", fx, "C1"))
    # segundo incidente com os mesmos fixtures (casca trocada)
    from tests.portal_falso import casca_para
    def outra(aba, raw):
        return casca_para(1000001, "Inq", 5026) if aba == "casca" else raw
    ingerir_coleta(con, montar_coleta(tmp_path / "b", fx, "C2", outra, incidente=1000001))
    portal = PortalFalso({("Pet", 15556): 7514886, ("Inq", 5026): 1000001})
    rel = Relogio()
    cliente = ClienteEducado(transport=portal.transporte(), relogio=rel.monotonic, dormir=rel.sleep, teto=500)
    r = baixar_documentos(con, cliente=cliente, blobs=tmp_path / "blobs", coletas=tmp_path / "coletas", log=lambda s: None)
    assert r["baixados"] == 57   # os mesmos 57 documentos (endpoint, id) são únicos; só o vínculo difere
    assert len({x for x in con.execute("select incidente from documento")}) >= 1
    apagar_projecao(con); criar_schema(con)
    for reg in sorted((tmp_path / "coletas").glob("*.jsonl")):
        ingerir_coleta(con, reg)
    assert con.execute("select count(*) from documento where sha256 is not null").fetchone()[0] == 57
