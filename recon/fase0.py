"""Fase 0 — reconhecimento do portal do STF.

Script descartável de reconhecimento. Não é o coletor definitivo (Fase 1).
Faz, em ordem:

  A. relê robots.txt e grava snapshot
  B. GET no verImpressao.asp com UA identificado (coleta) e UA de navegador (comparação)
  C. análise offline do HTML salvo (abas, links de documento, contagens, incidentes)
  D. download de UM PDF de inteiro teor da aba Decisões
  E. teste de camada de texto com pdftotext

Regras de coleta aplicadas aqui e obrigatórias nas fases seguintes:
  - sessão única, sem concorrência
  - intervalo mínimo de 3 s entre requisições ao portal, medido e logado
  - backoff exponencial em 429/5xx; 403 não é retentado
  - teto duro de requisições por execução
  - snapshot append-only: nome com timestamp, sha256 no .meta.json, nunca sobrescrever

Uso:
  python recon/fase0.py                      # execução completa (com rede)
  python recon/fase0.py --offline <html>     # só a análise C sobre um HTML salvo
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from selectolax.parser import HTMLParser

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
BUNDLE = ROOT / "recon" / "certs" / "stf-chain.pem"
PDFTOTEXT = Path(r"C:\Program Files\Git\mingw64\bin\pdftotext.exe")

BASE = "https://portal.stf.jus.br"
ROBOTS_URL = f"{BASE}/robots.txt"
INCIDENTE = "7514886"
VERIMPRESSAO = f"{BASE}/processos/verImpressao.asp?imprimir=true&incidente={INCIDENTE}"

CONTATO = "ldickmann12@gmail.com"
UA_IDENT = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; stf-mapeador/0.1; +mailto:{CONTATO})"
UA_BROWSER = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

MIN_INTERVAL_S = 3.0
MAX_REQUESTS = 6
BACKOFF_BASE_S = 5.0
BACKOFF_TRIES = 3

ABAS = [
    "Informações", "Partes", "Andamentos", "Decisões", "Sessão Virtual",
    "Deslocamentos", "Petições", "Recursos", "Pautas",
]


# ---------------------------------------------------------------- utilidades

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ts_tag(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_new(path: Path, data: bytes) -> None:
    """Grava sem sobrescrever. Se já existe, é erro: snapshots são append-only."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"snapshot já existe, não sobrescrevo: {path}")
    path.write_bytes(data)


def write_meta(path: Path, meta: dict) -> None:
    write_new(path, json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))


# ---------------------------------------------------------------- cliente educado

class PoliteClient:
    """Uma sessão, uma requisição por vez, ≥3 s entre elas, backoff, teto duro."""

    def __init__(self, log: list[dict]):
        self.log = log
        self.count = 0
        self.last_at: float | None = None
        self.client = httpx.Client(
            verify=str(BUNDLE),
            follow_redirects=True,
            timeout=httpx.Timeout(60.0),
            headers={"From": CONTATO, "Accept-Language": "pt-BR,pt;q=0.9"},
        )

    def _wait(self) -> float:
        if self.last_at is None:
            return 0.0
        elapsed = time.monotonic() - self.last_at
        wait = max(0.0, MIN_INTERVAL_S - elapsed)
        if wait:
            time.sleep(wait)
        return wait

    def get(self, url: str, *, ua: str, tag: str, referer: str | None = None) -> httpx.Response | None:
        if self.count >= MAX_REQUESTS:
            raise RuntimeError(f"teto de {MAX_REQUESTS} requisições atingido; não faço a {self.count + 1}ª")
        headers = {"User-Agent": ua}
        if referer:
            headers["Referer"] = referer

        for attempt in range(1, BACKOFF_TRIES + 1):
            waited = self._wait()
            started = utcnow()
            self.count += 1
            entry = {
                "n": self.count, "tag": tag, "url": url, "ua": ua, "referer": referer,
                "attempt": attempt, "waited_s": round(waited, 2), "started_at": started.isoformat(),
            }
            try:
                r = self.client.get(url, headers=headers)
            except httpx.HTTPError as e:
                self.last_at = time.monotonic()
                entry.update(error=f"{type(e).__name__}: {e}")
                self.log.append(entry)
                print(f"  [{self.count}] {tag}: ERRO {entry['error']}")
                return None
            self.last_at = time.monotonic()
            entry.update(
                status=r.status_code, final_url=str(r.url), bytes=len(r.content),
                content_type=r.headers.get("content-type"), server=r.headers.get("server"),
                redirects=[(str(h.url), h.status_code) for h in r.history],
                elapsed_s=round(r.elapsed.total_seconds(), 2),
            )
            self.log.append(entry)
            print(f"  [{self.count}] {tag}: {r.status_code} {entry['content_type']} {entry['bytes']} bytes "
                  f"(esperou {waited:.1f}s; tentativa {attempt})")

            if r.status_code == 429 or r.status_code >= 500:
                if attempt < BACKOFF_TRIES:
                    delay = BACKOFF_BASE_S * (2 ** (attempt - 1))
                    print(f"      backoff {delay:.0f}s")
                    time.sleep(delay)
                    continue
            return r
        return None


