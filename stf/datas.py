"""Datas citadas no trecho literal de cada asserção, por expressão regular, sem modelo.

Uma asserção cujo trecho traz exatamente uma data vira um ponto na cronologia dos fatos "segundo os documentos":
o que o documento diz que aconteceu, quando, e com que tipo epistêmico (fato registrado pelo juízo, alegação de
uma parte, fundamento do julgador). Asserções com várias datas ficam registradas, mas fora da cronologia
(não dá para saber por regra qual data é a do evento).
"""

from __future__ import annotations

import datetime as dt
import re
import sqlite3

MESES = {"janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
         "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}
_RE = re.compile(
    r"(?<![\d./-])(?P<d1>\d{1,2})[./](?P<m1>\d{1,2})[./](?P<a1>\d{4})(?!\d|[./]\d)"
    r"|(?<!\d)(?P<d2>\d{1,2})º?\s+de\s+(?P<m2>janeiro|fevereiro|março|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+(?P<a2>\d{4})\b",
    re.I)
ANO_MIN, ANO_MAX = 1988, 2100   # antes da Constituição de 1988 e depois de 2100, não é data deste caso


def datas_no_texto(texto: str) -> list[tuple[str, str]]:
    """[(AAAA-MM-DD, literal)] na ordem em que aparecem; datas impossíveis ou fora da faixa são ignoradas."""
    out = []
    for m in _RE.finditer(texto or ""):
        if m.group("d1"):
            d, mes, a = int(m.group("d1")), int(m.group("m1")), int(m.group("a1"))
        else:
            d, mes, a = int(m.group("d2")), MESES[m.group("m2").lower()], int(m.group("a2"))
        if not (ANO_MIN <= a <= ANO_MAX):
            continue
        try:
            iso = dt.date(a, mes, d).isoformat()
        except ValueError:
            continue
        out.append((iso, m.group(0)))
    return out


def construir_datas(con: sqlite3.Connection) -> dict:
    """Recria assercao_data a partir do trecho_fonte de cada asserção. Idempotente."""
    with con:
        con.execute("DELETE FROM assercao_data")
        n_ass = n_datas = n_unica = 0
        for a in con.execute("SELECT id, trecho_fonte FROM assercao ORDER BY id"):
            datas = datas_no_texto(a["trecho_fonte"])
            distintas = sorted({d for d, _ in datas})
            if not distintas:
                continue
            n_ass += 1
            n_unica += len(distintas) == 1
            vistas = set()
            for iso, literal in datas:
                if iso in vistas:
                    continue
                vistas.add(iso)
                con.execute("INSERT INTO assercao_data (assercao_id, data, literal, n_datas) VALUES (?,?,?,?)", (a["id"], iso, literal, len(distintas)))
                n_datas += 1
    return {"assercoes_com_data": n_ass, "datas": n_datas, "com_data_unica": n_unica}
