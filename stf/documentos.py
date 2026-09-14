"""Camada documental: download com cache por sha256, texto por página, chunking com página.

- Um documento é identificado por (endpoint, id_portal). Uma vez baixado (sha256 preenchido),
  nunca é rebaixado. O blob vai para o BlobStore; o registro JSONL da rodada guarda a
  proveniência; `documento` recebe sha256/blob_path/http_status/baixado_em.
- Texto: PDF via pdfplumber (preserva espaços; pypdf perdia), uma linha por página;
  RTF via striprtf. Tudo em `documento_pagina(documento_id, pagina, texto)`.
- Camada de texto: um PDF é "com camada" quando a maioria das páginas tem mais que
  MIN_CHARS_PAGINA caracteres alfanuméricos. Caso contrário `precisa_ocr=1`; nenhum OCR é
  feito aqui (decisão de custo separada).
- Chunks: quebra por página e por parágrafo numerado ("1.", "2." …) ou título em caixa alta
  (RELATÓRIO, VOTO, DECISÃO, DESPACHO, EMENTA…), com tamanho máximo; cada chunk carrega
  pagina_inicio/pagina_fim e a seção em que está.
"""

from __future__ import annotations

import io
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import config
from .coleta import ClienteEducado
from .store import BlobStore, RegistroColeta, caminho_relativo, resolver_raw, sha256

MIN_CHARS_PAGINA = 40
MAX_CHARS_CHUNK = 1800

_AUTENTICACAO_RE = re.compile(
    r"c[oó]digo\s+([0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4})\s+e\s+senha\s+([0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4})",
    re.I)
_PARAGRAFO_RE = re.compile(r"^\s*(\d{1,3})\.\s+\S")
_TITULO_RE = re.compile(r"^\s*(RELATÓRIO|RELATORIO|VOTO|VOTO VOGAL|VOTO VISTA|DECISÃO|DECISAO|DESPACHO|EMENTA|ACÓRDÃO|ACORDAO|DISPOSITIVO|EXTRATO DE ATA|CERTIDÃO DE JULGAMENTO)\s*:?\s*$",
                        re.I)
_RODAPE_RE = re.compile(r"Documento assinado digitalmente conforme MP.*?(?:senha\s+[0-9A-F-]{19})", re.S | re.I)


# ---------------------------------------------------------------- texto

