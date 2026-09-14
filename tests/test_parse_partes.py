from stf.parse.partes import parse_partes


def test_partes_conta_56_entradas(fx):
    partes = parse_partes(fx("partes"))
    assert len(partes) == 56


def test_partes_primeira_entrada_e_o_requerente(fx):
    p = parse_partes(fx("partes"))[0]
    assert p.papel_portal == "REQTE.(S)"
    assert p.papel == "requerente"
    assert p.nome == "DELEGADO DE POLÍCIA FEDERAL"
    assert p.oab == []
    assert p.bloco == 0


def test_partes_advogado_com_varias_oab(fx):
    partes = parse_partes(fx("partes"))
    adv = next(p for p in partes if p.nome == "SERGIO RODRIGUES LEONARDO")
    assert adv.papel_portal == "ADV.(A/S)"
    assert adv.papel == "advogado"
    assert adv.oab == ["40852/DF", "85000/MG", "317006/SP"]


def test_partes_advogado_pertence_ao_bloco_da_parte_representada(fx):
    partes = parse_partes(fx("partes"))
    vorcaro = next(p for p in partes if p.nome == "DANIEL BUENO VORCARO")
    advs = [p for p in partes if p.papel == "advogado" and p.bloco == vorcaro.bloco + 1]
    # o portal agrupa os advogados no bloco seguinte ao da parte representada
    assert [a.nome for a in advs] == [
        "SERGIO RODRIGUES LEONARDO", "THIAGO MACHADO DE CARVALHO", "ENGELS AUGUSTO MUNIZ",
    ]
    assert vorcaro.papel == "requerido"


def test_partes_papeis_normalizados_sem_inferencia(fx):
    partes = parse_partes(fx("partes"))
    from collections import Counter
    c = Counter(p.papel for p in partes)
    assert c == {"requerente": 1, "advogado": 38, "requerido": 14, "autoridade_policial": 1, "interessado": 2}
    # o literal do portal é preservado sempre
    assert all(p.papel_portal for p in partes)


def test_partes_sem_representacao_nao_vira_pessoa(fx):
    partes = parse_partes(fx("partes"))
    sem = [p for p in partes if p.nome == "SEM REPRESENTAÇÃO NOS AUTOS"]
    # o fixture real tem duas partes sem representação (blocos 1 e 30)
    assert [p.bloco for p in sem] == [1, 30]
    assert all(p.e_placeholder for p in sem)
    assert all(p.papel == "advogado" and p.oab == [] for p in sem)


def test_separa_oab_em_formatos_reais_do_portal():
    from stf.parse.partes import _separa_oab
    casos = {
        "ALVARO AUGUSTO MACEDO VASQUES ORIONE SOUZA (30814/A/MT, 317282/SP)": ["30814/A/MT", "317282/SP"],
        "ODEL MIKAEL JEAN ANTUN (62591/DF, 229733/RJ, 141073A/RS, 172515/SP)": ["62591/DF", "229733/RJ", "141073A/RS", "172515/SP"],
        "PEDRO IVO RODRIGUES VELLOSO CORDEIRO (23944/DF, 32957 A/PB, 450956/SP)": ["23944/DF", "32957 A/PB", "450956/SP"],
        "TICIANO FIGUEIREDO DE OLIVEIRA (5922-A/AP, 23870/DF)": ["5922-A/AP", "23870/DF"],
        "CARMEN MANSANO DA COSTA BARROS FILHA (01875/A/DF, 041099/RJ)": ["01875/A/DF", "041099/RJ"],
        "SEM REPRESENTAÇÃO NOS AUTOS": [],
        "KING PARTICIPAÇÕES IMOBILIÁRIAS LTDA": [],
    }
    for bruto, oabs in casos.items():
        nome, extraidas = _separa_oab(bruto)
        assert extraidas == oabs, bruto
        assert "(" not in nome or not oabs, bruto
