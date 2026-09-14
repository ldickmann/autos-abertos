"""Vigilância do portal: comparação entre cópias vira registro append-only de 'sumiu', 'apareceu', 'mudou'."""
import json

from stf.vigiar import comparar, registrar
from tests.test_diff import _simular_coleta_antiga
from tests.test_ingest import montar_coleta


def test_comparar_lista_o_que_sumiu_no_portal(tmp_path, fx):
    completa = montar_coleta(tmp_path / "a", fx, "C0")
    encolhida = montar_coleta(tmp_path / "b", fx, "C1", _simular_coleta_antiga)   # cópia nova com menos itens = coisas sumiram
    r = comparar(completa, encolhida)
    assert r["incidente"] == 7514886 and r["resumo"]["sumiu"] == 12 and r["resumo"]["apareceu"] == 0 and r["resumo"]["mudou"] == 0
    tipos = {(m["o_que"], m["mudanca"]) for m in r["mudancas"]}
    assert tipos == {("andamento", "sumiu"), ("parte", "sumiu"), ("petição", "sumiu")}
    assert any(m["item"].startswith("2026-09-11 ") for m in r["mudancas"] if m["o_que"] == "andamento")


def test_registrar_e_append_only(tmp_path):
    log = tmp_path / "CHANGELOG-PORTAL.md"; js = tmp_path / "mudancas.json"
    rel = [{"incidente": 1, "processo": "Pet 1", "antes": "c0", "depois": "c1", "abas_identicas": [], "mudancas": [],
            "resumo": {"sumiu": 0, "apareceu": 0, "mudou": 0}}]
    registrar(rel, changelog=log, mudancas_json=js)
    rel2 = [{"incidente": 1, "processo": "Pet 1", "antes": "c1", "depois": "c2", "abas_identicas": [],
             "mudancas": [{"o_que": "andamento", "mudanca": "sumiu", "item": "2026-01-01 Decisão"}], "resumo": {"sumiu": 1, "apareceu": 0, "mudou": 0}}]
    registrar(rel2, changelog=log, mudancas_json=js)
    texto = log.read_text("utf-8")
    assert texto.startswith("# O que mudou no portal do STF") and texto.count("\n## ") == 2
    assert "sem mudanças" in texto and "andamento sumiu: 2026-01-01 Decisão" in texto
    hist = json.loads(js.read_text("utf-8"))
    assert len(hist) == 2 and hist[1]["processos"][0]["resumo"]["sumiu"] == 1
