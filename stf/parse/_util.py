"""Utilitários compartilhados pelos parsers. Zero rede, zero LLM."""

from __future__ import annotations

import re
from datetime import datetime

from selectolax.parser import HTMLParser, Node

_WS = re.compile(r"\s+")


def decode(raw: bytes) -> str:
    """O portal serve UTF-8 (declarado na casca; os fragmentos não declaram).
    Falha de decodificação é erro, não silêncio: um byte fora de UTF-8 indica
    mudança no portal e precisa aparecer."""
    return raw.decode("utf-8")


def clean(text: str | None) -> str:
    return _WS.sub(" ", text or "").strip()


def tree(raw: bytes) -> HTMLParser:
    return HTMLParser(decode(raw))


def text_of(node: Node | None) -> str:
    return clean(node.text()) if node is not None else ""


def data_iso(ddmmaaaa: str) -> str:
    """'27/02/2026' → '2026-02-27'. Data fora do formato é erro explícito."""
    return datetime.strptime(ddmmaaaa.strip(), "%d/%m/%Y").date().isoformat()


def datahora_iso(texto: str) -> str:
    """'11/09/2026 15:09:12' → '2026-09-11T15:09:12'."""
    return datetime.strptime(texto.strip(), "%d/%m/%Y %H:%M:%S").isoformat()
