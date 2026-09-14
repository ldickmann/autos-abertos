from stf.resolver import interpretar_resolucao, url_resolucao


def test_url_de_resolucao():
    assert url_resolucao("Pet", 15556) == "https://portal.stf.jus.br/processos/listarProcessos.asp?classe=Pet&numeroProcesso=15556"


def test_redirect_para_detalhe_resolve_o_incidente():
    r = interpretar_resolucao("Pet", 15556, "https://portal.stf.jus.br/processos/detalhe.asp?incidente=7514886", b"<html></html>")
    assert r.status == "resolvido" and r.incidentes == [7514886]


def test_pagina_de_lista_com_varios_incidentes():
    html = b'<a href="detalhe.asp?incidente=111">a</a><a href="verProcessoAndamento.asp?incidente=222">b</a><a href="detalhe.asp?incidente=111">c</a>'
    r = interpretar_resolucao("Pet", 1, "https://portal.stf.jus.br/processos/listarProcessos.asp?classe=Pet&numeroProcesso=1", html)
    assert r.status == "multiplos" and r.incidentes == [111, 222]


def test_sem_incidente_algum():
    r = interpretar_resolucao("Pet", 1, "https://portal.stf.jus.br/processos/listarProcessos.asp?classe=Pet&numeroProcesso=1", b"<html>nada</html>")
    assert r.status == "nao_encontrado" and r.incidentes == []
