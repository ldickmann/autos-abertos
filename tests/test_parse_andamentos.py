from stf.parse.andamentos import parse_andamentos


def test_andamentos_conta_407_itens_em_ordem_de_exibicao(fx):
    a = parse_andamentos(fx("andamentos"))
    assert len(a) == 407
    assert [x.posicao for x in a[:3]] == [0, 1, 2]
    assert a[0].data == "2026-09-11" and a[0].tipo == "Remessa"
    assert a[-1].data == "2026-02-27" and a[-1].tipo == "Protocolado"


def test_andamento_descricao_e_texto_limpo(fx):
    a = parse_andamentos(fx("andamentos"))
    assert a[-1].descricao == "Petição Inicial (nº 21692) recebida em 27/02/2026, às 15:47:11"
    assert a[0].descricao == "da Petição nº 114945/2026 para GABINETE MINISTRO ANDRÉ MENDONÇA"


def test_andamento_documentos_com_rotulo_endpoint_id_e_formato(fx):
    a = parse_andamentos(fx("andamentos"))
    dist = next(x for x in a if x.tipo == "Distribuído por prevenção")
    assert len(dist.documentos) == 1
    d = dist.documentos[0]
    assert d.rotulo == "Certidão"
    assert d.endpoint == "downloadPeca"
    assert d.id_portal == "15384501728"
    assert d.formato == "pdf"
    assert d.url == "https://portal.stf.jus.br/processos/downloadPeca.asp?id=15384501728&ext=.pdf"


def test_andamentos_total_de_links_de_documento(fx):
    a = parse_andamentos(fx("andamentos"))
    docs = [d for x in a for d in x.documentos]
    assert len(docs) == 72
    rtf = [d for d in docs if d.formato == "rtf"]
    assert len(rtf) == 1 and rtf[0].endpoint == "downloadTexto" and rtf[0].id_portal == "6820169"


def test_andamento_captura_explicacao_do_portal_quando_existe(fx):
    a = parse_andamentos(fx("andamentos"))
    dist = next(x for x in a if x.tipo == "Distribuído por prevenção")
    assert dist.explicacao_portal.startswith("O processo foi enviado para o(a) ministro(a)")
    assert a[0].explicacao_portal is None


def test_decisoes_usa_mesmo_parser_e_e_subconjunto_de_andamentos(fx):
    a = parse_andamentos(fx("andamentos"))
    d = parse_andamentos(fx("decisoes"))
    assert len(d) == 27
    chave = lambda x: (x.data, x.tipo, x.descricao, tuple(doc.url for doc in x.documentos))
    assert set(map(chave, d)) <= set(map(chave, a))


def test_pautas_e_recursos(fx):
    p = parse_andamentos(fx("pautas"))
    assert len(p) == 1 and p[0].tipo == "Pauta publicada no DJE - 2ª Turma" and p[0].data == "2026-03-05"
    assert parse_andamentos(fx("recursos")) == []
