"""Datas citadas no trecho literal das asserções: extração determinística e projeção assercao_data."""
from stf.datas import construir_datas, datas_no_texto
from stf.db import abrir, criar_schema


def test_reconhece_formatos_usuais_dos_documentos():
    t = ("Em 18/11/2025 o Banco Central decretou a liquidação; a representação de 3.6.2026 e o ofício de 1º de junho de 2026; "
         "publicado no DJe de 20/05/2026. Valores como 12/2025 ou 3/6 não contam; CPF 286.491.528-64 também não.")
    assert datas_no_texto(t) == [("2025-11-18", "18/11/2025"), ("2026-06-03", "3.6.2026"), ("2026-06-01", "1º de junho de 2026"), ("2026-05-20", "20/05/2026")]


def test_ignora_datas_impossiveis_e_anos_fora_da_faixa():
    assert datas_no_texto("31/02/2026 e 10/13/2025 e 05/05/1850 e 05/05/2150") == []


def test_projecao_guarda_todas_as_datas_e_marca_a_unica():
    con = abrir(":memory:"); criar_schema(con)
    con.execute("INSERT INTO documento (id, incidente, endpoint, id_portal, formato, url, sha256, tem_camada_texto, snapshot_first_seen) VALUES (1, 100, 'x', 'p', 'pdf', 'u', 's', 1, 1)")
    con.execute("INSERT INTO extracao (id, documento_id, sha256_documento, prompt_version, modelo, executada_em, status) VALUES (1, 1, 's', 'v', 'm', 't', 'ok')")
    for i, trecho in enumerate(["decretada em 18/11/2025 pelo BC", "prazo de 30/01/2026 a 15/02/2026", "sem data nenhuma"], start=1):
        con.execute("INSERT INTO assercao (id, documento_id, extracao_id, pagina, tipo_epistemico, texto, trecho_fonte, entidades_json, modelo, prompt_version, criado_em) "
                    "VALUES (?, 1, 1, 1, 'fato_processual', 't', ?, '[]', 'm', 'v', 't')", (i, trecho))
    con.commit()
    r = construir_datas(con)
    assert r == {"assercoes_com_data": 2, "datas": 3, "com_data_unica": 1}
    linhas = con.execute("SELECT assercao_id, data, literal, n_datas FROM assercao_data ORDER BY assercao_id, data").fetchall()
    assert [tuple(x) for x in linhas] == [(1, "2025-11-18", "18/11/2025", 1), (2, "2026-01-30", "30/01/2026", 2), (2, "2026-02-15", "15/02/2026", 2)]
    assert construir_datas(con) == r   # idempotente
