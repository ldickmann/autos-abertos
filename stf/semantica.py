"""Fase 4: camada semântica. Único ponto do sistema onde entra LLM.

Contrato:
- prompt versionado em arquivo (stf/prompts/extracao_vN.md); `prompt_version` = nome + sha256 curto do conteúdo;
- uma extração por (documento, sha256 do blob, prompt_version, modelo); resultado em cache na tabela
  `extracao`, com a resposta bruta guardada em blob para auditoria;
- saída em JSON estrito, validada por Pydantic; malformada → resposta rejeitada inteira;
- cada asserção precisa de página existente e trecho literal presente nessa página; senão é descartada
  (restrição 1: sem ponteiro rastreável, não entra; não vai para revisão manual);
- tipo epistêmico ∈ {fato_processual, alegacao_parte, fundamento_decisorio} (restrição 2), imposto no schema;
- entidades citadas resolvem para a entidade canônica das partes pelo nome normalizado; senão entram como
  entidade nova com origem 'documento' ("terceiro mencionado");
- nada aqui deduz conduta, caráter ou intenção; o prompt proíbe e o schema não tem campo para isso.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal, Protocol

from pydantic import BaseModel, Field, ValidationError

from . import config
from .entidades import normalizar
from .store import BlobStore, caminho_relativo, resolver_raw

PROMPT_PATH = Path(__file__).parent / "prompts" / "extracao_v1.md"
PROMPT_TEXTO = PROMPT_PATH.read_text("utf-8")
PROMPT_VERSION = f"{PROMPT_PATH.stem}-{hashlib.sha256(PROMPT_TEXTO.encode('utf-8')).hexdigest()[:12]}"
MODELO_PADRAO = "claude-opus-5"
MAX_TRECHO = 300

TipoEpistemico = Literal["fato_processual", "alegacao_parte", "fundamento_decisorio"]
TipoEntidade = Literal["pessoa", "organizacao", "orgao_publico", "ministro", "advogado", "desconhecido"]


class EntidadeCitada(BaseModel):
    nome: str = Field(min_length=1)
    tipo: TipoEntidade


class AssercaoExtraida(BaseModel):
    tipo_epistemico: TipoEpistemico
    texto: str = Field(min_length=1)
    pagina: int = Field(ge=1)
    trecho_fonte: str = Field(min_length=1)
    atribuida_a: str | None = None
    entidades: list[EntidadeCitada] = Field(default_factory=list)


class Extracao(BaseModel):
    assercoes: list[AssercaoExtraida]
    observacoes: str | None = None


SCHEMA_SAIDA = Extracao.model_json_schema()


# ---------------------------------------------------------------- cliente LLM

class ClienteLLM(Protocol):
    modelo: str

    def extrair(self, system: str, entrada: str, *, documento_id: int) -> tuple[str, dict]:
        """Devolve (texto_json, uso) onde uso = {"input_tokens", "output_tokens", "cache_read_input_tokens", ...}."""


class ClienteAnthropic:
    """Anthropic SDK, saída estruturada por json_schema, streaming (documentos longos)."""

    def __init__(self, modelo: str = MODELO_PADRAO, effort: str = "high"):
        import anthropic
        self.client = anthropic.Anthropic()
        self.modelo = modelo
        self.effort = effort

    def extrair(self, system: str, entrada: str, *, documento_id: int) -> tuple[str, dict]:
        with self.client.messages.stream(
            model=self.modelo,
            max_tokens=32000,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": entrada}],
            output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": SCHEMA_SAIDA}},
        ) as stream:
            msg = stream.get_final_message()
        if msg.stop_reason == "refusal":
            raise RuntimeError(f"recusa do modelo: {getattr(msg, 'stop_details', None)}")
        if msg.stop_reason == "max_tokens":
            raise RuntimeError("resposta truncada (max_tokens)")
        texto = "".join(b.text for b in msg.content if b.type == "text")
        u = msg.usage
        uso = {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
               "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
               "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0}
        return texto, uso


class ClienteFalso:
    """Para testes e dry-run: devolve sempre a mesma resposta."""

    def __init__(self, resposta: str, modelo: str = "falso-1"):
        self.resposta, self.modelo, self.chamadas = resposta, modelo, 0

    def extrair(self, system: str, entrada: str, *, documento_id: int) -> tuple[str, dict]:
        self.chamadas += 1
        return self.resposta, {"input_tokens": len(entrada) // 4, "output_tokens": len(self.resposta) // 4,
                               "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}


class ClienteArquivo:
    """Execução pelo Claude Code (plano Max), sem API: a resposta de cada documento é lida de
    `<dir>/<documento_id>.json`, escrita por quem leu a entrada correspondente. Sem arquivo → erro,
    e o documento fica pendente. A validação e a persistência são as mesmas dos outros clientes."""

    def __init__(self, dir_respostas: Path, modelo: str = "claude-code/claude-opus-5"):
        self.dir = Path(dir_respostas)
        self.modelo = modelo

    def extrair(self, system: str, entrada: str, *, documento_id: int) -> tuple[str, dict]:
        p = self.dir / f"{documento_id}.json"
        if not p.exists():
            raise FileNotFoundError(f"sem resposta para o documento {documento_id}: {p}")
        texto = p.read_text("utf-8")
        return texto, {"input_tokens": len(entrada) // 4, "output_tokens": len(texto) // 4,
                       "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}


def preparar_entradas(con: sqlite3.Connection, dir_entradas: Path, *, documentos: list[int] | None = None,
                      limite: int | None = None, prompt_version: str = PROMPT_VERSION,
                      modelo: str = "claude-code/claude-opus-5") -> dict:
    """Grava `<id>.entrada.md` (instruções + texto por página) para cada documento ainda sem extração
    válida, e um MANIFEST.json com id, título, tamanho e caminho de resposta esperado."""
    dir_entradas = Path(dir_entradas)
    dir_entradas.mkdir(parents=True, exist_ok=True)
    sql = ("SELECT d.id, d.sha256, d.incidente, d.titulo, d.paginas FROM documento d WHERE d.sha256 IS NOT NULL AND d.tem_camada_texto=1 "
           "AND EXISTS (SELECT 1 FROM documento_pagina p WHERE p.documento_id=d.id) "
           "AND NOT EXISTS (SELECT 1 FROM extracao e WHERE e.documento_id=d.id AND e.sha256_documento=d.sha256 "
           "AND e.prompt_version=? AND e.modelo=? AND e.status='ok')")
    params: list = [prompt_version, modelo]
    if documentos:
        sql += f" AND d.id IN ({','.join('?' * len(documentos))})"
        params += documentos
    sql += " ORDER BY d.id"
    if limite:
        sql += f" LIMIT {int(limite)}"
    manifesto = {"prompt_version": prompt_version, "modelo": modelo, "documentos": []}
    for d in con.execute(sql, params).fetchall():
        paginas = [r["texto"] for r in con.execute("SELECT texto FROM documento_pagina WHERE documento_id=? ORDER BY pagina", (d["id"],))]
        entrada = montar_entrada(paginas)
        proc = con.execute("SELECT classe, numero FROM processo WHERE incidente_principal=?", (d["incidente"],)).fetchone()
        rotulo = f"{proc['classe']} {proc['numero']}" if proc else f"incidente {d['incidente']}"
        texto = (f"# Documento {d['id']}: {d['titulo']} ({rotulo}, {len(paginas)} página(s))\n\n"
                 f"Resposta esperada em `{d['id']}.json`, JSON estrito no schema abaixo.\n\n"
                 f"## Instruções (prompt {prompt_version})\n\n{PROMPT_TEXTO}\n\n"
                 f"## Schema JSON da resposta\n\n```json\n{json.dumps(SCHEMA_SAIDA, ensure_ascii=False)}\n```\n\n"
                 f"## Documento\n\n{entrada}\n")
        (dir_entradas / f"{d['id']}.entrada.md").write_text(texto, "utf-8")
        manifesto["documentos"].append({"id": d["id"], "titulo": d["titulo"], "processo": rotulo, "paginas": len(paginas),
                                        "chars": sum(len(p) for p in paginas), "entrada": f"{d['id']}.entrada.md",
                                        "resposta": f"{d['id']}.json"})
    (dir_entradas / "MANIFEST.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=1), "utf-8")
    return {"preparados": len(manifesto["documentos"]), "chars": sum(x["chars"] for x in manifesto["documentos"])}


# ---------------------------------------------------------------- entrada e validação

def montar_entrada(paginas: list[str]) -> str:
    return "\n\n".join(f"[página {i}]\n{t}" for i, t in enumerate(paginas, start=1))


_WS = re.compile(r"\s+")


def _norm(s: str) -> str:
    return _WS.sub(" ", s).strip().casefold()


def validar_resposta(texto_json: str, paginas: list[str]) -> tuple[list[AssercaoExtraida], list[dict], str | None]:
    """Devolve (válidas, descartadas, motivo_de_rejeicao_total). Rejeição total anula tudo."""
    try:
        dados = json.loads(texto_json)
    except (ValueError, TypeError):
        return [], [], "json_invalido"
    try:
        ext = Extracao.model_validate(dados)
    except ValidationError:
        return [], [], "schema_invalido"
    normalizadas = [_norm(p) for p in paginas]
    ok: list[AssercaoExtraida] = []
    descartadas: list[dict] = []
    for a in ext.assercoes:
        if a.pagina > len(paginas):
            descartadas.append({"motivo": "pagina_inexistente", "assercao": a.model_dump()})
            continue
        trecho = _norm(a.trecho_fonte)
        if len(a.trecho_fonte) > MAX_TRECHO or not trecho or trecho not in normalizadas[a.pagina - 1]:
            descartadas.append({"motivo": "trecho_nao_encontrado", "assercao": a.model_dump()})
            continue
        ok.append(a)
    return ok, descartadas, None


# ---------------------------------------------------------------- persistência

def _resolver_entidade(con, citada: EntidadeCitada, sid: int | None) -> int:
    chave = f"nome:{normalizar(citada.nome)}"
    row = con.execute("SELECT id FROM entidade WHERE chave=?", (chave,)).fetchone()
    if row:
        return row["id"]
    # advogados canônicos têm chave por OAB; tenta casar pelo nome antes de criar
    row = con.execute("SELECT id FROM entidade WHERE nome=? AND tipo='advogado'", (normalizar(citada.nome),)).fetchone()
    if row:
        return row["id"]
    cur = con.execute("INSERT INTO entidade (tipo, chave, nome, natureza_provavel, origem) VALUES (?,?,?,?,?)",
                      (citada.tipo, chave, citada.nome.strip(), None, "documento"))
    return cur.lastrowid


def extrair_assercoes(con: sqlite3.Connection, cliente: ClienteLLM, *, documentos: list[int] | None = None,
                      limite: int | None = None, prompt_version: str = PROMPT_VERSION, prompt_texto: str = PROMPT_TEXTO,
                      blobs: Path = config.BLOBS, log: Callable[[str], None] = print) -> dict:
    bs = BlobStore(blobs)
    sql = ("SELECT d.id, d.sha256, d.incidente, d.titulo FROM documento d WHERE d.sha256 IS NOT NULL AND d.tem_camada_texto=1 "
           "AND EXISTS (SELECT 1 FROM documento_pagina p WHERE p.documento_id=d.id)")
    params: list = []
    if documentos:
        sql += f" AND d.id IN ({','.join('?' * len(documentos))})"
        params += documentos
    sql += " ORDER BY d.id"
    if limite:
        sql += f" LIMIT {int(limite)}"
    res = {"processados": 0, "pulados_cache": 0, "assercoes": 0, "descartadas": 0, "rejeitadas": 0, "erros": 0,
           "input_tokens": 0, "output_tokens": 0}
    for d in con.execute(sql, params).fetchall():
        ja = con.execute("SELECT id, status FROM extracao WHERE documento_id=? AND sha256_documento=? AND prompt_version=? AND modelo=?",
                         (d["id"], d["sha256"], prompt_version, cliente.modelo)).fetchone()
        if ja and ja["status"].startswith("ok"):
            res["pulados_cache"] += 1
            continue
        paginas = [r["texto"] for r in con.execute(
            "SELECT texto FROM documento_pagina WHERE documento_id=? ORDER BY pagina", (d["id"],))]
        entrada = montar_entrada(paginas)
        inicio = datetime.now(timezone.utc).isoformat()
        try:
            texto_json, uso = cliente.extrair(prompt_texto, entrada, documento_id=d["id"])
        except Exception as ex:  # noqa: BLE001 — registrar o erro e seguir para o próximo documento
            res["erros"] += 1
            con.execute("INSERT OR REPLACE INTO extracao (documento_id, sha256_documento, prompt_version, modelo, executada_em, status) "
                        "VALUES (?,?,?,?,?,?)", (d["id"], d["sha256"], prompt_version, cliente.modelo, inicio, f"erro:{type(ex).__name__}"))
            con.commit()
            log(f"  doc {d['id']}: ERRO {type(ex).__name__}: {ex}")
            continue
        p = bs.gravar(texto_json.encode("utf-8"), ext="llm.json")
        validas, descartadas, motivo = validar_resposta(texto_json, paginas)
        status = f"rejeitada:{motivo}" if motivo else "ok"
        with con:
            con.execute("DELETE FROM extracao WHERE documento_id=? AND sha256_documento=? AND prompt_version=? AND modelo=?",
                        (d["id"], d["sha256"], prompt_version, cliente.modelo))
            cur = con.execute(
                "INSERT INTO extracao (documento_id, sha256_documento, prompt_version, modelo, executada_em, status, "
                "input_tokens, output_tokens, cache_read_tokens, assercoes_validas, assercoes_descartadas, resposta_path, descartadas_json) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (d["id"], d["sha256"], prompt_version, cliente.modelo, inicio, status, uso.get("input_tokens", 0),
                 uso.get("output_tokens", 0), uso.get("cache_read_input_tokens", 0), len(validas), len(descartadas),
                 caminho_relativo(p, config.RAIZ), json.dumps(descartadas, ensure_ascii=False)))
            eid = cur.lastrowid
            for a in validas:
                cur = con.execute(
                    "INSERT INTO assercao (documento_id, extracao_id, pagina, tipo_epistemico, texto, trecho_fonte, atribuida_a, "
                    "entidades_json, modelo, prompt_version, criado_em) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (d["id"], eid, a.pagina, a.tipo_epistemico, a.texto, a.trecho_fonte, a.atribuida_a,
                     json.dumps([e.model_dump() for e in a.entidades], ensure_ascii=False), cliente.modelo, prompt_version, inicio))
                aid = cur.lastrowid
                for e in a.entidades:
                    ent = _resolver_entidade(con, e, None)
                    con.execute("INSERT OR IGNORE INTO assercao_entidade (assercao_id, entidade_id, nome_literal, tipo_citado) VALUES (?,?,?,?)",
                                (aid, ent, e.nome, e.tipo))
        res["processados"] += 1
        res["assercoes"] += len(validas)
        res["descartadas"] += len(descartadas)
        res["rejeitadas"] += int(motivo is not None)
        res["input_tokens"] += uso.get("input_tokens", 0)
        res["output_tokens"] += uso.get("output_tokens", 0)
        log(f"  doc {d['id']} ({d['titulo']}): {status}, {len(validas)} válidas, {len(descartadas)} descartadas")
    return res


def estimar_tokens(con: sqlite3.Connection, documentos: list[int] | None = None) -> dict:
    """Estimativa grosseira (4 chars/token) para dimensionar custo antes de chamar a API."""
    sql = "SELECT d.id, d.titulo, SUM(p.chars) chars, COUNT(p.pagina) paginas FROM documento d JOIN documento_pagina p ON p.documento_id=d.id"
    params: list = []
    if documentos:
        sql += f" WHERE d.id IN ({','.join('?' * len(documentos))})"
        params += documentos
    sql += " GROUP BY d.id ORDER BY chars DESC"
    rows = [dict(r) for r in con.execute(sql, params)]
    prompt_tokens = len(PROMPT_TEXTO) // 4
    total_in = sum(r["chars"] // 4 + prompt_tokens for r in rows)
    return {"documentos": len(rows), "prompt_tokens": prompt_tokens, "input_tokens_estimados": total_in,
            "maior": rows[0] if rows else None}


def _blob_texto(p: str) -> str:
    return resolver_raw(p, config.RAIZ).read_text("utf-8")
