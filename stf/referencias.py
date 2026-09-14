"""Referências determinísticas tiradas do texto dos documentos e das descrições de andamentos.

Quatro cruzamentos, todos por expressão regular e casamento exato, sem modelo de linguagem:

- documento_ref_processo    documento/página → processo citado no texto ("Pet 15.556", "HC 247450")
- documento_ref_dispositivo documento/página → dispositivo legal citado ("art. 312 do CPP")
- andamento_peticao         andamento → petição, pelo número em "Petição: 114945" (mesmo incidente)
- documento_ref_andamento   intimação → andamento a que ela se refere ("Andamento(s): - Vista à PGR - 20/05/2026")

Cada linha guarda o trecho literal de onde saiu (ou o número citado), para que a interface mostre a fonte.
Tudo é projeção: `construir_referencias` apaga e recria. Nenhuma linha diz algo sobre pessoas.
"""

from __future__ import annotations

import re
import sqlite3
from collections import Counter

# classes processuais do STF que aparecem como "<Classe> <número>"; a forma canônica é o valor do dicionário
CLASSES = {c.upper(): c for c in ("Pet", "Inq", "Rcl", "HC", "RHC", "AP", "MS", "ADPF", "ADI", "ADC", "ADO",
                                  "RE", "ARE", "Ext", "PPE", "MI", "AC", "AO", "SL", "SS", "STA")}
_RE_PROCESSO = re.compile(
    r"\b(" + "|".join(sorted(CLASSES, key=len, reverse=True)) + r")\.?\s?(?:n[º°.]?\s?)?(\d{1,3}\.\d{3}|\d{3,6})\b", re.I)

_DIPLOMAS = [
    (re.compile(r"C[óo]digo de Processo Penal|\bCPP\b", re.I), "CPP"),
    (re.compile(r"C[óo]digo de Processo Civil|\bCPC\b", re.I), "CPC"),
    (re.compile(r"C[óo]digo Penal|\bCP\b"), "CP"),
    (re.compile(r"Constitui[çc][ãa]o(?: Federal| da Rep[úu]blica)?|\bCF(?:/88)?\b|\bCRFB(?:/88)?\b"), "CF"),
    (re.compile(r"Regimento Interno|\bRISTF\b", re.I), "RISTF"),
    (re.compile(r"\b(Decreto-Lei|Lei Complementar|Lei)\s*(?:n[º°.]?\s*)?([\d.]+)\s*/\s*(\d{2,4})", re.I), "LEI"),
]
_RE_ARTIGOS = re.compile(r"\barts?\.?\s*((?:\d{1,4}(?:\s?[º°])?(?:-[A-Z])?(?:\s*,\s*|\s+e\s+|\s+a\s+)?)+)", re.I)
_RE_NUMERO_ARTIGO = re.compile(r"\d{1,4}(?:-[A-Z])?")
_JANELA_DIPLOMA = 90

_RE_PETICAO = re.compile(r"Peti[çc][ãa]o(?: Sigilosa| F[íi]sica| Eletr[ôo]nica)?:\s*(\d{3,7})\b")
_RE_ANDAMENTO_CITADO = re.compile(r"^\s*-\s*(.+?)\s*-\s*(\d{2})/(\d{2})/(\d{4})\s*$", re.M)


def _trecho(texto: str, inicio: int, fim: int, margem: int = 60) -> str:
    a, b = max(0, inicio - margem), min(len(texto), fim + margem)
    return re.sub(r"\s+", " ", texto[a:b]).strip()


def processos_citados(texto: str) -> list[tuple[str, int, str]]:
    """[(classe canônica, número, trecho)] por ocorrência. Anos puros (1990–2099) sem ponto de milhar não contam."""
    out = []
    for m in _RE_PROCESSO.finditer(texto):
        bruto = m.group(2)
        numero = int(bruto.replace(".", ""))
        if "." not in bruto and 1990 <= numero <= 2099:
            continue
        out.append((CLASSES[m.group(1).upper()], numero, _trecho(texto, m.start(), m.end())))
    return out


def _normalizar_diploma(m: re.Match, rotulo: str) -> str:
    if rotulo != "LEI":
        return rotulo
    tipo, numero, ano = m.group(1), m.group(2).strip("."), m.group(3)
    if len(ano) == 2:
        ano = ("19" if int(ano) > 30 else "20") + ano
    tipo = " ".join(w.capitalize() for w in tipo.lower().split())
    return f"{'-'.join(x.capitalize() for x in tipo.split('-'))} {numero}/{ano}"


def dispositivos_citados(texto: str) -> list[tuple[str, str, str]]:
    """[(artigo, diploma normalizado, trecho)] para cada "art. N ... do <diploma>" com o diploma até 90 caracteres à frente."""
    out = []
    for m in _RE_ARTIGOS.finditer(texto):
        janela = texto[m.end(): m.end() + _JANELA_DIPLOMA]
        achado = None
        for rx, rotulo in _DIPLOMAS:
            d = rx.search(janela)
            if d and (achado is None or d.start() < achado[0].start()):
                achado = (d, rotulo)
        if achado is None:
            continue
        diploma = _normalizar_diploma(*achado)
        trecho = _trecho(texto, m.start(), m.end() + achado[0].end())
        for n in _RE_NUMERO_ARTIGO.findall(m.group(1)):
            out.append((n, diploma, trecho))
    return out


