"""Fontes externas oficiais (Banco Central, Senado…): captura educada, hash, histórico append-only."""
import json

import httpx

from stf.coleta import ClienteEducado
from stf.db import abrir, criar_schema
from stf.externas import capturar_fontes, exportar_fontes, reingerir_externas


class Relogio:
    t = 0.0
    def monotonic(self): return self.t
    def sleep(self, s): self.t += s


def _cliente(respostas: dict[str, tuple[int, bytes, str]]):
    def handler(req: httpx.Request) -> httpx.Response:
        st, corpo, ct = respostas.get(str(req.url), (404, b"nao", "text/html"))
        return httpx.Response(st, content=corpo, headers={"content-type": ct})
    rel = Relogio()
    return ClienteEducado(transport=httpx.MockTransport(handler), relogio=rel.monotonic, dormir=rel.sleep, teto=50), rel


FONTES = [
    {"id": "bcb-liq", "rotulo": "Registro da liquidação no BC", "orgao": "Banco Central do Brasil", "url": "https://www4.bcb.gov.br/Lid/x", "capturar": True, "por_que": "ato oficial"},
    {"id": "wiki", "rotulo": "Verbete", "orgao": "Wikipédia", "url": "https://pt.wikipedia.org/wiki/x", "capturar": False, "por_que": "referência secundária"},
]


def test_captura_so_as_marcadas_e_guarda_hash_com_historico(tmp_path):
    con = abrir(":memory:"); criar_schema(con)
    cliente, rel = _cliente({"https://www4.bcb.gov.br/Lid/x": (200, b"<html>liquidacao</html>", "text/html")})
    r1 = capturar_fontes(con, FONTES, cliente=cliente, blobs=tmp_path / "blobs")
    assert r1 == {"capturadas": 1, "erros": 0, "puladas": 1}
    assert cliente.count == 1                      # a não marcada não gera requisição
    rel.t += 10
    r2 = capturar_fontes(con, FONTES, cliente=cliente, blobs=tmp_path / "blobs")
    assert r2["capturadas"] == 1
    snaps = con.execute("SELECT fonte_id, http_status, sha256, bytes FROM fonte_externa_snapshot ORDER BY id").fetchall()
    assert len(snaps) == 2 and snaps[0]["sha256"] == snaps[1]["sha256"] and snaps[0]["bytes"] == 23   # append-only, conteúdo idêntico
    exp = exportar_fontes(con, FONTES)
    bcb = next(f for f in exp if f["id"] == "bcb-liq")
    assert bcb["ultima"]["sha256"] == snaps[0]["sha256"] and len(bcb["historico"]) == 2 and bcb["mudou"] is False
    wiki = next(f for f in exp if f["id"] == "wiki")
    assert wiki["ultima"] is None and wiki["capturar"] is False


def test_erro_http_fica_registrado_sem_blob(tmp_path):
    con = abrir(":memory:"); criar_schema(con)
    cliente, _ = _cliente({})
    r = capturar_fontes(con, FONTES[:1], cliente=cliente, blobs=tmp_path / "blobs")
    assert r == {"capturadas": 0, "erros": 1, "puladas": 0}
    s = con.execute("SELECT http_status, sha256 FROM fonte_externa_snapshot").fetchone()
    assert s["http_status"] == 404 and s["sha256"] is None
    assert json.loads(json.dumps(exportar_fontes(con, FONTES[:1])))[0]["ultima"]["http_status"] == 404


def test_registro_jsonl_reconstroi_a_tabela(tmp_path):
    con = abrir(":memory:"); criar_schema(con)
    cliente, _ = _cliente({"https://www4.bcb.gov.br/Lid/x": (200, b"<html>x</html>", "text/html")})
    reg = tmp_path / "externas.jsonl"
    capturar_fontes(con, FONTES, cliente=cliente, blobs=tmp_path / "blobs", registro=reg)
    capturar_fontes(con, FONTES, cliente=cliente, blobs=tmp_path / "blobs", registro=reg)
    assert len(reg.read_text("utf-8").splitlines()) == 2
    con2 = abrir(":memory:"); criar_schema(con2)
    assert reingerir_externas(con2, reg) == 2
    assert con2.execute("SELECT COUNT(*) FROM fonte_externa_snapshot").fetchone()[0] == 2
