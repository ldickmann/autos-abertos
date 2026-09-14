"""Pede ao Wayback Machine (Internet Archive) uma cópia das páginas públicas do site e dos arquivos-chave do repositório.

Uso: python scripts/arquivar.py            # tenta salvar cada URL e grava docs/wayback.json (append)
     python scripts/arquivar.py --checar   # consulta se já existe cópia de cada URL (API de disponibilidade)

Não precisa de conta. O serviço "Save Page Now" às vezes responde 429/500; basta rodar de novo mais tarde.
Para depositar o pacote completo (release .zip) como item do archive.org, é preciso uma conta: ver docs/ESPELHOS.md.
"""

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SITE = "https://ldickmann.github.io/autos-abertos"
REPO = "https://github.com/ldickmann/autos-abertos"
URLS = [f"{SITE}/", f"{SITE}/verificar/", f"{SITE}/decisoes/", f"{SITE}/linha-do-tempo/", f"{SITE}/mudancas/", f"{SITE}/glossario/",
        f"{SITE}/sobre/", f"{SITE}/processo/7514886/", f"{SITE}/data/integridade.json", f"{SITE}/data/decisoes.json", f"{SITE}/data/meta.json",
        REPO, f"{REPO}/releases/latest", "https://raw.githubusercontent.com/ldickmann/autos-abertos/main/INTEGRIDADE.sha256",
        "https://raw.githubusercontent.com/ldickmann/autos-abertos/main/CHANGELOG-PORTAL.md"]
UA = {"User-Agent": "autos-abertos/0.1 (+mailto:ldickmann12@gmail.com)"}
SAIDA = RAIZ / "docs" / "wayback.json"


def checar(u: str) -> str | None:
    req = urllib.request.Request("https://archive.org/wayback/available?url=" + u, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    s = d.get("archived_snapshots", {}).get("closest")
    return s["url"] if s and s.get("available") else None


def salvar(u: str) -> tuple[int | None, str | None]:
    req = urllib.request.Request("https://web.archive.org/save/" + u, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            loc = r.headers.get("Content-Location") or ""
            return r.status, ("https://web.archive.org" + loc if loc.startswith("/web/") else r.geturl())
    except urllib.error.HTTPError as e:
        return e.code, None


def main() -> int:
    historico = json.loads(SAIDA.read_text("utf-8")) if SAIDA.exists() else []
    rodada = {"em": datetime.now(timezone.utc).isoformat(timespec="minutes"), "modo": "checar" if "--checar" in sys.argv else "salvar", "urls": []}
    ok = 0
    for u in URLS:
        try:
            if "--checar" in sys.argv:
                copia = checar(u); status = 200 if copia else 404
            else:
                status, copia = salvar(u)
        except Exception as e:  # noqa: BLE001
            status, copia = None, None
            print("erro", u, str(e)[:80])
        rodada["urls"].append({"url": u, "status": status, "copia": copia})
        print("ok  " if copia else "--  ", status, u, "→", (copia or "")[:80])
        ok += bool(copia)
        time.sleep(3 if "--checar" in sys.argv else 8)
    historico.append(rodada)
    SAIDA.write_text(json.dumps(historico, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print(f"{ok} de {len(URLS)} com cópia; registro em {SAIDA.relative_to(RAIZ)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
