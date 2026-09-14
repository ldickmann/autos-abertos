"""Relações entre processos, extraídas por regex de andamentos com texto padronizado.

Fontes reconhecidas (todas do próprio portal, sem inferência):
- "Distribuído por prevenção": "Processo que justifica: X. Processos relacionados: A, B, C"
- Certidões de autuação: "autuação da PET 16440 e da PET 16441"

O destino é (classe, número). O portal não expõe o incidente; a resolução é da Fase 2.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .andamentos import Andamento

_PROC_RE = re.compile(r"\b([A-Z][A-Za-z]{1,6})\s?(\d{1,7})\b")
_JUSTIFICA_RE = re.compile(r"Processo que justifica:\s*(.+?)(?:\.\s*Processos relacionados:|\.?\s*$)")
_RELACIONADOS_RE = re.compile(r"Processos relacionados:\s*(.+?)\.?\s*$")
_AUTUACAO_RE = re.compile(r"autua[çc][ãa]o d[aoe]s?\s+(.+)$", re.I)

_CLASSES_STF = {"PET", "INQ", "HC", "RCL", "AP", "ADPF", "ADI", "ADO", "ADC", "MS", "RE", "ARE",
                "AI", "AC", "PPE", "EXT", "MI", "SL", "SS", "STA", "AO", "AR", "EP", "CC", "RHC", "RMS"}


@dataclass(frozen=True)
class Relacao:
    classe: str
    numero: int
    tipo: str
    posicao_andamento: int


def _processos(texto: str) -> list[tuple[str, int]]:
    out = []
    for m in _PROC_RE.finditer(texto):
        classe, num = m.group(1), int(m.group(2))
        if classe.upper() in _CLASSES_STF:
            out.append((classe[0].upper() + classe[1:].lower() if classe.isupper() else classe, num))
    return out


def extrair_relacoes(andamentos: list[Andamento]) -> list[Relacao]:
    out: list[Relacao] = []
    for a in andamentos:
        if a.tipo == "Distribuído por prevenção":
            if (m := _JUSTIFICA_RE.search(a.descricao)):
                out += [Relacao(c, n, "justifica_prevencao", a.posicao) for c, n in _processos(m.group(1))]
            if (m := _RELACIONADOS_RE.search(a.descricao)):
                out += [Relacao(c, n, "relacionado", a.posicao) for c, n in _processos(m.group(1))]
        elif a.tipo == "Certidão" and (m := _AUTUACAO_RE.search(a.descricao)):
            out += [Relacao(c, n, "autuado_a_partir", a.posicao) for c, n in _processos(m.group(1))]
    return out
