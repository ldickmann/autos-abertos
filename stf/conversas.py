"""Conversas descritas pela Polícia Federal em análises de celular (IPJ-A).

A PF não transcreve as conversas: descreve-as em prosa ("Em 15/03/2024, às 15:07:11 -03:00, FABIO FARIA diz a
DANIEL VORCARO que “O careca não pode atrasar”") e cola capturas de tela como figuras ("Figura 150 – ..."), que
não chegam ao texto extraído. O site reconstitui a conversa a partir dessa prosa, com uma regra conservadora:

- vira **balão** só a frase com estrutura inequívoca `NOME verbo [a NOME] [que] “citação”` e uma única citação;
- o resto da prosa vira **relato** literal da PF (com as citações marcadas), inclusive frases com mais de uma
  citação, em que não dá para atribuir cada fala com segurança;
- a legenda de cada figura vira uma **captura** (marcador da imagem que só existe no PDF).

Cada item guarda a página e a frase literal de onde saiu. Telefones (13 dígitos, "terminal 55...") são mascarados
antes de sair daqui; CPF, RG e endereço passam por `mascarar_texto`.
"""

from __future__ import annotations

import re
import unicodedata

from .fluxos import _RE_CPF_SOLTO, mascarar_texto

APARELHO_VORCARO = {"nome": "Daniel Vorcaro", "variantes": ["DANIEL BUENO VORCARO", "DANIEL VORCARO", "VORCARO"]}

VERBOS_FALA = ("diz", "responde", "escreve", "pergunta", "questiona", "informa", "encaminha", "envia", "orienta", "pede",
               "repassa", "confirma", "afirma", "manda", "complementa", "finaliza", "reencaminha", "comenta", "retoma",
               "conversa", "solicita", "reclama", "avisa", "explica", "esclarece", "acrescenta", "devolve", "cobra",
               "insiste", "agradece", "conclui", "relata", "sugere", "propõe", "alerta")
_VERBOS = "|".join(VERBOS_FALA)
_NOME = r"[A-ZÀ-Ú][A-ZÀ-Ú.\-]+(?:\s+(?:[A-ZÀ-Ú][A-ZÀ-Ú.\-]+|DE|DA|DO|DOS|DAS|E))*"
# um contato salvo no aparelho aparece entre aspas ("Gustavo Motorista"); é nome, não citação
_NOME_OU_CONTATO = rf"(?:{_NOME}|[“\"][A-ZÀ-Ú][^“”\"]{{1,40}}[”\"])"
_ASPAS = r"[“\"](?P<texto>[^“”\"]+)[”\"]"
_ABERTURAS = (r"Na sequência|Em seguida|Logo depois|Logo em seguida|Ainda|Depois|Minutos depois|Alguns minutos depois|"
              r"Imediatamente|No mesmo dia|Nesse momento|Neste momento|Na mesma conversa|Mais tarde|Antes disso|Após|"
              r"Em resposta|Pouco depois|Instantes depois|Então")

RE_MENSAGEM = re.compile(
    rf"^(?:(?:{_ABERTURAS})[^“”\",]{{0,40}}?,\s*)?"
    rf"(?:[Ee]m (?P<data>\d{{2}}/\d{{2}}/\d{{4}}),?\s*)?"
    rf"(?:[Àà]s (?P<hora>\d{{2}}:\d{{2}})(?::\d{{2}})?\s*(?P<fuso>-\s?03:00|UTC-3|UTC)?,?\s*)?"
    rf"(?P<de>{_NOME_OU_CONTATO})\s+(?P<verbo>{_VERBOS})\s+"
    rf"(?:(?:a|para|ao|à)\s+(?P<para>{_NOME_OU_CONTATO})\s*,?\s*)?"
    rf"(?:(?:que|a mensagem|a seguinte mensagem|o seguinte|o texto)\s+|:\s*)?"
    rf"{_ASPAS}(?P<resto>.*)$", re.S)
