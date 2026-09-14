"""Política de coleta educada, testada com transporte simulado (sem rede) e relógio falso."""
import httpx
import pytest

from stf.coleta import ClienteEducado, TetoAtingido


class Relogio:
    def __init__(self):
        self.t = 1000.0
        self.dormiu: list[float] = []

    def monotonic(self):
        return self.t

    def sleep(self, s):
        self.dormiu.append(s)
        self.t += s


def cliente(handler, relogio, **kw):
    return ClienteEducado(
        transport=httpx.MockTransport(handler), relogio=relogio.monotonic, dormir=relogio.sleep, **kw
    )


def test_espaca_requisicoes_em_pelo_menos_3s():
    rel = Relogio()
    c = cliente(lambda req: httpx.Response(200, text="ok"), rel)
    c.get("https://portal.stf.jus.br/x", aba="a")
    rel.t += 0.5  # meio segundo depois
    c.get("https://portal.stf.jus.br/y", aba="b")
    assert rel.dormiu == [pytest.approx(2.5)]


def test_teto_de_requisicoes_e_duro():
    rel = Relogio()
    c = cliente(lambda req: httpx.Response(200, text="ok"), rel, teto=2)
    c.get("https://portal.stf.jus.br/1", aba="a")
    c.get("https://portal.stf.jus.br/2", aba="b")
    with pytest.raises(TetoAtingido):
        c.get("https://portal.stf.jus.br/3", aba="c")


def test_403_nao_e_retentado():
    rel = Relogio()
    chamadas = []
    c = cliente(lambda req: (chamadas.append(req.url), httpx.Response(403))[1], rel)
    r = c.get("https://portal.stf.jus.br/x", aba="a")
    assert r.status_code == 403 and len(chamadas) == 1


def test_503_e_retentado_com_backoff_exponencial():
    rel = Relogio()
    respostas = iter([503, 503, 200])
    c = cliente(lambda req: httpx.Response(next(respostas), text="ok"), rel)
    r = c.get("https://portal.stf.jus.br/x", aba="a")
    assert r.status_code == 200
    # dois backoffs: 5 s e 10 s (mais os intervalos mínimos de 3 s entre tentativas)
    assert 5.0 in rel.dormiu and 10.0 in rel.dormiu
    assert len(c.log) == 3 and [e["status"] for e in c.log] == [503, 503, 200]


def test_toda_requisicao_leva_ua_identificado_e_from():
    rel = Relogio()
    vistos = []
    c = cliente(lambda req: (vistos.append(dict(req.headers)), httpx.Response(200))[1], rel)
    c.get("https://portal.stf.jus.br/x", aba="a")
    h = vistos[0]
    assert h["user-agent"].startswith("Mozilla/5.0 (") and "stf-mapeador/" in h["user-agent"]
    assert "+mailto:" in h["user-agent"] and h["from"]