def construir_referencias(con: sqlite3.Connection) -> dict:
    with con:
        for t in ("documento_ref_processo", "documento_ref_dispositivo", "andamento_peticao", "documento_ref_andamento"):
            con.execute(f"DELETE FROM {t}")

        # C1 e C2: texto dos documentos, página a página
        n_proc = n_disp = 0
        for r in con.execute("SELECT documento_id, pagina, texto FROM documento_pagina ORDER BY documento_id, pagina"):
            procs: dict[tuple[str, int], list[str]] = {}
            for classe, numero, trecho in processos_citados(r["texto"]):
                procs.setdefault((classe, numero), []).append(trecho)
            for (classe, numero), trechos in procs.items():
                con.execute("INSERT INTO documento_ref_processo (documento_id, pagina, classe, numero, ocorrencias, trecho) VALUES (?,?,?,?,?,?)",
                            (r["documento_id"], r["pagina"], classe, numero, len(trechos), trechos[0]))
                n_proc += 1
            disps: dict[str, list[str]] = {}
            for artigo, diploma, trecho in dispositivos_citados(r["texto"]):
                disps.setdefault(f"art. {artigo} {diploma}", []).append((artigo, diploma, trecho))
            for chave, itens in disps.items():
                artigo, diploma, trecho = itens[0]
                con.execute("INSERT INTO documento_ref_dispositivo (documento_id, pagina, artigo, diploma, dispositivo, ocorrencias, trecho) VALUES (?,?,?,?,?,?,?)",
                            (r["documento_id"], r["pagina"], artigo, diploma, chave, len(itens), trecho))
                n_disp += 1

        # C3: andamento → petição do mesmo incidente com o mesmo número (antes da barra do ano)
        peticoes: dict[tuple[int, str], list[int]] = {}
        for p in con.execute("SELECT id, incidente, numero FROM peticao"):
            peticoes.setdefault((p["incidente"], p["numero"].split("/")[0]), []).append(p["id"])
        n_pet = amb = 0
        for a in con.execute("SELECT id, incidente, descricao FROM andamento WHERE descricao LIKE '%Peti%:%'"):
            m = _RE_PETICAO.search(a["descricao"])
            if not m:
                continue
            ids = peticoes.get((a["incidente"], m.group(1)), [])
            if len(ids) == 1:
                con.execute("INSERT INTO andamento_peticao (andamento_id, peticao_id, numero_citado) VALUES (?,?,?)", (a["id"], ids[0], m.group(1)))
                n_pet += 1
            elif len(ids) > 1:
                amb += 1

        # C4: intimação → andamento citado no bloco "Andamento(s):"
        n_and = 0
        for d in con.execute("SELECT d.id, d.incidente, p.pagina, p.texto FROM documento d JOIN documento_pagina p ON p.documento_id=d.id "
                             "WHERE p.texto LIKE '%Andamento(s):%'"):
            texto = d["texto"]
            bloco = texto[texto.find("Andamento(s):"):]
            for m in _RE_ANDAMENTO_CITADO.finditer(bloco):
                tipo, iso = m.group(1).strip(), f"{m.group(4)}-{m.group(3)}-{m.group(2)}"
                # dois andamentos idênticos na mesma data são indistinguíveis no texto: a intimação liga a ambos
                for h in con.execute("SELECT id FROM andamento WHERE incidente=? AND data=? AND tipo=?", (d["incidente"], iso, tipo)):
                    con.execute("INSERT OR IGNORE INTO documento_ref_andamento (documento_id, pagina, andamento_id, tipo_citado, data_citada) VALUES (?,?,?,?,?)",
                                (d["id"], d["pagina"], h["id"], tipo, iso))
                    n_and += 1
    return {"processos_citados": n_proc, "dispositivos": n_disp, "andamento_peticao": n_pet, "peticoes_ambiguas": amb,
            "documento_andamento": n_and}


def resumo_dispositivos(con: sqlite3.Connection) -> list[dict]:
    """Dispositivos legais por número de documentos que os citam, com os documentos."""
    out = []
    for r in con.execute("SELECT dispositivo, artigo, diploma, COUNT(DISTINCT documento_id) docs, SUM(ocorrencias) oc "
                         "FROM documento_ref_dispositivo GROUP BY dispositivo ORDER BY docs DESC, oc DESC"):
        docs = [dict(x) for x in con.execute(
            "SELECT r.documento_id, d.incidente, d.titulo, MIN(r.pagina) AS pagina, SUM(r.ocorrencias) AS ocorrencias "
            "FROM documento_ref_dispositivo r JOIN documento d ON d.id=r.documento_id WHERE r.dispositivo=? GROUP BY r.documento_id ORDER BY d.id",
            (r["dispositivo"],))]
        out.append({"dispositivo": r["dispositivo"], "artigo": r["artigo"], "diploma": r["diploma"], "documentos": docs, "ocorrencias": r["oc"]})
    return out


def contagem_por_diploma(con: sqlite3.Connection) -> Counter:
    return Counter({r["diploma"]: r["n"] for r in con.execute(
        "SELECT diploma, COUNT(DISTINCT documento_id) n FROM documento_ref_dispositivo GROUP BY diploma")})
