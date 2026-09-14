"""Fluxos financeiros: esquema, parsers do RIF, validação do dataset curado, carga e export."""
import json

import pytest

from stf.db import abrir, criar_schema
from stf.fluxos import (centavos, chave_ator, mascarar_documento, parse_principais, parse_relacionados)

TABELAS = ["fluxo_fonte", "fluxo_ator", "fluxo_comunicacao", "fluxo_participacao", "fluxo_transacao", "fluxo_bem", "fluxo_ocorrencia"]


def test_schema_cria_tabelas_de_fluxos():
    con = abrir(":memory:"); criar_schema(con)
    nomes = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert set(TABELAS) <= nomes


# ---------------------------------------------------------------- utilitários

def test_centavos_le_valores_em_reais_do_rif():
    assert centavos("R$19.205.000,00") == 1_920_500_000
    assert centavos("R$ 86.200,27") == 8_620_027
    assert centavos("57.110.313,00") == 5_711_031_300
    assert centavos("23.118.509,79") == 2_311_850_979


def test_mascara_cpf_no_padrao_do_portal_da_transparencia_e_mantem_cnpj():
    assert mascarar_documento("027.818.816-86") == "***.818.816-**"
    assert mascarar_documento("02781881686") == "***.818.816-**"
    assert mascarar_documento("57.391.420/0001-63") == "57.391.420/0001-63"


def test_chave_de_ator_distingue_pf_de_pj_sem_guardar_cpf_inteiro():
    assert chave_ator("57.391.420/0001-63") == ("cnpj:57391420000163", "pessoa_juridica")
    assert chave_ator("027.818.816-86") == ("cpf:818816", "pessoa_fisica")
    assert chave_ator("02781881686") == ("cpf:818816", "pessoa_fisica")


def test_ator_citado_so_por_nome_tem_chave_por_nome_e_tipo_desconhecido():
    assert chave_ator("nome:Dubem Business  Marketing Ltda") == ("nome:DUBEM BUSINESS MARKETING LTDA", "desconhecido")
    assert mascarar_documento("nome:Dubem Business Marketing Ltda") is None


def test_transacao_aceita_tipo_transferencia_generico():
    d = _dataset()
    d["comunicacoes"][0]["transacoes"][0]["tipo"] = "transferencia"
    assert validar_dataset(d, paginas={3: PAG3}) == []


def test_ingerir_fluxos_cria_ator_por_nome_quando_nao_ha_documento(tmp_path):
    con = _banco_com_documento()
    d = _dataset()
    d["comunicacoes"][0]["participacoes"].append({"nome": "DUBEM LTDA", "documento": "nome:DUBEM LTDA", "papel": "beneficiario"})
    arq = tmp_path / "rif.json"; arq.write_text(json.dumps(d, ensure_ascii=False), "utf-8")
    ingerir_fluxos(con, arq)
    a = con.execute("SELECT * FROM fluxo_ator WHERE chave='nome:DUBEM LTDA'").fetchone()
    assert a["tipo"] == "desconhecido" and a["documento_mascarado"] is None and a["nome"] == "DUBEM LTDA"


# ---------------------------------------------------------------- parsers

def test_parse_relacionados_le_nome_documento_e_papel():
    texto = ("Relacionados CPF/CNPJ Tipo do Envolvimento\n"
             "ROGUE PARTICIPACOES S.A. 19.936.735/0001-50 Outros\n"
             "ELISANGELA MAIA ROCHA 56979207687 48.319.756/0001-24 Remetente\n"
             "ANA PAULA PACIFICO FLORET 283.446.138-41 Procurador / Representante Legal\n"
             "37.398.826 JOAO MIGUEL DE OLIVEIRA RIBEIRO DA SILVA 37.398.826/0001-60 Beneficiário\n"
             "Segmento: Banco Central - Atípicas\n")
    assert parse_relacionados(texto) == [
        {"nome": "ROGUE PARTICIPACOES S.A.", "documento": "19.936.735/0001-50", "papel": "outros"},
        {"nome": "ELISANGELA MAIA ROCHA 56979207687", "documento": "48.319.756/0001-24", "papel": "remetente"},
        {"nome": "ANA PAULA PACIFICO FLORET", "documento": "283.446.138-41", "papel": "procurador"},
        {"nome": "37.398.826 JOAO MIGUEL DE OLIVEIRA RIBEIRO DA SILVA", "documento": "37.398.826/0001-60", "papel": "beneficiario"},
    ]


