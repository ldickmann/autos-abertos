"""Saídas abertas: CSV para planilha e feed Atom para acompanhar mudanças e avisos."""
import csv
import io
import xml.etree.ElementTree as ET

from stf.saidas import csv_assercoes, csv_decisoes, feed_atom


def _csv(texto: str) -> list[dict]:
    assert texto.startswith("﻿")   # BOM: o Excel abre em UTF-8 sem perguntar
    return list(csv.DictReader(io.StringIO(texto.lstrip("﻿")), delimiter=";"))


def test_csv_de_decisoes_e_assercoes_tem_fonte_em_cada_linha():
    itens = [{"id": 1, "data": "2026-06-03", "incidente": 7514886, "processo": "Pet 15556", "pedido": "prisão preventiva de X", "quem_pediu": "PF", "resultado": "deferido",
              "decisao": "decretou", "quem_decidiu": "Min. Y", "condicoes": ["a", "b"], "documento_id": 55, "pagina": 47, "trecho_fonte": "DEFIRO; \"aspas\"", "url_documento": "https://x/55.pdf"}]
    linhas = _csv(csv_decisoes(itens))
    assert linhas[0]["processo"] == "Pet 15556" and linhas[0]["condicoes"] == "a | b" and linhas[0]["documento_id"] == "55" and linhas[0]["trecho_fonte"] == 'DEFIRO; "aspas"'
    assercoes = [{"id": 9, "documento": {"id": 3, "incidente": 1, "titulo": "Decisão", "url": "u"}, "pagina": 2, "tipo_epistemico": "alegacao_parte", "texto": "t", "trecho_fonte": "f",
                  "atribuida_a": "PF", "entidades": [{"nome": "A"}, {"nome": "B"}], "modelo": "m", "prompt_version": "v", "data_andamento": "2026-01-01"}]
    l = _csv(csv_assercoes(assercoes))[0]
    assert l["tipo_epistemico"] == "alegacao_parte" and l["entidades"] == "A | B" and l["documento_id"] == "3" and l["pagina"] == "2"


def test_feed_atom_lista_avisos_e_rodadas_de_mudanca():
    avisos = [{"id": "sessao", "titulo": "Sessão", "inicio": "2026-09-15T10:00:00-03:00", "resumo": "R", "acao": {"url": "https://yt"}}]
    mudancas = [{"em": "2026-09-14T13:33+00:00", "processos": [{"processo": "Pet 1", "resumo": {"sumiu": 1, "apareceu": 0, "mudou": 0}, "mudancas": [{"o_que": "andamento", "mudanca": "sumiu", "item": "x"}]}]}]
    xml = feed_atom("https://site", avisos=avisos, mudancas=mudancas, gerado_em="2026-09-14T14:00:00+00:00")
    raiz = ET.fromstring(xml)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    titulos = [e.find("a:title", ns).text for e in raiz.findall("a:entry", ns)]
    assert titulos[0].startswith("Base atualizada") and any("Sessão" in t for t in titulos) and any("1 mudança" in t for t in titulos)
    assert all(e.find("a:id", ns).text for e in raiz.findall("a:entry", ns))