RE_FIGURA = re.compile(r"^Figura (?P<numero>\d+)\s+[–\-]\s+(?P<legenda>.+)$")
# título de seção numerado ("5.4 Cobranças de pagamento…", "5. DA ANÁLISE…"), curto e sem ponto final
RE_SECAO = re.compile(r"^\d{1,2}(?:\.\d{1,2}){0,3}\.?\s+[A-ZÀ-Ú][^.]{3,140}$")
RE_RODAPE = re.compile(r"^(?:Página \d+ de \d+|IPJ-A nº .+)$")
RE_CITACAO = re.compile(r"[“\"]([^“”\"]+)[”\"]")
RE_LEGENDA_CONVERSA = re.compile(rf"{_NOME}\s+(?:{_VERBOS})\b")
RE_VERBO_CONVERSA = re.compile(rf"\b(?:{_VERBOS}|mensagem|conversa|áudio)\b")
_RE_TELEFONE = re.compile(r"\b(\d{4})(\d{6,11})\b")
_RE_PLACA = re.compile(r"\b([A-Z]{3})(?:-?\d[A-Z]\d{2}|[- ]?\d{4})\b")
# siglas de classe processual do STF que têm a forma "AAA9999" e não são placa
_CLASSES_STF = {"INQ", "PET", "RCL", "ADI", "ADC", "ADO", "ADP", "ARE", "RHC", "RMS", "STA", "PSV", "EXT", "PPE", "SEC", "AOE",
                "RVC", "QO", "EMB", "AGR", "EDV", "HC", "MS", "AC", "AP", "AO", "MI", "EP", "EL", "SL", "SS", "RE", "AI", "AR", "SE", "CC", "CR", "EI", "IF", "PA",
                "IPL", "IPJ", "RIF", "NUP", "SEI", "PJE", "NIRE", "ANO", "LEI", "ART", "RES", "SR", "DPF"}
# CPF que o PDF quebrou ("077.295.156- 01") e endereços pessoais: depois do CPF numa lista de pessoas, em "Endereço N:",
# ou introduzidos por "residente/domiciliado em"; "com sede" (empresa) fica.
_RE_CPF_QUEBRADO = re.compile(r"(?<![\d./-])(\d{3})\.(\d{3})\.(\d{3})-\s(\d{2})(?!\d)")
_VIAS = r"(?:Rua|R\.|Av\.?|Avenida|Al\.?|Alameda|Travessa|Tv\.|Estrada|Rod\.?|Rodovia|Praça|Quadra|Q\.|Cond\.|Condomínio|Sítio|Chácara|Fazenda|SHIS|SQS|SQN|SQSW|SMDB|SMPW|QI|QL)"
_RE_END_APOS_CPF = re.compile(rf"(\*\*\*\.\d{{3}}\.\d{{3}}-\*\*\)?)\s*((?:Endereço \d:|{_VIAS})[^;]{{3,400}}?)(?=;|\n\d+ - |$)", re.S)
_RE_END_RESIDENTE = re.compile(r"\b(residente(?: e domiciliad[oa])?|domiciliad[oa]|com endereço(?: residencial)?)\s+(?:n[oa]s?|nest[ae]|em|à|a)\s+[^;.]{3,200}", re.I)
_RE_NIRE = re.compile(r"\bNIRE\s*n?[ºo°]?\s*[\d.]{9,14}", re.I)
# verbo de fala com o que vem antes: sujeito nomeado ("VORCARO responde", "“Vivi Moraes” (terminal …), envia"),
# continuação do mesmo sujeito ("depois acrescenta", "e complementa") ou outro sujeito ("…, que afirma", "Ele diz")
_RE_VERBO_COM_CONTEXTO = re.compile(
    rf"(?P<sujeito>{_NOME_OU_CONTATO})(?:\s*\(terminal [^)]*\))?\s*,?\s+(?P<verbo>{_VERBOS})\b"
    rf"|(?P<continuacao>\b(?:depois|e|em seguida|também|ainda|então|logo|por fim|adiante)\s*,?\s+)(?P<verbo2>{_VERBOS})\b"
    rf"|(?P<verbo3>\b(?:{_VERBOS}))\b")
