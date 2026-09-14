from stf.parse.andamentos import parse_andamentos
from stf.parse.relacoes import extrair_relacoes


def test_relacoes_da_distribuicao_por_prevencao(fx):
    a = parse_andamentos(fx("andamentos"))
    rel = extrair_relacoes(a)
    por_tipo = {}
    for r in rel:
        por_tipo.setdefault(r.tipo, []).append((r.classe, r.numero))
    assert por_tipo["justifica_prevencao"] == [("Inq", 5026)]
    assert por_tipo["relacionado"] == [("Inq", 5035), ("Pet", 15198), ("Pet", 15499), ("Pet", 15504)]
    assert por_tipo["autuado_a_partir"] == [("Pet", 16440), ("Pet", 16441)]


def test_relacao_aponta_para_o_andamento_fonte(fx):
    a = parse_andamentos(fx("andamentos"))
    rel = extrair_relacoes(a)
    fonte = {r.posicao_andamento for r in rel if r.tipo == "justifica_prevencao"}
    assert fonte == {next(x.posicao for x in a if x.tipo == "Distribuído por prevenção")}


def test_texto_sem_padrao_nao_gera_relacao():
    from stf.parse.andamentos import Andamento
    a = [Andamento(posicao=0, data="2026-01-01", tipo="Petição", descricao="Juntada Petição: 1/2026")]
    assert extrair_relacoes(a) == []
