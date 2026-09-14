"""Resolução classe+número → incidente(s), via listarProcessos.asp.

Verificado na Fase 0: `listarProcessos.asp?classe=Pet&numeroProcesso=15556` responde 302
para `detalhe.asp?incidente=7514886`. Se o portal devolver uma página de lista (sem
redirect), todos os `incidente=N` dela são registrados como candidatos ("multiplos").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse

from . import config

_INC_RE = re.compile(rb"incidente=(\d+)")


@dataclass
class Resolucao:
    classe: str
    numero: int
    status: str                       # resolvido | multiplos | nao_encontrado
    incidentes: list[int] = field(default_factory=list)
    url_final: str = ""


def url_resolucao(classe: str, numero: int) -> str:
    return f"{config.BASE_PROCESSOS}listarProcessos.asp?classe={classe}&numeroProcesso={numero}"


def interpretar_resolucao(classe: str, numero: int, url_final: str, html: bytes) -> Resolucao:
    p = urlparse(url_final)
    q = {k: v[0] for k, v in parse_qs(p.query).items()}
    if p.path.endswith("/detalhe.asp") and q.get("incidente", "").isdigit():
        return Resolucao(classe, numero, "resolvido", [int(q["incidente"])], url_final)
    vistos: list[int] = []
    for m in _INC_RE.finditer(html):
        n = int(m.group(1))
        if n not in vistos:
            vistos.append(n)
    if len(vistos) == 1:
        return Resolucao(classe, numero, "resolvido", vistos, url_final)
    if vistos:
        return Resolucao(classe, numero, "multiplos", vistos, url_final)
    return Resolucao(classe, numero, "nao_encontrado", [], url_final)