# o que vem antes de uma citação que não é fala: nome de contato ("salvo como “…”"), descrição ("emoji de "…"")
_RE_ANTES_DE_NAO_FALA = re.compile(r"(?:como|denominad\w*|intitulad\w*|usuário|contato|chamad\w*|segundo|salvo|emoji de|refere-se a|apelid\w*)\s*[“\"][^“”\"]*$")
_RE_PREPOSICAO_ANTES = re.compile(r"\b(?:a|para|ao|à|com|de|do|da)\s*[“\"][^“”\"]*$")
# endereços de Brasília (setor + número), que a regra genérica de "Rua/Av." não pega
_RE_ENDERECO_DF = re.compile(r"\b(?:SMDB|SHIS|SQS|SQN|SQSW|SQNW|SHIN|SMPW|SHIGS|SHCGN|SMLN|SHTN|SCLN|CLN|CLS|QI|QL)\s+\d+[^“”\".;]*")
_RE_INICIO_FRASE = re.compile(
    rf"^(?:Em \d|[Àà]s \d|{_ABERTURAS}|Como|Para |Registre|Observ|Nota-se|Verific|Constat|Também|Além|Ess[ea]s?\b|Est[ea]s?\b|"
    rf"Os? |As? |Segundo|Conforme|Cabe|Import|Ressalt|Destac|Já |Mais|N[oa]s? |Seus? |Suas? |Trata|Tal|Dess[ea]|Nest|"
    rf"{_NOME}\s+(?:{_VERBOS})\b)")


def mascarar_telefone(texto: str) -> str:
    """Números de 10 a 15 dígitos seguidos (telefone com DDI, IMEI) viram os 4 primeiros dígitos + pontos.
    Datas, valores, CNPJ formatado e números com separador ficam como estão."""
    return _RE_TELEFONE.sub(lambda m: m.group(1) + "•" * len(m.group(2)), texto)


def mascarar_placa(texto: str) -> str:
    """Placas de veículo (Mercosul: ABC1D23; antigo: ABC-1234 / ABC 1234 / ABC1234) viram marcador; siglas de classe
    processual (INQ5026, ADI 1234) ficam."""
    return _RE_PLACA.sub(lambda m: m.group(0) if m.group(1) in _CLASSES_STF else "[placa omitida]", texto)


def _limpar(texto: str, omitir: tuple[str, ...] = ()) -> str:
    t = re.sub(r"\s+", " ", texto).strip()
    for trecho in omitir:  # omissões curadas por documento (endereços que a regra não reconhece)
        t = t.replace(trecho, "[endereço omitido]")
    t = _RE_ENDERECO_DF.sub("[endereço omitido]", t)
    return mascarar_placa(mascarar_telefone(mascarar_texto(t) or ""))  # CPF (11 dígitos) antes do telefone (10–15)


def mascarar_pagina(texto: str | None, omitir: tuple[str, ...] = ()) -> str | None:
    """Texto de página como vai para o site: telefones, placas, endereços do DF e CPFs mascarados, sem tocar no resto
    (quebras de linha preservadas, para o trecho literal das asserções continuar conferível)."""
    if not texto:
        return texto
    t = texto
    for trecho in omitir:
        t = t.replace(trecho, "[endereço omitido]")
    t = _RE_ENDERECO_DF.sub("[endereço omitido]", t)
    nires = _RE_NIRE.findall(t)  # NIRE (registro de empresa, 11 dígitos) não é CPF: guarda e devolve
    t = _RE_NIRE.sub("\x00NIRE\x00", t)
    t = _RE_CPF_QUEBRADO.sub(lambda m: f"***.{m.group(2)}.{m.group(3)}-**", t)
    t = _RE_CPF_SOLTO.sub(lambda m: f"***.{m.group(2)}.{m.group(3)}-**", t)  # CPF (11 dígitos) antes do telefone (10–15)
    t = _RE_END_APOS_CPF.sub(lambda m: f"{m.group(1)} [endereço omitido]", t)
    t = _RE_END_RESIDENTE.sub(lambda m: f"{m.group(1)} [endereço omitido]", t)
    t = mascarar_placa(mascarar_telefone(t))
    for n in nires:
        t = t.replace("\x00NIRE\x00", n, 1)
    return t


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def segmentar_pagina(texto: str) -> list[str]:
    """Frases de um bloco de prosa: descarta rodapés, junta as linhas quebradas pelo PDF e separa em pontuação final
    seguida de maiúscula, aspas ou parêntese (números como 3.422.268,14 e horários 15:07:11 não separam)."""
    linhas = [ln.strip() for ln in texto.splitlines() if ln.strip() and not RE_RODAPE.match(ln.strip())]
    blob = " ".join(linhas)
    partes = re.split(r"(?<=[.!?:;])\s+(?=[A-ZÀ-Ú“\"(])", blob)
    return [p.strip() for p in partes if p.strip()]


