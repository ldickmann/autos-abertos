"""Vigilância de mudanças no portal: recoleta cada processo, compara com a cópia anterior e registra o que mudou.

O objetivo é que remoções, alterações e sigilos supervenientes fiquem visíveis, com as datas das duas cópias.
Tudo é append-only: a coleta nova vira mais um registro JSONL; o CHANGELOG-PORTAL.md só cresce; `mudancas.json`
é a projeção para o site. Nada é interpretado: o que se registra é "sumiu", "apareceu", "mudou de X para Y".
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import config
from .coleta import ClienteEducado, coletar_incidente
from .diff import diff_coletas
from .ingest import ingerir_coleta

_RE_REG = re.compile(r"^(\d{8}T\d{6}Z)-(\d+)\.jsonl$")


def registros_por_incidente(coletas: Path = config.COLETAS) -> dict[int, list[Path]]:
    """Registros de coleta completa (um incidente por arquivo), em ordem cronológica."""
    out: dict[int, list[Path]] = {}
    for p in sorted(Path(coletas).glob("*.jsonl")):
        m = _RE_REG.match(p.name)
        if m:
            out.setdefault(int(m.group(2)), []).append(p)
    return out


def _resumo_lista(nome: str, d, rotulo: Callable) -> list[dict]:
    itens = []
    for x in d.removidos:
        itens.append({"o_que": nome, "mudanca": "sumiu", "item": rotulo(x)})
    for x in d.incluidos:
        itens.append({"o_que": nome, "mudanca": "apareceu", "item": rotulo(x)})
    return itens


def comparar(registro_antes: Path, registro_depois: Path) -> dict:
    d = diff_coletas(registro_antes, registro_depois)
    mudancas: list[dict] = []
    for campo, (a, b) in d.incidente_campos_alterados.items():
        mudancas.append({"o_que": "cabeçalho", "mudanca": "mudou", "item": f"{campo}: {a!r} → {b!r}"})
    for aba in d.abas_so_em_a:
        mudancas.append({"o_que": "aba do portal", "mudanca": "sumiu", "item": aba})
    for aba in d.abas_so_em_b:
        mudancas.append({"o_que": "aba do portal", "mudanca": "apareceu", "item": aba})
    mudancas += _resumo_lista("andamento", d.andamentos, lambda a: f"{a.data} {a.tipo}" + (f" — {a.descricao[:120]}" if getattr(a, 'descricao', '') else ""))
    mudancas += _resumo_lista("parte", d.partes, lambda p: f"{p.papel_portal} {p.nome}")
    mudancas += _resumo_lista("petição", d.peticoes, lambda p: f"{p.numero} ({p.data_peticionamento})")
    mudancas += _resumo_lista("deslocamento", d.deslocamentos, lambda x: f"{x.data_envio} → {x.destino}")
    return {"incidente": d.incidente, "antes": d.coleta_a, "depois": d.coleta_b, "abas_identicas": d.abas_identicas,
            "mudancas": mudancas, "resumo": {"sumiu": sum(m["mudanca"] == "sumiu" for m in mudancas),
                                              "apareceu": sum(m["mudanca"] == "apareceu" for m in mudancas),
                                              "mudou": sum(m["mudanca"] == "mudou" for m in mudancas)}}


def vigiar(con: sqlite3.Connection, *, incidentes: list[int] | None = None, cliente: ClienteEducado | None = None,
           coletas: Path = config.COLETAS, blobs: Path = config.BLOBS, log: Callable[[str], None] = print) -> list[dict]:
    """Recoleta cada incidente (um por vez, educadamente), ingere e compara com a coleta completa anterior."""
    alvos = incidentes or [r["incidente_principal"] for r in con.execute(
        "SELECT incidente_principal FROM processo WHERE incidente_principal IN (SELECT numero FROM incidente) ORDER BY profundidade, classe, numero")]
    c = cliente or ClienteEducado(teto=config.TETO_REQUISICOES_POR_COLETA * (len(alvos) + 1))
    relatorio = []
    for inc in alvos:
        anteriores = registros_por_incidente(coletas).get(inc, [])
        log(f"[{inc}] recoletando ({len(anteriores)} coleta(s) anterior(es))")
        novo = coletar_incidente(inc, blobs=blobs, coletas=coletas, cliente=c, log=lambda s: None)
        ingerir_coleta(con, novo)
        if anteriores:
            r = comparar(anteriores[-1], novo)
        else:
            r = {"incidente": inc, "antes": None, "depois": novo.stem, "abas_identicas": [], "mudancas": [], "resumo": {"sumiu": 0, "apareceu": 0, "mudou": 0}}
        rot = con.execute("SELECT classe || ' ' || numero FROM processo WHERE incidente_principal=?", (inc,)).fetchone()
        r["processo"] = rot[0] if rot else str(inc)
        relatorio.append(r)
        log(f"[{inc}] {r['processo']}: {r['resumo']}")
    return relatorio


def registrar(relatorio: list[dict], *, changelog: Path = config.RAIZ / "CHANGELOG-PORTAL.md",
              mudancas_json: Path = config.RAIZ / "web" / "public" / "data" / "mudancas.json") -> None:
    """Acrescenta uma seção datada ao CHANGELOG-PORTAL.md (append-only) e atualiza mudancas.json com todo o histórico."""
    agora = datetime.now(timezone.utc).isoformat(timespec="minutes")
    linhas = [f"## {agora}", ""]
    total = sum(sum(r["resumo"].values()) for r in relatorio)
    linhas.append(f"{len(relatorio)} processo(s) recoletado(s); {total} mudança(s) em relação à cópia anterior." if total else
                  f"{len(relatorio)} processo(s) recoletado(s); nenhuma mudança em relação à cópia anterior.")
    linhas.append("")
    for r in relatorio:
        if not r["mudancas"]:
            linhas.append(f"- {r['processo']} (incidente {r['incidente']}): sem mudanças. Cópias comparadas: `{r['antes']}` → `{r['depois']}`.")
            continue
        linhas.append(f"- {r['processo']} (incidente {r['incidente']}): {r['resumo']['apareceu']} apareceu, {r['resumo']['sumiu']} sumiu, {r['resumo']['mudou']} mudou. Cópias: `{r['antes']}` → `{r['depois']}`.")
        for m in r["mudancas"]:
            linhas.append(f"  - {m['o_que']} {m['mudanca']}: {m['item']}")
    linhas.append("")
    cabecalho = ("# O que mudou no portal do STF\n\nRegistro append-only das recoletas (`python -m stf vigiar`). Cada seção compara a cópia nova "
                 "de cada processo com a cópia completa anterior. \"Sumiu\" quer dizer que um item que o portal mostrava deixou de aparecer; "
                 "\"apareceu\" é um item novo; \"mudou\" é um campo do cabeçalho com valor diferente. Nada aqui é interpretado.\n\n")
    if changelog.exists():
        changelog.write_text(changelog.read_text("utf-8").rstrip("\n") + "\n\n" + "\n".join(linhas), "utf-8")
    else:
        changelog.write_text(cabecalho + "\n".join(linhas), "utf-8")
    historico = []
    if mudancas_json.exists():
        try:
            historico = json.loads(mudancas_json.read_text("utf-8"))
        except ValueError:
            historico = []
    historico.append({"em": agora, "processos": relatorio})
    mudancas_json.parent.mkdir(parents=True, exist_ok=True)
    mudancas_json.write_text(json.dumps(historico, ensure_ascii=False, indent=1, default=lambda o: asdict(o) if hasattr(o, "__dataclass_fields__") else str(o)), "utf-8")
