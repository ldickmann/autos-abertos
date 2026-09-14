# stf-mapeador

Camada de acesso estruturado a processos públicos do Supremo Tribunal Federal: coleta educada,
snapshots imutáveis, projeção SQLite com busca, proveniência em cada linha.

Não é um resumo com IA. É uma base auditável sobre a qual, mais tarde, uma camada semântica
classifica asserções em `fato_processual`, `alegacao_parte` ou `fundamento_decisorio`, sempre
com ponteiro para documento e página.

## Estado

| fase | estado | relatório |
|---|---|---|
| 0 — reconhecimento | concluída | [FASE0-RELATORIO.md](FASE0-RELATORIO.md) |
| 1 — ingestão determinística | concluída | [FASE1-RELATORIO.md](FASE1-RELATORIO.md) |
| 2 — grafo de processos e entidades | concluída | [FASE2-RELATORIO.md](FASE2-RELATORIO.md) |
| 3 — documentos | em andamento | |
| 4 — camada semântica | | |
| 5 — interface | | |

## Uso

```bash
python -m pip install -r requirements.txt
python -m pytest -q                       # 65 testes, offline
python -m stf coletar 7514886             # 11 requisições, ≥3 s entre elas, UA identificado
python -m stf buscar "prisao preventiva"
python -m stf diff <coleta_a> <coleta_b>
python -m stf reconstruir                 # recria o SQLite a partir dos blobs
python -m stf expandir 7514886 --profundidade 2   # resolve e coleta os processos relacionados
python -m stf grafo                       # lista de arestas + data/grafo.json
python -m stf cruzamentos                 # entidades em vários processos, relações, coincidências
```

Fonte de verdade: `data/raw/blobs/` (conteúdo por sha256) e `data/raw/coletas/*.jsonl`.
`data/stf.sqlite` é projeção derivada.

## Política de coleta

Ver [FASE0-RELATORIO.md, seção 2](FASE0-RELATORIO.md). Resumo: user-agent identificado com
contato em toda requisição, uma requisição por vez, intervalo mínimo de 3 s, backoff em 429/5xx,
sem descoberta automática, teto duro por execução. O `robots.txt` do portal desaconselha acesso
automatizado a `/processos`; a exceção adotada e seus limites estão documentados no relatório.
