"""Sessão virtual: JSON de sistemas.stf.jus.br (votacao?oi= e votacao?sessaoVirtual=), parse determinístico."""
from pathlib import Path

from stf.sessao import parse_objetos_incidente, parse_sessao_virtual

FIX = Path(__file__).parent / "fixtures" / "7514886"


def test_objetos_incidente_do_processo():
    objs = parse_objetos_incidente((FIX / "votacao_oi.json").read_bytes())
    assert len(objs) == 1
    o = objs[0]
    assert o.id == 7519395 and o.principal == 7514886 and o.pai == 7514886
    assert o.tipo == "IJ" and o.identificacao == "Pet 15556 Ref"
    assert o.identificacao_completa == "REFERENDO NA PETIÇÃO 15556"


def test_sessao_virtual_com_placar_e_documentos():
    listas = parse_sessao_virtual((FIX / "sessao_virtual_7519395.json").read_bytes())
    assert len(listas) == 1
    l = listas[0]
    assert l.objeto_incidente_id == 7519395 and l.nome_lista == "138-2026" and l.julgado is False
    assert l.colegiado == "Segunda Turma" and l.data_inicio == "2026-03-13" and l.data_fim == "2026-03-20"
    assert l.relator == "MIN. ANDRÉ MENDONÇA" and l.tipo_lista == "Listas dos Relatores (Referendos)"
    assert [(v.ministro, v.tipo_voto, v.data) for v in l.votos] == [
        ("MIN. LUIZ FUX", "Acompanho o relator", "2026-03-13"),
        ("MIN. DIAS TOFFOLI", "Suspeito", "2026-03-13"),
        ("MIN. NUNES MARQUES", "Acompanho o relator", "2026-03-13"),
        ("MIN. GILMAR MENDES", "Acompanho o relator com ressalvas", "2026-03-20"),
    ]
    docs = {(d.rotulo, d.id_portal): d.url for d in l.documentos}
    assert ("Voto", "490815") in docs and ("Relatório", "490817") in docs and ("Voto Vogal", "503028") in docs
    assert docs[("Voto Vogal", "503028")].endswith("/votos/503028/conteudo.pdf")
    assert l.documentos[-1].ministro == "MIN. GILMAR MENDES"


def test_json_vazio_e_lista_vazia():
    assert parse_objetos_incidente(b"[]") == [] and parse_sessao_virtual(b"[ ]") == []


class Relogio:
    t = 0.0
    def monotonic(self): return self.t
    def sleep(self, s): self.t += s


def test_coleta_inclui_sessao_virtual_e_ingestao_projeta_votos(tmp_path):
    from stf.coleta import ClienteEducado, coletar_incidente
    from stf.db import abrir, criar_schema
    from stf.ingest import ingerir_coleta
    from tests.portal_falso import PortalFalso
    portal = PortalFalso({("Pet", 15556): 7514886})
    rel = Relogio()
    cliente = ClienteEducado(transport=portal.transporte(), relogio=rel.monotonic, dormir=rel.sleep, teto=50)
    reg = coletar_incidente(7514886, blobs=tmp_path / "blobs", coletas=tmp_path / "coletas", cliente=cliente, log=lambda s: None)
    abas = [l.split('"aba": "')[1].split('"')[0] for l in reg.read_text("utf-8").splitlines()]
    assert abas[-2:] == ["votacao_json", "sessao_virtual_json"]   # 1 + 1 objeto IJ
    con = abrir(":memory:"); criar_schema(con)
    ingerir_coleta(con, reg)
    o = con.execute("select * from objeto_incidente where id=7519395").fetchone()
    assert o["incidente_principal"] == 7514886 and o["tipo"] == "IJ"
    l = con.execute("select * from lista_julgamento where objeto_incidente_id=7519395").fetchone()
    assert l["colegiado"] == "Segunda Turma" and l["data_inicio"] == "2026-03-13" and l["relator"] == "MIN. ANDRÉ MENDONÇA"
    votos = con.execute("select ministro, tipo_voto from voto where lista_id=? order by ordem", (l["id"],)).fetchall()
    assert [tuple(v) for v in votos][1] == ("MIN. DIAS TOFFOLI", "Suspeito") and len(votos) == 4
    docs = con.execute("select id_portal, titulo, url from documento where endpoint='votos' order by id_portal").fetchall()
    assert [(d["id_portal"], d["titulo"]) for d in docs] == [("490815", "Voto"), ("490817", "Relatório"), ("503028", "Voto Vogal")]
    # documentos de voto pertencem ao incidente principal e são baixáveis pela camada documental
    assert all(d["url"].startswith("https://digital.stf.jus.br/") for d in docs)
