"""Carimbo de tempo independente do manifesto de integridade (OpenTimestamps).

Uso, a partir da raiz do projeto, depois de `python -m stf exportar`:

    python scripts/carimbar.py            # cria/atualiza INTEGRIDADE.sha256.ots e docs/carimbos/<data>-<raiz>.ots
    python scripts/carimbar.py --upgrade  # tenta completar provas pendentes (a âncora na Bitcoin leva algumas horas)
    python scripts/carimbar.py --verify   # verifica todas as provas guardadas

O que isso prova: que o arquivo INTEGRIDADE.sha256 (e, por ele, cada hash do manifesto) existia na data do carimbo.
Não depende de quem guarda os arquivos: a prova é verificável offline contra a cadeia da Bitcoin. Os calendários
públicos do OpenTimestamps (alice/bob.btc.calendar.opentimestamps.org, finney.calendar.eternitywall.com) recebem
só o hash, nunca o conteúdo.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ALVO = RAIZ / "INTEGRIDADE.sha256"
PASTA = RAIZ / "docs" / "carimbos"


def _ambiente() -> dict:
    """No Windows, python-bitcoinlib procura 'ssl.dll' pelo PATH; o Git para Windows traz o OpenSSL como libcrypto-3-x64.dll.
    Expõe uma cópia com o nome esperado numa pasta temporária, só para o processo do ots."""
    env = dict(os.environ)
    if sys.platform == "win32":
        origem = Path(r"C:/Program Files/Git/mingw64/bin/libcrypto-3-x64.dll")
        if origem.exists():
            shim = Path(tempfile.gettempdir()) / "ots-shim"
            shim.mkdir(exist_ok=True)
            for nome in ("ssl.dll", "libcrypto-3-x64.dll"):
                if not (shim / nome).exists():
                    shutil.copy(origem, shim / nome)
            env["PATH"] = str(shim) + os.pathsep + env.get("PATH", "")
    return env


def ots(*args: str) -> int:
    exe = shutil.which("ots") or str(Path(sys.executable).parent / "Scripts" / "ots.exe")
    print("$ ots", " ".join(args))
    return subprocess.call([exe, *args], cwd=RAIZ, env=_ambiente())


def main() -> int:
    PASTA.mkdir(parents=True, exist_ok=True)
    if "--verify" in sys.argv:
        rc = 0
        for prova in sorted(PASTA.glob("*.ots")):
            original = PASTA / prova.name[:-4]
            if original.exists():
                rc |= ots("verify", "-f", str(original), str(prova))
        return rc
    if "--upgrade" in sys.argv:
        rc = 0
        for prova in sorted(PASTA.glob("*.ots")):
            rc |= ots("upgrade", str(prova))
        return rc
    if not ALVO.exists():
        print("INTEGRIDADE.sha256 não existe; rode `python -m stf exportar` antes.")
        return 1
    raiz = ALVO.read_text("utf-8").split()[0]
    data = ALVO.read_text("utf-8").split("gerado_em=")[-1].strip()[:10]
    copia = PASTA / f"{data}-{raiz[:12]}.sha256"
    copia.write_bytes(ALVO.read_bytes())
    prova = copia.with_suffix(".sha256.ots")
    if prova.exists():
        print(f"já carimbado: {prova.name}")
        return 0
    rc = ots("stamp", str(copia))
    if rc == 0 and prova.exists():
        print(f"prova criada: {prova.relative_to(RAIZ)} (sha256 do arquivo carimbado: {hashlib.sha256(copia.read_bytes()).hexdigest()[:16]}…)")
        print("A prova fica completa quando o calendário ancorar na Bitcoin; rode `python scripts/carimbar.py --upgrade` mais tarde.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
