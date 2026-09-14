"""Fase 4: camada semântica. O LLM propõe; a validação determinística decide o que entra.

Regras testadas aqui (restrições 1, 2 e 5):
- asserção sem página válida ou sem trecho literal presente na página é DESCARTADA;
- tipo epistêmico fora dos três valores rejeita a asserção no schema;
- JSON malformado rejeita a resposta inteira; nada é remendado;
- entidades citadas resolvem para a entidade canônica das partes quando o nome bate; senão viram
  entidade nova com origem 'documento' (status "terceiro mencionado");
- cache por (documento, sha256, prompt_version, modelo): não reprocessa sem mudança.
"""
import json

import pytest

from stf.db import abrir, criar_schema
from stf.entidades import construir_entidades
from stf.ingest import ingerir_coleta
from stf.semantica import (PROMPT_VERSION, ClienteFalso, extrair_assercoes, montar_entrada, validar_resposta)
from tests.test_ingest import montar_coleta

PAGINAS = [
    "PETIÇÃO 15.556 DISTRITO FEDERAL\nRELATOR: MIN. ANDRÉ MENDONÇA\nREQTE.(S): DELEGADO DE POLÍCIA FEDERAL",
    "DECISÃO:\n1. A Polícia Federal sustenta que houve dilapidação patrimonial pelos investigados.\n"
    "2. O extrato do SISBAJUD comprova o bloqueio dos valores.\n"
    "3. Ante o exposto, DECRETO A PRISÃO PREVENTIVA de DANIEL BUENO VORCARO.\nBrasília, 4 de março de 2026.",
]


def resposta_boa() -> str:
    return json.dumps({"assercoes": [
        {"tipo_epistemico": "alegacao_parte", "texto": "A Polícia Federal sustenta que houve dilapidação patrimonial.",
         "pagina": 2, "trecho_fonte": "A Polícia Federal sustenta que houve dilapidação patrimonial pelos investigados.",
         "atribuida_a": "Polícia Federal", "entidades": [{"nome": "Polícia Federal", "tipo": "orgao_publico"}]},
        {"tipo_epistemico": "fundamento_decisorio", "texto": "O relator apontou o extrato do SISBAJUD como prova do bloqueio.",
         "pagina": 2, "trecho_fonte": "O extrato do SISBAJUD comprova o bloqueio dos valores.",
         "atribuida_a": "MIN. ANDRÉ MENDONÇA", "entidades": [{"nome": "MIN. ANDRÉ MENDONÇA", "tipo": "ministro"}]},
        {"tipo_epistemico": "fato_processual", "texto": "Em 04/03/2026 foi decretada a prisão preventiva de Daniel Bueno Vorcaro.",
         "pagina": 2, "trecho_fonte": "DECRETO A PRISÃO PREVENTIVA de DANIEL BUENO VORCARO",
         "atribuida_a": None, "entidades": [{"nome": "DANIEL BUENO VORCARO", "tipo": "pessoa"}]},
        # sem trecho literal na página: deve ser descartada
        {"tipo_epistemico": "fato_processual", "texto": "O investigado é culpado.", "pagina": 2,
         "trecho_fonte": "este trecho não existe no documento", "atribuida_a": None, "entidades": []},
        # página inexistente: descartada
        {"tipo_epistemico": "fato_processual", "texto": "Algo na página 9.", "pagina": 9,
         "trecho_fonte": "DECISÃO:", "atribuida_a": None, "entidades": []},
    ], "observacoes": None}, ensure_ascii=False)


def test_montar_entrada_marca_paginas():
    txt = montar_entrada(PAGINAS)
    assert txt.startswith("[página 1]\n") and "[página 2]\n" in txt


def test_validar_descarta_sem_ponteiro_rastreavel():
    ok, descartadas, motivo = validar_resposta(resposta_boa(), PAGINAS)
    assert motivo is None and len(ok) == 3 and len(descartadas) == 2
    assert {d["motivo"] for d in descartadas} == {"trecho_nao_encontrado", "pagina_inexistente"}
    assert ok[0].tipo_epistemico == "alegacao_parte" and ok[0].pagina == 2


def test_validar_rejeita_json_malformado_e_tipo_invalido():
    ok, desc, motivo = validar_resposta("{not json", PAGINAS)
    assert ok == [] and desc == [] and motivo == "json_invalido"
    ruim = json.dumps({"assercoes": [{"tipo_epistemico": "conclusao_do_modelo", "texto": "x", "pagina": 1,
                                       "trecho_fonte": "PETIÇÃO 15.556", "atribuida_a": None, "entidades": []}]})
    ok, desc, motivo = validar_resposta(ruim, PAGINAS)
    assert ok == [] and motivo == "schema_invalido"


def test_trecho_e_comparado_sem_diferencas_de_espaco_e_caixa():
    r = json.dumps({"assercoes": [{"tipo_epistemico": "fato_processual", "texto": "t", "pagina": 2,
                                   "trecho_fonte": "decreto a prisão   preventiva de daniel bueno vorcaro",
                                   "atribuida_a": None, "entidades": []}]})
    ok, desc, _ = validar_resposta(r, PAGINAS)
    assert len(ok) == 1