# ---------------------------------------------------------------- análise offline

def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def analyze_html(raw: bytes, declared_charset: str | None) -> dict:
    """Análise determinística do HTML servido. Zero rede."""
    charset = declared_charset or "utf-8"
    try:
        html = raw.decode(charset)
    except (UnicodeDecodeError, LookupError):
        html = raw.decode("utf-8", errors="replace")
        charset = f"{charset} (falhou; usado utf-8 com replace)"
    tree = HTMLParser(html)
    out: dict = {"charset_usado": charset, "bytes": len(raw)}

    # meta charset declarado no próprio HTML
    m = re.search(r'charset=["\']?([\w-]+)', html[:4000], re.I)
    out["meta_charset_no_html"] = m.group(1) if m else None

    # --- carga secundária?
    scripts = [s.text() or "" for s in tree.css("script")]
    script_srcs = [s.attributes.get("src") for s in tree.css("script[src]")]
    inline = "\n".join(scripts)
    out["carga_secundaria"] = {
        "iframes": [i.attributes.get("src") for i in tree.css("iframe")],
        "script_src": script_srcs,
        "inline_scripts": len([s for s in scripts if s.strip()]),
        "usa_fetch": bool(re.search(r"\bfetch\s*\(", inline)),
        "usa_xhr": "XMLHttpRequest" in inline,
        "usa_jquery_ajax": bool(re.search(r"\$\.(ajax|get|post|load)\s*\(|\.load\s*\(", inline)),
        "urls_asp_em_scripts": sorted(set(re.findall(r"[\w/.-]+\.asp\??[\w=&%.-]*", inline)))[:40],
    }

    # --- estrutura de abas: procurar cabeçalhos/ids com o nome de cada aba
    text_all = tree.body.text() if tree.body else tree.text()
    out["abas_presentes_por_texto"] = {aba: (aba in text_all) for aba in ABAS}
    ids = sorted({n.attributes.get("id") for n in tree.css("[id]") if n.attributes.get("id")})
    out["ids_no_html"] = ids[:80]
    out["headings"] = [_clean(h.text()) for h in tree.css("h1,h2,h3,h4,h5") if _clean(h.text())][:80]

    # --- todos os links, agrupados por host+path
    links = []
    for a in tree.css("a[href]"):
        href = a.attributes.get("href", "")
        if not href or href.startswith(("#", "javascript:")):
            continue
        absolute = urljoin(VERIMPRESSAO, href)
        p = urlparse(absolute)
        links.append({
            "text": _clean(a.text())[:120], "href": href, "abs": absolute,
            "host": p.netloc, "path": p.path, "params": {k: v[0] for k, v in parse_qs(p.query).items()},
        })
    out["total_links"] = len(links)
    by_path: dict[str, int] = {}
    for l in links:
        key = f"{l['host']}{l['path']}"
        by_path[key] = by_path.get(key, 0) + 1
    out["links_por_endpoint"] = dict(sorted(by_path.items(), key=lambda kv: -kv[1]))

    # padrões de link de documento: qualquer coisa com pdf/peca/texto/download no path ou params
    doc_like = [l for l in links if re.search(r"pdf|peca|peça|texto|download|inteiro|documento", l["abs"], re.I)]
    out["links_documento_amostra"] = doc_like[:15]
    out["links_documento_total"] = len(doc_like)
    param_shapes = sorted({f"{l['host']}{l['path']}?{'&'.join(sorted(l['params']))}" for l in doc_like})
    out["links_documento_formatos"] = param_shapes

    # --- incidentes referenciados
    incidentes: dict[str, set[str]] = {}
    for l in links:
        inc = l["params"].get("incidente")
        if inc:
            incidentes.setdefault(inc, set()).add(f"href:{l['path']} [{l['text'][:60]}]")
    for mm in re.finditer(r"incidente=(\d{5,9})", html):
        incidentes.setdefault(mm.group(1), set()).add("regex:incidente=")
    out["incidentes_referenciados"] = {k: sorted(v) for k, v in sorted(incidentes.items())}

    # --- campos da aba Informações (rótulo → valor), heurística por proximidade textual
    campos = {}
    for rot in ["Classe", "Número Único", "Numero Unico", "Relator", "Relator do último incidente",
                "Assunto", "Número de Origem", "Numero de Origem", "Origem", "Data de Protocolo",
                "Sigilo", "Meio", "Publicidade", "Tramitação", "Procedência", "Autuação"]:
        idx = text_all.find(rot)
        if idx >= 0:
            campos[rot] = _clean(text_all[idx:idx + 300])
    out["campos_informacoes_bruto"] = campos

    # --- contagens por tabela: para cada <table>, cabeçalho + nº de linhas
    tabelas = []
    for t in tree.css("table"):
        rows = t.css("tr")
        head = _clean(" | ".join(_clean(c.text()) for c in (rows[0].css("th,td") if rows else [])))[:160]
        tabelas.append({"linhas": len(rows), "cabecalho": head})
    out["tabelas"] = tabelas

    # --- contagem por seção: texto entre o título de uma aba e o da próxima
    secoes = {}
    positions = [(text_all.find(aba), aba) for aba in ABAS]
    positions = sorted([p for p in positions if p[0] >= 0])
    for i, (pos, aba) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text_all)
        chunk = text_all[pos:end]
        datas = re.findall(r"\b\d{2}/\d{2}/\d{4}\b", chunk)
        secoes[aba] = {"chars": len(chunk), "datas_ddmmaaaa": len(datas)}
    out["secoes_por_titulo"] = secoes

    return out


