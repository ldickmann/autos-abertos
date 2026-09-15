"""Extrator de conversas descritas pela PF (IPJ-A): cada balão nasce de uma frase com estrutura inequívoca
"NOME verbo [a NOME] que “citação”"; o resto vira relato literal. Nada é inferido além do que a frase diz."""

from stf.conversas import APARELHO_VORCARO, extrair_conversas, mascarar_telefone, segmentar_pagina


def _pagina(n, texto):
    return {"n": n, "texto": texto}


def test_mensagem_com_data_hora_e_destinatario():
    texto = ("Em 15/03/2024, às 15:07:11 -03:00, FABIO FARIA diz a DANIEL\n"
             "VORCARO que “O careca não pode atrasar”:\n"
             "Página 150 de 218\nIPJ-A nº 3298613/2026")
    out = extrair_conversas([_pagina(150, texto)], APARELHO_VORCARO)
    assert [p["n"] for p in out["paginas"]] == [150]
    (item,) = out["paginas"][0]["itens"]
    assert item["tipo"] == "mensagem"
    assert item["de"] == "FABIO FARIA" and item["para"] == "DANIEL VORCARO"
    assert item["texto"] == "O careca não pode atrasar"
    assert item["data"] == "2024-03-15" and item["hora"] == "15:07" and item["fuso"] == "-03:00"
    assert item["lado"] == "recebida"
    assert item["trecho"].startswith("Em 15/03/2024, às 15:07:11 -03:00, FABIO FARIA diz a DANIEL VORCARO")


def test_mensagem_do_dono_do_aparelho_vai_para_o_lado_enviado():
    texto = "DANIEL VORCARO diz a MARTHA que “Ciro e alexandre”.\nPágina 180 de 218"
    out = extrair_conversas([_pagina(180, texto)], APARELHO_VORCARO)
    (item,) = out["paginas"][0]["itens"]
    assert item["lado"] == "enviada" and item["de"] == "DANIEL VORCARO" and item["para"] == "MARTHA"
    assert item["data"] is None and item["hora"] is None


def test_parafrase_com_citacao_parcial_vira_relato():
    # "diz que está com “...”": a citação é um pedaço da fala dentro de uma paráfrase — não vira balão
    texto = "DANIEL VORCARO diz a MARTHA que está com “Ciro e alexandre”.\nPágina 180 de 218"
    out = extrair_conversas([_pagina(180, texto)], APARELHO_VORCARO)
    (item,) = out["paginas"][0]["itens"]
    assert item["tipo"] == "relato" and item["citacoes"] == ["Ciro e alexandre"]


def test_figura_de_conversa_vira_captura_com_legenda():
    texto = ("Figura 150 – FABIO FARIA diz a DANIEL VORCARO que “O careca não pode atrasar”\n"
             "Imediatamente após a cobrança de FABIO FARIA, DANIEL\n"
             "VORCARO envia mensagem para ANGELO SILVA:\n"
             "Página 151 de 218\nIPJ-A nº 3298613/2026")
    out = extrair_conversas([_pagina(151, texto)], APARELHO_VORCARO)
    itens = out["paginas"][0]["itens"]
    assert itens[0]["tipo"] == "figura" and itens[0]["numero"] == 150
    assert itens[0]["legenda"] == "FABIO FARIA diz a DANIEL VORCARO que “O careca não pode atrasar”"
    assert itens[1]["tipo"] == "relato"
    assert itens[1]["texto"] == "Imediatamente após a cobrança de FABIO FARIA, DANIEL VORCARO envia mensagem para ANGELO SILVA:"


def test_legenda_em_duas_linhas():
    texto = ("Figura 151 – DANIEL VORCARO diz a ANGELO SILVA que o contrato BARCI DE MORAES é o\n"
             "mais importante e manda pagar imediatamente\n"
             "Na sequência dos fatos, alguns minutos depois, DANIEL BUENO\n"
             "VORCARO diz a sua funcionária que “É op pgto mais importante que temos”.\n"
             "Página 152 de 218")
    out = extrair_conversas([_pagina(152, texto)], APARELHO_VORCARO)
    itens = out["paginas"][0]["itens"]
    assert itens[0]["tipo"] == "figura"
    assert itens[0]["legenda"] == "DANIEL VORCARO diz a ANGELO SILVA que o contrato BARCI DE MORAES é o mais importante e manda pagar imediatamente"
    assert itens[1]["tipo"] == "relato" and itens[1]["citacoes"] == ["É op pgto mais importante que temos"]


