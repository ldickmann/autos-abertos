"""Pedidos e resultados por decisão: seleção de documentos, validação literal e persistência."""
import json

from stf.db import abrir, criar_schema
from stf.decisoes import PROMPT_VERSION, documentos_decisorios, ingerir_decisoes, validar_resposta
from stf.semantica import ClienteFalso

PAGINAS = ["Trata-se de representação da Polícia Federal pela prisão preventiva de X.",
           "Ante o exposto, DEFIRO o pedido e decreto a prisão preventiva de X, nos termos do art. 312 do CPP. Brasília, 3 de junho de 2026."]


def _base(tmp_path):
    con = abrir(":memory:"); criar_schema(con)
    for i, (titulo, dec) in enumerate([("Decisão monocrática", 0), ("Despacho", 1), ("Despacho", 0), ("Intimação", 0)], start=1):
        con.execute("INSERT INTO documento (id, incidente, endpoint, id_portal, formato, url, titulo, sha256, tem_camada_texto, snapshot_first_seen) "
                    "VALUES (?, 100, 'downloadPeca', ?, 'pdf', 'u', ?, ?, 1, 1)", (i, f"p{i}", titulo, f"sha{i}"))
        for n, t in enumerate(PAGINAS, start=1):
            con.execute("INSERT INTO documento_pagina VALUES (?, ?, ?, ?)", (i, n, t, len(t)))
        con.execute("INSERT INTO andamento (id, incidente, hash_natural, data, tipo, descricao, posicao, e_decisao, snapshot_first_seen, snapshot_last_seen) "
                    "VALUES (?, 100, ?, '2026-06-03', ?, '', ?, ?, 1, 1)", (i, f"h{i}", titulo, i, dec))
        con.execute("INSERT INTO andamento_documento VALUES (?, ?, 'doc')", (i, i))
    con.commit()
    return con


def test_seleciona_decisoes_e_despachos_marcados_como_decisao(tmp_path):
    con = _base(tmp_path)
    assert [d["id"] for d in documentos_decisorios(con)] == [1, 2]   # decisão; despacho com e_decisao. Despacho comum e intimação ficam fora


def test_validacao_exige_trecho_literal_e_pagina_existente():
    bom = {"pedido": "prisão preventiva de X", "quem_pediu": "Polícia Federal", "resultado": "deferido", "decisao": "decretou a prisão preventiva de X",
           "quem_decidiu": "Ministro relator", "data": "2026-06-03", "pagina": 2, "trecho_fonte": "DEFIRO o pedido e decreto a prisão preventiva de X", "condicoes": []}
    resp = {"itens": [bom, {**bom, "pagina": 9}, {**bom, "trecho_fonte": "texto que não existe"}, {**bom, "resultado": "aprovado"}], "observacoes": None}
    ok, desc, motivo = validar_resposta(json.dumps(resp), PAGINAS)
    assert motivo == "schema_invalido" and ok == []     # resultado fora do enum invalida o JSON inteiro
    resp["itens"].pop()
    ok, desc, motivo = validar_resposta(json.dumps(resp), PAGINAS)
    assert motivo is None and len(ok) == 1 and [d["motivo"] for d in desc] == ["pagina_inexistente", "trecho_nao_encontrado"]
    assert validar_resposta("não é json", PAGINAS)[2] == "json_invalido"


def test_ingestao_persiste_itens_validos_com_cache(tmp_path):
    con = _base(tmp_path)
    resp = json.dumps({"itens": [{"pedido": "prisão preventiva de X", "quem_pediu": "Polícia Federal", "resultado": "deferido",
                                  "decisao": "decretou a prisão preventiva de X", "quem_decidiu": "Ministro relator", "data": "2026-06-03",
                                  "pagina": 2, "trecho_fonte": "DEFIRO o pedido", "condicoes": ["recolhimento noturno"]}], "observacoes": None})
    r = ingerir_decisoes(con, ClienteFalso(resp), blobs=tmp_path / "blobs", log=lambda s: None)
    assert r["processados"] == 2 and r["itens"] == 2 and r["descartados"] == 0
    it = con.execute("SELECT * FROM decisao_item WHERE documento_id=1").fetchone()
    assert it["resultado"] == "deferido" and json.loads(it["condicoes_json"]) == ["recolhimento noturno"] and it["prompt_version"] == PROMPT_VERSION
    assert con.execute("SELECT COUNT(*) FROM extracao WHERE prompt_version=? AND status='ok'", (PROMPT_VERSION,)).fetchone()[0] == 2
    r2 = ingerir_decisoes(con, ClienteFalso(resp), blobs=tmp_path / "blobs", log=lambda s: None)
    assert r2["pulados_cache"] == 2 and con.execute("SELECT COUNT(*) FROM decisao_item").fetchone()[0] == 2