def test_parse_principais_le_lista_de_remetentes_com_quantidade_e_total():
    texto = ("Principais remetentes/depositantes identificados: FABIANO CAMPOS ZETTEL - 027.818.816-86 ( ADVOGADO - ADVOGADO ) - MIDIA - 26 lançamento(s)\n"
             "no total de: R$19.205.000,00 LAGOINHA PARTICIPACOES LTDA. - 54.305.666/0001-87 ( HOLDINGS DE INSTITUICOES NAO-FINANCEIRAS ) -\n"
             "3 lançamento(s) no total de: R$1.100.000,00 Resumo de lançamentos a débito")
    itens = parse_principais(texto, "remetentes")
    assert itens == [
        {"nome": "FABIANO CAMPOS ZETTEL", "documento": "027.818.816-86", "atividade": "ADVOGADO - ADVOGADO", "quantidade": 26, "valor_centavos": 1_920_500_000},
        {"nome": "LAGOINHA PARTICIPACOES LTDA.", "documento": "54.305.666/0001-87", "atividade": "HOLDINGS DE INSTITUICOES NAO-FINANCEIRAS", "quantidade": 3, "valor_centavos": 110_000_000},
    ]


def test_parse_principais_destinatarios_para_no_fim_da_lista():
    texto = ("Principais destinatários de recursos identificados: JORLAN INCORPORADORA E CONSTRUTORA LTDA - 02.237.485/0001-67 ( INCORPORACAO DE EMPREENDIMENTOS IMOBILIARIOS ) - 8\n"
             "lançamento(s) no total de: R$2.566.200,00 MUZZI MISK CONSTRUTORA E ENGENHARIA LTDA - 46.715.172/0001-42 ( CONSTRUCAO DE\n"
             "EDIFICIOS ) - 26 lançamento(s) no total de: R$2.302.945,68 CONSIDERAÇÕES Outorgado da analisada")
    itens = parse_principais(texto, "destinatarios")
    assert [i["nome"] for i in itens] == ["JORLAN INCORPORADORA E CONSTRUTORA LTDA", "MUZZI MISK CONSTRUTORA E ENGENHARIA LTDA"]
    assert itens[1]["atividade"] == "CONSTRUCAO DE EDIFICIOS" and itens[1]["valor_centavos"] == 230_294_568


# ---------------------------------------------------------------- validação e carga

from stf.fluxos_carga import ingerir_fluxos, validar_dataset  # noqa: E402

PAG3 = ("1 - IGREJA TESTE\nRelacionados CPF/CNPJ Tipo do Envolvimento\n"
        "IGREJA TESTE 57.391.420/0001-63 Titular\nFULANO DA SILVA 027.818.816-86 Remetente\n"
        "Informações Adicionais: Principais remetentes/depositantes identificados: FULANO DA SILVA - 027.818.816-86 ( ADVOGADO ) - 26 lançamento(s)\n"
        "no total de: R$19.205.000,00 Resumo de lançamentos a débito")


def _dataset(**sobrescrever):
    d = {
        "fonte": {"tipo": "rif", "identificador": "140515.2.9294.11521", "orgao": "COAF", "destinatario": "PF/SP",
                  "emitido_em": "2026-02-25", "documento": {"endpoint": "docspublicos", "id_portal": "Pet15645/00002_b19a2bb7"},
                  "incidente": 7526458},
        "comunicacoes": [{
            "secao": "suspeita", "numero": "1", "titular": "57.391.420/0001-63", "segmento": "Banco Central - Atípicas",
            "comunicante": "Banco do Brasil S.A.", "local": "Belo Horizonte-MG", "periodo_inicio": "2024-12-24", "periodo_fim": "2025-12-08",
            "valor": "57.110.313,00", "creditos": "28.493.311,91", "debitos": "28.617.002,01",
            "informacoes": "Período analisado", "pagina_inicio": 3, "pagina_fim": 3,
            "participacoes": [{"nome": "IGREJA TESTE", "documento": "57.391.420/0001-63", "papel": "titular"},
                              {"nome": "FULANO DA SILVA", "documento": "027.818.816-86", "papel": "remetente", "atividade": "ADVOGADO"}],
            "transacoes": [{"origem": "027.818.816-86", "destino": "57.391.420/0001-63", "valor": "19.205.000,00", "tipo": "pix",
                            "natureza": "agregado", "quantidade": 26, "periodo_inicio": "2024-12-24", "periodo_fim": "2025-12-08",
                            "pagina": 3, "trecho": "( ADVOGADO ) - 26 lançamento(s) no total de: R$19.205.000,00"}],
            "bens": [], "ocorrencias": [{"norma": "Carta-Circular BCB 4.001/2020, art. 1º", "codigo": "IV-a", "descricao": "movimentação incompatível"}],
        }],
    }
    d.update(sobrescrever)
    return d