def extrair_paginas_pdf(data: bytes) -> list[str]:
    import pdfplumber
    paginas: list[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for p in pdf.pages:
            paginas.append(p.extract_text() or "")
    return paginas


def rtf_para_texto(data: bytes) -> str:
    from striprtf.striprtf import rtf_to_text
    return rtf_to_text(data.decode("latin-1", errors="replace"))


def codigo_autenticacao(texto: str) -> tuple[str, str] | None:
    m = _AUTENTICACAO_RE.search(texto)
    return (m.group(1).upper(), m.group(2).upper()) if m else None


def _alnum(s: str) -> int:
    return sum(ch.isalnum() for ch in s)


def chunkar(paginas: list[str], max_chars: int = MAX_CHARS_CHUNK) -> list[dict]:
    """Chunks com página de início e fim. Quebra em parágrafo numerado ou título; nunca no meio de linha."""
    chunks: list[dict] = []
    atual: list[str] = []
    atual_ini = atual_fim = 1
    secao: str | None = None

    def fechar():
        nonlocal atual
        texto = "\n".join(atual).strip()
        if texto:
            chunks.append({"ordem": len(chunks), "pagina_inicio": atual_ini, "pagina_fim": atual_fim,
                           "secao": secao, "texto": texto, "chars": len(texto)})
        atual = []

    for num, pagina in enumerate(paginas, start=1):
        for linha in pagina.splitlines():
            if not linha.strip():
                continue
            if _RODAPE_RE.search(linha):
                continue
            titulo = _TITULO_RE.match(linha)
            novo_paragrafo = _PARAGRAFO_RE.match(linha) is not None
            tamanho = sum(len(x) + 1 for x in atual)
            if atual and (titulo or novo_paragrafo or tamanho + len(linha) > max_chars):
                fechar()
            if not atual:
                atual_ini = num
            if titulo:
                secao = titulo.group(1).upper()
            atual.append(linha.rstrip())
            atual_fim = num
    fechar()
    return chunks


# ---------------------------------------------------------------- download

def baixar_documentos(con: sqlite3.Connection, *, incidente: int | None = None, cliente: ClienteEducado | None = None,
                      blobs: Path = config.BLOBS, coletas: Path = config.COLETAS, teto: int | None = None,
                      log: Callable[[str], None] = print) -> dict:
    """Baixa todo documento sem sha256 (cache). Uma rodada = um registro JSONL."""
    c = cliente or ClienteEducado(teto=teto or config.TETO_REQUISICOES_POR_RODADA_DOCS)
    bs = BlobStore(blobs)
    pend = con.execute(
        "SELECT id, incidente, endpoint, id_portal, formato, url FROM documento WHERE sha256 IS NULL"
        + (" AND incidente=?" if incidente else "") + " ORDER BY incidente, id",
        (incidente,) if incidente else ()).fetchall()
    res = {"pendentes": len(pend), "baixados": 0, "erros": 0, "interrompido_por_teto": False}
    if not pend:
        return res
    rodada = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-documentos-{incidente or 'todos'}"
    reg = RegistroColeta(coletas, rodada)
    con.execute("INSERT OR IGNORE INTO coleta (id, incidente, registro_path, ingerida_em) VALUES (?,?,?,?)",
                (rodada, incidente or 0, str(reg.caminho), datetime.now(timezone.utc).isoformat()))
    con.commit()
    from .coleta import TetoAtingido
    for d in pend:
        referer = f"{config.BASE_PROCESSOS}detalhe.asp?incidente={d['incidente']}"
        try:
            r = c.get(d["url"], aba="documento", referer=referer)
        except TetoAtingido as e:
            log(f"teto: {e}")
            res["interrompido_por_teto"] = True
            break
        e = c.log[-1]
        if r is None:
            res["erros"] += 1
            reg.anotar({"incidente": d["incidente"], "aba": "documento", "url": d["url"], "fetched_at": e["iniciada_em"],
                        "http_status": 0, "sha256": None, "bytes": 0, "raw_path": None, "erro": e.get("erro"),
                        "endpoint": d["endpoint"], "id_portal": d["id_portal"]})
            log(f"  doc {d['endpoint']}/{d['id_portal']}: ERRO {e.get('erro')}")
            continue
        e_pdf = r.content.startswith(b"%PDF-")
        e_rtf = r.content.lstrip().startswith(b"{\\rtf")
        ext = "pdf" if e_pdf else ("rtf" if e_rtf else "resp.html")
        p = bs.gravar(r.content, ext=ext)
        digest = sha256(r.content)
        linha = {"incidente": d["incidente"], "aba": "documento", "url": d["url"], "url_final": str(r.url),
                 "fetched_at": e["iniciada_em"], "http_status": r.status_code, "sha256": digest, "bytes": len(r.content),
                 "raw_path": caminho_relativo(p, config.RAIZ), "content_type": r.headers.get("content-type"),
                 "user_agent": config.USER_AGENT, "redirects": e.get("redirects", []),
                 "endpoint": d["endpoint"], "id_portal": d["id_portal"], "formato_real": ext}
        reg.anotar(linha)
        cur = con.execute(
            "INSERT INTO snapshot (coleta_id, incidente, aba, url, fetched_at, http_status, sha256, bytes, raw_path, content_type) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (rodada, d["incidente"], "documento", d["url"], e["iniciada_em"], r.status_code, digest, len(r.content),
             linha["raw_path"], r.headers.get("content-type")))
        ok = r.status_code == 200 and (e_pdf or e_rtf)
        registrar_download(con, d["endpoint"], d["id_portal"], digest if ok else None, linha["raw_path"], r.status_code,
                           e["iniciada_em"], cur.lastrowid, ext)
        con.commit()
        res["baixados" if ok else "erros"] += 1
        log(f"  doc {d['endpoint']}/{d['id_portal']}: {r.status_code} {ext} {len(r.content)} B")
    return res


