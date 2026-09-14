"""Guarda-corpo de neutralidade: textos gerados ou editoriais não podem conter juízo sobre pessoas.

Vale para: asserções `fato_processual` (texto do sistema), itens de decisão (pedido/decisão, texto do sistema),
verbetes do glossário e as introduções das páginas do site. Alegações e fundamentos ficam de fora porque reproduzem,
atribuídas, o que partes e julgadores disseram. A conferência é por palavra, fora de aspas.
"""
import re
import sqlite3
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
JUIZOS = re.compile(r"\b(culpad[oa]s?|criminos[oa]s?|corrupt[oa]s?|bandid[oa]s?|ladr(?:ão|ões|a)|mentiros[oa]s?|desonest[oa]s?|fraudador(?:es|a)?|golpista|canalha|safad[oa]|vagabund[oa])\b", re.I)
_ASPAS = re.compile(r"[“\"'][^”\"']{0,400}[”\"']")
# nomes de crimes previstos em lei não são juízo sobre ninguém: "organização criminosa" (Lei 12.850/2013), "associação criminosa" (art. 288 CP)
_TIPOS_PENAIS = re.compile(r"\b(organiza|associa|fac)[çc](?:[ãa]o|[õo]es)\s+criminosas?\b", re.I)


def _fora_de_aspas(texto: str) -> str:
    return _TIPOS_PENAIS.sub(" ", _ASPAS.sub(" ", texto or ""))


def _achados(texto: str) -> list[str]:
    return JUIZOS.findall(_fora_de_aspas(texto))


def test_glossario_sem_juizo():
    import json
    for v in json.loads((RAIZ / "stf" / "curadoria" / "glossario.json").read_text("utf-8"))["verbetes"]:
        assert not _achados(v["explicacao"] + " " + v.get("mais", "")), v["termo"]


def test_introducoes_das_paginas_sem_juizo():
    for p in (RAIZ / "web" / "app").rglob("page.tsx"):
        texto = re.sub(r"\{[^}]*\}", " ", p.read_text("utf-8"))   # tira expressões JSX, ficam os textos literais
        assert not _achados(texto), p


@pytest.mark.skipif(not (RAIZ / "data" / "stf.sqlite").exists(), reason="base local ausente (CI)")
def test_textos_gerados_sem_juizo():
    con = sqlite3.connect(RAIZ / "data" / "stf.sqlite")
    problemas = []
    for (i, t) in con.execute("SELECT id, texto FROM assercao WHERE tipo_epistemico='fato_processual'"):
        if _achados(t):
            problemas.append(("assercao", i, t[:120]))
    for (i, p, d) in con.execute("SELECT id, pedido, decisao FROM decisao_item"):
        if _achados(p) or _achados(d):
            problemas.append(("decisao_item", i, (p + " / " + d)[:120]))
    assert not problemas, problemas[:10]