@pytest.fixture
def banco(tmp_path, fx):
    con = abrir(":memory:"); criar_schema(con)
    ingerir_coleta(con, montar_coleta(tmp_path, fx, "C1"))
    construir_entidades(con)
    doc = con.execute("select id from documento where id_portal='15389657076'").fetchone()["id"]
    con.execute("update documento set sha256='abc', blob_path='x', paginas=2, tem_camada_texto=1 where id=?", (doc,))
    con.executemany("insert into documento_pagina (documento_id, pagina, texto, chars) values (?,?,?,?)",
                    [(doc, i, t, len(t)) for i, t in enumerate(PAGINAS, start=1)])
    con.commit()
    return con, doc


def test_extrair_persiste_so_o_validado_com_proveniencia(banco):
    con, doc = banco
    cliente = ClienteFalso(resposta_boa())
    r = extrair_assercoes(con, cliente, documentos=[doc], log=lambda s: None)
    assert r["processados"] == 1 and r["assercoes"] == 3 and r["descartadas"] == 2
    rows = con.execute("select * from assercao where documento_id=? order by id", (doc,)).fetchall()
    assert [x["tipo_epistemico"] for x in rows] == ["alegacao_parte", "fundamento_decisorio", "fato_processual"]
    assert all(x["pagina"] == 2 and x["prompt_version"] == PROMPT_VERSION and x["modelo"] == cliente.modelo for x in rows)
    assert all(x["trecho_fonte"] for x in rows)
    ex = con.execute("select * from extracao where documento_id=?", (doc,)).fetchone()
    assert ex["status"] == "ok" and ex["assercoes_validas"] == 3 and ex["assercoes_descartadas"] == 2
    assert ex["resposta_path"]   # resposta bruta guardada para auditoria


def test_entidades_resolvem_para_canonicas_ou_viram_terceiro_mencionado(banco):
    con, doc = banco
    extrair_assercoes(con, ClienteFalso(resposta_boa()), documentos=[doc], log=lambda s: None)
    vorcaro = con.execute("select id, origem from entidade where nome='DANIEL BUENO VORCARO'").fetchone()
    assert vorcaro["origem"] == "partes"   # já existia pelas partes; não duplica
    lig = con.execute("select a.tipo_epistemico from assercao_entidade ae join assercao a on a.id=ae.assercao_id "
                      "where ae.entidade_id=?", (vorcaro["id"],)).fetchall()
    assert [l[0] for l in lig] == ["fato_processual"]
    mendonca = con.execute("select * from entidade where nome like '%MENDON%'").fetchone()
    assert mendonca["origem"] == "documento" and mendonca["tipo"] == "ministro"
    assert con.execute("select count(*) from entidade where nome='DANIEL BUENO VORCARO'").fetchone()[0] == 1


def test_cache_nao_reprocessa_sem_mudanca(banco):
    con, doc = banco
    cliente = ClienteFalso(resposta_boa())
    extrair_assercoes(con, cliente, documentos=[doc], log=lambda s: None)
    r2 = extrair_assercoes(con, cliente, documentos=[doc], log=lambda s: None)
    assert r2["processados"] == 0 and r2["pulados_cache"] == 1 and cliente.chamadas == 1
    # o mesmo documento com outro prompt_version reprocessa
    r3 = extrair_assercoes(con, cliente, documentos=[doc], prompt_version="v999", log=lambda s: None)
    assert r3["processados"] == 1 and cliente.chamadas == 2


def test_resposta_malformada_registra_rejeicao_e_nao_persiste_nada(banco):
    con, doc = banco
    r = extrair_assercoes(con, ClienteFalso("{{{"), documentos=[doc], log=lambda s: None)
    assert r["rejeitadas"] == 1 and con.execute("select count(*) from assercao").fetchone()[0] == 0
    assert con.execute("select status from extracao").fetchone()[0] == "rejeitada:json_invalido"


def test_preparar_entradas_e_cliente_arquivo(banco, tmp_path):
    """Execução pelo Claude Code: entradas em arquivo, respostas em arquivo, mesma validação."""
    from stf.semantica import ClienteArquivo, preparar_entradas
    con, doc = banco
    r = preparar_entradas(con, tmp_path / "entradas", documentos=[doc])
    assert r["preparados"] == 1
    entrada = (tmp_path / "entradas" / f"{doc}.entrada.md").read_text("utf-8")
    assert "[página 2]" in entrada and "DECRETO A PRISÃO PREVENTIVA" in entrada and "fato_processual" in entrada
    manifesto = json.loads((tmp_path / "entradas" / "MANIFEST.json").read_text("utf-8"))
    assert manifesto["documentos"][0]["id"] == doc and manifesto["prompt_version"] == PROMPT_VERSION
    (tmp_path / "respostas").mkdir()
    (tmp_path / "respostas" / f"{doc}.json").write_text(resposta_boa(), "utf-8")
    cliente = ClienteArquivo(tmp_path / "respostas", modelo="claude-code/teste")
    res = extrair_assercoes(con, cliente, documentos=[doc], log=lambda s: None)
    assert res["assercoes"] == 3 and res["descartadas"] == 2
    assert con.execute("select modelo from assercao limit 1").fetchone()[0] == "claude-code/teste"
    # sem resposta em arquivo: erro registrado, nada persistido, documento continua pendente
    (tmp_path / "respostas" / f"{doc}.json").unlink()
    con.execute("delete from assercao_entidade"); con.execute("delete from assercao"); con.execute("delete from extracao"); con.commit()
    res2 = extrair_assercoes(con, cliente, documentos=[doc], log=lambda s: None)
    assert res2["erros"] == 1 and res2["processados"] == 0
