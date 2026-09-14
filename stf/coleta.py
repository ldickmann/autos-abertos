"""Coleta educada de um incidente: casca + abas listadas pela própria casca.

Política (restrição 4, reescrita na Fase 0):
- UA identificado com contato e cabeçalho From em toda requisição;
- uma requisição por vez, intervalo mínimo entre elas medido pelo relógio;
- backoff exponencial em 429/5xx; 403 não é retentado;
- teto duro de requisições por coleta;
- robots.txt relido e gravado no início de cada coleta;
- nenhuma descoberta automática: só as URLs que a casca do incidente-alvo declara.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin

import httpx

from . import config
from .parse.casca import parse_casca
from .sessao import parse_objetos_incidente, url_oi, url_sessao
from .store import BlobStore, RegistroColeta, caminho_relativo, sha256


class TetoAtingido(RuntimeError):
    pass


class ClienteEducado:
    def __init__(self, *, transport: httpx.BaseTransport | None = None,
                 relogio: Callable[[], float] = time.monotonic, dormir: Callable[[float], None] = time.sleep,
                 teto: int = config.TETO_REQUISICOES_POR_COLETA, intervalo: float = config.INTERVALO_MINIMO_S,
                 verify: str | bool | None = None):
        self.relogio, self.dormir, self.teto, self.intervalo = relogio, dormir, teto, intervalo
        self.count = 0
        self.ultima: float | None = None
        self.log: list[dict] = []
        kw: dict = {
            "follow_redirects": True, "timeout": httpx.Timeout(config.TIMEOUT_S),
            "headers": {"User-Agent": config.USER_AGENT, "From": config.CONTATO, "Accept-Language": "pt-BR,pt;q=0.9"},
        }
        if transport is not None:
            kw["transport"] = transport
        else:
            kw["verify"] = verify if verify is not None else str(config.BUNDLE_TLS)
        self.http = httpx.Client(**kw)

    def _esperar(self) -> float:
        if self.ultima is None:
            return 0.0
        falta = self.intervalo - (self.relogio() - self.ultima)
        if falta > 0:
            self.dormir(falta)
            return falta
        return 0.0

    def get(self, url: str, *, aba: str, referer: str | None = None, headers: dict | None = None) -> httpx.Response | None:
        headers = {**({"Referer": referer} if referer else {}), **(headers or {})}
        for tentativa in range(1, config.BACKOFF_TENTATIVAS + 1):
            if self.count >= self.teto:
                raise TetoAtingido(f"teto de {self.teto} requisições atingido antes de {aba} ({url})")
            esperou = self._esperar()
            self.count += 1
            inicio = datetime.now(timezone.utc).isoformat()
            entrada = {"n": self.count, "aba": aba, "url": url, "tentativa": tentativa,
                       "esperou_s": round(esperou, 2), "iniciada_em": inicio}
            try:
                r = self.http.get(url, headers=headers)
            except httpx.HTTPError as e:
                self.ultima = self.relogio()
                entrada["erro"] = f"{type(e).__name__}: {e}"
                self.log.append(entrada)
                return None
            self.ultima = self.relogio()
            # cada salto de redirect é uma requisição a mais no portal; conta no teto
            self.count += len(r.history)
            entrada.update(status=r.status_code, bytes=len(r.content), url_final=str(r.url),
                           redirects=[(str(h.url), h.status_code) for h in r.history])
            self.log.append(entrada)
            if (r.status_code == 429 or r.status_code >= 500) and tentativa < config.BACKOFF_TENTATIVAS:
                self.dormir(config.BACKOFF_BASE_S * (2 ** (tentativa - 1)))
                continue
            return r
        return r  # última tentativa, ainda com erro


def _ext(content_type: str | None, url: str) -> str:
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct == "application/pdf" or url.lower().endswith(".pdf"):
        return "pdf"
    if ct == "text/plain":
        return "txt"
    if "rtf" in ct or "ext=RTF" in url:
        return "rtf"
    if "json" in ct:
        return "json"
    return "html"


def coletar_incidente(incidente: int, *, blobs: Path = config.BLOBS, coletas: Path = config.COLETAS,
                      cliente: ClienteEducado | None = None, log: Callable[[str], None] = print) -> Path:
    """Executa uma coleta completa e devolve o caminho do registro JSONL."""
    c = cliente or ClienteEducado()
    bs = BlobStore(blobs)
    coleta_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{incidente}"
    reg = RegistroColeta(coletas, coleta_id)

    def gravar(aba: str, url: str, r: httpx.Response | None, entrada: dict) -> None:
        if r is None:
            reg.anotar({"incidente": incidente, "aba": aba, "url": url, "fetched_at": entrada["iniciada_em"],
                        "http_status": 0, "sha256": None, "bytes": 0, "raw_path": None, "erro": entrada.get("erro")})
            log(f"  {aba}: ERRO {entrada.get('erro')}")
            return
        ext = _ext(r.headers.get("content-type"), str(r.url))
        p = bs.gravar(r.content, ext=ext)
        reg.anotar({"incidente": incidente, "aba": aba, "url": url, "url_final": str(r.url),
                    "fetched_at": entrada["iniciada_em"], "http_status": r.status_code, "sha256": sha256(r.content),
                    "bytes": len(r.content), "raw_path": caminho_relativo(p, config.RAIZ), "content_type": r.headers.get("content-type"),
                    "user_agent": config.USER_AGENT, "redirects": entrada.get("redirects", []),
                    "esperou_s": entrada["esperou_s"]})
        log(f"  {aba}: {r.status_code} {len(r.content)} B (esperou {entrada['esperou_s']}s)")

    log(f"coleta {coleta_id}")
    r = c.get(config.ROBOTS_URL, aba="robots")
    gravar("robots", config.ROBOTS_URL, r, c.log[-1])

    url_casca = f"{config.BASE_PROCESSOS}verImpressao.asp?imprimir=true&incidente={incidente}"
    r = c.get(url_casca, aba="casca")
    gravar("casca", url_casca, r, c.log[-1])
    if r is None or r.status_code != 200:
        log("  casca indisponível; coleta encerrada")
        return reg.caminho

    casca = parse_casca(r.content)
    if casca.incidente != incidente:
        raise RuntimeError(f"casca devolvida é do incidente {casca.incidente}, pedido {incidente}")
    for aba, rel in casca.abas.items():
        url = urljoin(config.BASE_PROCESSOS, rel)
        r = c.get(url, aba=aba, referer=url_casca)
        gravar(aba, url, r, c.log[-1])

    # sessão virtual: a aba do portal carrega este JSON de outro host; seguimos a mesma dependência
    if "sessao" in casca.abas:
        _coletar_sessao(c, incidente, gravar)
    return reg.caminho


def _coletar_sessao(c: ClienteEducado, incidente: int, gravar) -> None:
    referer = f"{config.BASE_PROCESSOS}detalhe.asp?incidente={incidente}"
    url = url_oi(incidente)
    r = c.get(url, aba="votacao_json", referer=referer)
    gravar("votacao_json", url, r, c.log[-1])
    if r is not None and r.status_code == 200:
        try:
            objetos = parse_objetos_incidente(r.content)
        except ValueError:
            objetos = []
        for o in objetos:
            url = url_sessao(o.id)
            r2 = c.get(url, aba="sessao_virtual_json", referer=referer)
            gravar("sessao_virtual_json", url, r2, c.log[-1])


def coletar_sessao_virtual(incidente: int, *, blobs: Path = config.BLOBS, coletas: Path = config.COLETAS,
                           cliente: ClienteEducado | None = None, log: Callable[[str], None] = print) -> Path:
    """Só os JSONs de sessão virtual de um incidente já coletado (1 + N requisições)."""
    c = cliente or ClienteEducado()
    bs = BlobStore(blobs)
    coleta_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-sessao-{incidente}"
    reg = RegistroColeta(coletas, coleta_id)

    def gravar(aba: str, url: str, r: httpx.Response | None, entrada: dict) -> None:
        if r is None:
            reg.anotar({"incidente": incidente, "aba": aba, "url": url, "fetched_at": entrada["iniciada_em"],
                        "http_status": 0, "sha256": None, "bytes": 0, "raw_path": None, "erro": entrada.get("erro")})
            log(f"  {aba}: ERRO {entrada.get('erro')}")
            return
        p = bs.gravar(r.content, ext=_ext(r.headers.get("content-type"), str(r.url)))
        reg.anotar({"incidente": incidente, "aba": aba, "url": url, "url_final": str(r.url),
                    "fetched_at": entrada["iniciada_em"], "http_status": r.status_code, "sha256": sha256(r.content),
                    "bytes": len(r.content), "raw_path": caminho_relativo(p, config.RAIZ), "content_type": r.headers.get("content-type"),
                    "user_agent": config.USER_AGENT, "redirects": entrada.get("redirects", []), "esperou_s": entrada["esperou_s"]})
        log(f"  {aba}: {r.status_code} {len(r.content)} B")

    log(f"sessão virtual {coleta_id}")
    _coletar_sessao(c, incidente, gravar)
    return reg.caminho