def test_relato_com_varias_citacoes_e_telefone_mascarado():
    texto = ("DANIEL BUENO VORCARO diz a sua funcionária, em contato salvo como “Romy Banco Master”\n"
             "(terminal 5511914794467) que o pagamento não pode “atrasar um dia”, pois “É op pgto mais importante que temos”.\n"
             "Página 152 de 218")
    out = extrair_conversas([_pagina(152, texto)], APARELHO_VORCARO)
    (item,) = out["paginas"][0]["itens"]
    assert item["tipo"] == "relato"
    assert "5511914794467" not in item["texto"] and "terminal 5511•••••••••" in item["texto"]
    assert item["citacoes"] == ["Romy Banco Master", "atrasar um dia", "É op pgto mais importante que temos"]
    assert "5511914794467" not in item["trecho"]


def test_pagina_sem_conversa_fica_de_fora():
    texto = ("Esses arquivos residuais foram localizados em pasta temporária do dispositivo com a nomenclatura “tmp”.\n"
             "Figura 79 – Sequência dos eventos relacionadas com a Nota criada em 05/11/2025 às 17:10:51 UTC\n"
             "Página 80 de 218")
    out = extrair_conversas([_pagina(80, texto)], APARELHO_VORCARO)
    assert out is None


def test_mensagem_com_hora_sem_data_e_verbos_variados():
    texto = ("Às 10:42:52 -03:00, GUSTAVO MOTORISTA responde a DANIEL VORCARO que “Onix prata, ABC1D23”.\n"
             "Na sequência, às 10:46:44 -03:00, DANIEL BUENO VORCARO encaminha a mensagem “Tucumã 99” e informa que está “descendo”.\n"
             "Página 20 de 218")
    out = extrair_conversas([_pagina(20, texto)], APARELHO_VORCARO)
    itens = out["paginas"][0]["itens"]
    assert itens[0]["tipo"] == "mensagem" and itens[0]["hora"] == "10:42" and itens[0]["de"] == "GUSTAVO MOTORISTA"
    # duas citações na mesma frase: não há como atribuir cada uma com segurança → relato, com as citações listadas
    assert itens[1]["tipo"] == "relato" and itens[1]["citacoes"] == ["Tucumã 99", "descendo"]


def test_mascarar_telefone_preserva_datas_valores_e_cnpj():
    assert mascarar_telefone("terminal 5511914794467 e 556192664093") == "terminal 5511••••••••• e 5561••••••••"
    assert mascarar_telefone("R$ 3.422.268,14 em 15/03/2024 às 15:07:11, CNPJ 07.875.796/0001-75, IPJ 144738439.2026") == \
        "R$ 3.422.268,14 em 15/03/2024 às 15:07:11, CNPJ 07.875.796/0001-75, IPJ 144738439.2026"


def test_segmentar_pagina_separa_frases_sem_quebrar_numeros():
    frases = segmentar_pagina("ROMY envia documento no valor de R$ 3.422.268,14. Na sequência, às 15:10:00 -03:00, VORCARO responde: ok.\nPágina 1 de 2")
    assert frases == ["ROMY envia documento no valor de R$ 3.422.268,14.", "Na sequência, às 15:10:00 -03:00, VORCARO responde: ok."]


def test_fuso_com_espaco_aspas_retas_e_verbo_sem_que():
    texto = ('Às 10:42:02 - 03:00, DANIEL BUENO VORCARO pergunta "Chego 11 cravado?" e informa que enviará os dados.\n'
             "Página 19 de 218")
    out = extrair_conversas([_pagina(19, texto)], APARELHO_VORCARO)
    (item,) = out["paginas"][0]["itens"]
    assert item["tipo"] == "mensagem" and item["texto"] == "Chego 11 cravado?" and item["hora"] == "10:42" and item["lado"] == "enviada"


def test_contato_entre_aspas_e_nome_nao_citacao():
    texto = ('Às 10:42:16 -03:00, DANIEL BUENO VORCARO solicita a "Gustavo Motorista" que "Modelo e placa nosso carro".\n'
             "Página 20 de 218")
    out = extrair_conversas([_pagina(20, texto)], APARELHO_VORCARO)
    (item,) = out["paginas"][0]["itens"]
    assert item["tipo"] == "mensagem" and item["para"] == "Gustavo Motorista" and item["texto"] == "Modelo e placa nosso carro"


