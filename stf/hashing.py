"""Chaves naturais para deduplicação entre coletas.

Andamento: (incidente, data, tipo, descricao, documentos, k), onde k é o ordinal
da ocorrência entre itens idênticos contado a partir do mais antigo (fim da lista
servida). Como o portal insere itens novos no topo, os k dos itens antigos não
mudam entre coletas. Se um item antigo for removido pelo portal, os k dos itens
idênticos mais recentes mudam; isso aparece no diff como remoção + inclusão, o
que é o comportamento desejado (não inventar continuidade).

Parte: (incidente, papel_portal, nome, oab, bloco). Advogados iguais em blocos
diferentes são entradas diferentes: representam partes diferentes.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Iterable

from .parse.andamentos import Andamento
from .parse.partes import Parte


def _h(*partes: object) -> str:
    payload = json.dumps(partes, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def chave_conteudo_andamento(a: Andamento) -> tuple:
    return (a.data, a.tipo, a.descricao, tuple(sorted((d.endpoint, d.id_portal) for d in a.documentos)))


def hash_andamentos(incidente: int, andamentos: list[Andamento]) -> list[str]:
    """Devolve um hash por andamento, na mesma ordem da lista de entrada."""
    vistos: Counter[tuple] = Counter()
    hashes: list[str | None] = [None] * len(andamentos)
    for idx in range(len(andamentos) - 1, -1, -1):  # do mais antigo para o mais recente
        chave = chave_conteudo_andamento(andamentos[idx])
        k = vistos[chave]
        vistos[chave] += 1
        hashes[idx] = _h("andamento", incidente, *chave, k)
    return hashes  # type: ignore[return-value]


def hash_parte(incidente: int, p: Parte) -> str:
    return _h("parte", incidente, p.papel_portal, p.nome, sorted(p.oab), p.bloco)


def hash_partes(incidente: int, partes: Iterable[Parte]) -> list[str]:
    return [hash_parte(incidente, p) for p in partes]