def _blocos(texto: str) -> list[tuple[str, str]]:
    """Divide a página em blocos ordenados: ('prosa', texto), ('figura', legenda com 'Figura N – ') e ('secao', título)."""
    linhas = [ln.strip() for ln in texto.splitlines() if ln.strip() and not RE_RODAPE.match(ln.strip())]
    blocos: list[tuple[str, str]] = []
    prosa: list[str] = []
    i = 0
    while i < len(linhas):
        ln = linhas[i]
        tipo = "figura" if RE_FIGURA.match(ln) else "secao" if RE_SECAO.match(ln) else None
        if tipo:
            if prosa:
                blocos.append(("prosa", "\n".join(prosa)))
                prosa = []
            bloco = ln
            absorvidas = 0
            # legenda/título continua na linha seguinte se não terminou em pontuação e a linha não abre frase de prosa
            while (absorvidas < 2 and i + 1 < len(linhas) and not re.search(r"[.:;!?”\"]$", bloco)
                   and not RE_FIGURA.match(linhas[i + 1]) and not RE_SECAO.match(linhas[i + 1]) and not _RE_INICIO_FRASE.match(linhas[i + 1])
                   and (tipo == "figura" or linhas[i + 1][0].islower())):  # título só continua em linha que começa minúscula
                i += 1
                bloco += " " + linhas[i]
                absorvidas += 1
            blocos.append((tipo, bloco))
        else:
            prosa.append(ln)
        i += 1
    if prosa:
        blocos.append(("prosa", "\n".join(prosa)))
    return blocos


def _lado(nome: str, aparelho: dict) -> str:
    n = _sem_acento(re.sub(r"\s+", " ", nome)).upper()
    return "enviada" if any(n == _sem_acento(v).upper() for v in aparelho["variantes"]) else "recebida"


def _e_nome_citado(frase: str, citacao: str) -> bool:
    """Citação que não é fala: introduzida por "como/denominado/segundo/emoji de…", ou nome curto e capitalizado
    depois de preposição ("envia mensagem a “Alexandre de Moraes BRASILIA”")."""
    inicio = frase.find("“" + citacao)
    if inicio < 0:
        inicio = frase.find('"' + citacao)
    antes = frase[max(0, inicio - 30):inicio + 1]
    if _RE_ANTES_DE_NAO_FALA.search(antes):
        return True
    palavras = citacao.split()
    parece_nome = len(palavras) <= 4 and all(w[0].isupper() or w.lower() in ("de", "da", "do", "dos", "das", "e") for w in palavras)
    return parece_nome and bool(_RE_PREPOSICAO_ANTES.search(antes))


