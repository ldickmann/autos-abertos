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
