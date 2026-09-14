from stf.parse.deslocamentos import parse_deslocamentos
from stf.parse.peticoes import parse_peticoes


def test_peticoes_conta_113_e_le_a_primeira(fx):
    p = parse_peticoes(fx("peticoes"))
    assert len(p) == 113
    assert p[0].numero == "114945/2026"
    assert p[0].data_peticionamento == "2026-09-11"
    assert p[0].recebido_em == "2026-09-11T15:09:12"
    assert p[0].recebido_por == "GABINETE MINISTRO ANDRÉ MENDONÇA"
    assert p[0].posicao == 0


def test_deslocamentos_conta_90_e_le_recebimento_opcional(fx):
    d = parse_deslocamentos(fx("deslocamentos"))
    assert len(d) == 90
    assert d[0].destino == "PROCURADORIA-GERAL DA REPÚBLICA"
    assert d[0].enviado_por == "GERÊNCIA DE PROCESSOS ORIGINÁRIOS CRIMINAIS"
    assert d[0].data_envio == "2026-08-28"
    assert d[0].guia == "24516/2026"
    assert d[0].recebido_em is None
    assert d[1].recebido_em == "2026-08-28"
    assert d[-1].enviado_por == "DIVERSOS" and d[-1].guia == "5258280/2026"
