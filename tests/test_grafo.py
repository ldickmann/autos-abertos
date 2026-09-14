"""Entidades canônicas e grafo: tudo que se cruza entre processos, sem inferência."""
import pytest

from stf.coleta import ClienteEducado
from stf.db import abrir, criar_schema
from stf.entidades import construir_entidades
from stf.expandir import expandir
from stf.grafo import construir_grafo, cruzamentos, formatar_arestas, formatar_cruzamentos
from tests.portal_falso import PortalFalso

SEMENTE = 7514886
PROCESSOS = {("Inq", 5026): 1000001, ("Inq", 5035): 1000002, ("Pet", 15198): 1000003, ("Pet", 15499): 1000004,
             ("Pet", 15504): 1000005, ("Pet", 16440): 1000006, ("Pet", 16441): 1000007, ("Pet", 15556): SEMENTE}


class Relogio:
    t = 0.0
    def monotonic(self): return self.t
    def sleep(self, s): self.t += s


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("grafo")
    con = abrir(":memory:"); criar_schema(con)
    rel = Relogio()
    cliente = ClienteEducado(transport=PortalFalso(PROCESSOS).transporte(), relogio=rel.monotonic, dormir=rel.sleep, teto=500)
    expandir(con, SEMENTE, profundidade=1, cliente=cliente, blobs=tmp / "blobs", coletas=tmp / "coletas", log=lambda s: None)
    construir_entidades(con)
    return con


def test_entidades_canonicas_por_nome_e_por_oab(con):
    # 8 incidentes com as mesmas 56 partes (fixtures iguais) → as entidades não se multiplicam
    n = con.execute("select count(*) from entidade").fetchone()[0]
    assert n == 54  # 56 partes − 2 placeholders "SEM REPRESENTAÇÃO NOS AUTOS"
    adv = con.execute("select * from entidade where nome='SERGIO RODRIGUES LEONARDO'").fetchone()
    assert adv["tipo"] == "advogado" and adv["chave"] == "oab:40852/DF"
    vorcaro = con.execute("select * from entidade where nome='DANIEL BUENO VORCARO'").fetchone()
    assert vorcaro["tipo"] == "parte" and vorcaro["chave"] == "nome:DANIEL BUENO VORCARO"
    assert con.execute("select count(*) from entidade_mencao where entidade_id=?", (vorcaro["id"],)).fetchone()[0] == 8


def test_natureza_provavel_so_por_sufixo_explicito(con):
    ltda = con.execute("select natureza_provavel from entidade where nome like 'KING PARTICIPAÇÕES%'").fetchone()[0]
    pessoa = con.execute("select natureza_provavel from entidade where nome='DANIEL BUENO VORCARO'").fetchone()[0]
    assert ltda == "pessoa_juridica" and pessoa is None


def test_entidades_e_idempotente(con):
    antes = con.execute("select count(*) from entidade").fetchone()[0]
    construir_entidades(con)
    assert con.execute("select count(*) from entidade").fetchone()[0] == antes


def test_grafo_tem_processos_entidades_e_arestas_tipadas(con):
    g = construir_grafo(con)
    tipos_nos = {n["tipo"] for n in g["nodes"]}
    assert tipos_nos == {"processo", "entidade"}
    processos = [n for n in g["nodes"] if n["tipo"] == "processo"]
    assert len(processos) == 8
    pet = next(n for n in processos if n["id"] == "processo:Pet/15556")
    assert pet["dados"]["incidente"] == SEMENTE and pet["dados"]["relator"] == "MIN. ANDRÉ MENDONÇA"
    tipos_arestas = {e["tipo"] for e in g["edges"]}
    assert {"relacao", "parte_em", "representa"} <= tipos_arestas
    rel = [e for e in g["edges"] if e["tipo"] == "relacao" and e["origem"] == "processo:Pet/15556"]
    assert {(e["destino"], e["dados"]["subtipo"]) for e in rel} == {
        ("processo:Inq/5026", "justifica_prevencao"), ("processo:Inq/5035", "relacionado"),
        ("processo:Pet/15198", "relacionado"), ("processo:Pet/15499", "relacionado"), ("processo:Pet/15504", "relacionado"),
        ("processo:Pet/16440", "autuado_a_partir"), ("processo:Pet/16441", "autuado_a_partir"),
    }
    # toda aresta carrega proveniência
    assert all("fonte" in e["dados"] for e in g["edges"])


def test_advogado_representa_a_parte_do_bloco_anterior(con):
    g = construir_grafo(con)
    ids = {n["dados"].get("nome"): n["id"] for n in g["nodes"] if n["tipo"] == "entidade"}
    rep = [e for e in g["edges"] if e["tipo"] == "representa" and e["origem"] == ids["SERGIO RODRIGUES LEONARDO"]]
    assert {e["destino"] for e in rep} == {ids["DANIEL BUENO VORCARO"]}
    assert {e["dados"]["incidente"] for e in rep} == set(PROCESSOS.values())


def test_cruzamentos_lista_entidades_em_mais_de_um_processo(con):
    c = cruzamentos(con)
    multi = {x["nome"]: x["processos"] for x in c["entidades_em_varios_processos"]}
    assert len(multi["DANIEL BUENO VORCARO"]) == 8
    assert all(len(v) == 8 for v in multi.values())
    assert c["numero_origem_coincidencias"]  # "15556", "5026", "5035"… batem com processos do grafo
    texto = formatar_cruzamentos(c)
    assert "DANIEL BUENO VORCARO" in texto and "8 processos" in texto


def test_formatar_arestas_e_lista_de_texto(con):
    texto = formatar_arestas(construir_grafo(con))
    assert "processo:Pet/15556 --relacao:justifica_prevencao--> processo:Inq/5026" in texto
