"""Referências determinísticas: processos e dispositivos citados em documentos, andamento↔petição, intimação→andamento."""
from stf.db import abrir, criar_schema
from stf.referencias import construir_referencias, dispositivos_citados, processos_citados, resumo_dispositivos


def test_processos_citados_normaliza_classe_e_milhar():
    t = "Trata-se de agravo na Pet 15.556, apensa ao INQ 5026 e à Rcl nº 88121. Ver HC 247450 e PET 15556. Em 2026 (Pet 2025?)."
    r = processos_citados(t)
    assert [(c, n) for c, n, _ in r] == [("Pet", 15556), ("Inq", 5026), ("Rcl", 88121), ("HC", 247450), ("Pet", 15556)]
    assert all("Pet 15.556" in x[2] or x[2] for x in r)  # trecho literal em volta


def test_processos_citados_ignora_anos_puros_e_numeros_curtos():
    assert processos_citados("Pet 2024 e AP 12 e MS 25668") == [("MS", 25668, "Pet 2024 e AP 12 e MS 25668")]


def test_dispositivos_citados():
    t = ("nos termos do art. 312 do Código de Processo Penal e dos arts. 319, 320 do CPP; art. 4º da Lei n. 9.613/1998; "
         "art. 2º, § 1º, da Lei nº 12.850/2013; art. 5º, LXVI, da CF; art. 230-C do RISTF; art. 27 da Lei 6.385/76. O artigo sem diploma fica de fora: art. 99.")
    r = [(a, d) for a, d, _ in dispositivos_citados(t)]
    assert r == [("312", "CPP"), ("319", "CPP"), ("320", "CPP"), ("4", "Lei 9.613/1998"), ("2", "Lei 12.850/2013"),
                 ("5", "CF"), ("230-C", "RISTF"), ("27", "Lei 6.385/1976")]


def _base():
    con = abrir(":memory:"); criar_schema(con)
    con.execute("INSERT INTO documento (id, incidente, endpoint, id_portal, formato, url, titulo, sha256, tem_camada_texto, snapshot_first_seen) "
                "VALUES (1, 100, 'downloadPeca', 'x', 'pdf', 'u', 'Intimação', 'abc', 1, 1)")
    con.execute("INSERT INTO documento_pagina VALUES (1, 1, ?, 0)", (
        "COMUNICAÇÃO na Pet 15556. Decisão com base no art. 312 do CPP.\nAndamento(s):\n- Vista à PGR para fins de intimação - 20/05/2026\n- Inexistente - 01/01/2020\n",))
    for i, (data, tipo, desc) in enumerate([("2026-05-20", "Vista à PGR para fins de intimação", ""),
                                            ("2026-09-11", "Petição", "Manifestação - Petição: 114945 Data: 11/09/2026"),
                                            ("2026-09-11", "Petição", "Manifestação - Petição: 999 Data: 11/09/2026")]):
        con.execute("INSERT INTO andamento (id, incidente, hash_natural, data, tipo, descricao, posicao, snapshot_first_seen, snapshot_last_seen) "
                    "VALUES (?, 100, ?, ?, ?, ?, ?, 1, 1)", (i + 1, f"h{i}", data, tipo, desc, i))
    con.execute("INSERT INTO peticao (id, incidente, hash_natural, numero, posicao, snapshot_first_seen, snapshot_last_seen) VALUES (7, 100, 'p1', '114945/2026', 0, 1, 1)")
    con.execute("INSERT INTO peticao (id, incidente, hash_natural, numero, posicao, snapshot_first_seen, snapshot_last_seen) VALUES (8, 100, 'p2', '999/2025', 0, 1, 1)")
    con.execute("INSERT INTO peticao (id, incidente, hash_natural, numero, posicao, snapshot_first_seen, snapshot_last_seen) VALUES (9, 100, 'p3', '999/2026', 0, 1, 1)")
    con.commit()
    return con


def test_construir_referencias_e_idempotente():
    con = _base()
    r1 = construir_referencias(con)
    r2 = construir_referencias(con)
    assert r1 == r2 == {"processos_citados": 1, "dispositivos": 1, "andamento_peticao": 1, "peticoes_ambiguas": 1, "documento_andamento": 1}
    assert con.execute("SELECT classe, numero, ocorrencias FROM documento_ref_processo").fetchall()[0][:] == ("Pet", 15556, 1)
    assert con.execute("SELECT andamento_id, peticao_id FROM andamento_peticao").fetchall()[0][:] == (2, 7)   # o 999 é ambíguo (2025 e 2026): fica de fora
    assert con.execute("SELECT andamento_id, tipo_citado, data_citada FROM documento_ref_andamento").fetchall()[0][:] == (1, "Vista à PGR para fins de intimação", "2026-05-20")
    res = resumo_dispositivos(con)
    assert res[0]["dispositivo"] == "art. 312 CPP" and res[0]["documentos"][0]["documento_id"] == 1