def _banco_com_documento():
    con = abrir(":memory:"); criar_schema(con)
    con.execute("INSERT INTO documento (id, incidente, endpoint, id_portal, formato, url, snapshot_first_seen) VALUES (274, 7526458, 'docspublicos', 'Pet15645/00002_b19a2bb7', 'pdf', 'u', 0)")
    con.execute("INSERT INTO documento_pagina (documento_id, pagina, texto, chars) VALUES (274, 3, ?, ?)", (PAG3, len(PAG3)))
    con.execute("INSERT INTO entidade (id, tipo, chave, nome, origem) VALUES (9, 'parte', 'nome:FULANO DA SILVA', 'FULANO DA SILVA', 'partes')")
    con.commit()
    return con


def test_validar_dataset_aceita_o_exemplo():
    assert validar_dataset(_dataset(), paginas={3: PAG3}) == []


def test_validar_dataset_rejeita_trecho_ausente_enum_ruim_e_valor_sem_centavos():
    d = _dataset()
    t = d["comunicacoes"][0]["transacoes"][0]
    t["trecho"] = "isto não está na página"; t["tipo"] = "cripto"; t["valor"] = "19205000"
    erros = validar_dataset(d, paginas={3: PAG3})
    assert any("trecho" in e for e in erros) and any("tipo" in e for e in erros) and any("valor" in e for e in erros)


def test_validar_dataset_ignora_espacos_ao_conferir_o_trecho():
    d = _dataset()
    d["comunicacoes"][0]["transacoes"][0]["trecho"] = "26 lançamento(s) no total de: R$19.205.000,00"   # quebra de linha na página
    assert validar_dataset(d, paginas={3: PAG3}) == []


def test_ingerir_fluxos_grava_fonte_atores_comunicacao_transacao_e_liga_entidade(tmp_path):
    con = _banco_com_documento()
    arq = tmp_path / "rif.json"; arq.write_text(json.dumps(_dataset(), ensure_ascii=False), "utf-8")
    r = ingerir_fluxos(con, arq)
    assert r["comunicacoes"] == 1 and r["transacoes"] == 1 and r["atores"] == 2

    fonte = con.execute("SELECT * FROM fluxo_fonte").fetchone()
    assert fonte["documento_id"] == 274 and fonte["curadoria_sha256"] and fonte["curadoria_path"].endswith("rif.json")
    atores = {a["chave"]: a for a in con.execute("SELECT * FROM fluxo_ator")}
    assert atores["cpf:818816"]["documento_mascarado"] == "***.818.816-**" and atores["cpf:818816"]["entidade_id"] == 9
    assert atores["cnpj:57391420000163"]["tipo"] == "pessoa_juridica" and atores["cnpj:57391420000163"]["entidade_id"] is None
    assert "027.818.816-86" not in json.dumps([dict(a) for a in atores.values()])   # CPF inteiro nunca entra no banco

    com = con.execute("SELECT * FROM fluxo_comunicacao").fetchone()
    assert com["valor_centavos"] == 5_711_031_300 and com["titular_ator_id"] == atores["cnpj:57391420000163"]["id"]
    tx = con.execute("SELECT * FROM fluxo_transacao").fetchone()
    assert tx["valor_centavos"] == 1_920_500_000 and tx["origem_ator_id"] == atores["cpf:818816"]["id"] and tx["natureza"] == "agregado"
    assert con.execute("SELECT COUNT(*) FROM fluxo_participacao").fetchone()[0] == 2
    assert con.execute("SELECT norma FROM fluxo_ocorrencia").fetchone()[0].startswith("Carta-Circular")


