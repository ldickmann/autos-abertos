"""Expansor: a partir de um incidente já ingerido, resolve os processos relacionados,
coleta cada um por completo até a profundidade pedida, sob teto de requisições."""
import pytest

from stf.coleta import ClienteEducado
from stf.db import abrir, criar_schema
from stf.expandir import expandir
from tests.portal_falso import PortalFalso

SEMENTE = 7514886
# os 7 processos que o fixture relaciona; Pet 15499 simulado como "não encontrado"
PROCESSOS = {("Inq", 5026): 1000001, ("Inq", 5035): 1000002, ("Pet", 15198): 1000003,
             ("Pet", 15499): None, ("Pet", 15504): 1000005, ("Pet", 16440): 1000006, ("Pet", 16441): 1000007,
             ("Pet", 15556): SEMENTE}


class Relogio:
    t = 0.0
    def monotonic(self): return self.t
    def sleep(self, s): self.t += s


@pytest.fixture
def ambiente(tmp_path):
    con = abrir(":memory:"); criar_schema(con)
    portal = PortalFalso(PROCESSOS)
    rel = Relogio()
    cliente = ClienteEducado(transport=portal.transporte(), relogio=rel.monotonic, dormir=rel.sleep, teto=500)
    return con, portal, cliente, tmp_path


def test_expandir_profundidade_1_coleta_os_vizinhos_por_completo(ambiente):
    con, portal, cliente, tmp = ambiente
    rel = expandir(con, SEMENTE, profundidade=1, cliente=cliente, blobs=tmp / "blobs", coletas=tmp / "coletas", log=lambda s: None)
    # semente coletada (11) + 7 resoluções + 6 vizinhos encontrados × 11 abas
    assert rel.resolvidos == 6 and rel.nao_encontrados == 1 and rel.coletados == 7
    assert con.execute("select count(*) from incidente").fetchone()[0] == 7
    assert con.execute("select count(*) from processo where status='resolvido'").fetchone()[0] == 6
    assert con.execute("select status from processo where classe='Pet' and numero=15556").fetchone()[0] == "semente"
    assert con.execute("select status from processo where classe='Pet' and numero=15499").fetchone()[0] == "nao_encontrado"
    snaps = con.execute("select count(*) from snapshot where incidente=1000001").fetchone()[0]
    assert snaps == 14  # resolução + robots + casca + 9 abas + votacao_json + 1 sessão virtual
    # os vizinhos relacionam os mesmos processos (fixtures iguais): fronteira vazia na profundidade 1
    assert rel.fronteira == []


def test_expandir_nao_recoleta_incidente_ja_coletado(ambiente):
    con, portal, cliente, tmp = ambiente
    expandir(con, SEMENTE, profundidade=1, cliente=cliente, blobs=tmp / "blobs", coletas=tmp / "coletas", log=lambda s: None)
    n = len(portal.requisicoes)
    rel2 = expandir(con, SEMENTE, profundidade=1, cliente=cliente, blobs=tmp / "blobs", coletas=tmp / "coletas", log=lambda s: None)
    assert rel2.coletados == 0 and rel2.resolvidos == 0
    assert len(portal.requisicoes) == n  # zero requisições novas


def test_teto_interrompe_sem_corromper(ambiente, tmp_path):
    con, portal, _, tmp = ambiente
    rel_ = Relogio()
    cliente = ClienteEducado(transport=portal.transporte(), relogio=rel_.monotonic, dormir=rel_.sleep, teto=20)
    rel = expandir(con, SEMENTE, profundidade=1, cliente=cliente, blobs=tmp / "blobs", coletas=tmp / "coletas", log=lambda s: None)
    assert rel.interrompido_por_teto is True
    # o teto conta saltos de redirect; pode passar por no máximo um salto na última requisição
    assert 20 <= len(portal.requisicoes) <= 21
    # o que foi ingerido está íntegro; o que não foi fica pendente e é retomável
    assert con.execute("select count(*) from incidente").fetchone()[0] >= 1
    assert rel.pendentes  # processos resolvidos mas não coletados, ou ainda não resolvidos


def test_profundidade_0_so_resolve_sem_coletar_vizinhos(ambiente):
    con, portal, cliente, tmp = ambiente
    rel = expandir(con, SEMENTE, profundidade=0, cliente=cliente, blobs=tmp / "blobs", coletas=tmp / "coletas", log=lambda s: None)
    assert rel.resolvidos == 6 and rel.coletados == 1
    assert con.execute("select count(*) from incidente").fetchone()[0] == 1
    assert len(rel.fronteira) == 6


def test_reconstruir_recupera_a_tabela_processo_a_partir_dos_registros(ambiente):
    """`processo` é projeção: os registros de resolução (JSONL + blob) bastam para recriá-la."""
    from stf.db import apagar_projecao, criar_schema
    from stf.ingest import ingerir_coleta
    con, portal, cliente, tmp = ambiente
    expandir(con, SEMENTE, profundidade=1, cliente=cliente, blobs=tmp / "blobs", coletas=tmp / "coletas", log=lambda s: None)
    antes = sorted(tuple(r) for r in con.execute("select classe, numero, incidente_principal, status from processo"))
    apagar_projecao(con); criar_schema(con)
    for reg in sorted((tmp / "coletas").glob("*.jsonl")):
        ingerir_coleta(con, reg)
    depois = sorted(tuple(r) for r in con.execute("select classe, numero, incidente_principal, status from processo"))
    assert depois == antes and len(depois) == 8
