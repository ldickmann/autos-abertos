"""Portal falso para testes do expansor: responde com os fixtures, sem rede.

Simula:
- listarProcessos.asp?classe=X&numeroProcesso=N → 302 → detalhe.asp?incidente=M (ou 200 sem redirect)
- verImpressao.asp?incidente=M → casca do fixture com incidente/classe/número trocados
- aba*.asp?incidente=M → fixtures (as mesmas para todo incidente; só a casca muda)
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

FIX = Path(__file__).parent / "fixtures" / "7514886"


def casca_para(incidente: int, classe: str, numero: int) -> bytes:
    raw = (FIX / "casca.html").read_text("utf-8")
    raw = raw.replace("7514886", str(incidente)).replace("Pet 15556", f"{classe} {numero}")
    raw = raw.replace("'Pet'", f"'{classe}'").replace("+ 15556", f"+ {numero}")
    return raw.encode("utf-8")


class PortalFalso:
    def __init__(self, processos: dict[tuple[str, int], int | None], abas_por_incidente: dict[int, dict[str, bytes]] | None = None):
        """processos: (classe, numero) → incidente principal, ou None para 'não encontrado'."""
        self.processos = processos
        self.por_incidente = {inc: (c, n) for (c, n), inc in processos.items() if inc}
        self.abas = abas_por_incidente or {}
        self.requisicoes: list[str] = []

    def transporte(self) -> httpx.MockTransport:
        return httpx.MockTransport(self)

    def __call__(self, req: httpx.Request) -> httpx.Response:
        url = str(req.url)
        self.requisicoes.append(url)
        p = urlparse(url)
        q = {k: v[0] for k, v in parse_qs(p.query).items()}
        nome = p.path.rsplit("/", 1)[-1]
        if nome == "robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /processos\n")
        if nome == "listarProcessos.asp":
            inc = self.processos.get((q["classe"], int(q["numeroProcesso"])))
            if inc is None:
                return httpx.Response(200, text="<html><body>Nenhum processo encontrado</body></html>")
            return httpx.Response(302, headers={"Location": f"detalhe.asp?incidente={inc}"})
        if nome == "detalhe.asp":
            inc = int(q["incidente"])
            c, n = self.por_incidente[inc]
            return httpx.Response(200, content=casca_para(inc, c, n))
        if nome == "verImpressao.asp":
            inc = int(q["incidente"])
            c, n = self.por_incidente[inc]
            return httpx.Response(200, content=casca_para(inc, c, n))
        if nome.startswith("aba"):
            inc = int(q["incidente"])
            aba = nome[3:-4].lower()
            personalizada = self.abas.get(inc, {}).get(aba)
            return httpx.Response(200, content=personalizada if personalizada is not None else (FIX / f"{aba}.html").read_bytes())
        return httpx.Response(404)