def _atribuir_falas(frase: str, citacoes: list[str], aparelho: dict) -> tuple[str | None, list[str]]:
    """Quem fala num relato: um único NOME + verbo de fala, sem outro sujeito na frase, antes da primeira citação.
    Devolve (falante, falas). Sem falante inequívoco → (None, [])."""
    falas = [c for c in citacoes if not _e_nome_citado(frase, c)]
    if not falas:
        return None, []
    primeira = min(frase.find(q) for q in ("“" + falas[0], '"' + falas[0]) if frase.find(q) >= 0)
    sujeitos: list[tuple[str, int]] = []
    for m in _RE_VERBO_COM_CONTEXTO.finditer(frase):
        if m["sujeito"]:
            sujeitos.append((re.sub(r"\s+", " ", m["sujeito"]).strip("“”\""), m.start()))
        elif m["continuacao"]:
            continue
        else:
            return None, []  # verbo com outro sujeito (pronome, "que afirma"): ambíguo
    nomes = {n for n, _ in sujeitos}
    if len(nomes) != 1 or sujeitos[0][1] > primeira:
        return None, []
    return sujeitos[0][0], falas


def _item_de_frase(frase: str, pagina: int, aparelho: dict) -> dict:
    frase_limpa = _limpar(frase, tuple(aparelho.get("omitir", ())))
    citacoes = RE_CITACAO.findall(frase_limpa)
    m = RE_MENSAGEM.match(frase_limpa)
    if m:
        de = re.sub(r"\s+", " ", m["de"]).strip("“”\"")
        para = re.sub(r"\s+", " ", m["para"]).strip("“”\"") if m["para"] else None
        # fora os nomes de contato entre aspas, a frase precisa ter exatamente uma citação: a mensagem
        if [c for c in citacoes if c not in (de, para)] != [m["texto"]]:
            m = None
    if m:
        data = m["data"]
        return {"tipo": "mensagem", "pagina": pagina, "de": de, "para": para, "verbo": m["verbo"], "texto": m["texto"].strip(),
                "data": f"{data[6:10]}-{data[3:5]}-{data[0:2]}" if data else None, "hora": m["hora"], "fuso": m["fuso"],
                "lado": _lado(de, aparelho), "trecho": frase_limpa}
    de, falas = _atribuir_falas(frase_limpa, citacoes, aparelho)
    return {"tipo": "relato", "pagina": pagina, "texto": frase_limpa, "citacoes": citacoes, "de": de,
            "lado": _lado(de, aparelho) if de else None, "falas": falas, "trecho": frase_limpa}


def _item_de_figura(legenda_completa: str, pagina: int, aparelho: dict) -> dict:
    m = RE_FIGURA.match(re.sub(r"\s+", " ", legenda_completa))
    assert m
    omitir = tuple(aparelho.get("omitir", ()))
    legenda = _limpar(m["legenda"], omitir)
    return {"tipo": "figura", "pagina": pagina, "numero": int(m["numero"]), "legenda": legenda,
            "conversa": bool(RE_LEGENDA_CONVERSA.search(legenda)), "trecho": _limpar(legenda_completa, omitir)}


def _pagina_e_conversa(itens: list[dict]) -> bool:
    for it in itens:
        if it["tipo"] == "mensagem":
            return True
        if it["tipo"] == "figura" and it["conversa"]:
            return True
        if it["tipo"] == "relato" and (it["falas"] or (it["citacoes"] and RE_LEGENDA_CONVERSA.search(it["texto"]))):
            return True
    return False


def extrair_conversas(paginas: list[dict], aparelho: dict) -> dict | None:
    """`paginas`: [{"n": int, "texto": str}]. Devolve {"aparelho", "paginas": [{"n", "itens": [...]}]} só com as
    páginas em que a PF descreve conversa; None se nenhuma."""
    saida = []
    for p in paginas:
        itens: list[dict] = []
        for tipo, bloco in _blocos(p["texto"] or ""):
            if tipo == "figura":
                itens.append(_item_de_figura(bloco, p["n"], aparelho))
            elif tipo == "secao":
                itens.append({"tipo": "secao", "pagina": p["n"], "texto": _limpar(bloco, tuple(aparelho.get("omitir", ())))})
            else:
                itens.extend(_item_de_frase(f, p["n"], aparelho) for f in segmentar_pagina(bloco))
        if _pagina_e_conversa(itens):
            saida.append({"n": p["n"], "itens": itens})
    if not saida:
        return None
    return {"aparelho": aparelho["nome"], "paginas": saida}
