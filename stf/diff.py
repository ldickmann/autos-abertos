"""Diff entre duas coletas do mesmo incidente.

Trabalha direto nos blobs (a fonte), sem banco. Compara por hash natural em cada
aba e por campo no cabeçalho. A saída lista o que entrou, o que saiu e o que
mudou, sem interpretar.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from .hashing import _h, hash_andamentos, hash_parte
from .parse.andamentos import parse_andamentos
from .parse.casca import parse_casca
from .parse.deslocamentos import parse_deslocamentos
from .parse.informacoes import parse_informacoes
from .parse.partes import parse_partes
from .parse.peticoes import parse_peticoes
from . import config
from .store import RegistroColeta, resolver_raw

ABAS = ["casca", "informacoes", "partes", "andamentos", "decisoes", "sessao",
        "deslocamentos", "peticoes", "recursos", "pautas"]


@dataclass
class DiffLista:
    incluidos: list[Any] = field(default_factory=list)
    removidos: list[Any] = field(default_factory=list)

    @property
    def vazio(self) -> bool:
        return not self.incluidos and not self.removidos


@dataclass
class DiffColetas:
    coleta_a: str
    coleta_b: str
    incidente: int
    abas_identicas: list[str] = field(default_factory=list)
    abas_so_em_a: list[str] = field(default_factory=list)
    abas_so_em_b: list[str] = field(default_factory=list)
    incidente_campos_alterados: dict[str, tuple[Any, Any]] = field(default_factory=dict)
    partes: DiffLista = field(default_factory=DiffLista)
    andamentos: DiffLista = field(default_factory=DiffLista)
    peticoes: DiffLista = field(default_factory=DiffLista)
    deslocamentos: DiffLista = field(default_factory=DiffLista)

    @property
    def vazio(self) -> bool:
        return (not self.incidente_campos_alterados and not self.abas_so_em_a and not self.abas_so_em_b
                and all(d.vazio for d in (self.partes, self.andamentos, self.peticoes, self.deslocamentos)))


def _carregar(registro_path: Path) -> tuple[str, int, dict[str, dict]]:
    regs = RegistroColeta.ler(registro_path)
    por_aba = {}
    for r in regs:
        if r["http_status"] == 200 and r["aba"] not in por_aba:
            por_aba[r["aba"]] = r
    return regs[0]["coleta_id"], regs[0]["incidente"], por_aba


def _blob(reg: dict) -> bytes:
    return resolver_raw(reg["raw_path"], config.RAIZ).read_bytes()


def _diff_por_hash(itens_a: list, hashes_a: list[str], itens_b: list, hashes_b: list[str]) -> DiffLista:
    ha, hb = dict(zip(hashes_a, itens_a)), dict(zip(hashes_b, itens_b))
    return DiffLista(
        incluidos=[hb[h] for h in hashes_b if h not in ha],
        removidos=[ha[h] for h in hashes_a if h not in hb],
    )


def _campos_cabecalho(por_aba: dict[str, dict]) -> dict:
    out: dict = {}
    if "casca" in por_aba:
        c = parse_casca(_blob(por_aba["casca"]))
        out.update({f.name: getattr(c, f.name) for f in fields(c) if f.name != "abas"})
    if "informacoes" in por_aba:
        i = parse_informacoes(_blob(por_aba["informacoes"]))
        out.update({f.name: getattr(i, f.name) for f in fields(i)})
    return out


def diff_coletas(registro_a: Path, registro_b: Path) -> DiffColetas:
    id_a, inc_a, abas_a = _carregar(registro_a)
    id_b, inc_b, abas_b = _carregar(registro_b)
    if inc_a != inc_b:
        raise ValueError(f"coletas de incidentes diferentes: {inc_a} vs {inc_b}")
    d = DiffColetas(coleta_a=id_a, coleta_b=id_b, incidente=inc_a)

    for aba in ABAS:
        if aba in abas_a and aba in abas_b:
            if abas_a[aba]["sha256"] == abas_b[aba]["sha256"]:
                d.abas_identicas.append(aba)
        elif aba in abas_a:
            d.abas_so_em_a.append(aba)
        elif aba in abas_b:
            d.abas_so_em_b.append(aba)

    ca, cb = _campos_cabecalho(abas_a), _campos_cabecalho(abas_b)
    d.incidente_campos_alterados = {k: (ca.get(k), cb.get(k)) for k in sorted(set(ca) | set(cb)) if ca.get(k) != cb.get(k)}

    if "partes" in abas_a and "partes" in abas_b:
        pa, pb = parse_partes(_blob(abas_a["partes"])), parse_partes(_blob(abas_b["partes"]))
        d.partes = _diff_por_hash(pa, [hash_parte(inc_a, p) for p in pa], pb, [hash_parte(inc_a, p) for p in pb])
    if "andamentos" in abas_a and "andamentos" in abas_b:
        aa, ab = parse_andamentos(_blob(abas_a["andamentos"])), parse_andamentos(_blob(abas_b["andamentos"]))
        d.andamentos = _diff_por_hash(aa, hash_andamentos(inc_a, aa), ab, hash_andamentos(inc_a, ab))
    if "peticoes" in abas_a and "peticoes" in abas_b:
        pa, pb = parse_peticoes(_blob(abas_a["peticoes"])), parse_peticoes(_blob(abas_b["peticoes"]))
        hp = lambda p: _h("peticao", inc_a, p.numero, p.data_peticionamento, p.recebido_em, p.recebido_por)
        d.peticoes = _diff_por_hash(pa, [hp(p) for p in pa], pb, [hp(p) for p in pb])
    if "deslocamentos" in abas_a and "deslocamentos" in abas_b:
        da, db_ = parse_deslocamentos(_blob(abas_a["deslocamentos"])), parse_deslocamentos(_blob(abas_b["deslocamentos"]))
        hd = lambda x: _h("deslocamento", inc_a, x.destino, x.enviado_por, x.data_envio, x.guia, x.recebido_em)
        d.deslocamentos = _diff_por_hash(da, [hd(x) for x in da], db_, [hd(x) for x in db_])
    return d


def _plural(n: int, s: str, p: str) -> str:
    return f"{n} {s if n == 1 else p}"


def formatar_diff(d: DiffColetas) -> str:
    linhas = [f"diff {d.coleta_a} → {d.coleta_b}  (incidente {d.incidente})"]
    if d.vazio:
        linhas.append("  sem diferenças")
    if d.abas_identicas:
        linhas.append(f"  abas com bytes idênticos: {', '.join(d.abas_identicas)}")
    if d.abas_so_em_a:
        linhas.append(f"  abas só em {d.coleta_a}: {', '.join(d.abas_so_em_a)}")
    if d.abas_so_em_b:
        linhas.append(f"  abas só em {d.coleta_b}: {', '.join(d.abas_so_em_b)}")
    for k, (a, b) in d.incidente_campos_alterados.items():
        linhas.append(f"  cabeçalho.{k}: {a!r} → {b!r}")

    def bloco(nome_s: str, nome_p: str, dl: DiffLista, fmt) -> None:
        if dl.incluidos:
            linhas.append(f"  +{_plural(len(dl.incluidos), nome_s, nome_p)}")
            linhas.extend(f"    + {fmt(x)}" for x in dl.incluidos)
        if dl.removidos:
            linhas.append(f"  -{_plural(len(dl.removidos), nome_s, nome_p)}")
            linhas.extend(f"    - {fmt(x)}" for x in dl.removidos)

    bloco("parte", "partes", d.partes, lambda p: f"{p.papel_portal} {p.nome}" + (f" ({', '.join(p.oab)})" if p.oab else ""))
    bloco("andamento", "andamentos", d.andamentos,
          lambda a: f"{a.data} | {a.tipo} | {a.descricao[:100]}" + (f" [{len(a.documentos)} doc]" if a.documentos else ""))
    bloco("petição", "petições", d.peticoes, lambda p: f"{p.numero} | peticionada {p.data_peticionamento} | recebida {p.recebido_em}")
    bloco("deslocamento", "deslocamentos", d.deslocamentos,
          lambda x: f"{x.data_envio} | {x.enviado_por} → {x.destino} | guia {x.guia} | recebido {x.recebido_em}")
    return "\n".join(linhas)
