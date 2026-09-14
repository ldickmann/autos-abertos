"""Matérias do Congresso (APIs de dados abertos do Senado e da Câmara): parse determinístico, consulta educada, projeção."""
import json
from pathlib import Path

import httpx

from stf.coleta import ClienteEducado
from stf.db import abrir, criar_schema
from stf.legislativo import (CONSULTAS, consultar, parse_camara, parse_senado, reingerir_legislativo, url_camara, url_senado)

FX = Path(__file__).parent / "fixtures" / "legislativo"


def test_parse_senado_normaliza_campos_e_url_publica():
    itens = parse_senado((FX / "senado_banco_master.json").read_bytes())
    assert len(itens) == 3
    r = itens[0]
    assert r["casa"] == "senado" and r["codigo"] == "172388" and r["sigla"] == "REQ" and r["numero"] == 1 and r["ano"] == 2026 and r["comissao"] == "CTFC"
    assert r["autor"].startswith("Senador Eduardo Girão") and r["data"] == "2026-01-30" and "banco Master" in r["ementa"]
    assert r["url"] == "https://www25.senado.leg.br/web/atividade/materias/-/materia/172388"


def test_parse_camara_normaliza_campos_e_url_publica():
    itens = parse_camara((FX / "camara_banco_master.json").read_bytes())
    assert [(i["sigla"], i["numero"], i["ano"]) for i in itens] == [("PFC", 24, 2026), ("RCP", 1, 2026)]
    assert itens[1]["casa"] == "camara" and itens[1]["codigo"] == "2600034" and itens[1]["data"] == "2026-02-02"
    assert itens[1]["url"] == "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=2600034"


class Relogio:
    t = 0.0
    def monotonic(self): return self.t
    def sleep(self, s): self.t += s


def test_consulta_guarda_bruto_e_projeta_sem_duplicar(tmp_path):
    respostas = {url_senado("Banco Master"): (FX / "senado_banco_master.json").read_bytes(), url_camara("Banco Master"): (FX / "camara_banco_master.json").read_bytes(),
                 url_senado("Vorcaro"): (FX / "senado_banco_master.json").read_bytes()}   # mesma resposta → mesmas matérias, não duplica
    def handler(req: httpx.Request) -> httpx.Response:
        corpo = respostas.get(str(req.url))
        return httpx.Response(200, content=corpo, headers={"content-type": "application/json"}) if corpo else httpx.Response(404)
    rel = Relogio()
    cliente = ClienteEducado(transport=httpx.MockTransport(handler), relogio=rel.monotonic, dormir=rel.sleep, teto=20)
    con = abrir(":memory:"); criar_schema(con)
    reg = tmp_path / "legislativo.jsonl"
    r = consultar(con, [{"casa": "senado", "palavra": "Banco Master"}, {"casa": "camara", "palavra": "Banco Master"}, {"casa": "senado", "palavra": "Vorcaro"}],
                  cliente=cliente, blobs=tmp_path / "blobs", registro=reg)
    assert r == {"consultas": 3, "erros": 0, "materias": 5}
    assert con.execute("SELECT COUNT(*) FROM materia_legislativa").fetchone()[0] == 5
    assert json.loads(con.execute("SELECT consultas_json FROM materia_legislativa WHERE codigo='172388'").fetchone()[0]) == ["senado:Banco Master", "senado:Vorcaro"]
    assert len(reg.read_text("utf-8").splitlines()) == 3
    con2 = abrir(":memory:"); criar_schema(con2)
    assert reingerir_legislativo(con2, reg, raiz=tmp_path) == 5      # projeção refeita só do registro + blobs
    assert isinstance(CONSULTAS, list) and CONSULTAS
