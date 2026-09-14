"""Expansão do grafo a partir de um incidente-semente.

Algoritmo (busca em largura, uma sessão HTTP, sem paralelismo):
1. garante que a semente está coletada e ingerida (reaproveita coleta recente);
2. lê as relações (classe, número) extraídas dos andamentos do incidente;
3. resolve cada processo ainda não resolvido (1 requisição: listarProcessos.asp → 302);
4. se a profundidade permite, coleta o incidente resolvido por completo (11 requisições)
   e ingere; seus próprios relacionados entram na fila com profundidade + 1;
5. o que fica além da profundidade é registrado como fronteira (resolvido, não coletado).

O teto de requisições do ClienteEducado interrompe a expansão de forma limpa: tudo que
foi ingerido fica íntegro e a próxima execução retoma do ponto em que parou, porque
resolução e coleta são registradas no banco assim que acontecem.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from . import config
from .coleta import ClienteEducado, TetoAtingido, coletar_incidente
from .ingest import ingerir_coleta, upsert_processo
from .resolver import interpretar_resolucao, url_resolucao
from .store import BlobStore, RegistroColeta, caminho_relativo, sha256

REAPROVEITAR_COLETA_DE_ATE = timedelta(hours=12)


@dataclass
class RelatorioExpansao:
    semente: int
    profundidade: int
    coletados: int = 0
    resolvidos: int = 0
    nao_encontrados: int = 0
    multiplos: int = 0
    fronteira: list[tuple[str, int, int]] = field(default_factory=list)   # (classe, numero, incidente) resolvidos e não coletados
    pendentes: list[tuple[str, int]] = field(default_factory=list)        # não processados por teto
    interrompido_por_teto: bool = False
    requisicoes: int = 0


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _coleta_recente(con, incidente: int) -> bool:
    row = con.execute(
        "SELECT MAX(s.fetched_at) FROM snapshot s WHERE s.incidente=? AND s.aba='casca' AND s.http_status=200",
        (incidente,)).fetchone()
    if not row or not row[0]:
        return False
    return _agora() - datetime.fromisoformat(row[0]) < REAPROVEITAR_COLETA_DE_ATE


def _registrar_processo_da_semente(con, incidente: int, profundidade: int) -> None:
    inc = con.execute("SELECT classe, numero_processo FROM incidente WHERE numero=?", (incidente,)).fetchone()
    if inc is None:
        return
    if profundidade == 0:
        con.execute("UPDATE processo SET status='semente', profundidade=0 WHERE classe=? AND numero=?",
                    (inc["classe"], inc["numero_processo"]))
    else:
        upsert_processo(con, inc["classe"], inc["numero_processo"], incidente, "resolvido", profundidade=profundidade)
    con.commit()


def _relacionados(con, incidente: int) -> list[tuple[str, int]]:
    rows = con.execute(
        "SELECT DISTINCT classe_destino, numero_destino FROM processo_relacao WHERE incidente_origem=? "
        "ORDER BY classe_destino, numero_destino", (incidente,)).fetchall()
    return [(r["classe_destino"], r["numero_destino"]) for r in rows]


def _resolver(con, cliente: ClienteEducado, bs: BlobStore, reg: RegistroColeta, classe: str, numero: int,
              profundidade: int, log: Callable[[str], None]) -> dict | None:
    url = url_resolucao(classe, numero)
    r = cliente.get(url, aba="resolucao")
    entrada = cliente.log[-1]
    semente = int(reg.coleta_id.rsplit("-", 1)[-1])
    if r is None:
        upsert_processo(con, classe, numero, None, "erro", resolvido_em=_agora().isoformat(), profundidade=profundidade)
        con.commit()
        log(f"  {classe} {numero}: ERRO {entrada.get('erro')}")
        return None
    p = bs.gravar(r.content, ext="html")
    res = interpretar_resolucao(classe, numero, str(r.url), r.content)
    linha = {"incidente": semente, "aba": "resolucao", "url": url, "url_final": str(r.url), "fetched_at": entrada["iniciada_em"],
             "http_status": r.status_code, "sha256": sha256(r.content), "bytes": len(r.content),
             "raw_path": caminho_relativo(p, config.RAIZ), "content_type": r.headers.get("content-type"),
             "user_agent": config.USER_AGENT, "redirects": entrada.get("redirects", []),
             "classe": classe, "numero": numero, "profundidade": profundidade,
             "incidente_resolvido": res.incidentes[0] if res.status == "resolvido" else None}
    reg.anotar(linha)
    cur = con.execute(
        "INSERT INTO snapshot (coleta_id, incidente, aba, url, fetched_at, http_status, sha256, bytes, raw_path, content_type) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (reg.coleta_id, linha["incidente_resolvido"] or semente, "resolucao", url, entrada["iniciada_em"],
         r.status_code, sha256(r.content), len(r.content), caminho_relativo(p, config.RAIZ), r.headers.get("content-type")))
    upsert_processo(con, classe, numero, linha["incidente_resolvido"], res.status,
                    candidatos=res.incidentes if res.status == "multiplos" else None, url_final=res.url_final,
                    snapshot_id=cur.lastrowid, resolvido_em=entrada["iniciada_em"], profundidade=profundidade)
    con.commit()
    log(f"  {classe} {numero}: {res.status} {res.incidentes}")
    return {"status": res.status, "incidentes": res.incidentes}


def expandir(con, semente: int, *, profundidade: int = 1, cliente: ClienteEducado | None = None,
             blobs: Path = config.BLOBS, coletas: Path = config.COLETAS,
             log: Callable[[str], None] = print) -> RelatorioExpansao:
    c = cliente or ClienteEducado(teto=config.TETO_REQUISICOES_POR_EXPANSAO)
    bs = BlobStore(blobs)
    rel = RelatorioExpansao(semente=semente, profundidade=profundidade)
    reg_resolucoes = RegistroColeta(coletas, f"{_agora().strftime('%Y%m%dT%H%M%SZ')}-resolucoes-{semente}")
    con.execute("INSERT OR IGNORE INTO coleta (id, incidente, registro_path, ingerida_em) VALUES (?,?,?,?)",
                (reg_resolucoes.coleta_id, semente, str(reg_resolucoes.caminho), _agora().isoformat()))
    con.commit()

    def coletar_e_ingerir(incidente: int) -> None:
        if _coleta_recente(con, incidente):
            log(f"incidente {incidente}: coleta recente reaproveitada")
            return
        registro = coletar_incidente(incidente, blobs=blobs, coletas=coletas, cliente=c, log=log)
        ingerir_coleta(con, registro)
        rel.coletados += 1

    fila: deque[tuple[int, int]] = deque([(semente, 0)])
    vistos: set[int] = {semente}
    try:
        while fila:
            incidente, prof = fila.popleft()
            coletar_e_ingerir(incidente)
            _registrar_processo_da_semente(con, incidente, prof)
            for classe, numero in _relacionados(con, incidente):
                row = con.execute("SELECT incidente_principal, status FROM processo WHERE classe=? AND numero=?",
                                  (classe, numero)).fetchone()
                if row is None or row["status"] == "erro":
                    res = _resolver(con, c, bs, reg_resolucoes, classe, numero, prof + 1, log)
                    if res is None:
                        rel.pendentes.append((classe, numero))
                        continue
                    if res["status"] == "resolvido":
                        rel.resolvidos += 1
                    elif res["status"] == "multiplos":
                        rel.multiplos += 1
                    else:
                        rel.nao_encontrados += 1
                    alvo = res["incidentes"][0] if res["status"] == "resolvido" else None
                else:
                    alvo = row["incidente_principal"]
                if alvo is None or alvo in vistos:
                    continue
                vistos.add(alvo)
                if prof + 1 <= profundidade:
                    fila.append((alvo, prof + 1))
                else:
                    rel.fronteira.append((classe, numero, alvo))
    except TetoAtingido as e:
        rel.interrompido_por_teto = True
        log(f"teto: {e}")
        rel.pendentes.extend((r["classe"], r["numero"]) for r in con.execute(
            "SELECT p.classe, p.numero FROM processo p LEFT JOIN incidente i ON i.numero=p.incidente_principal "
            "WHERE p.status='resolvido' AND i.numero IS NULL"))
        rel.pendentes.extend((cl, nu) for (inc, _) in fila for (cl, nu) in _relacionados(con, inc))
    rel.requisicoes = c.count
    return rel
