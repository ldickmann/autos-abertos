"""hash_natural do andamento.

Não existe campo `ordem` no HTML e há andamentos idênticos no mesmo dia
(cinco "Expedido(a)" em 05/03/2026 com a mesma descrição e sem documento).
A chave é (incidente, data, tipo, descricao, documentos, k), onde k é o ordinal
da ocorrência entre itens idênticos, contado a partir do mais antigo (fim da lista),
para que a inserção de itens novos no topo não mude o hash dos antigos.
"""
from stf.hashing import hash_andamentos
from stf.parse.andamentos import parse_andamentos


def test_hashes_sao_unicos_mesmo_com_itens_identicos(fx):
    a = parse_andamentos(fx("andamentos"))
    hashes = hash_andamentos(7514886, a)
    assert len(hashes) == 407
    assert len(set(hashes)) == 407


def test_hash_e_estavel_quando_itens_novos_entram_no_topo(fx):
    a = parse_andamentos(fx("andamentos"))
    completo = hash_andamentos(7514886, a)
    sem_os_10_mais_recentes = hash_andamentos(7514886, a[10:])
    assert sem_os_10_mais_recentes == completo[10:]


def test_hash_depende_do_incidente(fx):
    a = parse_andamentos(fx("andamentos"))[:3]
    assert hash_andamentos(7514886, a) != hash_andamentos(1, a)


def test_hash_muda_se_descricao_muda(fx):
    a = parse_andamentos(fx("andamentos"))[:1]
    h1 = hash_andamentos(7514886, a)
    a[0].descricao += " (retificado)"
    assert hash_andamentos(7514886, a) != h1