def test_placa_de_veiculo_mascarada():
    texto = ('DANIEL VORCARO envia a FABIO FARIA os dados “Range Rover Vogue” e “RSB7C37”.\nPágina 19 de 218')
    out = extrair_conversas([_pagina(19, texto)], APARELHO_VORCARO)
    (item,) = out["paginas"][0]["itens"]
    assert "RSB7C37" not in item["texto"] and "[placa omitida]" in item["texto"]


def test_pagina_de_metodologia_com_aspas_nao_e_conversa():
    texto = ('A primeira, denominada "Logs", registra eventos do sistema operacional, como o momento em que uma mensagem é enviada pelo WhatsApp.\n'
             "Página 6 de 218")
    assert extrair_conversas([_pagina(6, texto)], APARELHO_VORCARO) is None


def _unico(texto, n=1):
    out = extrair_conversas([_pagina(n, texto)], APARELHO_VORCARO)
    (item,) = out["paginas"][0]["itens"]
    return item


def test_relato_com_um_falante_e_varias_citacoes_vira_falas():
    it = _unico("VORCARO responde que “Opcao 1 não é o negocio”, depois acrescenta “Os ativos sao deles...ja”.", 160)
    assert it["tipo"] == "relato" and it["de"] == "VORCARO" and it["lado"] == "enviada"
    assert it["falas"] == ["Opcao 1 não é o negocio", "Os ativos sao deles...ja"]


def test_relato_com_segundo_sujeito_nao_atribui():
    it = _unico("DANIEL VORCARO retoma a conversa com ANGELO SILVA, que afirma que irá “pagar antecipado e depois pegamos a NF”:", 153)
    assert it["tipo"] == "relato" and it["de"] is None and it["falas"] == []
    assert it["citacoes"] == ["pagar antecipado e depois pegamos a NF"]


def test_relato_ignora_nome_citado_como_fala():
    it = _unico("PALHARES explica que, segundo “Guilherme”, o “escritório deles não pode ser parte do contrato”.", 162)
    assert it["de"] == "PALHARES" and it["lado"] == "recebida"
    assert it["falas"] == ["escritório deles não pode ser parte do contrato"]
    assert it["citacoes"] == ["Guilherme", "escritório deles não pode ser parte do contrato"]


def test_relato_contato_com_terminal_entre_nome_e_verbo():
    it = _unico("Em 11/01/2024, o contato denominado “Vivi Moraes” (terminal 5511914794467), envia mensagem para DANIEL BUENO VORCARO às 16:48:59 -03:00, informando que, “Conforme conversamos, estou enviando minuta”.", 28)
    assert it["tipo"] == "relato" and it["de"] == "Vivi Moraes" and it["lado"] == "recebida"
    assert it["falas"] == ["Conforme conversamos, estou enviando minuta"]


def test_relato_continuacao_com_e_depois():
    it = _unico("No dia 08/02/2024, VORCARO pede a seu cunhado FABIANO ZETTEL que envie o “contrato barci moraes assinado”, e depois questiona “Quando era o primeiro pgto?”.", 149)
    assert it["de"] == "VORCARO" and it["falas"] == ["contrato barci moraes assinado", "Quando era o primeiro pgto?"]


def test_nome_de_contato_apos_preposicao_nao_e_fala():
    it = _unico("Segundos após o screenshot, DANIEL VORCARO envia uma mensagem de Whatsapp a “Alexandre de Moraes BRASILIA”.", 16)
    assert it["falas"] == [] and it["citacoes"] == ["Alexandre de Moraes BRASILIA"]


def test_descricao_de_emoji_nao_e_fala():
    it = _unico('FÁBIO FARIA pergunta se DANIEL BUENO pode falar, ao qual se refere por meio do emoji de "homem careca".', 30)
    assert it["falas"] == []


