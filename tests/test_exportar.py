"""Exportação para a interface: JSON estático com proveniência em cada item."""
import json

from stf.coleta import ClienteEducado
from stf.db import abrir, criar_schema
from stf.entidades import construir_entidades
from stf.expandir import expandir
from stf.exportar import exportar
from tests.portal_falso import PortalFalso


class Relogio:
    t = 0.0
    def monotonic(self): return self.t
    def sleep(self, s): self.t += s


def test_exporta_arquivos_com_proveniencia(tmp_path):
    con = abrir(":memory:"); criar_schema(con)
    rel = Relogio()
    cliente = ClienteEducado(transport=PortalFalso({("Pet", 15556): 7514886, ("Inq", 5026): 1000001}).transporte(),
                             relogio=rel.monotonic, dormir=rel.sleep, teto=500)
    expandir(con, 7514886, profundidade=0, cliente=cliente, blobs=tmp_path / "blobs", coletas=tmp_path / "coletas", log=lambda s: None)
    construir_entidades(con)
    saida = tmp_path / "web"
    r = exportar(con, saida, semente=7514886)
    assert r["processos"] == 1 and (saida / "meta.json").exists()
    meta = json.loads((saida / "meta.json").read_text("utf-8"))
    assert meta["semente"] == 7514886 and meta["coletado_em"]["7514886"]
    proc = json.loads((saida / "processo" / "7514886.json").read_text("utf-8"))
    assert proc["cabecalho"]["classe"] == "Pet" and len(proc["andamentos"]) == 407 and len(proc["partes"]) == 56
    a = proc["andamentos"][0]
    assert a["snapshot"] and a["snapshot"]["fetched_at"] and a["snapshot"]["sha256"]
    assert proc["partes"][0]["status_processual"] == "requerente" and proc["partes"][0]["entidade_id"]
    assert proc["sessoes"] and proc["sessoes"][0]["votos"][1]["tipo_voto"] == "Suspeito"
    assert "Distribuído por prevenção" in proc["explicacoes_portal"]
    busca = json.loads((saida / "busca.json").read_text("utf-8"))
    assert any(e["tipo"] == "andamento" and "PRISÃO PREVENTIVA" in e["texto"] for e in busca)
    ents = json.loads((saida / "entidades.json").read_text("utf-8"))
    vorcaro = next(e for e in ents if e["nome"] == "DANIEL BUENO VORCARO")
    assert vorcaro["mencoes"][0]["papel_portal"] == "REQDO.(A/S)" and vorcaro["origem"] == "partes"
    assert (saida / "grafo.json").exists() and (saida / "cruzamentos.json").exists()
    assert json.loads((saida / "assercoes.json").read_text("utf-8")) == []
    fluxos = json.loads((saida / "fluxos.json").read_text("utf-8"))            # sem fluxos carregados: estrutura vazia, nunca ausente
    assert fluxos["fontes"] == [] and fluxos["grafo"] == {"nos": [], "arestas": []}
    assert (saida / "fluxos.csv").read_text("utf-8").startswith("fonte,comunicacao,secao")
    assert (saida / "fluxos_atores.csv").exists() and (saida / "fluxos_comunicacoes.csv").exists() and (saida / "fluxos_bens.csv").exists()


def test_processo_exportado_traz_assercoes_dentro_de_cada_documento(tmp_path):
    con = abrir(":memory:"); criar_schema(con)
    rel = Relogio()
    cliente = ClienteEducado(transport=PortalFalso({("Pet", 15556): 7514886}).transporte(), relogio=rel.monotonic, dormir=rel.sleep, teto=500)
    expandir(con, 7514886, profundidade=0, cliente=cliente, blobs=tmp_path / "blobs", coletas=tmp_path / "coletas", log=lambda s: None)
    construir_entidades(con)
    doc = con.execute("select id from documento where id_portal='15389657076'").fetchone()["id"]
    con.execute("update documento set sha256='abc', blob_path='x', paginas=1, tem_camada_texto=1 where id=?", (doc,))
    con.execute("insert into documento_pagina (documento_id, pagina, texto, chars) values (?,1,'DESPACHO: Abra-se vista.',24)", (doc,))
    con.execute("insert into extracao (documento_id, sha256_documento, prompt_version, modelo, executada_em, status) values (?,'abc','v1','m','2026-09-14','ok')", (doc,))
    eid = con.execute("select id from extracao").fetchone()["id"]
    con.execute("insert into assercao (documento_id, extracao_id, pagina, tipo_epistemico, texto, trecho_fonte, entidades_json, modelo, prompt_version, criado_em) "
                "values (?,?,1,'fato_processual','Foi aberta vista.','Abra-se vista.','[]','m','v1','2026-09-14')", (doc, eid))
    con.commit()
    exportar(con, tmp_path / "web", semente=7514886)
    proc = json.loads((tmp_path / "web" / "processo" / "7514886.json").read_text("utf-8"))
    andamento = next(a for a in proc["andamentos"] if any(d["id"] == doc for d in a["documentos"]))
    d = next(d for d in andamento["documentos"] if d["id"] == doc)
    assert d["assercoes"] == [{"id": 1, "pagina": 1, "tipo_epistemico": "fato_processual", "texto": "Foi aberta vista.",
                               "trecho_fonte": "Abra-se vista.", "atribuida_a": None}]
    assert proc["contagem_assercoes"] == {"fato_processual": 1, "alegacao_parte": 0, "fundamento_decisorio": 0}
