"""Fase 0, passada 2 — as nove abas do verImpressao.asp e um PDF.

Motivo desta segunda passada: a passada 1 (fase0.py) mostrou que verImpressao.asp é
uma casca. As abas são carregadas pelo navegador via jQuery a partir de nove endpoints
aba*.asp. Abrir a página uma vez no navegador dispara exatamente estas requisições.
Aqui elas são feitas em sequência, ≥3 s entre cada, com UA identificado.

Teto desta execução: 12 requisições (9 abas + 1 PDF + margem para redirects).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fase0  # noqa: E402  (reutiliza PoliteClient, análise e utilidades)

fase0.MAX_REQUESTS = 12

INC = fase0.INCIDENTE
BASE_PROC = f"{fase0.BASE}/processos/"
ABAS = {
    "informacoes": f"abaInformacoes.asp?incidente={INC}",
    "partes": f"abaPartes.asp?incidente={INC}",
    "andamentos": f"abaAndamentos.asp?incidente={INC}&imprimir=true",
    "decisoes": f"abaDecisoes.asp?incidente={INC}",
    "sessao": f"abaSessao.asp?incidente={INC}&tema=N",
    "deslocamentos": f"abaDeslocamentos.asp?incidente={INC}",
    "peticoes": f"abaPeticoes.asp?incidente={INC}",
    "recursos": f"abaRecursos.asp?incidente={INC}",
    "pautas": f"abaPautas.asp?incidente={INC}",
}


def main() -> None:
    log: list[dict] = []
    run_at = fase0.utcnow()
    tag = fase0.ts_tag(run_at)
    inc_dir = fase0.RAW / INC / "abas"
    pc = fase0.PoliteClient(log)
    results: dict = {"run_at": run_at.isoformat(), "incidente": INC, "abas": {}}

    print("B2. nove abas")
    saved: dict[str, Path] = {}
    for nome, rel in ABAS.items():
        url = BASE_PROC + rel
        r = pc.get(url, ua=fase0.UA_IDENT, tag=f"aba/{nome}", referer=fase0.VERIMPRESSAO)
        if r is None:
            results["abas"][nome] = {"error": log[-1].get("error")}
            continue
        fname = inc_dir / f"{tag}_{nome}.html"
        fase0.write_new(fname, r.content)
        meta = {
            "url": url, "final_url": str(r.url), "fetched_at": log[-1]["started_at"],
            "sha256": fase0.sha256(r.content), "http_status": r.status_code, "bytes": len(r.content),
            "charset": r.charset_encoding, "content_type": r.headers.get("content-type"),
            "request_headers": {"User-Agent": fase0.UA_IDENT, "From": fase0.CONTATO, "Referer": fase0.VERIMPRESSAO},
            "response_headers": dict(r.headers), "redirects": log[-1]["redirects"],
            "raw_path": str(fname.relative_to(fase0.ROOT)),
        }
        fase0.write_meta(fname.with_suffix(".meta.json"), meta)
        results["abas"][nome] = {k: meta[k] for k in ("http_status", "sha256", "bytes", "charset", "content_type", "raw_path")}
        if r.status_code == 200:
            saved[nome] = fname

    print("C2. análise offline por aba")
    analises = {}
    for nome, path in saved.items():
        charset = json.loads(path.with_suffix(".meta.json").read_text("utf-8")).get("charset")
        analises[nome] = fase0.analyze_html(path.read_bytes(), charset)
    results["analises"] = analises

    print("D2. um PDF de inteiro teor da aba Decisões")
    docs = analises.get("decisoes", {}).get("links_documento_amostra") or []
    pref = [d for d in docs if re.search(r"inteiro|teor|decis|pdf|peca", d["abs"] + d["text"], re.I)] or docs
    if not pref:
        results["pdf"] = {"error": "nenhum link de documento na aba Decisões"}
    else:
        alvo = pref[0]
        r = pc.get(alvo["abs"], ua=fase0.UA_IDENT, tag="pdf", referer=fase0.VERIMPRESSAO)
        if r is None:
            results["pdf"] = {"error": log[-1].get("error"), "link": alvo}
        else:
            is_pdf = r.content.startswith(b"%PDF-")
            digest = fase0.sha256(r.content)
            fname = fase0.RAW / INC / "docs" / (f"{digest}.pdf" if is_pdf else f"{digest}.resp.html")
            fase0.write_new(fname, r.content)
            meta = {
                "link": alvo, "final_url": str(r.url), "fetched_at": log[-1]["started_at"],
                "sha256": digest, "http_status": r.status_code, "bytes": len(r.content),
                "content_type": r.headers.get("content-type"),
                "content_disposition": r.headers.get("content-disposition"),
                "redirects": log[-1]["redirects"], "is_pdf_magic": is_pdf,
                "cookies_na_sessao": sorted(pc.client.cookies.keys()),
                "raw_path": str(fname.relative_to(fase0.ROOT)),
            }
            fase0.write_meta(Path(str(fname) + ".meta.json"), meta)
            results["pdf"] = meta
            if is_pdf:
                print("E2. camada de texto")
                results["pdf_texto"] = fase0.pdf_text_probe(fname)
            else:
                results["pdf_texto"] = {"skip": "resposta não é PDF",
                                        "inicio": r.content[:600].decode("utf-8", "replace")}

    results["request_log"] = log
    out = fase0.ROOT / "recon" / f"fase0-abas-resultado_{tag}.json"
    fase0.write_new(out, json.dumps(results, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
    print(f"\nresultado: {out.relative_to(fase0.ROOT)}  ({pc.count} requisições ao portal)")


if __name__ == "__main__":
    main()