def test_endereco_de_brasilia_e_omissoes_curadas():
    from stf.conversas import extrair_conversas as ex
    texto = "FABIO FARIA envia a DANIEL BUENO VORCARO endereço, no “SMDB 26, Lote 08, Casa F Residencial Boa Vista”, em Brasília. VORCARO encaminha a mensagem “Tucumã 99”.\nPágina 36 de 218"
    out = ex([_pagina(36, texto)], {**APARELHO_VORCARO, "omitir": ["Tucumã 99"]})
    itens = out["paginas"][0]["itens"]
    assert "SMDB" not in itens[0]["texto"] and "[endereço omitido]" in itens[0]["texto"]
    assert itens[1]["tipo"] == "mensagem" and itens[1]["texto"] == "[endereço omitido]"
    assert itens[1]["trecho"] == "VORCARO encaminha a mensagem “[endereço omitido]”."


def test_titulo_de_secao_numerado_vira_marcador():
    texto = ("5.4 Cobranças de pagamento referente ao primeiro contrato do Banco Master com\n"
             "o Escritório de VIVIANE DE MORAES\n"
             "Em outros trechos de diálogos, DANIEL VORCARO trata da relação contratual.\n"
             "VORCARO pede a FABIANO ZETTEL que envie o “contrato barci moraes assinado”.\nPágina 149 de 218")
    out = extrair_conversas([_pagina(149, texto)], APARELHO_VORCARO)
    itens = out["paginas"][0]["itens"]
    assert itens[0] == {"tipo": "secao", "pagina": 149, "texto": "5.4 Cobranças de pagamento referente ao primeiro contrato do Banco Master com o Escritório de VIVIANE DE MORAES"}
    assert itens[1]["tipo"] == "relato" and itens[1]["texto"].startswith("Em outros trechos")
    assert itens[2]["tipo"] == "relato" and itens[2]["de"] == "VORCARO" and itens[2]["falas"] == ["contrato barci moraes assinado"]


def test_mascarar_pagina_cpf_antes_de_telefone_e_classes_processuais_nao_sao_placa():
    from stf.conversas import mascarar_pagina
    assert mascarar_pagina("BARRETO,\n00203577108, em 26/02") == "BARRETO,\n***.035.771-**, em 26/02"
    assert mascarar_pagina("PET16019 117\nINQ5026 1025\nADI 1234 x\nplaca ABC-1234 e RSB7C37 e KLM 9876") == \
        "PET16019 117\nINQ5026 1025\nADI 1234 x\nplaca [placa omitida] e [placa omitida] e [placa omitida]"
    assert mascarar_pagina("terminal 5511914794467") == "terminal 5511•••••••••"


def test_mascarar_pagina_enderecos_pessoais_e_falsos_positivos():
    from stf.conversas import mascarar_pagina
    lista = ("1 - JOÃO SILVA (CPF 123.456.789-00)\nRua Galeno de Revoredo, n. 20, apto 132, Itaim Bibi, São Paulo/SP,\nCEP 04531-030;\n"
             "2 - MARIA SOUZA (CPF 987.654.321-00)\nEndereço 1: R. Dr. Ibsen, 141, São\nPaulo/SP Endereço 2: Rua Fausto, 40, apto 501 – Belo Horizonte/MG;\n"
             "3 - PEDRO LIMA (CPF\n077.295.156- 01) Rua Augusto de Lima, 585, Sarzedo/MG;\n4 - ANA (CPF 111.222.333-44);\n"
             "5 - JOSE (CPF 111.222.333-55)\nEndereço a ser confirmado pela autoridade policial.")
    out = mascarar_pagina(lista)
    for s in ("Galeno", "Ibsen", "Fausto", "Augusto de Lima", "Sarzedo", "04531"):
        assert s not in out, s
    assert "077.295.156" not in out and "***.295.156-**" in out
    assert out.count("[endereço omitido]") == 3
    assert "Endereço a ser confirmado pela autoridade policial." in out
    prosa = "KAROLINA, administradora, CPF nº 111.222.333-44, domiciliada nesta Capital, na Rua das Flores, 10, apto 2. A empresa X, com sede nesta Capital, na Av. Paulista, 1000."
    out2 = mascarar_pagina(prosa)
    assert "Rua das Flores" not in out2 and "domiciliada [endereço omitido]" in out2
    assert "Av. Paulista, 1000" in out2  # sede de empresa é pública
    assert mascarar_pagina("no IPL 2024.0087917 - SR/PF e NIRE 35300052178, RENAVAM 12345678901") == "no IPL 2024.0087917 - SR/PF e NIRE 35300052178, RENAVAM ***.456.789-**"