# ---------------------------------------------------------------- PDF

def pdf_text_probe(pdf_path: Path) -> dict:
    data = pdf_path.read_bytes()
    out = {
        "magic_ok": data.startswith(b"%PDF-"),
        "bytes": len(data),
        "tem_/Font": b"/Font" in data,
        "tem_/Image": b"/Image" in data,
        "filtros_imagem": [f for f in ("DCTDecode", "CCITTFaxDecode", "JBIG2Decode", "JPXDecode") if f.encode() in data],
        "pages_by_regex": len(re.findall(rb"/Type\s*/Page[^s]", data)),
    }
    if not PDFTOTEXT.exists():
        out["pdftotext"] = "não encontrado"
        return out
    proc = subprocess.run([str(PDFTOTEXT), "-layout", "-enc", "UTF-8", str(pdf_path), "-"],
                          capture_output=True, timeout=120)
    txt = proc.stdout.decode("utf-8", errors="replace")
    pages = [p for p in txt.split("\f") if p.strip()]
    alnum = sum(ch.isalnum() for ch in txt)
    out["pdftotext"] = {
        "returncode": proc.returncode,
        "stderr": proc.stderr.decode("utf-8", errors="replace")[:500],
        "chars": len(txt),
        "alnum_chars": alnum,
        "paginas_com_texto": len(pages),
        "alnum_por_pagina": round(alnum / max(1, len(pages)), 1),
        "amostra_inicio": _clean(txt[:600]),
    }
    return out


# ---------------------------------------------------------------- main

def run_offline(html_path: Path) -> None:
    meta_path = html_path.with_suffix(".meta.json")
    charset = None
    if meta_path.exists():
        charset = json.loads(meta_path.read_text("utf-8")).get("charset")
    res = analyze_html(html_path.read_bytes(), charset)
    print(json.dumps(res, ensure_ascii=False, indent=2))


