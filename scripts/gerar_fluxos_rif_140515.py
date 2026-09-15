"""Gera data/curadoria/fluxos/rif-140515.json a partir do texto do RIF 140515 (documento 274, Pet 15.645).

Extração assistida: os blocos regulares (tabelas "Relacionados", listas "Principais remetentes/destinatários",
resumos por tipo de transação) saem dos parsers de stf/fluxos.py; os fluxos narrativos (TEDs datadas, escrituras,
veículos) estão transcritos abaixo, cada um com o trecho literal da página. O JSON gerado é validado contra o
texto das páginas antes de ser gravado; é ele (e não este script) que a carga lê.

Uso: python scripts/gerar_fluxos_rif_140515.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from stf import config  # noqa: E402
from stf.db import abrir  # noqa: E402
from stf.fluxos import chave_ator, mascarar_texto, parse_principais, parse_relacionados  # noqa: E402
from stf.fluxos_carga import trecho_na_pagina, validar_dataset  # noqa: E402

SAIDA = RAIZ / "data" / "curadoria" / "fluxos" / "rif-140515.json"
DOC = {"endpoint": "docspublicos", "id_portal": "Pet15645/00002_b19a2bb7"}

IGREJA = "57.391.420/0001-63"
ZETTEL = "027.818.816-86"
MORIAH = "02.425.349/0002-81"
SUPER = "31.446.245/0001-70"
PAIVA = "090.476.856-28"
DUBEM = "nome:Dubem Business Marketing Eventos e Produções Artísticas Ltda"

CC_4001 = "Banco Central do Brasil - Carta-Circular nº 4.001/2020, art. 1º"
RES_25 = "Resolução Coaf nº 25/2013 - art. 5º"
PROV_149_162 = "CNJ - Provimento CN n. 149/2023, art. 162 (incluído pelo Provimento CN n. 161, de 11.3.2024)"
PROV_88_25 = "CNJ - Provimento 88/2019, art. 25-II; Provimento 149/2023, art. 161-II"
PROV_149_171 = "CNJ - Provimento CN n. 149/2023, art. 171 (incluído pelo Provimento CN n. 161, de 11.3.2024)"


def fatia(texto: str, inicio: str, fim: str | None = None) -> str:
    i = texto.index(inicio)
    j = texto.index(fim, i) if fim else len(texto)
    return texto[i:j]


def pagina_de(trecho: str, paginas: dict[int, str], candidatas: list[int]) -> int:
    for p in candidatas:
        if trecho_na_pagina(trecho, paginas[p]):
            return p
    raise ValueError(f"trecho não encontrado nas páginas {candidatas}: {trecho[:60]!r}")


def reais(c: int) -> str:
    inteiro, cents = divmod(c, 100)
    return f"{inteiro:,}".replace(",", ".") + f",{cents:02d}"


def item_agregado(it: dict, paginas: dict[int, str], candidatas: list[int], *, origem: str | None, destino: str | None,
                  periodo: tuple[str, str]) -> dict:
    """Uma linha de 'Principais remetentes/destinatários' vira um fluxo agregado. O trecho é o rabo do item,
    que cabe numa única página mesmo quando o nome quebrou de página."""
    trecho = f"{it['quantidade']} lançamento(s) no total de: R${reais(it['valor_centavos'])}"
    return {"origem": origem, "destino": destino, "valor": reais(it["valor_centavos"]), "tipo": "transferencia", "natureza": "agregado",
            "quantidade": it["quantidade"], "periodo_inicio": periodo[0], "periodo_fim": periodo[1],
            "descricao": f"{'remetente' if destino == IGREJA else 'destinatário'} identificado pelo banco: {it['nome']} ({it['atividade'] or 'atividade não informada'})",
            "pagina": pagina_de(trecho, paginas, candidatas), "trecho": trecho}


def resumos_por_tipo(bloco: str, pagina: int, *, origem: str | None, destino: str | None, periodo: tuple[str, str]) -> list[dict]:
    """'8.039 PIX - R$ 23.984.705,56 90 CDB/RDB - R$ 4.371.890,51 ...' → um fluxo resumo_tipo por tipo."""
    mapa = {"PIX": "pix", "CDB/RDB": "cdb_rdb", "CREDITO(S) CARTOES": "cartao", "CHEQUE DEVOLVIDO": "cheque", "DOC/TED": "ted",
            "PAGAMENTO TITULO": "pagamento_titulo", "TRIBUTOS/IMPOSTOS": "tributo", "CHEQUE(S)": "cheque"}
    out = []
    for m in re.finditer(r"([\d.]+)\s+([A-Z()/ ]+?)\s+-\s+R\$\s*([\d.]+,\d{2})", " ".join(bloco.split())):
        qtd, rotulo, valor = m.groups()
        rotulo = rotulo.strip()
        out.append({"origem": origem, "destino": destino, "valor": valor, "tipo": mapa.get(rotulo, "outros"), "natureza": "resumo_tipo",
                    "quantidade": int(qtd.replace(".", "")), "periodo_inicio": periodo[0], "periodo_fim": periodo[1],
                    "descricao": f"total de {rotulo.lower()} no período, segundo o banco", "pagina": pagina,
                    "trecho": f"{qtd} {rotulo} - R$ {valor}"})
    return out


def participacoes_de(texto: str) -> list[dict]:
    return parse_relacionados(texto)


def gerar(paginas: dict[int, str]) -> dict:
    p = paginas
    coms: list[dict] = []

    # ---------------- relato do COAF (p.1): a comunicação retida
    coms.append({
        "secao": "suspeita", "numero": "relato-3", "titular": DUBEM, "segmento": "Banco Central - Atípicas",
        "comunicante": "Banco Safra (Natal) — comunicação retida pelo COAF", "local": "Natal-RN",
        "periodo_inicio": "2024-07-15", "periodo_fim": "2024-09-03", "valor": "1.000.000,00",
        "informacoes": fatia(p[1], "Cabe também pontuar", "Este relatório de inteligência").strip(),
        "pagina_inicio": 1, "pagina_fim": 2,
        "participacoes": [{"nome": "SUPER EMPREENDIMENTOS E PARTICIPACOES S.A", "documento": SUPER, "papel": "remetente"},
                          {"nome": "Dubem Business Marketing Eventos e Produções Artísticas Ltda", "documento": DUBEM, "papel": "titular"}],
        "transacoes": [{"origem": SUPER, "destino": DUBEM, "valor": "1.000.000,00", "tipo": "transferencia", "natureza": "agregado",
                        "periodo_inicio": "2024-07-15", "periodo_fim": "2024-09-03",
                        "descricao": "comunicação não entregue à PF: o COAF a reteve por mencionar pessoa com possível foro por prerrogativa de função (STJ/STF)",
                        "pagina": 1, "trecho": "Super Empreendimentos e Participações S.A teria enviado R$1.000.000,00 à titular"}],
        "bens": [], "ocorrencias": [{"norma": "Lei 9.613/1998, art. 11, II", "codigo": None,
                                     "descricao": "comunicação de operação suspeita retida pelo COAF (possível foro por prerrogativa de função)"}],
    })

    # ---------------- 1 — Igreja Batista da Lagoinha Belvedere (p.3–5)
    per = ("2024-12-24", "2025-12-08")
    rel = participacoes_de(fatia(p[3], "Relacionados CPF/CNPJ") + "\n" + fatia(p[4], "CARLOS MARTINS", "Segmento: Banco Central"))
    info = fatia(p[4], "Informações Adicionais:", "Este relatório de inteligência").strip() + "\n" + fatia(p[5], "OBRAS DE ACABAMENTO", "CONSIDERAÇÕES").strip()
    consid = fatia(p[5], "CONSIDERAÇÕES", "Ocorrências:").strip()
    tx: list[dict] = []
    tx += resumos_por_tipo(fatia(p[4], "QUANTIDADE - TIPO DE TRANSAÇÃO - VALOR TOTAL 8.039", "Principais"), 4, origem=None, destino=IGREJA, periodo=per)
    tx += resumos_por_tipo(fatia(p[4], "QUANTIDADE - TIPO DE TRANSAÇÃO - VALOR TOTAL 709", "Principais destinatários"), 4, origem=None, destino=None, periodo=per)
    for t in tx:
        if t["destino"] is None:
            t["origem"] = IGREJA
    t45 = p[4] + "\n" + p[5]
    for it in parse_principais(t45, "remetentes"):
        tx.append(item_agregado(it, p, [4, 5], origem=it["documento"], destino=IGREJA, periodo=per))
    for it in parse_principais(t45, "destinatarios"):
        tx.append(item_agregado(it, p, [4, 5], origem=IGREJA, destino=it["documento"], periodo=per))
    tx += [
        {"origem": IGREJA, "destino": "52.604.742/0001-20", "valor": "86.200,27", "tipo": "transferencia", "natureza": "individual", "data": "2025-10-31",
         "descricao": "exemplo citado pelo banco", "pagina": 5,
         "trecho": "NOME BENEFICIÁRIO: AFEB ESTRUTURAS METALICAS LTDA DATA: 31/10/2025 VALOR PAGO: R$ 86.200,27"},
        {"origem": "19.936.735/0001-50", "destino": "53.537.680/0001-43", "valor": "62.636,81", "tipo": "transferencia", "natureza": "individual", "data": "2025-11-04",
         "descricao": "exemplo citado pelo banco (pagador Rogue Participações, não a igreja)", "pagina": 5,
         "trecho": "NOME BENEFICIÁRIO: BPO GESTAO DE DISPONIVEL LTDA DATA: 04/11/2025 VALOR PAGO: R$ 62.636,81"},
    ]
    atividades = {it["documento"]: it["atividade"] for it in parse_principais(t45, "remetentes") + parse_principais(t45, "destinatarios")}
    for r in rel:
        if atividades.get(r["documento"]):
            r["atividade"] = atividades[r["documento"]]
    coms.append({
        "secao": "suspeita", "numero": "1", "titular": IGREJA, "segmento": "Banco Central - Atípicas", "comunicante": "Banco do Brasil S.A.",
        "local": "Belo Horizonte-MG", "periodo_inicio": per[0], "periodo_fim": per[1], "valor": "57.110.313,00",
        "creditos": "28.493.311,91", "debitos": "28.617.002,01", "informacoes": info, "consideracoes": consid,
        "pagina_inicio": 3, "pagina_fim": 5, "participacoes": rel, "transacoes": tx, "bens": [],
        "ocorrencias": [
            {"norma": CC_4001, "codigo": "IV-a", "descricao": "movimentação de recursos incompatível com o patrimônio, a atividade econômica ou a ocupação profissional e a capacidade financeira do cliente"},
            {"norma": CC_4001, "codigo": "IV-ac", "descricao": "movimentação de valores incompatíveis com o faturamento mensal das pessoas jurídicas"},
            {"norma": CC_4001, "codigo": "IV-l", "descricao": "operações que, por sua habitualidade, valor e forma, configurem artifício para burla da identificação da origem, do destino, dos responsáveis ou dos destinatários finais"},
        ],
    })

    # ---------------- 2.x — Moriah Asset (p.5–6): veículos
    rel_moriah = [{"nome": "MORIAH ASSET EMPREENDIMENTOS E PARTICIPACOES LTDA", "documento": MORIAH, "papel": "titular"},
                  {"nome": "FABIANO CAMPOS ZETTEL", "documento": ZETTEL, "papel": "outros"}]
    oc_25 = [{"norma": RES_25, "codigo": None, "descricao": "operações que possam configurar sérios indícios da ocorrência dos crimes previstos na Lei nº 9.613/1998"}]
    coms.append({
        "secao": "suspeita", "numero": "2.1", "titular": MORIAH, "segmento": "Bens de luxo ou de alto valor", "comunicante": "concessionária de veículos (não nomeada)",
        "local": "SÃO PAULO-SP", "periodo_inicio": "2025-04-28", "periodo_fim": "2025-08-14", "valor": "1.530.000,00",
        "informacoes": fatia(p[5], "Informações Adicionais: POR OCASIÃO", "Este relatório de inteligência").strip(), "pagina_inicio": 5, "pagina_fim": 6,
        "participacoes": rel_moriah,
        "bens": [{"id": "rr1", "tipo": "veiculo", "descricao": "Range Rover 2024/2025", "valor": "1.530.000,00", "data_negocio": "2025-04-28"},
                 {"id": "rr2", "tipo": "veiculo", "descricao": "Range Rover 2024/2025 (segunda aquisição)", "valor": "1.170.000,00", "data_negocio": "2025-06-06"}],
        "transacoes": [
            {"origem": MORIAH, "destino": None, "valor": "1.530.000,00", "tipo": "compra_veiculo", "natureza": "individual", "data": "2025-04-28", "bem": "rr1",
             "descricao": "pago com um usado avaliado em R$ 1.230.000,00 e R$ 300.000,00 financiados; o comunicante diz não ter apurado a origem do usado", "pagina": 5,
             "trecho": "VENDA DE 01 RANGE ROVER 2024 2025 EM 28.04.2025 PELO VALOR DE R$ 1.530.000,00"},
            {"origem": MORIAH, "destino": None, "valor": "1.170.000,00", "tipo": "compra_veiculo", "natureza": "individual", "data": "2025-06-06", "bem": "rr2",
             "descricao": "usado anterior avaliado em R$ 1.190.000,00, entrada de R$ 156.200,00 e troco de R$ 176.200,00", "pagina": 5,
             "trecho": "DETECTAMOS EM 06.06.2025 UMA NOVA AQUISIÇÃO DE UMA RANGE ROVER 2024 2025 PELO VALOR DE R$ 1.170.000,00"},
        ],
        "ocorrencias": oc_25,
    })
    coms.append({
        "secao": "suspeita", "numero": "2.2", "titular": MORIAH, "segmento": "Bens de luxo ou de alto valor", "comunicante": "concessionária de veículos (não nomeada)",
        "local": "SÃO PAULO-SP", "periodo_inicio": "2025-12-04", "periodo_fim": "2025-12-05", "valor": "1.600.000,00",
        "informacoes": fatia(p[6], "Informações Adicionais: REFERENTE À NEGOCIAÇÃO DE COMPRA, NF 206", "Ocorrências:").strip(), "pagina_inicio": 6, "pagina_fim": 6,
        "participacoes": rel_moriah,
        "bens": [{"id": "cad", "tipo": "veiculo", "descricao": "Cadillac Escalade Sport 2025/2025", "valor": "1.600.000,00", "data_negocio": "2025-12-04",
                  "identificacao": {"nf": "206 de 04/12/2025", "placa": "TEE-7C16", "renavam": "01436319177", "chassi": "1GYS9PRL7SR175472"}}],
        "transacoes": [{"origem": MORIAH, "destino": None, "valor": "1.600.000,00", "tipo": "compra_veiculo", "natureza": "individual", "data": "2025-12-04", "bem": "cad",
                        "descricao": "NF 206 de 04/12/2025", "pagina": 6, "trecho": "NF 206 DE 04/12/2025, NO VALOR TOTAL DE R$ 1.600.000,00"}],
        "ocorrencias": oc_25,
    })
    coms.append({
        "secao": "suspeita", "numero": "2.3", "titular": MORIAH, "segmento": "Bens de luxo ou de alto valor", "comunicante": "concessionária de veículos (não nomeada)",
        "local": "BELO HORIZONTE-MG", "periodo_inicio": "2025-12-02", "periodo_fim": "2025-12-05", "valor": "650.000,00",
        "informacoes": fatia(p[6], "Informações Adicionais: REFERENTE À NEGOCIAÇÃO DE COMPRA, NF 25491", "Ocorrências:").strip(), "pagina_inicio": 6, "pagina_fim": 6,
        "participacoes": rel_moriah,
        "bens": [{"id": "audi", "tipo": "veiculo", "descricao": "Audi RS6 Avant 4.0 TFSI 2020/2021", "valor": "650.000,00", "data_negocio": "2025-12-02",
                  "identificacao": {"nf": "25491 de 02/12/2025", "placa": "GCG0C22", "renavam": "01253291648", "chassi": "WUA82CF28MN903130"}}],
        "transacoes": [{"origem": MORIAH, "destino": None, "valor": "650.000,00", "tipo": "compra_veiculo", "natureza": "individual", "data": "2025-12-02", "bem": "audi",
                        "descricao": "NF 25491 de 02/12/2025", "pagina": 6, "trecho": "NF 25491 DE 02/12/2025, NO VALOR TOTAL DE R$ 650.000,00"}],
        "ocorrencias": oc_25,
    })

    # ---------------- 3.1 — Super Empreendimentos, conta no Sicoob Credifor (p.6–7)
    rel_31 = participacoes_de(fatia(p[6], "3.1\nRelacionados") + "\n" + fatia(p[7], "VL KAWAMURA", "Segmento: Banco Central"))
    per31 = ("2022-06-01", "2022-06-30")
    coms.append({
        "secao": "suspeita", "numero": "3.1", "titular": SUPER, "segmento": "Banco Central - Atípicas",
        "comunicante": "Cooperativa de Crédito Credifor Ltda. – Sicoob Credifor", "local": "Formiga-MG",
        "periodo_inicio": per31[0], "periodo_fim": per31[1], "valor": "19.693.098,00", "creditos": "9.900.020,00", "debitos": "9.793.078,30",
        "informacoes": fatia(p[7], "Informações Adicionais:", "Ocorrências:").strip(), "pagina_inicio": 6, "pagina_fim": 7,
        "participacoes": rel_31, "bens": [],
        "transacoes": [
            {"origem": ZETTEL, "destino": SUPER, "valor": "4.950.000,00", "tipo": "ted", "natureza": "individual", "data": "2022-06-15", "pagina": 7, "trecho": "15/06/2022 R$ 4.950.000,00"},
            {"origem": ZETTEL, "destino": SUPER, "valor": "50.000,00", "tipo": "ted", "natureza": "individual", "data": "2022-06-22", "pagina": 7, "trecho": "22/06/2022 R$ 50.000,00"},
            {"origem": ZETTEL, "destino": SUPER, "valor": "660.000,00", "tipo": "ted", "natureza": "individual", "data": "2022-06-10", "pagina": 7, "trecho": "10/06/2022 R$ 660.000,00"},
            {"origem": ZETTEL, "destino": SUPER, "valor": "3.520.000,00", "tipo": "ted", "natureza": "individual", "data": "2022-06-09", "pagina": 7, "trecho": "09/06/2022 R$ 3.520.000,00"},
            {"origem": "399.115.431-53", "destino": SUPER, "valor": "700.000,00", "tipo": "ted", "natureza": "individual", "data": "2022-06-08", "pagina": 7,
             "trecho": "08/06/2022R$ 700.000,00 - origem: ISAAC SIDNEY M FERREIRA"},
            {"origem": ZETTEL, "destino": SUPER, "valor": "20.000,00", "tipo": "pix", "natureza": "individual", "data": "2022-06-07", "pagina": 7,
             "trecho": "07/06/2022 R$ 20.000,00 - origem: FABIANO"},
            {"origem": SUPER, "destino": None, "valor": "7.189.100,67", "tipo": "boleto", "natureza": "agregado", "quantidade": 5, "periodo_inicio": per31[0], "periodo_fim": per31[1],
             "descricao": "pagamentos de títulos/boletos, beneficiários não informados", "pagina": 7, "trecho": "5 Pagamentos diversos de títulos/boletos, Totalizando: R$ 7.189.100,67"},
            {"origem": SUPER, "destino": "36.579.177/0001-31", "valor": "1.600.000,00", "tipo": "ted", "natureza": "individual", "data": "2022-06-09", "pagina": 7, "trecho": "09/06/2022 R$ 1.600.000,00 - destino: N.Q.H.S.P.E"},
            {"origem": SUPER, "destino": "27.338.150/0001-66", "valor": "330.000,00", "tipo": "ted", "natureza": "individual", "data": "2022-06-10", "pagina": 7, "trecho": "10/06/2022 R$ 330.000,00 - destino: VL Kawamura"},
            {"origem": SUPER, "destino": "34.101.079/0001-69", "valor": "165.000,00", "tipo": "ted", "natureza": "individual", "data": "2022-06-10", "pagina": 7, "trecho": "10/06/2022 R$ 165.000,00 - destino: Flavia M C Semini ME"},
            {"origem": SUPER, "destino": "12.076.845/0001-40", "valor": "165.000,00", "tipo": "ted", "natureza": "individual", "data": "2022-06-10", "pagina": 7, "trecho": "10/06/2022 R$ 165.000,00 - destino: Private Investimentos"},
            {"origem": SUPER, "destino": "34.101.079/0001-69", "valor": "165.000,00", "tipo": "ted", "natureza": "individual", "data": "2022-06-17", "pagina": 7, "trecho": "17/06/2022 R$\n165.000,00 - destino: Flavia M C Semini ME"},
            {"origem": SUPER, "destino": "216.959.918-50", "valor": "100.000,00", "tipo": "ted", "natureza": "individual", "data": "2022-06-23", "pagina": 7, "trecho": "23/06/2022 R$ 100.000,00 - destino: Antônio Augusto"},
        ],
        "ocorrencias": [
            {"norma": CC_4001, "codigo": "IV-a", "descricao": "movimentação de recursos incompatível com o patrimônio, a atividade econômica ou a ocupação profissional e a capacidade financeira do cliente"},
            {"norma": CC_4001, "codigo": "IV-ac", "descricao": "movimentação de valores incompatíveis com o faturamento mensal das pessoas jurídicas"},
            {"norma": CC_4001, "codigo": "IV-e", "descricao": "movimentação de quantia significativa por meio de conta até então pouco movimentada ou de conta que acolha depósito inusitado"},
        ],
    })

    # ---------------- cartórios: comunicações suspeitas 3.2–3.5 (p.8–9)
    def cartorio(numero, secao, pagina_inicio, pagina_fim, rel_txt, data_com, valor, informacoes, ocorrencias, *, comunicante="cartório de notas de São Paulo",
                 local="São Paulo-SP", bens=None, transacoes=None, titular=SUPER):
        return {"secao": secao, "numero": numero, "titular": titular, "segmento": "Notários e Registradores", "comunicante": comunicante, "local": local,
                "periodo_inicio": data_com, "periodo_fim": data_com, "valor": valor, "informacoes": informacoes, "pagina_inicio": pagina_inicio,
                "pagina_fim": pagina_fim, "participacoes": participacoes_de(rel_txt), "bens": bens or [], "transacoes": transacoes or [],
                "ocorrencias": ocorrencias}

    oc_162_vi = {"norma": PROV_149_162, "codigo": "VI", "descricao": "registro de título no qual conste valor declarado de bem com diferença anormal em relação a outros valores a ele associados (avaliação fiscal, valor patrimonial)"}
    oc_162_i = {"norma": PROV_149_162, "codigo": "I", "descricao": "doação de bem imóvel a terceiro sem vínculo familiar aparente com o doador, com valor venal igual ou superior a R$ 100.000,00"}
    oc_162_v = {"norma": PROV_149_162, "codigo": "V", "descricao": "registro de transmissões sucessivas do mesmo bem em período e com diferença de valor anormais"}
    oc_25_ii = {"norma": PROV_88_25, "codigo": "25-II", "descricao": "diferença superior a 100% entre o valor da avaliação fiscal (ou patrimonial) e o valor declarado"}
    oc_171 = {"norma": PROV_149_171, "codigo": "171", "descricao": "pagamento ou recebimento em espécie, ou por título ao portador, de valor igual ou superior a R$ 100.000,00 em operação comunicada pelo tabelião"}

    coms.append(cartorio("3.2", "suspeita", 8, 8, fatia(p[8], "3.2\nRelacionados", "Segmento Local"), "2024-05-21", "36.918.510,00",
                         fatia(p[8], "Informações Adicionais:", "Ocorrências:").strip(), [oc_162_vi], comunicante="23º Tabelião de Notas de São Paulo",
                         bens=[{"id": "im_luzom", "tipo": "imovel", "descricao": "Imóvel em São Paulo comprado da Luzom SPE (escritura de 30/04/2024; promessa de 29/01/2024)",
                                "valor": "23.118.509,79", "valor_referencia": "3.743.479,00", "data_negocio": "2024-04-30",
                                "identificacao": {"tabeliao": "23º Tabelião de Notas de São Paulo", "livro": "5.006", "folhas": "357/368"}}],
                         transacoes=[
                             {"origem": SUPER, "destino": "11.396.222/0001-91", "valor": "23.118.509,79", "tipo": "escritura_compra", "natureza": "individual", "data": "2024-04-30", "bem": "im_luzom",
                              "descricao": "compra do imóvel; valor venal de referência R$ 3.743.479,00", "pagina": 8,
                              "trecho": "transmitiu por venda a SUPER\nEMPREENDIMENTOS E PARTICIPAÇÕES S.A., CNPJ nº 31.446.245/0001-70, NIRE 35300521714, com sede nesta Capital, na Avenida Horácio\nLafer nº 160, 13°andar, Itaim Bibi, o imóvel desta matrícula pelo valor de R$23.118.509,79"},
                             {"origem": SUPER, "destino": "11.396.222/0001-91", "valor": "13.800.000,00", "tipo": "alienacao_fiduciaria", "natureza": "agregado", "quantidade": 6,
                              "periodo_inicio": "2024-05-29", "periodo_fim": "2024-10-29", "bem": "im_luzom",
                              "descricao": "dívida garantida por alienação fiduciária do mesmo imóvel: 6 parcelas de R$ 2.300.000,00, a primeira em 29/05/2024, com juros pela Selic", "pagina": 8,
                              "trecho": "para garantia da\ndívida no valor de R$13.800.000,00, pagável através de 06 parcelas no valor de R$2.300.000,00"},
                         ]))
    coms.append(cartorio("3.3", "suspeita", 8, 8, fatia(p[8], "3.3\nRelacionados", "Segmento Local"), "2024-05-10", "50.000.000,00",
                         fatia(p[8], "Informações Adicionais: ESCRITURA DE VENDA", "Ocorrências:").strip(), [oc_162_vi],
                         bens=[{"id": "im_birman", "tipo": "imovel", "descricao": "Imóvel em São Paulo comprado de Alexandre Café Birman", "valor": "50.000.000,00", "data_negocio": "2024-05-10"}],
                         transacoes=[{"origem": SUPER, "destino": "002.293.896-60", "valor": "50.000.000,00", "tipo": "escritura_compra", "natureza": "individual", "data": "2024-05-10", "bem": "im_birman",
                                      "descricao": "escritura de venda e compra com valor superior a 100% da avaliação fiscal; data da comunicação (a da escritura não consta)", "pagina": 8,
                                      "trecho": "Notários e Registradores SAO PAULO-SP 10/5/2024 até 10/5/2024 50.000.000,00"}]))
    coms.append(cartorio("3.4", "suspeita", 8, 9, fatia(p[8], "3.4\nRelacionados", "Segmento Local"), "2025-01-30", "4.347.000,00",
                         fatia(p[8], "Informações Adicionais: Por escritura de 16 de dezembro").strip() + "\n" + fatia(p[9], "R$4.347.000,00", "Ocorrências:").strip(),
                         [oc_162_i, oc_162_v, oc_162_vi], comunicante="9º Tabelião de Notas de São Paulo",
                         bens=[{"id": "im_doacao", "tipo": "imovel", "descricao": "Imóvel em São Paulo doado pela Super a Karolina Santos Trainotti (escritura de 16/12/2024)",
                                "valor": "4.347.000,00", "valor_referencia": "1.318.344,00", "data_negocio": "2024-12-16",
                                "identificacao": {"tabeliao": "9º Tabelião de Notas de São Paulo", "livro": "11.733", "folhas": "031"}}],
                         transacoes=[{"origem": SUPER, "destino": "077.640.489-09", "valor": "4.347.000,00", "tipo": "escritura_doacao", "natureza": "individual", "data": "2024-12-16", "bem": "im_doacao",
                                      "descricao": "doação de pessoa jurídica a pessoa física pelo valor fiscal atribuído; título devolvido com exigências, prenotação vencida em 30/01/2025; comunicada de novo em 25/02/2025 (item 3.5)",
                                      "pagina": 9, "trecho": "R$4.347.000,00. (Valor de referência: R$1.318.344,00). Doação de pessoa juridica para pessoa fisica"}]))
    coms.append(cartorio("3.5", "suspeita", 9, 9, fatia(p[9], "3.5\nRelacionados", "Segmento Local"), "2025-02-25", "4.347.000,00",
                         fatia(p[9], "Informações Adicionais: Por escritura de 16 de dezembro", "Ocorrências:").strip(), [oc_162_i, oc_162_vi],
                         comunicante="9º Tabelião de Notas de São Paulo",
                         bens=[{"id": "im_doacao2", "tipo": "imovel", "descricao": "Mesmo imóvel da comunicação 3.4 (segunda comunicação da doação; valor de referência atualizado)",
                                "valor": "4.347.000,00", "valor_referencia": "1.350.268,00", "data_negocio": "2024-12-16"}]))

    # ---------------- comunicações automáticas 1.1–1.9 (p.9–12): escrituras da Super
    def esc(num, pag_ini, pag_fim, rel_txt, data_com, valor, informacoes, **kw):
        return cartorio(num, "automatica", pag_ini, pag_fim, rel_txt, data_com, valor, informacoes, [oc_25_ii], **kw)

    coms.append(esc("1.1", 9, 10, fatia(p[9], "1.1\nRelacionados", "Segmento Local"), "2022-03-14", "38.000.000,00", "Diferença entre o valor fiscal e valor declarado",
                    bens=[{"id": "im11", "tipo": "imovel", "descricao": "Imóvel em São Paulo (escritura entre Super e IM2D Participações; direção da venda não informada)", "valor": "38.000.000,00", "data_negocio": "2022-03-14"}]))
    coms.append(esc("1.2", 10, 10, fatia(p[10], "1.2\nRelacionados", "Segmento Local"), "2022-05-10", "8.700.000,00", "Diferença entre o valor fiscal e valor declarado",
                    bens=[{"id": "im12", "tipo": "imovel", "descricao": "Imóvel em São Paulo (escritura entre Super e Carolina e Rafael Rossi Cuppoloni; direção não informada)", "valor": "8.700.000,00", "data_negocio": "2022-05-10"}]))
    coms.append(esc("1.3", 10, 10, fatia(p[10], "1.3\nRelacionados", "Segmento Local"), "2022-08-11", "10.340.000,00", "Diferença entre o valor fiscal e valor declarado",
                    bens=[{"id": "im13", "tipo": "imovel", "descricao": "Imóvel em São Paulo (escritura entre Super, Rafael Fernandes Estevez e Cristina de Azevedo Bohrer; direção não informada)", "valor": "10.340.000,00", "data_negocio": "2022-08-11"}]))
    coms.append(esc("1.4", 10, 10, fatia(p[10], "1.4\nRelacionados", "Segmento Local"), "2022-08-22", "8.500.000,00", "Diferença entre o valor fiscal e valor declarado",
                    bens=[{"id": "im14", "tipo": "imovel", "descricao": "Imóvel em São Paulo (escritura entre Super e Marcel Zanin Mauro; direção não informada)", "valor": "8.500.000,00", "data_negocio": "2022-08-22"}]))
    coms.append(esc("1.5", 10, 11, fatia(p[10], "1.5\nRelacionados") + "\n" + fatia(p[11], "SINGULARE", "Segmento Local"), "2023-05-10", "30.903.911,00",
                    "ESCRITURA DE VENDA E COMPRA COM VALOR DE TRANSAÇÃO SUPERIOR A 100% DO VALOR DE AVALIAÇÃO FISCAL.",
                    bens=[{"id": "im15", "tipo": "imovel", "descricao": "Imóvel em São Paulo comprado do High Yield Distressed Fundo de Investimento (Singulare CTVM como representante)", "valor": "30.903.911,00", "data_negocio": "2023-05-10"}],
                    transacoes=[{"origem": SUPER, "destino": "25.295.530/0001-35", "valor": "30.903.911,00", "tipo": "escritura_compra", "natureza": "individual", "data": "2023-05-10", "bem": "im15",
                                 "descricao": "vendedor identificado na comunicação; data da comunicação", "pagina": 11,
                                 "trecho": "Notários e Registradores SAO PAULO-SP 10/5/2023 até 10/5/2023 30.903.911,00"}]))
    coms.append(esc("1.6", 11, 11, fatia(p[11], "1.6\nRelacionados", "Segmento Local"), "2024-02-20", "7.000.000,00", "Diferença entre o valor fiscal e valor declarado",
                    bens=[{"id": "im16", "tipo": "imovel", "descricao": "Imóvel em São Paulo (escritura entre Super e Marcelo Adriano de Almeida; direção não informada)", "valor": "7.000.000,00", "data_negocio": "2024-02-20"}]))
    coms.append(esc("1.7", 11, 11, fatia(p[11], "1.7\nRelacionados", "Segmento Local"), "2024-03-08", "43.710.000,00", "Diferença entre o valor fiscal e valor declarado",
                    bens=[{"id": "im17", "tipo": "imovel", "descricao": "Imóvel em São Paulo (escritura entre Super, BRL Trust DTVM e Terra – Fundo de Investimento Imobiliário; direção não informada)", "valor": "43.710.000,00", "data_negocio": "2024-03-08"}]))
    coms.append(esc("1.8", 11, 12, fatia(p[11], "1.8\nRelacionados", "Segmento Local"), "2024-04-09", "48.000.000,00",
                    fatia(p[12], "Informações Adicionais: Por escritura de 27 de março", "Ocorrências:").strip(), comunicante="9º Tabelião de Notas de São Paulo",
                    bens=[{"id": "im18", "tipo": "imovel", "descricao": "Imóvel em São Paulo comprado da Grip Negócios Imobiliários (escritura de 27/03/2024; instrumento particular de 26/02/2024)",
                           "valor": "48.000.000,00", "valor_referencia": "6.990.176,00", "data_negocio": "2024-03-27",
                           "identificacao": {"tabeliao": "9º Tabelião de Notas de São Paulo", "livro": "11.609", "folhas": "359"}}],
                    transacoes=[{"origem": SUPER, "destino": "26.771.372/0001-05", "valor": "48.000.000,00", "tipo": "escritura_compra", "natureza": "individual", "data": "2024-03-27", "bem": "im18",
                                 "descricao": "R$ 5 milhões recebidos antes da escritura sem especificar a forma; valor de referência R$ 6.990.176,00", "pagina": 12,
                                 "trecho": "o imóvel desta matrícula pelo valor de R$48.000.000,00"}]))
    coms.append(esc("1.9", 12, 12, fatia(p[12], "1.9\nRelacionados", "Segmento Local"), "2024-04-10", "16.990.000,00",
                    fatia(p[12], "Informações Adicionais: Diferença entre o valor fiscal e valor declarado e forma", "Ocorrências:").strip(), comunicante="9º Tabelião de Notas de São Paulo",
                    bens=[{"id": "im19", "tipo": "imovel", "descricao": "Imóvel em São Paulo comprado de Vitor Silva Lourenço e Thais Fabrile Berlingeri Lourenço (escritura de 28/03/2024)",
                           "valor": "16.990.000,00", "valor_referencia": "3.749.247,00", "data_negocio": "2024-03-28",
                           "identificacao": {"tabeliao": "9º Tabelião de Notas de São Paulo", "livro": "11.610", "folhas": "011"}}],
                    transacoes=[{"origem": SUPER, "destino": "348.259.538-08", "valor": "16.990.000,00", "tipo": "escritura_compra", "natureza": "individual", "data": "2024-03-28", "bem": "im19",
                                 "descricao": "vendedores: Vitor Silva Lourenço e Thais Fabrile Berlingeri Lourenço; R$ 11 milhões pagos antes da escritura sem especificar o meio", "pagina": 12,
                                 "trecho": "o imóvel desta matrícula pelo valor de R$16.990.000,00"}]))

    # ---------------- operações em espécie 1.1–1.3 (p.12–13): Pipe Participações, Guaxupé-MG
    def especie(num, pag_ini, pag_fim, rel_txt, data_com, valor, informacoes, descricao_bem):
        return cartorio(num, "especie", pag_ini, pag_fim, rel_txt, data_com, valor, informacoes, [oc_171], comunicante="tabelião de notas de Guaxupé-MG",
                        local="Guaxupé-MG", titular="31.825.443/0001-45",
                        bens=[{"id": f"im_pipe_{num.replace('.', '')}", "tipo": "imovel", "descricao": descricao_bem, "valor": valor, "data_negocio": data_com}])

    coms.append(especie("1.1", 12, 13, fatia(p[12], "1 - PIPE PARTICIPACOES LTDA.\n1.1\nRelacionados", "Segmento Local"), "2024-08-23", "240.000,00",
                        fatia(p[12], "Informações Adicionais: R$240.000,00").strip(), "Imóvel em Guaxupé-MG (escritura entre Noah, Pipe, Luis Roberto Neves de Souza e Gustavo Cistolo Ribeiro; direção não informada)"))
    coms.append(especie("1.2", 13, 13, fatia(p[13], "1.2\nRelacionados", "Segmento Local"), "2024-10-08", "205.000,00",
                        fatia(p[13], "Informações Adicionais: R$205.000,00", "Ocorrências:").strip(), "Imóvel em Guaxupé-MG (escritura entre Noah, Pipe, Hélio Anacleto de Souza e Luis Roberto Neves de Souza; direção não informada)"))
    coms.append(especie("1.3", 13, 13, fatia(p[13], "1.3\nRelacionados", "Segmento Local"), "2024-10-08", "199.864,00",
                        fatia(p[13], "Informações Adicionais: R$199.863,89", "Ocorrências:").strip(), "Imóvel em Guaxupé-MG (escritura entre Pipe, Jatahi, Noah e pessoas físicas; direção não informada)"))

    return {
        "fonte": {"tipo": "rif", "identificador": "140515.2.9294.11521", "orgao": "COAF", "destinatario": "PF/SP", "emitido_em": "2026-02-25",
                  "documento": DOC, "incidente": 7526458,
                  "observacoes": "RIF gerado no Procedimento 2025.0049253 (SEI-C 191995), 823 relacionados (303 PF, 520 PJ); o PDF só detalha as comunicações "
                                 "em que alguém do pedido é titular; as planilhas .csv anexas não estão nos autos públicos; comunicações com pessoa de possível foro "
                                 "por prerrogativa de função foram retidas pelo COAF (p. 1–2)."},
        "gerado_por": "scripts/gerar_fluxos_rif_140515.py",
        "comunicacoes": coms,
    }


def main() -> None:
    con = abrir(config.BANCO)
    doc = con.execute("SELECT id FROM documento WHERE endpoint=? AND id_portal=?", (DOC["endpoint"], DOC["id_portal"])).fetchone()
    if not doc:
        raise SystemExit("documento do RIF não está no banco; rode `python -m stf acervo ...` antes")
    paginas = {r[0]: r[1] for r in con.execute("SELECT pagina, texto FROM documento_pagina WHERE documento_id=?", (doc[0],))}
    dados = gerar(paginas)
    erros = validar_dataset(dados, paginas=paginas)
    if erros:
        print("\n".join(erros))
        raise SystemExit(f"{len(erros)} erro(s) de validação")
    # o arquivo publicado não leva CPF inteiro: referências de ator viram a chave mascarada e os textos literais são mascarados
    def ref(v):
        return chave_ator(v)[0] if isinstance(v, str) and not v.startswith("nome:") else v
    for c in dados["comunicacoes"]:
        c["titular"] = ref(c.get("titular"))
        for k in ("informacoes", "consideracoes"):
            if c.get(k):
                c[k] = mascarar_texto(c[k])
        for p in c.get("participacoes") or []:
            p["documento"] = ref(p["documento"]); p["nome"] = mascarar_texto(p["nome"])
        for t in c.get("transacoes") or []:
            t["origem"] = ref(t.get("origem")); t["destino"] = ref(t.get("destino"))
            if t.get("descricao"):
                t["descricao"] = mascarar_texto(t["descricao"])
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(dados, ensure_ascii=False, indent=1), "utf-8")
    n_tx = sum(len(c["transacoes"]) for c in dados["comunicacoes"])
    print(f"{len(dados['comunicacoes'])} comunicações, {n_tx} transações, {sum(len(c['bens']) for c in dados['comunicacoes'])} bens -> {SAIDA}")


if __name__ == "__main__":
    main()
