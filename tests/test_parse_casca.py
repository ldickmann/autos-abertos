from stf.parse.casca import parse_casca


def test_casca_extrai_cabecalho_do_processo(fx):
    c = parse_casca(fx("casca"))
    assert c.incidente == 7514886
    assert c.classe == "Pet"
    assert c.numero_processo == 15556
    assert c.numero_unico == "0165738-43.2026.1.00.0000"
    assert c.relator == "MIN. ANDRÉ MENDONÇA"
    assert c.relator_ultimo_incidente == "MIN. ANDRÉ MENDONÇA"
    assert c.ultimo_incidente == "Pet-AgR-quarto"


def test_casca_extrai_flags_de_tramitacao(fx):
    c = parse_casca(fx("casca"))
    assert c.publicidade == "Público"
    assert c.natureza == "Criminal"
    assert c.reu_preso is True
    assert c.meio == "E"
    assert c.peca == "P"
    assert c.tipo_tramitacao == "Processo Eletrônico"


def test_casca_lista_as_nove_abas_com_urls_relativas(fx):
    c = parse_casca(fx("casca"))
    assert list(c.abas) == [
        "partes", "andamentos", "informacoes", "decisoes", "sessao",
        "deslocamentos", "peticoes", "recursos", "pautas",
    ]
    assert c.abas["andamentos"] == "abaAndamentos.asp?incidente=7514886&imprimir=true"
    assert c.abas["sessao"] == "abaSessao.asp?incidente=7514886&tema=N"
    assert c.abas["partes"] == "abaPartes.asp?incidente=7514886"


def test_casca_rejeita_html_sem_incidente():
    import pytest
    from stf.parse.casca import CascaInvalida
    with pytest.raises(CascaInvalida):
        parse_casca(b"<html><body>Sem processo</body></html>")
