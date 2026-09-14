from stf.parse.informacoes import parse_informacoes


def test_informacoes_campos_basicos(fx):
    i = parse_informacoes(fx("informacoes"))
    assert i.assuntos == ["DIREITO PROCESSUAL PENAL | Prisão Preventiva"]
    assert i.data_protocolo == "2026-02-27"
    assert i.orgao_origem == "SUPREMO TRIBUNAL FEDERAL"
    assert i.origem == "DISTRITO FEDERAL"
    assert i.descricao_procedencia == "DF - DISTRITO FEDERAL"


def test_informacoes_numeros_de_origem_sao_lista_limpa(fx):
    i = parse_informacoes(fx("informacoes"))
    assert i.numeros_origem == [
        "15556", "01657384320261000000", "1447384392026", "10450144820254010000",
        "11170654220254013400", "50000932620264036181", "20250087917", "5026",
        "5035", "15504", "15499", "15198",
    ]


def test_informacoes_volumes_e_folhas_vazios_viram_none(fx):
    i = parse_informacoes(fx("informacoes"))
    assert i.volumes is None
    assert i.folhas is None
