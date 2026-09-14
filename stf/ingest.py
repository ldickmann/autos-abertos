"""Ingestão: registro de coleta (JSONL) + blobs → projeção SQLite.

Idempotente: ingerir a mesma coleta duas vezes não duplica nada.
Append-only na projeção: linhas de fato nunca são apagadas nem têm o conteúdo
alterado; só `snapshot_last_seen`/`posicao` avançam quando o item reaparece.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .hashing import _h, hash_andamentos, hash_parte
from .parse.andamentos import parse_andamentos
from .parse.casca import parse_casca
from .parse.deslocamentos import parse_deslocamentos
from .parse.informacoes import parse_informacoes
from .parse.partes import parse_partes
from .parse.peticoes import parse_peticoes
from .parse.relacoes import extrair_relacoes
from .resolver import interpretar_resolucao
from . import config
from .store import RegistroColeta, resolver_raw

ABAS_ANDAMENTO = {"decisoes": "e_decisao", "pautas": "e_pauta", "recursos": "e_recurso"}


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ler_blob(reg: dict) -> bytes:
    p = resolver_raw(reg["raw_path"], config.RAIZ)
    data = p.read_bytes()
    if hashlib.sha256(data).hexdigest() != reg["sha256"]:
        raise RuntimeError(f"blob não confere com o registro: {p}")
    return data


def upsert_processo(con, classe: str, numero: int, incidente: int | None, status: str, *, candidatos=None,
                    url_final=None, snapshot_id=None, resolvido_em=None, profundidade=None) -> None:
    """Uma linha por (classe, número). Nunca rebaixa 'semente'/'resolvido' para outro status."""
    con.execute(
        "INSERT INTO processo (classe, numero, incidente_principal, status, candidatos, url_final, snapshot_id, resolvido_em, profundidade) "
        "VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(classe, numero) DO UPDATE SET "
        "incidente_principal=COALESCE(excluded.incidente_principal, processo.incidente_principal), "
        "status=CASE WHEN processo.status='semente' THEN 'semente' "
        "            WHEN processo.status='resolvido' AND excluded.status <> 'semente' THEN 'resolvido' "
        "            ELSE excluded.status END, "
        "candidatos=COALESCE(excluded.candidatos, processo.candidatos), "
        "url_final=COALESCE(excluded.url_final, processo.url_final), "
        "snapshot_id=COALESCE(excluded.snapshot_id, processo.snapshot_id), "
        "resolvido_em=COALESCE(excluded.resolvido_em, processo.resolvido_em), "
        "profundidade=COALESCE(processo.profundidade, excluded.profundidade)",
        (classe, numero, incidente, status, json.dumps(candidatos) if candidatos else None, url_final, snapshot_id,
         resolvido_em, profundidade),
    )


def _registrar_snapshots(con: sqlite3.Connection, coleta_id: str, registros: list[dict]) -> dict[str, dict]:
    """Insere as linhas de snapshot e devolve {aba: {"id": snapshot_id, "reg": registro}}
    para as abas com HTTP 200. Linhas de resolução (listarProcessos) derivam a tabela `processo`."""
    por_aba: dict[str, dict] = {}
    semente = int(coleta_id.rsplit("-", 1)[-1]) if "-resolucoes-" in coleta_id else None
    for r in registros:
        incidente = r.get("incidente_resolvido") or r["incidente"] or semente
        cur = con.execute(
            "INSERT OR IGNORE INTO snapshot (coleta_id, incidente, aba, url, fetched_at, http_status, "
            "sha256, bytes, raw_path, content_type) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (coleta_id, incidente, r["aba"], r["url"], r["fetched_at"], r["http_status"],
             r["sha256"], r["bytes"], r["raw_path"], r.get("content_type")),
        )
        sid = cur.lastrowid if cur.rowcount else con.execute(
            "SELECT id FROM snapshot WHERE coleta_id=? AND aba=? AND url=? AND fetched_at=?",
            (coleta_id, r["aba"], r["url"], r["fetched_at"])).fetchone()[0]
        if r["aba"] == "resolucao" and r["http_status"] == 200:
            res = interpretar_resolucao(r["classe"], int(r["numero"]), r.get("url_final") or r["url"], _ler_blob(r))
            upsert_processo(con, res.classe, res.numero, res.incidentes[0] if res.status == "resolvido" else None,
                            res.status, candidatos=res.incidentes if res.status == "multiplos" else None,
                            url_final=res.url_final, snapshot_id=sid, resolvido_em=r["fetched_at"],
                            profundidade=r.get("profundidade"))
        elif r["aba"] == "resolucao":
            upsert_processo(con, r["classe"], int(r["numero"]), None, "erro", url_final=r.get("url_final"),
                            snapshot_id=sid, resolvido_em=r["fetched_at"], profundidade=r.get("profundidade"))
        if r["http_status"] == 200 and r["aba"] not in por_aba:
            por_aba[r["aba"]] = {"id": sid, "reg": r}
    return por_aba


def _projetar_incidente(con, incidente: int, snap_casca: dict, snap_info: dict | None) -> None:
    casca = parse_casca(_ler_blob(snap_casca["reg"]))
    if casca.incidente != incidente:
        raise RuntimeError(f"casca do incidente {casca.incidente} registrada como {incidente}")
    info = parse_informacoes(_ler_blob(snap_info["reg"])) if snap_info else None
    campos = {
        "classe": casca.classe, "numero_processo": casca.numero_processo, "numero_unico": casca.numero_unico,
        "relator": casca.relator, "relator_ultimo_incidente": casca.relator_ultimo_incidente,
        "ultimo_incidente": casca.ultimo_incidente, "publicidade": casca.publicidade,
        "natureza": casca.natureza, "reu_preso": int(casca.reu_preso), "tipo_tramitacao": casca.tipo_tramitacao,
        "meio": casca.meio,
        "assuntos": json.dumps(info.assuntos if info else [], ensure_ascii=False),
        "data_protocolo": info.data_protocolo if info else None,
        "orgao_origem": info.orgao_origem if info else None,
        "origem": info.origem if info else None,
        "numeros_origem": json.dumps(info.numeros_origem if info else [], ensure_ascii=False),
        "descricao_procedencia": info.descricao_procedencia if info else None,
    }
    sid = snap_casca["id"]
    visto = snap_casca["reg"]["fetched_at"]
    existente = con.execute("SELECT numero FROM incidente WHERE numero=?", (incidente,)).fetchone()
    if existente is None:
        cols = ", ".join(campos)
        con.execute(
            f"INSERT INTO incidente (numero, {cols}, primeiro_visto_em, ultimo_visto_em, "
            f"snapshot_first_seen, snapshot_last_seen) VALUES (?, {','.join('?' * len(campos))}, ?, ?, ?, ?)",
            (incidente, *campos.values(), visto, visto, sid, sid),
        )
    else:
        sets = ", ".join(f"{k}=?" for k in campos)
        con.execute(
            f"UPDATE incidente SET {sets}, ultimo_visto_em=MAX(ultimo_visto_em, ?), snapshot_last_seen=? "
            f"WHERE numero=?",
            (*campos.values(), visto, sid, incidente),
        )
    versao_hash = _h("incidente", incidente, campos)
    con.execute(
        "INSERT OR IGNORE INTO incidente_versao (incidente, snapshot_id, hash, campos) VALUES (?,?,?,?)",
        (incidente, sid, versao_hash, json.dumps(campos, ensure_ascii=False)),
    )
    # todo incidente coletado é um processo resolvido (a casca diz classe e número);
    # se existe um registro de resoluções cujo id termina em "-resolucoes-<incidente>", ele foi semente de expansão
    upsert_processo(con, casca.classe, casca.numero_processo, incidente, "resolvido", resolvido_em=visto)
    if con.execute("SELECT 1 FROM coleta WHERE id LIKE ?", (f"%-resolucoes-{incidente}",)).fetchone():
        con.execute("UPDATE processo SET status='semente', profundidade=0 WHERE incidente_principal=?", (incidente,))


def _upsert_visto(con, tabela: str, hash_natural: str, campos: dict, sid: int, *, avancar: bool = True) -> int:
    """Insere se novo (first=last=sid); se existe e `avancar`, avança last_seen e posicao.
    `avancar=False` é usado pelas abas-subconjunto (decisões, pautas, recursos): elas só
    marcam flags; a proveniência canônica do andamento é o snapshot da aba Andamentos."""
    row = con.execute(f"SELECT id FROM {tabela} WHERE hash_natural=?", (hash_natural,)).fetchone()
    if row:
        if avancar:
            con.execute(
                f"UPDATE {tabela} SET snapshot_last_seen=MAX(snapshot_last_seen, ?), posicao=? WHERE id=?",
                (sid, campos["posicao"], row["id"]),
            )
        return row["id"]
    cols = ", ".join(campos)
    cur = con.execute(
        f"INSERT INTO {tabela} (hash_natural, {cols}, snapshot_first_seen, snapshot_last_seen) "
        f"VALUES (?, {','.join('?' * len(campos))}, ?, ?)",
        (hash_natural, *campos.values(), sid, sid),
    )
    return cur.lastrowid


def _projetar_partes(con, incidente: int, snap: dict) -> None:
    for p in parse_partes(_ler_blob(snap["reg"])):
        _upsert_visto(con, "parte", hash_parte(incidente, p), {
            "incidente": incidente, "papel_portal": p.papel_portal, "papel": p.papel, "nome": p.nome,
            "oab": json.dumps(p.oab), "bloco": p.bloco, "posicao": p.posicao,
            "e_placeholder": int(p.e_placeholder),
        }, snap["id"])


def _projetar_andamentos(con, incidente: int, snap: dict, aba: str) -> dict[str, int]:
    """Projeta uma aba com estrutura de andamento. Devolve {hash: andamento_id}."""
    itens = parse_andamentos(_ler_blob(snap["reg"]))
    hashes = hash_andamentos(incidente, itens)
    ids: dict[str, int] = {}
    visto = snap["reg"]["fetched_at"]
    for a, h in zip(itens, hashes):
        aid = _upsert_visto(con, "andamento", h, {
            "incidente": incidente, "data": a.data, "tipo": a.tipo, "descricao": a.descricao,
            "posicao": a.posicao, "aba_origem": aba,
        }, snap["id"], avancar=(aba == "andamentos"))
        ids[h] = aid
        if aba in ABAS_ANDAMENTO:
            con.execute(f"UPDATE andamento SET {ABAS_ANDAMENTO[aba]}=1 WHERE id=?", (aid,))
        con.execute(
            "INSERT INTO tipo_andamento (nome, explicacao_portal, primeiro_visto_em) VALUES (?,?,?) "
            "ON CONFLICT(nome) DO UPDATE SET explicacao_portal=COALESCE(tipo_andamento.explicacao_portal, excluded.explicacao_portal)",
            (a.tipo, a.explicacao_portal, visto),
        )
        for d in a.documentos:
            con.execute(
                "INSERT OR IGNORE INTO documento (incidente, endpoint, id_portal, formato, url, titulo, snapshot_first_seen) "
                "VALUES (?,?,?,?,?,?,?)",
                (incidente, d.endpoint, d.id_portal, d.formato, d.url, d.rotulo, snap["id"]),
            )
            did = con.execute("SELECT id FROM documento WHERE endpoint=? AND id_portal=?",
                              (d.endpoint, d.id_portal)).fetchone()["id"]
            con.execute("INSERT OR IGNORE INTO andamento_documento (andamento_id, documento_id, rotulo) VALUES (?,?,?)",
                        (aid, did, d.rotulo))
    if aba == "andamentos":
        for r in extrair_relacoes(itens):
            fonte = ids[hashes[r.posicao_andamento]]
            con.execute(
                "INSERT OR IGNORE INTO processo_relacao (incidente_origem, classe_destino, numero_destino, tipo, "
                "fonte_andamento_id, snapshot_first_seen) VALUES (?,?,?,?,?,?)",
                (incidente, r.classe, r.numero, r.tipo, fonte, snap["id"]),
            )
    return ids


def _projetar_peticoes(con, incidente: int, snap: dict) -> None:
    for p in parse_peticoes(_ler_blob(snap["reg"])):
        h = _h("peticao", incidente, p.numero, p.data_peticionamento, p.recebido_em, p.recebido_por)
        _upsert_visto(con, "peticao", h, {
            "incidente": incidente, "numero": p.numero, "data_peticionamento": p.data_peticionamento,
            "recebido_em": p.recebido_em, "recebido_por": p.recebido_por, "posicao": p.posicao,
        }, snap["id"])


def _projetar_deslocamentos(con, incidente: int, snap: dict) -> None:
    for d in parse_deslocamentos(_ler_blob(snap["reg"])):
        h = _h("deslocamento", incidente, d.destino, d.enviado_por, d.data_envio, d.guia, d.recebido_em)
        _upsert_visto(con, "deslocamento", h, {
            "incidente": incidente, "destino": d.destino, "enviado_por": d.enviado_por,
            "data_envio": d.data_envio, "guia": d.guia, "recebido_em": d.recebido_em, "posicao": d.posicao,
        }, snap["id"])


def ingerir_coleta(con: sqlite3.Connection, registro_path: Path) -> dict:
    """Ingere uma coleta. Devolve um resumo com contagens por tabela."""
    registros = RegistroColeta.ler(registro_path)
    if not registros:
        raise ValueError(f"registro vazio: {registro_path}")
    coleta_id = registros[0]["coleta_id"]
    if "-resolucoes-" in coleta_id:
        # registro de resoluções de uma expansão: o incidente é a semente, que está no id
        incidente = int(coleta_id.rsplit("-", 1)[-1])
    else:
        incidentes = {r["incidente"] for r in registros}
        if len(incidentes) != 1:
            raise ValueError(f"registro com mais de um incidente: {incidentes}")
        incidente = incidentes.pop()

    with con:
        con.execute("INSERT OR IGNORE INTO coleta (id, incidente, registro_path, ingerida_em) VALUES (?,?,?,?)",
                    (coleta_id, incidente, str(registro_path), _agora()))
        snaps = _registrar_snapshots(con, coleta_id, registros)
        if "-resolucoes-" in coleta_id:
            con.execute("UPDATE processo SET status='semente', profundidade=0 WHERE incidente_principal=?", (incidente,))

        if "casca" in snaps:
            _projetar_incidente(con, incidente, snaps["casca"], snaps.get("informacoes"))
        if "partes" in snaps:
            _projetar_partes(con, incidente, snaps["partes"])
        # andamentos primeiro; decisões/pautas/recursos são subconjuntos e só marcam flags
        for aba in ("andamentos", "decisoes", "pautas", "recursos"):
            if aba in snaps:
                _projetar_andamentos(con, incidente, snaps[aba], aba)
        if "peticoes" in snaps:
            _projetar_peticoes(con, incidente, snaps["peticoes"])
        if "deslocamentos" in snaps:
            _projetar_deslocamentos(con, incidente, snaps["deslocamentos"])

    return resumo(con, incidente)


def resumo(con: sqlite3.Connection, incidente: int | None = None) -> dict:
    where = f" WHERE incidente={int(incidente)}" if incidente else ""
    out = {}
    for t in ("coleta", "snapshot", "parte", "andamento", "documento", "peticao", "deslocamento", "processo_relacao"):
        col = "incidente_origem" if t == "processo_relacao" else "incidente"
        w = where.replace("incidente=", f"{col}=") if where else ""
        out[t] = con.execute(f"SELECT COUNT(*) FROM {t}{w}").fetchone()[0]
    out["incidente"] = con.execute("SELECT COUNT(*) FROM incidente").fetchone()[0]
    return out
