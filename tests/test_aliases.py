"""Chave forte, aliases curados e propostas para revisão; função do documento pelo título."""
from stf.aliases import canonizar, normalizar_chave, propor_aliases
from stf.db import abrir, criar_schema
from stf.entidades import chave_de, chave_ministro, chave_nome
from stf.funcoes import funcao_de


def test_normalizacao_forte_junta_pontuacao_hifen_e_sociedade_anonima():
    assert normalizar_chave("KING PARTICIPAÇÕES IMOBILIÁRIAS LTDA.") == normalizar_chave("KING PARTICIPACOES IMOBILIARIAS LTDA")
    assert normalizar_chave("Procuradoria-Geral da República") == normalizar_chave("Procuradoria Geral da República")
    assert normalizar_chave("Banco Master S.A.") == normalizar_chave("BANCO MÁSTER S/A") == "BANCO MASTER SA"
    assert normalizar_chave("Comissão de Valores Mobiliários — CVM") == "COMISSAO DE VALORES MOBILIARIOS CVM"
    # o que é diferente continua diferente
    assert normalizar_chave("6ª Vara Criminal") != normalizar_chave("8ª Vara Criminal")


def test_aliases_curados_resolvem_para_a_chave_canonica():
    assert chave_nome("ANDRÉMENDONÇA") == "ministro:ANDRE MENDONCA"
    assert chave_ministro("Ministro André Mendoça (relator)") == "ministro:ANDRE MENDONCA"
    assert chave_nome("Procuradoria-Geral de República") == "nome:PROCURADORIA GERAL DA REPUBLICA"
    assert canonizar("nome:QUALQUER COISA") == "nome:QUALQUER COISA"
    assert chave_de("parte", "DANIEL BUENO VORCARO", []) == ("parte", "nome:DANIEL BUENO VORCARO")


def test_propostas_listam_parecidos_sem_fundir():
    con = abrir(":memory:"); criar_schema(con)
    for i, (nome, tipo) in enumerate([("Fundo Garantidor de Crédito", "organizacao"), ("Fundo Garantidor de Créditos", "organizacao"),
                                       ("MICAELA FERRAZ SEVERO", "pessoa"), ("MICAELA FERRAS SEVERO", "pessoa"), ("Outra Coisa Qualquer", "organizacao")]):
        con.execute("INSERT INTO entidade (id, tipo, chave, nome, origem) VALUES (?,?,?,?,'documento')", (i + 1, tipo, f"k{i}", nome))
    props = propor_aliases(con)
    pares = {(p["a"]["nome"], p["b"]["nome"]) for p in props}
    assert ("Fundo Garantidor de Crédito", "Fundo Garantidor de Créditos") in pares
    assert next(p for p in props if p["a"]["nome"].startswith("MICAELA"))["pessoas"] is True
    assert all(p["decisao"] is None for p in props)          # nada é decidido pelo código
    assert con.execute("SELECT COUNT(*) FROM entidade").fetchone()[0] == 5   # nada fundido


def test_funcao_do_documento_pelo_titulo():
    assert funcao_de("Decisão monocrática") == "decisao"
    assert funcao_de("Inteiro teor do acórdão") == "acordao"
    assert funcao_de("Voto Vogal") == "voto"
    assert funcao_de("Despacho") == "despacho" and funcao_de("Despacho", e_decisao=True) == "decisao"
    assert funcao_de("Vista à PGR") == "vista"
    assert funcao_de("Termo de disponibilização de autos") == "termo"
    assert funcao_de("Certidão de trânsito em julgado") == "certidao"
    assert funcao_de(None) == "outro"
