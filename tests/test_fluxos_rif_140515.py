"""Consistência interna do dataset curado do RIF 140515 (data/curadoria/fluxos/rif-140515.json)."""
import json
from pathlib import Path

import pytest

from stf.fluxos import centavos

ARQ = Path(__file__).parent.parent / "data" / "curadoria" / "fluxos" / "rif-140515.json"
IGREJA, ZETTEL, SUPER, MORIAH = "cnpj:57391420000163", "cpf:818816", "cnpj:31446245000170", "cnpj:02425349000281"   # chaves mascaradas, como no arquivo


@pytest.fixture(scope="module")
def dados():
    return json.loads(ARQ.read_text("utf-8"))


def _com(dados, secao, numero):
    return next(c for c in dados["comunicacoes"] if c["secao"] == secao and c["numero"] == numero)


def test_creditos_e_debitos_da_igreja_por_tipo_somam_os_totais_do_banco(dados):
    c = _com(dados, "suspeita", "1")
    resumos = [t for t in c["transacoes"] if t["natureza"] == "resumo_tipo"]
    creditos = sum(centavos(t["valor"]) for t in resumos if t["destino"] == IGREJA)
    debitos = sum(centavos(t["valor"]) for t in resumos if t["origem"] == IGREJA)
    assert creditos == centavos(c["creditos"]) == 2_849_331_191
    assert debitos == centavos(c["debitos"]) == 2_861_700_201


def test_vinte_remetentes_e_vinte_destinatarios_da_igreja_com_zettel_no_topo(dados):
    c = _com(dados, "suspeita", "1")
    agreg = [t for t in c["transacoes"] if t["natureza"] == "agregado"]
    remetentes = [t for t in agreg if t["destino"] == IGREJA]                                   # inclui a própria igreja (18 lançamentos)
    destinatarios = [t for t in agreg if t["origem"] == IGREJA and t["destino"] != IGREJA]
    assert len(remetentes) == 20 and len(destinatarios) == 20
    assert any(t["origem"] == IGREJA for t in remetentes)
    assert remetentes[0]["origem"] == ZETTEL and centavos(remetentes[0]["valor"]) == 1_920_500_000 and remetentes[0]["quantidade"] == 26
    assert sum(centavos(t["valor"]) for t in remetentes) <= centavos(c["creditos"])
    assert sum(centavos(t["valor"]) for t in destinatarios) <= centavos(c["debitos"])


def test_teds_de_zettel_para_a_super_somam_9_18_milhoes_e_creditos_batem(dados):
    c = _com(dados, "suspeita", "3.1")
    teds_zettel = [t for t in c["transacoes"] if t["origem"] == ZETTEL and t["tipo"] == "ted"]
    assert sum(centavos(t["valor"]) for t in teds_zettel) == 918_000_000 and len(teds_zettel) == 4
    creditos = sum(centavos(t["valor"]) for t in c["transacoes"] if t["destino"] == SUPER)
    assert creditos == 990_000_000                      # TEDs 9.880.000 + PIX 20.000: o comunicante detalha isto
    assert centavos(c["creditos"]) == 990_002_000       # e informa "cerca de R$ 9.900.020,00" no total (R$ 20 não itemizados)
    teds_saida = [t for t in c["transacoes"] if t["origem"] == SUPER and t["tipo"] == "ted"]
    assert sum(centavos(t["valor"]) for t in teds_saida) == 252_500_000 and len(teds_saida) == 6


def test_quatro_veiculos_da_moriah_somam_4_95_milhoes(dados):
    tx = [t for c in dados["comunicacoes"] if c["titular"] == MORIAH for t in c["transacoes"]]
    assert len(tx) == 4 and all(t["tipo"] == "compra_veiculo" for t in tx)
    assert sum(centavos(t["valor"]) for t in tx) == 495_000_000


def test_luzom_compra_mais_divida_garantida_igual_ao_valor_comunicado(dados):
    c = _com(dados, "suspeita", "3.2")
    soma = sum(centavos(t["valor"]) for t in c["transacoes"])
    assert soma == 3_691_850_979                        # 23.118.509,79 + 13.800.000,00
    assert abs(soma - centavos(c["valor"])) < 100       # o cartório comunicou o valor arredondado (36.918.510,00)


def test_toda_transacao_tem_pagina_trecho_e_uma_ponta_conhecida(dados):
    for c in dados["comunicacoes"]:
        for t in c["transacoes"]:
            assert t["pagina"] and t["trecho"] and (t.get("origem") or t.get("destino"))


def test_nenhum_cpf_inteiro_fora_dos_campos_de_referencia(dados):
    """CPFs só podem aparecer como referência de ator (origem/destino/documento), nunca em textos livres exportáveis."""
    import re
    for c in dados["comunicacoes"]:
        for t in c["transacoes"]:
            assert not re.search(r"\d{3}\.\d{3}\.\d{3}-\d{2}", t.get("descricao") or "")