def test_ingerir_fluxos_recusa_dataset_invalido_sem_gravar_nada(tmp_path):
    con = _banco_com_documento()
    d = _dataset(); d["comunicacoes"][0]["transacoes"][0]["trecho"] = "nada disso"
    arq = tmp_path / "rif.json"; arq.write_text(json.dumps(d, ensure_ascii=False), "utf-8")
    with pytest.raises(ValueError):
        ingerir_fluxos(con, arq)
    assert con.execute("SELECT COUNT(*) FROM fluxo_fonte").fetchone()[0] == 0


def test_ingerir_fluxos_e_idempotente(tmp_path):
    con = _banco_com_documento()
    arq = tmp_path / "rif.json"; arq.write_text(json.dumps(_dataset(), ensure_ascii=False), "utf-8")
    ingerir_fluxos(con, arq); ingerir_fluxos(con, arq)
    assert con.execute("SELECT COUNT(*) FROM fluxo_transacao").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM fluxo_ator").fetchone()[0] == 2


# ---------------------------------------------------------------- dados pessoais nunca entram nas tabelas

def test_mascarar_texto_apaga_cpf_formatado_ou_nao_rg_e_endereco():
    from stf.fluxos import mascarar_texto
    t = ("FABIANO CAMPOS ZETTEL - 027.818.816-86 e CPF: 02781881686. ZETTEL, 02781881686. Bc. 237, RG nº 5.169.947-SSP/SC, domiciliada nesta Capital, na Avenida "
         "Presidente Juscelino Kubitschek nº 1545, ap. 3708, Vila Nova Conceição, o imóvel; CNPJ 57.391.420/0001-63 fica.")
    m = mascarar_texto(t)
    assert "027.818.816-86" not in m and "02781881686" not in m and "5.169.947" not in m and "Kubitschek" not in m
    assert "***.818.816-**" in m and "57.391.420/0001-63" in m and "[endereço omitido]" in m


def test_ingerir_fluxos_mascara_cpf_embutido_no_nome_de_mei(tmp_path):
    con = _banco_com_documento()
    d = _dataset()
    d["comunicacoes"][0]["participacoes"].append({"nome": "ELISANGELA MAIA ROCHA 56979207687", "documento": "48.319.756/0001-24", "papel": "remetente"})
    arq = tmp_path / "rif.json"; arq.write_text(json.dumps(d, ensure_ascii=False), "utf-8")
    ingerir_fluxos(con, arq)
    assert con.execute("SELECT nome FROM fluxo_ator WHERE chave='cnpj:48319756000124'").fetchone()[0] == "ELISANGELA MAIA ROCHA ***.792.076-**"


def test_validar_dataset_recusa_trecho_de_transacao_com_cpf():
    d = _dataset()
    d["comunicacoes"][0]["transacoes"][0]["trecho"] = "FULANO DA SILVA - 027.818.816-86 ( ADVOGADO ) - 26 lançamento(s)"
    assert any("CPF" in e for e in validar_dataset(d, paginas={3: PAG3}))


def test_ingerir_fluxos_mascara_cpf_nos_campos_literais(tmp_path):
    con = _banco_com_documento()
    d = _dataset()
    d["comunicacoes"][0]["informacoes"] = "Outorgou poderes para : FULANO DA SILVA - 027.818.816-86; CPF: 02781881686"
    d["comunicacoes"][0]["consideracoes"] = "Outorgado ( FULANO DA SILVA - 027.818.816-86) foi citado"
    d["comunicacoes"][0]["transacoes"][0]["descricao"] = "origem: FULANO, 02781881686"
    arq = tmp_path / "rif.json"; arq.write_text(json.dumps(d, ensure_ascii=False), "utf-8")
    ingerir_fluxos(con, arq)
    com = con.execute("SELECT informacoes, consideracoes FROM fluxo_comunicacao").fetchone()
    tx = con.execute("SELECT descricao FROM fluxo_transacao").fetchone()
    for texto in (com[0], com[1], tx[0]):
        assert "027.818.816-86" not in texto and "02781881686" not in texto
    assert "***.818.816-**" in com[0]


# ---------------------------------------------------------------- exportação

def _banco_carregado(tmp_path, extra_com=None):
    from stf.fluxos_export import exportar_fluxos  # noqa: F401  (garante que o módulo existe)
    con = _banco_com_documento()
    d = _dataset()
    if extra_com:
        d["comunicacoes"].append(extra_com)
    arq = tmp_path / "rif.json"; arq.write_text(json.dumps(d, ensure_ascii=False), "utf-8")
    ingerir_fluxos(con, arq)
    return con


