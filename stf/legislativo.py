"""Matérias do Congresso Nacional que mencionam o caso, pelas APIs oficiais de dados abertos do Senado e da Câmara.

Cada consulta (casa + palavra-chave, lista em `stf/curadoria/legislativo.json`) devolve JSON oficial, guardado como blob
(sha256) e registrado em `data/raw/legislativo.jsonl` (append-only). A tabela `materia_legislativa` é projeção: dá para
refazê-la só do registro e dos blobs (`reingerir_legislativo`). Nenhuma interpretação: sigla, número, ementa, autor e
data são os do próprio Congresso, com o link oficial para a tramitação.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from . import config
from .coleta import ClienteEducado
from .store import BlobStore, caminho_relativo, resolver_raw

_PATH = Path(__file__).parent / "curadoria" / "legislativo.json"
REGISTRO = config.DATA / "raw" / "legislativo.jsonl"
CONSULTAS: list[dict] = json.loads(_PATH.read_text("utf-8"))["consultas"] if _PATH.exists() else []


def url_senado(palavra: str) -> str:
    return f"https://legis.senado.leg.br/dadosabertos/materia/pesquisa/lista?palavraChave={quote(palavra)}"


def url_camara(palavra: str) -> str:
    return f"https://dadosabertos.camara.leg.br/api/v2/proposicoes?keywords={quote(palavra)}&itens=100&ordem=DESC&ordenarPor=id"


def parse_senado(bruto: bytes) -> list[dict]:
    d = json.loads(bruto)
    materias = (d.get("PesquisaBasicaMateria") or {}).get("Materias") or {}
    lista = materias.get("Materia") or []
    if isinstance(lista, dict):
        lista = [lista]
    out = []
    for m in lista:
        out.append({"casa": "senado", "codigo": str(m["Codigo"]), "sigla": m.get("Sigla"), "numero": int(m["Numero"]) if str(m.get("Numero", "")).isdigit() else None,
                    "ano": int(m["Ano"]) if str(m.get("Ano", "")).isdigit() else None, "comissao": m.get("SiglaComissao"), "identificacao": m.get("DescricaoIdentificacao"),
                    "ementa": m.get("Ementa") or "", "autor": m.get("Autor"), "data": m.get("Data"),
                    "url": f"https://www25.senado.leg.br/web/atividade/materias/-/materia/{m['Codigo']}", "url_api": m.get("UrlDetalheMateria")})
    return out


def parse_camara(bruto: bytes) -> list[dict]:
    d = json.loads(bruto)
    out = []
    for p in d.get("dados", []):
        out.append({"casa": "camara", "codigo": str(p["id"]), "sigla": p.get("siglaTipo"), "numero": p.get("numero"), "ano": p.get("ano"), "comissao": None,
                    "identificacao": f"{p.get('siglaTipo')} {p.get('numero')}/{p.get('ano')}", "ementa": p.get("ementa") or "", "autor": None,
                    "data": (p.get("dataApresentacao") or "")[:10] or None,
                    "url": f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={p['id']}", "url_api": p.get("uri")})
    return out


def _upsert(con: sqlite3.Connection, itens: list[dict], consulta: str, visto_em: str) -> int:
    n = 0
    for m in itens:
        row = con.execute("SELECT consultas_json FROM materia_legislativa WHERE casa=? AND codigo=?", (m["casa"], m["codigo"])).fetchone()
        if row:
            cons = json.loads(row["consultas_json"])
            if consulta not in cons:
                cons.append(consulta)
            con.execute("UPDATE materia_legislativa SET consultas_json=?, ultimo_visto_em=?, ementa=?, autor=COALESCE(?, autor), data=COALESCE(?, data) WHERE casa=? AND codigo=?",
                        (json.dumps(cons, ensure_ascii=False), visto_em, m["ementa"], m.get("autor"), m.get("data"), m["casa"], m["codigo"]))
        else:
            con.execute("INSERT INTO materia_legislativa (casa, codigo, sigla, numero, ano, comissao, identificacao, ementa, autor, data, url, url_api, consultas_json, primeiro_visto_em, ultimo_visto_em) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (m["casa"], m["codigo"], m.get("sigla"), m.get("numero"), m.get("ano"), m.get("comissao"), m.get("identificacao"), m["ementa"], m.get("autor"), m.get("data"),
                         m["url"], m.get("url_api"), json.dumps([consulta], ensure_ascii=False), visto_em, visto_em))
            n += 1
    return n


def consultar(con: sqlite3.Connection, consultas: list[dict], *, cliente: ClienteEducado | None = None, blobs: Path = config.BLOBS,
              raiz: Path = config.RAIZ, registro: Path | None = None) -> dict:
    c = cliente or ClienteEducado(teto=len(consultas) * 3 + 3)
    bs = BlobStore(blobs)
    res = {"consultas": 0, "erros": 0, "materias": 0}
    for q in consultas:
        url = url_senado(q["palavra"]) if q["casa"] == "senado" else url_camara(q["palavra"])
        agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
        r = c.get(url, aba=f"legislativo:{q['casa']}:{q['palavra']}", headers={"Accept": "application/json"})
        res["consultas"] += 1
        itens: list[dict] | None = None
        if r is not None and r.status_code == 200 and r.content:
            try:
                itens = parse_senado(r.content) if q["casa"] == "senado" else parse_camara(r.content)
            except (ValueError, KeyError, TypeError):
                itens = None   # resposta que não é o JSON esperado: fica registrada como erro, com o blob
        if itens is None:
            res["erros"] += 1
            linha = {"casa": q["casa"], "palavra": q["palavra"], "url": url, "fetched_at": agora, "http_status": r.status_code if r is not None else None}
        else:
            p = bs.gravar(r.content, ext="json")
            res["materias"] += _upsert(con, itens, f"{q['casa']}:{q['palavra']}", agora)
            linha = {"casa": q["casa"], "palavra": q["palavra"], "url": url, "fetched_at": agora, "http_status": r.status_code, "sha256": p.stem.split(".")[0],
                     "bytes": len(r.content), "raw_path": caminho_relativo(p, raiz), "materias": len(itens)}
        con.commit()
        if registro is not None:
            registro.parent.mkdir(parents=True, exist_ok=True)
            with registro.open("a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(linha, ensure_ascii=False) + "\n")
    return res


def reingerir_legislativo(con: sqlite3.Connection, registro: Path = REGISTRO, *, raiz: Path = config.RAIZ) -> int:
    """Refaz materia_legislativa a partir do registro e dos blobs (usado por `reconstruir`)."""
    with con:
        con.execute("DELETE FROM materia_legislativa")
        n = 0
        if not registro.exists():
            return 0
        for linha in registro.read_text("utf-8").splitlines():
            if not linha.strip():
                continue
            e = json.loads(linha)
            if not e.get("raw_path"):
                continue
            bruto = resolver_raw(e["raw_path"], raiz).read_bytes()
            itens = parse_senado(bruto) if e["casa"] == "senado" else parse_camara(bruto)
            n += _upsert(con, itens, f"{e['casa']}:{e['palavra']}", e["fetched_at"])
    return n


def exportar_legislativo(con: sqlite3.Connection) -> list[dict]:
    return [dict(r) | {"consultas": json.loads(r["consultas_json"])} for r in con.execute(
        "SELECT casa, codigo, sigla, numero, ano, comissao, identificacao, ementa, autor, data, url, url_api, consultas_json, primeiro_visto_em, ultimo_visto_em "
        "FROM materia_legislativa ORDER BY COALESCE(data, '') DESC, casa, sigla, numero")]