def registrar_download(con, endpoint: str, id_portal: str, digest: str | None, raw_path: str | None, status: int,
                       quando: str, snapshot_id: int | None, formato_real: str | None, *,
                       incidente: int | None = None, url: str | None = None) -> None:
    """Grava o resultado de um download em `documento`. Se a linha ainda não existe (reingestão em
    ordem diferente), cria-a com o que o registro sabe; a projeção dos andamentos completa o título."""
    if incidente is not None and url is not None:
        con.execute(
            "INSERT OR IGNORE INTO documento (incidente, endpoint, id_portal, formato, url, snapshot_first_seen) "
            "VALUES (?,?,?,?,?,?)", (incidente, endpoint, id_portal, formato_real or "pdf", url, snapshot_id or 0))
    con.execute(
        "UPDATE documento SET sha256=COALESCE(?, sha256), blob_path=COALESCE(?, blob_path), http_status=?, "
        "baixado_em=COALESCE(baixado_em, ?), snapshot_download=COALESCE(?, snapshot_download), "
        "formato=CASE WHEN ? IN ('pdf','rtf') THEN ? ELSE formato END WHERE endpoint=? AND id_portal=?",
        (digest, raw_path, status, quando, snapshot_id, formato_real, formato_real, endpoint, id_portal))


# ---------------------------------------------------------------- extração

def extrair_texto(con: sqlite3.Connection, *, log: Callable[[str], None] = print) -> dict:
    """Para todo documento baixado e ainda sem páginas: extrai texto, chunks, código de autenticação."""
    docs = con.execute(
        "SELECT d.id, d.formato, d.blob_path, d.sha256 FROM documento d WHERE d.sha256 IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM documento_pagina p WHERE p.documento_id = d.id) ORDER BY d.id").fetchall()
    res = {"extraidos": 0, "sem_camada_texto": 0, "erros": 0}
    for d in docs:
        try:
            data = resolver_raw(d["blob_path"], config.RAIZ).read_bytes()
            if sha256(data) != d["sha256"]:
                raise RuntimeError("blob não confere com o sha256 registrado")
            if d["formato"] == "pdf":
                paginas = extrair_paginas_pdf(data)
            elif d["formato"] == "rtf":
                paginas = [rtf_para_texto(data)]
            else:
                raise RuntimeError(f"formato sem extrator: {d['formato']}")
        except Exception as ex:  # noqa: BLE001 — registrar e seguir; o documento fica sem texto, não some
            res["erros"] += 1
            log(f"  doc {d['id']}: ERRO {type(ex).__name__}: {ex}")
            continue
        com_texto = sum(1 for p in paginas if _alnum(p) >= MIN_CHARS_PAGINA)
        tem_camada = int(paginas != [] and com_texto * 2 >= len(paginas))
        auth = codigo_autenticacao("\n".join(paginas))
        with con:
            con.executemany("INSERT INTO documento_pagina (documento_id, pagina, texto, chars) VALUES (?,?,?,?)",
                            [(d["id"], i, t, len(t)) for i, t in enumerate(paginas, start=1)])
            con.executemany(
                "INSERT INTO documento_chunk (documento_id, ordem, pagina_inicio, pagina_fim, secao, texto, chars) "
                "VALUES (?,?,?,?,?,?,?)",
                [(d["id"], c["ordem"], c["pagina_inicio"], c["pagina_fim"], c["secao"], c["texto"], c["chars"])
                 for c in chunkar(paginas)])
            con.execute(
                "UPDATE documento SET paginas=?, tem_camada_texto=?, precisa_ocr=?, codigo_autenticacao=?, senha_autenticacao=? WHERE id=?",
                (len(paginas), tem_camada, int(not tem_camada), auth[0] if auth else None, auth[1] if auth else None, d["id"]))
        res["extraidos"] += 1
        res["sem_camada_texto"] += int(not tem_camada)
    return res