ESCRITURA_SEM_DIRECAO = {
    "secao": "automatica", "numero": "1.1", "titular": "57.391.420/0001-63", "segmento": "Notários e Registradores",
    "comunicante": "cartório", "local": "SP", "periodo_inicio": "2022-03-14", "periodo_fim": "2022-03-14", "valor": "38.000.000,00",
    "informacoes": "Diferença entre o valor fiscal e valor declarado", "pagina_inicio": 3, "pagina_fim": 3,
    "participacoes": [{"nome": "IGREJA TESTE", "documento": "57.391.420/0001-63", "papel": "titular"},
                      {"nome": "IM2D LTDA", "documento": "02.684.297/0001-87", "papel": "titular"},
                      {"nome": "FULANO DA SILVA", "documento": "027.818.816-86", "papel": "procurador"}],
    "bens": [{"id": "im", "tipo": "imovel", "descricao": "Imóvel", "valor": "38.000.000,00", "identificacao": {"livro": "1"}}],
    "transacoes": [], "ocorrencias": [],
}


def test_exportar_fluxos_tem_fontes_atores_comunicacoes_transacoes_e_grafo(tmp_path):
    from stf.fluxos_export import exportar_fluxos
    con = _banco_carregado(tmp_path, ESCRITURA_SEM_DIRECAO)
    out = exportar_fluxos(con)
    assert set(out) >= {"fontes", "atores", "comunicacoes", "transacoes", "grafo"}
    assert out["fontes"][0]["identificador"] == "140515.2.9294.11521" and out["fontes"][0]["documento"]["id"] == 274
    ator = next(a for a in out["atores"] if a["chave"] == "cpf:818816")
    assert ator["documento_mascarado"] == "***.818.816-**" and ator["entidade_id"] == 9
    assert ator["totais"]["saidas_centavos"] == 1_920_500_000 and ator["totais"]["entradas_centavos"] == 0
    igreja = next(a for a in out["atores"] if a["chave"] == "cnpj:57391420000163")
    assert igreja["totais"]["entradas_centavos"] == 1_920_500_000
    assert out["transacoes"][0]["trecho_fonte"] and out["transacoes"][0]["documento_id"] == 274
    texto = json.dumps(out, ensure_ascii=False)
    assert "identificacao" not in texto and "027.818.816-86" not in texto   # bens sem identificação; CPF só mascarado


def test_grafo_agrega_por_par_e_liga_titulares_de_escritura_sem_direcao(tmp_path):
    from stf.fluxos_export import exportar_fluxos
    con = _banco_carregado(tmp_path, ESCRITURA_SEM_DIRECAO)
    g = exportar_fluxos(con)["grafo"]
    ids = {a["chave"]: a["id"] for a in exportar_fluxos(con)["atores"]}
    dirigida = next(e for e in g["arestas"] if e["dirigida"])
    assert dirigida["origem"] == ids["cpf:818816"] and dirigida["destino"] == ids["cnpj:57391420000163"]
    assert dirigida["valor_centavos"] == 1_920_500_000 and dirigida["n"] == 1 and dirigida["transacoes"]
    nao_dirigida = next(e for e in g["arestas"] if not e["dirigida"])
    assert {nao_dirigida["origem"], nao_dirigida["destino"]} == {ids["cnpj:57391420000163"], ids["cnpj:02684297000187"]}
    assert nao_dirigida["valor_centavos"] == 3_800_000_000 and nao_dirigida["comunicacao_id"]
    assert {n["id"] for n in g["nos"]} >= {ids["cpf:818816"], ids["cnpj:57391420000163"], ids["cnpj:02684297000187"]}


def test_fluxos_csv_uma_linha_por_transacao_com_pagina_e_trecho(tmp_path):
    from stf.fluxos_export import fluxos_csv
    con = _banco_carregado(tmp_path)
    csv = fluxos_csv(con)
    linhas = csv.strip().splitlines()
    assert linhas[0].startswith("fonte,comunicacao,secao,origem,destino,valor_reais,data,periodo_inicio,periodo_fim,tipo,natureza,quantidade,pagina,trecho")
    assert len(linhas) == 2 and "19205000.00" in linhas[1] and "FULANO DA SILVA" in linhas[1] and "IGREJA TESTE" in linhas[1]