def run_online() -> None:
    log: list[dict] = []
    run_at = utcnow()
    tag = ts_tag(run_at)
    inc_dir = RAW / INCIDENTE
    results: dict = {"run_at": run_at.isoformat(), "incidente": INCIDENTE}
    pc = PoliteClient(log)

    print("A. robots.txt")
    r = pc.get(ROBOTS_URL, ua=UA_IDENT, tag="robots")
    if r is not None:
        write_new(RAW / f"robots_{tag}.txt", r.content)
        results["robots"] = {"status": r.status_code, "sha256": sha256(r.content),
                             "text": r.text, "last_modified": r.headers.get("last-modified")}

    print("B. verImpressao.asp")
    html_ok: Path | None = None
    for ua, ua_tag in ((UA_IDENT, "ua-ident"), (UA_BROWSER, "ua-browser")):
        r = pc.get(VERIMPRESSAO, ua=ua, tag=f"verImpressao/{ua_tag}")
        if r is None:
            results[f"verImpressao_{ua_tag}"] = {"error": log[-1].get("error")}
            continue
        fname = inc_dir / f"{tag}_{ua_tag}_verImpressao.html"
        write_new(fname, r.content)
        meta = {
            "url": VERIMPRESSAO, "final_url": str(r.url), "fetched_at": log[-1]["started_at"],
            "sha256": sha256(r.content), "http_status": r.status_code, "bytes": len(r.content),
            "charset": r.charset_encoding, "request_headers": {"User-Agent": ua, "From": CONTATO},
            "response_headers": dict(r.headers), "redirects": log[-1]["redirects"], "raw_path": str(fname.relative_to(ROOT)),
        }
        write_meta(fname.with_suffix(".meta.json"), meta)
        results[f"verImpressao_{ua_tag}"] = {k: meta[k] for k in ("http_status", "sha256", "bytes", "charset", "final_url", "raw_path")}
        if r.status_code == 200 and html_ok is None and b"<html" in r.content[:2000].lower():
            html_ok = fname
            results["html_analisado"] = str(fname.relative_to(ROOT))

    if html_ok is None:
        results["analise"] = "nenhum HTML 200 obtido; análise não executada"
    else:
        print("C. análise offline")
        charset = json.loads(html_ok.with_suffix(".meta.json").read_text("utf-8")).get("charset")
        analise = analyze_html(html_ok.read_bytes(), charset)
        results["analise"] = analise

        print("D. um PDF de inteiro teor")
        docs = analise.get("links_documento_amostra") or []
        # preferir link cujo path/params sugira inteiro teor / decisão; senão o primeiro
        pref = [d for d in docs if re.search(r"inteiro|teor|decis|pdf", d["abs"] + d["text"], re.I)] or docs
        if not pref:
            results["pdf"] = {"error": "nenhum link de documento encontrado no HTML"}
        else:
            alvo = pref[0]
            r = pc.get(alvo["abs"], ua=UA_IDENT, tag="pdf", referer=VERIMPRESSAO)
            if r is None:
                results["pdf"] = {"error": log[-1].get("error"), "link": alvo}
            else:
                is_pdf = r.content.startswith(b"%PDF-")
                digest = sha256(r.content)
                ext = "pdf" if is_pdf else "resp.html"
                fname = inc_dir / "docs" / f"{digest}.{ext}"
                write_new(fname, r.content)
                meta = {
                    "link": alvo, "final_url": str(r.url), "fetched_at": log[-1]["started_at"],
                    "sha256": digest, "http_status": r.status_code, "bytes": len(r.content),
                    "content_type": r.headers.get("content-type"), "content_disposition": r.headers.get("content-disposition"),
                    "redirects": log[-1]["redirects"], "is_pdf_magic": is_pdf,
                    "cookies_na_sessao": sorted(pc.client.cookies.keys()), "raw_path": str(fname.relative_to(ROOT)),
                }
                write_meta(fname.with_suffix(fname.suffix + ".meta.json"), meta)
                results["pdf"] = meta
                if is_pdf:
                    print("E. camada de texto")
                    results["pdf_texto"] = pdf_text_probe(fname)
                else:
                    results["pdf_texto"] = {"skip": "resposta não é PDF", "inicio": r.content[:400].decode("utf-8", "replace")}

    results["request_log"] = log
    out = ROOT / "recon" / f"fase0-resultado_{tag}.json"
    write_new(out, json.dumps(results, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
    print(f"\nresultado: {out.relative_to(ROOT)}  ({pc.count} requisições ao portal)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", type=Path, help="analisa um HTML salvo, sem rede")
    args = ap.parse_args()
    if args.offline:
        run_offline(args.offline)
    else:
        if not BUNDLE.exists():
            sys.exit(f"bundle TLS ausente: {BUNDLE}")
        run_online()
