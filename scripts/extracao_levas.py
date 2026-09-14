"""Gera arquivos de instrução por subagente para uma leva da Fase 4.

Uso: python scripts/extracao_levas.py <nome-da-leva> <lotes separados por vírgula> <n_agentes>
Ex.: python scripts/extracao_levas.py A 11,12,13,14,15 7

Lê LOTES.json + MANIFEST.json, pega só os documentos ainda sem extração válida,
distribui em <n_agentes> pedaços de tamanho parecido (em caracteres) e escreve
data/extracao/entradas/LEVA-<nome>-<k>.md com caminhos absolutos do diretório atual.
"""

import json
import pathlib
import sqlite3
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ENTRADAS = RAIZ / "data" / "extracao" / "entradas"
RESPOSTAS = RAIZ / "data" / "extracao" / "respostas"


def main() -> None:
    nome, lotes_arg, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
    lotes_sel = [int(x) for x in lotes_arg.split(",")]
    con = sqlite3.connect(RAIZ / "data" / "stf.sqlite")
    feitos = {r[0] for r in con.execute("SELECT documento_id FROM extracao WHERE status='ok'")}
    lotes = json.loads((ENTRADAS / "LOTES.json").read_text("utf-8"))
    manifesto = {d["id"]: d for d in json.loads((ENTRADAS / "MANIFEST.json").read_text("utf-8"))["documentos"]}
    pendentes = [i for k in lotes_sel for i in lotes[k] if i not in feitos and i in manifesto]
    # maiores primeiro, distribuídos ao pedaço com menos caracteres acumulados
    pendentes.sort(key=lambda i: -manifesto[i]["chars"])
    pedacos: list[list[int]] = [[] for _ in range(n)]
    carga = [0] * n
    for i in pendentes:
        k = carga.index(min(carga))
        pedacos[k].append(i)
        carga[k] += manifesto[i]["chars"]
    for k, docs in enumerate(pedacos, start=1):
        if not docs:
            continue
        linhas = [f"# Leva {nome}, pedaço {k}: {len(docs)} documento(s), {sum(manifesto[i]['chars'] for i in docs)} caracteres", "",
                  "Para CADA documento abaixo: leia o arquivo de entrada inteiro e grave a resposta JSON no caminho indicado.", ""]
        for i in sorted(docs):
            d = manifesto[i]
            linhas.append(f"- doc {i}: {d['titulo']} ({d['processo']}, {d['paginas']} p., {d['chars']} chars) — entrada `{ENTRADAS / d['entrada']}` → resposta `{RESPOSTAS / d['resposta']}`")
        (ENTRADAS / f"LEVA-{nome}-{k}.md").write_text("\n".join(linhas) + "\n", "utf-8")
        print(f"LEVA-{nome}-{k}.md: {len(docs)} docs, {carga[k-1]} chars")
    print(f"total: {len(pendentes)} documentos pendentes nos lotes {lotes_sel}")


if __name__ == "__main__":
    main()
