"""Acesso anônimo ao compartilhamento SharePoint do STF (peças de processos com sigilo levantado).
Uso: python sp_stf.py inventario  -> grava inventario.tsv
     python sp_stf.py baixar <ServerRelativeUrl> [destino]
"""
import sys, json, time, hashlib, urllib.parse
from pathlib import Path
import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
# Links publicados pelo STF em https://noticias.stf.jus.br/postsnoticias/stf-disponibiliza-documentos-e-pecas-de-processos-que-sigilos-foram-levantados/
SHARES = {
    "Arquivos Pet 16704": "https://stfjusbr.sharepoint.com/:f:/s/STI--CRCS/IgDNcXLZ-Q0SQaDPoCO8FWPyAX1MERPDqK0aWoll9fKADYc",
    "Arquivos Pet 16669": "https://stfjusbr.sharepoint.com/:f:/s/STI--CRCS/IgAak7_eEjyzQp4i0cZywHQeAf4Aifugd-e97tX5NNCTC-A?e=SOTiIM",
}
SHARE = SHARES["Arquivos Pet 16704"]
HOST = "https://stfjusbr.sharepoint.com"
SITE = HOST + "/sites/STI--CRCS"
BASE = "/sites/STI--CRCS/Shared Documents/-CRCS/Compartilhamento Externo/Processos Judiciais/Arquivos Pet 16704"
SCR = Path(__file__).resolve().parent.parent / "recon" / "stf-docspublicos"

def cliente(share=SHARE):
    c = httpx.Client(headers={"User-Agent": UA, "From": "ldickmann12@gmail.com", "Accept": "*/*"}, timeout=120, follow_redirects=True)
    r = c.get(share, headers={"Accept": "text/html,*/*"}); r.raise_for_status()
    assert "FedAuth" in c.cookies, "sem cookie FedAuth"
    return c

def listar(c, rel):
    api = SITE + "/_api/web/GetFolderByServerRelativeUrl('" + urllib.parse.quote(rel).replace("'", "''") + "')?$expand=Folders,Files&$select=Folders/Name,Files/Name,Files/Length,Files/TimeLastModified,Files/ServerRelativeUrl&$top=5000"
    r = c.get(api, headers={"Accept": "application/json;odata=nometadata"}); r.raise_for_status()
    return r.json()

def inventario(c):
    out = []
    def walk(rel):
        j = listar(c, rel)
        for f in j.get("Files", []):
            out.append((rel[len(BASE)+1:], f["Name"], int(f["Length"]), f["TimeLastModified"], f["ServerRelativeUrl"]))
        for d in j.get("Folders", []):
            if d["Name"] == "Forms": continue
            time.sleep(0.3); walk(rel + "/" + d["Name"])
    walk(BASE)
    return out

def baixar(c, rel, destino):
    api = SITE + "/_api/web/GetFileByServerRelativeUrl('" + urllib.parse.quote(rel).replace("'", "''") + "')/$value"
    with c.stream("GET", api) as r:
        r.raise_for_status()
        h = hashlib.sha256(); n = 0
        destino.parent.mkdir(parents=True, exist_ok=True)
        with open(destino, "wb") as fh:
            for chunk in r.iter_bytes(1 << 20):
                fh.write(chunk); h.update(chunk); n += len(chunk)
    return n, h.hexdigest()

if __name__ == "__main__":
    cmd = sys.argv[1]
    pasta = sys.argv[2] if cmd == "inventario" and len(sys.argv) > 2 else None
    if pasta:  # pasta irmã, ex.: "Arquivos Pet 16669"
        BASE = BASE.rsplit("/", 1)[0] + "/" + pasta
        globals()["BASE"] = BASE
    c = cliente(SHARES.get(pasta or "Arquivos Pet 16704", SHARE))
    if cmd == "inventario":
        inv = inventario(c)
        p = SCR / ("inventario-" + BASE.rsplit("/", 1)[1].replace(" ", "_") + ".tsv")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("pasta\tnome\tbytes\tmodificado\turl\n")
            for row in inv: fh.write("\t".join(map(str, row)) + "\n")
        print(len(inv), "arquivos ->", p)
    elif cmd == "baixar":
        rel = sys.argv[2]
        dest = Path(sys.argv[3]) if len(sys.argv) > 3 else SCR / "sigilo" / Path(rel).name
        n, sha = baixar(c, rel, dest)
        print(n, sha, dest)
