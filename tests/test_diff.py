"""`diff` entre duas coletas: trabalha só com os blobs, sem banco."""
from selectolax.parser import HTMLParser

from stf.diff import diff_coletas, formatar_diff
from tests.test_ingest import montar_coleta


def _simular_coleta_antiga(aba, raw):
    """Remove os 10 andamentos mais recentes, a última parte e a petição mais recente."""
    if aba == "andamentos":
        t = HTMLParser(raw.decode("utf-8"))
        for item in t.css(".andamento-item")[:10]:
            item.decompose()
        return t.html.encode("utf-8")
    if aba == "partes":
        t = HTMLParser(raw.decode("utf-8"))
        t.css_first("#todas-partes").css(".processo-partes")[-1].decompose()
        return t.html.encode("utf-8")
    if aba == "peticoes":
        t = HTMLParser(raw.decode("utf-8"))
        t.css(".lista-dados")[0].decompose()
        return t.html.encode("utf-8")
    return raw


def test_diff_lista_inclusoes_por_aba(tmp_path, fx):
    antiga = montar_coleta(tmp_path / "a", fx, "C0", _simular_coleta_antiga)
    nova = montar_coleta(tmp_path / "b", fx, "C1")
    d = diff_coletas(antiga, nova)
    assert d.incidente == 7514886
    assert len(d.andamentos.incluidos) == 10 and d.andamentos.removidos == []
    assert d.andamentos.incluidos[0].data == "2026-09-11"
    assert len(d.partes.incluidos) == 1 and d.partes.removidos == []
    assert len(d.peticoes.incluidos) == 1 and d.peticoes.incluidos[0].numero == "114945/2026"
    assert d.deslocamentos.incluidos == [] and d.deslocamentos.removidos == []
    assert d.incidente_campos_alterados == {}
    assert d.abas_identicas == ["casca", "informacoes", "decisoes", "sessao", "deslocamentos", "recursos", "pautas"]


def test_diff_no_sentido_inverso_lista_remocoes(tmp_path, fx):
    antiga = montar_coleta(tmp_path / "a", fx, "C0", _simular_coleta_antiga)
    nova = montar_coleta(tmp_path / "b", fx, "C1")
    d = diff_coletas(nova, antiga)
    assert len(d.andamentos.removidos) == 10 and d.andamentos.incluidos == []


def test_diff_de_coleta_consigo_mesma_e_vazio(tmp_path, fx):
    c = montar_coleta(tmp_path, fx, "C1")
    d = diff_coletas(c, c)
    assert d.vazio
    assert len(d.abas_identicas) == 10


def test_formatar_diff_e_texto_legivel(tmp_path, fx):
    antiga = montar_coleta(tmp_path / "a", fx, "C0", _simular_coleta_antiga)
    nova = montar_coleta(tmp_path / "b", fx, "C1")
    texto = formatar_diff(diff_coletas(antiga, nova))
    assert "C0 → C1" in texto
    assert "+10 andamentos" in texto
    assert "+1 parte" in texto
    assert "2026-09-11 | Remessa" in texto
