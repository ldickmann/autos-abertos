"""Pedidos e resultados por decisão (extensão da Fase 4).

Mesmo regime da extração de asserções: prompt versionado (`prompts/decisao_v1.md`), schema Pydantic, validação
determinística (página existe; `trecho_fonte` literal ≤300 caracteres presente na página), resposta bruta guardada
como blob, cache por (documento, sha256, prompt_version, modelo) na tabela `extracao`. Itens válidos vão para
`decisao_item`; o que não passa é descartado e fica registrado em `extracao.descartadas_json`.

Só entram documentos com função decisória (decisão, acórdão, voto, despacho marcado como decisão pelo portal).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal

from pydantic import BaseModel, Field, ValidationError

from . import config
from .funcoes import funcao_de
from .semantica import MAX_TRECHO, ClienteLLM, _norm, montar_entrada
from .store import BlobStore, caminho_relativo

PROMPT_PATH = Path(__file__).parent / "prompts" / "decisao_v1.md"
PROMPT_TEXTO = PROMPT_PATH.read_text("utf-8")
PROMPT_VERSION = f"{PROMPT_PATH.stem}-{hashlib.sha256(PROMPT_TEXTO.encode('utf-8')).hexdigest()[:12]}"

Resultado = Literal["deferido", "indeferido", "parcialmente_deferido", "homologado", "referendado", "negado_seguimento",
                    "nao_conhecido", "prejudicado", "determinado_de_oficio", "outro"]
ROTULO_RESULTADO: dict[str, str] = {
    "deferido": "deferido (aceito)", "indeferido": "indeferido (negado)", "parcialmente_deferido": "deferido em parte",
    "homologado": "homologado", "referendado": "referendado pelo colegiado", "negado_seguimento": "seguimento negado",
    "nao_conhecido": "não conhecido", "prejudicado": "prejudicado (perdeu o objeto)", "determinado_de_oficio": "determinado de ofício",
    "outro": "outro",
}
FUNCOES_DECISORIAS = {"decisao", "acordao", "voto"}


class PedidoDecidido(BaseModel):
    pedido: str = Field(min_length=3)
    quem_pediu: str | None = None
    resultado: Resultado
    decisao: str = Field(min_length=3)
    quem_decidiu: str = Field(min_length=2)
    data: str | None = None
    pagina: int = Field(ge=1)
    trecho_fonte: str = Field(min_length=3)
    condicoes: list[str] = Field(default_factory=list)


class ExtracaoDecisao(BaseModel):
    itens: list[PedidoDecidido]
    observacoes: str | None = None


SCHEMA_SAIDA = ExtracaoDecisao.model_json_schema()


def documentos_decisorios(con: sqlite3.Connection) -> list[sqlite3.Row]:
    """Documentos com texto cuja função é decisória (título) ou cujo andamento o portal marca como decisão."""
    out = []
    for d in con.execute(
            "SELECT d.id, d.sha256, d.incidente, d.titulo, "
            "EXISTS (SELECT 1 FROM andamento_documento ad JOIN andamento a ON a.id=ad.andamento_id WHERE ad.documento_id=d.id AND a.e_decisao=1) AS e_decisao "
            "FROM documento d WHERE d.sha256 IS NOT NULL AND d.tem_camada_texto=1 "
            "AND EXISTS (SELECT 1 FROM documento_pagina p WHERE p.documento_id=d.id) ORDER BY d.id"):
        if funcao_de(d["titulo"], bool(d["e_decisao"])) in FUNCOES_DECISORIAS:
            out.append(d)
    return out


def preparar_entradas(con: sqlite3.Connection, dir_entradas: Path, *, documentos: list[int] | None = None,
                      modelo: str = "claude-code/claude-opus-5") -> dict:
    dir_entradas = Path(dir_entradas)
    dir_entradas.mkdir(parents=True, exist_ok=True)
    manifesto = {"prompt_version": PROMPT_VERSION, "modelo": modelo, "documentos": []}
    for d in documentos_decisorios(con):
        if documentos and d["id"] not in documentos:
            continue
        ja = con.execute("SELECT 1 FROM extracao WHERE documento_id=? AND sha256_documento=? AND prompt_version=? AND modelo=? AND status='ok'",
                         (d["id"], d["sha256"], PROMPT_VERSION, modelo)).fetchone()
        if ja:
            continue
        paginas = [r["texto"] for r in con.execute("SELECT texto FROM documento_pagina WHERE documento_id=? ORDER BY pagina", (d["id"],))]
        proc = con.execute("SELECT classe, numero FROM processo WHERE incidente_principal=?", (d["incidente"],)).fetchone()
        rotulo = f"{proc['classe']} {proc['numero']}" if proc else f"incidente {d['incidente']}"
        texto = (f"# Documento {d['id']}: {d['titulo']} ({rotulo}, {len(paginas)} página(s))\n\n"
                 f"Resposta esperada em `{d['id']}.json`, JSON estrito no schema abaixo.\n\n"
                 f"## Instruções (prompt {PROMPT_VERSION})\n\n{PROMPT_TEXTO}\n\n"
                 f"## Schema JSON da resposta\n\n```json\n{json.dumps(SCHEMA_SAIDA, ensure_ascii=False)}\n```\n\n"
                 f"## Documento\n\n{montar_entrada(paginas)}\n")
        (dir_entradas / f"{d['id']}.entrada.md").write_text(texto, "utf-8")
        manifesto["documentos"].append({"id": d["id"], "titulo": d["titulo"], "processo": rotulo, "paginas": len(paginas),
                                        "chars": sum(len(p) for p in paginas), "entrada": f"{d['id']}.entrada.md", "resposta": f"{d['id']}.json"})
    (dir_entradas / "MANIFEST.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=1), "utf-8")
    return {"preparados": len(manifesto["documentos"]), "chars": sum(x["chars"] for x in manifesto["documentos"])}


def validar_resposta(texto_json: str, paginas: list[str]) -> tuple[list[PedidoDecidido], list[dict], str | None]:
    try:
        dados = json.loads(texto_json)
    except (ValueError, TypeError):
        return [], [], "json_invalido"
    try:
        ext = ExtracaoDecisao.model_validate(dados)
    except ValidationError:
        return [], [], "schema_invalido"
    normalizadas = [_norm(p) for p in paginas]
    ok, descartadas = [], []
    for it in ext.itens:
        if it.pagina > len(paginas):
            descartadas.append({"motivo": "pagina_inexistente", "item": it.model_dump()})
            continue
        trecho = _norm(it.trecho_fonte)
        if len(it.trecho_fonte) > MAX_TRECHO or not trecho or trecho not in normalizadas[it.pagina - 1]:
            descartadas.append({"motivo": "trecho_nao_encontrado", "item": it.model_dump()})
            continue
        ok.append(it)
    return ok, descartadas, None


def ingerir_decisoes(con: sqlite3.Connection, cliente: ClienteLLM, *, documentos: list[int] | None = None,
                     blobs: Path = config.BLOBS, log: Callable[[str], None] = print) -> dict:
    bs = BlobStore(blobs)
    res = {"processados": 0, "pulados_cache": 0, "itens": 0, "descartados": 0, "rejeitadas": 0, "erros": 0}
    for d in documentos_decisorios(con):
        if documentos and d["id"] not in documentos:
            continue
        ja = con.execute("SELECT status FROM extracao WHERE documento_id=? AND sha256_documento=? AND prompt_version=? AND modelo=?",
                         (d["id"], d["sha256"], PROMPT_VERSION, cliente.modelo)).fetchone()
        if ja and ja["status"] == "ok":
            res["pulados_cache"] += 1
            continue
        paginas = [r["texto"] for r in con.execute("SELECT texto FROM documento_pagina WHERE documento_id=? ORDER BY pagina", (d["id"],))]
        inicio = datetime.now(timezone.utc).isoformat()
        try:
            texto_json, uso = cliente.extrair(PROMPT_TEXTO, montar_entrada(paginas), documento_id=d["id"])
        except Exception as ex:  # noqa: BLE001 — registrar e seguir
            res["erros"] += 1
            con.execute("INSERT OR REPLACE INTO extracao (documento_id, sha256_documento, prompt_version, modelo, executada_em, status) VALUES (?,?,?,?,?,?)",
                        (d["id"], d["sha256"], PROMPT_VERSION, cliente.modelo, inicio, f"erro:{type(ex).__name__}"))
            con.commit()
            log(f"  doc {d['id']}: ERRO {type(ex).__name__}: {ex}")
            continue
        p = bs.gravar(texto_json.encode("utf-8"), ext="llm.json")
        validos, descartados, motivo = validar_resposta(texto_json, paginas)
        status = f"rejeitada:{motivo}" if motivo else "ok"
        with con:
            antigo = con.execute("SELECT id FROM extracao WHERE documento_id=? AND sha256_documento=? AND prompt_version=? AND modelo=?",
                                 (d["id"], d["sha256"], PROMPT_VERSION, cliente.modelo)).fetchone()
            if antigo:
                con.execute("DELETE FROM decisao_item WHERE extracao_id=?", (antigo["id"],))
                con.execute("DELETE FROM extracao WHERE id=?", (antigo["id"],))
            cur = con.execute(
                "INSERT INTO extracao (documento_id, sha256_documento, prompt_version, modelo, executada_em, status, input_tokens, output_tokens, "
                "cache_read_tokens, assercoes_validas, assercoes_descartadas, resposta_path, descartadas_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (d["id"], d["sha256"], PROMPT_VERSION, cliente.modelo, inicio, status, uso.get("input_tokens", 0), uso.get("output_tokens", 0),
                 0, len(validos), len(descartados), caminho_relativo(p, config.RAIZ), json.dumps(descartados, ensure_ascii=False)))
            eid = cur.lastrowid
            for it in validos:
                con.execute(
                    "INSERT INTO decisao_item (documento_id, extracao_id, pagina, pedido, quem_pediu, resultado, decisao, quem_decidiu, data, "
                    "trecho_fonte, condicoes_json, modelo, prompt_version, criado_em) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (d["id"], eid, it.pagina, it.pedido, it.quem_pediu, it.resultado, it.decisao, it.quem_decidiu, it.data, it.trecho_fonte,
                     json.dumps(it.condicoes, ensure_ascii=False), cliente.modelo, PROMPT_VERSION, inicio))
        res["processados"] += 1
        res["itens"] += len(validos)
        res["descartados"] += len(descartados)
        res["rejeitadas"] += int(motivo is not None)
        log(f"  doc {d['id']} ({d['titulo']}): {status}, {len(validos)} itens, {len(descartados)} descartados")
    return res
