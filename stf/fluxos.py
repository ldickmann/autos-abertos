"""Fluxos financeiros descritos em peças dos autos (primeira fonte: RIF 140515 do COAF, Pet 15.645).

Três camadas, como no resto do projeto:
- bruta: o PDF (blob) e o texto por página (`documento_pagina`);
- extração: um dataset curado em JSON (`data/curadoria/fluxos/*.json`), montado com os parsers deste
  módulo para os blocos regulares do relatório e transcrito à mão para o resto — sempre com página e
  trecho literal;
- projeção: as tabelas `fluxo_*` (stf/db.py), carregadas por `ingerir_fluxos` só depois de o dataset
  passar na validação (inclusive a presença de cada trecho na página indicada).

Dinheiro é sempre em centavos inteiros. CPF nunca entra inteiro: a chave usa os seis dígitos do meio e
a exibição segue a máscara do Portal da Transparência (***.###.###-**).
"""

from __future__ import annotations

import re

RE_CNPJ = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")
RE_CPF = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
RE_VALOR = re.compile(r"R?\$?\s*([\d.]+,\d{2})")

PAPEIS = {
    "titular": "titular", "remetente": "remetente", "beneficiário": "beneficiario", "beneficiario": "beneficiario",
    "responsável": "responsavel", "responsavel": "responsavel", "procurador / representante legal": "procurador",
    "vendedor": "vendedor", "outros": "outros",
}


# ---------------------------------------------------------------- utilitários

def centavos(texto: str) -> int:
    """'R$19.205.000,00' → 1920500000. Só aceita o formato brasileiro com centavos."""
    m = RE_VALOR.search(texto)
    if not m:
        raise ValueError(f"valor não reconhecido: {texto!r}")
    inteiro, cents = m.group(1).split(",")
    return int(inteiro.replace(".", "")) * 100 + int(cents)


def _digitos(doc: str) -> str:
    return re.sub(r"\D", "", doc)


def mascarar_documento(doc: str) -> str | None:
    """CPF vira ***.###.###-** (máscara do Portal da Transparência); CNPJ fica inteiro (é público);
    ator citado só por nome ("nome:...") não tem documento."""
    if doc.startswith("nome:"):
        return None
    if doc.startswith("cpf:") and len(doc) == 10:      # referência já mascarada (só os seis dígitos do meio)
        return f"***.{doc[4:7]}.{doc[7:10]}-**"
    d = _digitos(doc)
    if len(d) == 11:
        return f"***.{d[3:6]}.{d[6:9]}-**"
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    return doc


def chave_ator(doc: str) -> tuple[str, str]:
    """Chave de deduplicação e tipo. Para CPF guarda só os seis dígitos do meio; "nome:X" é a saída para quem a
    peça cita sem CPF/CNPJ (normalização igual à das entidades do caso)."""
    if doc.startswith("nome:"):
        from .entidades import normalizar
        return f"nome:{normalizar(doc[5:])}", "desconhecido"
    if doc.startswith("cpf:") and doc[4:].isdigit() and len(doc) == 10:
        return doc, "pessoa_fisica"
    if doc.startswith("cnpj:") and doc[5:].isdigit() and len(doc) == 19:
        return doc, "pessoa_juridica"
    d = _digitos(doc)
    if len(d) == 14:
        return f"cnpj:{d}", "pessoa_juridica"
    if len(d) == 11:
        return f"cpf:{d[3:9]}", "pessoa_fisica"
    raise ValueError(f"documento não reconhecido: {doc!r}")


_RE_CPF_SOLTO = re.compile(r"(?<![\d./-])(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})(?!\d)(?![./-]\d)")
_RE_RG = re.compile(r"RG\s*n[ºo°]?\s*[\d.]+-?[A-Z]{2,5}/?[A-Z]{0,2}", re.I)
_RE_ENDERECO = re.compile(r"domiciliad[oa]s?\s+nesta\s+Capital,.*?(?=,\s*o\s+im[óo]vel|$)", re.I | re.S)


def mascarar_texto(texto: str | None) -> str | None:
    """Apaga dados pessoais de um trecho literal antes de ele entrar em tabela: CPF (formatado ou só dígitos) vira
    ***.###.###-**, RG e endereço residencial viram marcadores. CNPJ (14 dígitos) não é tocado."""
    if not texto:
        return texto
    t = _RE_ENDERECO.sub("[endereço omitido]", texto)
    t = _RE_RG.sub("RG [omitido]", t)
    return _RE_CPF_SOLTO.sub(lambda m: f"***.{m.group(2)}.{m.group(3)}-**", t)


# ---------------------------------------------------------------- parsers do RIF

_RE_RELACIONADO = re.compile(
    r"^(?P<nome>.+?)\s+(?P<doc>\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2})\s+"
    r"(?P<papel>Titular|Remetente|Benefici[áa]rio|Respons[áa]vel|Procurador / Representante Legal|Vendedor|Outros)\s*$")


def parse_relacionados(texto: str) -> list[dict]:
    """Linhas 'NOME DOCUMENTO PAPEL' da tabela 'Relacionados' de uma comunicação."""
    out = []
    for linha in texto.splitlines():
        m = _RE_RELACIONADO.match(linha.strip())
        if m:
            out.append({"nome": m["nome"].strip(), "documento": m["doc"], "papel": PAPEIS[m["papel"].lower()]})
    return out


_CABECALHO = {
    "remetentes": r"Principais\s+remetentes/depositantes\s+identificados:",
    "destinatarios": r"Principais\s+destinat[áa]rios\s+de\s+recursos\s+identificados:",
}
_RE_ITEM = re.compile(
    r"(?P<nome>.+?)\s+-\s+(?P<doc>\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2})\s+\(\s*(?P<atividade>.*?)\s*\)"
    r"(?:\s+-\s+MIDIA)?\s+-\s+(?P<qtd>[\d.]+)\s+lançamento\(s\)\s+no\s+total\s+de:\s*(?P<valor>R\$\s*[\d.]+,\d{2})", re.S)


def parse_principais(texto: str, lista: str) -> list[dict]:
    """'Principais remetentes/depositantes' ou 'Principais destinatários': nome, documento, atividade, N, total.
    A lista termina no próximo bloco ('Resumo de lançamentos', 'CONSIDERAÇÕES') ou no fim do texto."""
    m = re.search(_CABECALHO[lista], texto)
    if not m:
        return []
    corpo = texto[m.end():]
    fim = re.search(r"Resumo de lançamentos|CONSIDERAÇÕES|Ocorrências:", corpo)
    corpo = " ".join(corpo[: fim.start() if fim else None].split())
    out = []
    for it in _RE_ITEM.finditer(corpo):
        out.append({"nome": it["nome"].strip(), "documento": it["doc"], "atividade": " ".join(it["atividade"].split()),
                    "quantidade": int(it["qtd"].replace(".", "")), "valor_centavos": centavos(it["valor"])})
    return out
