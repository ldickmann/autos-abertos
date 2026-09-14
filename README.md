# Autos Abertos

Site público: https://ldickmann.github.io/autos-abertos/ · código: https://github.com/ldickmann/autos-abertos

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
| 3 — documentos | concluída | [FASE3-RELATORIO.md](FASE3-RELATORIO.md) |
| 4 — camada semântica | concluída pelo Claude Code (226/226 documentos, 2430 asserções) | [FASE4-RELATORIO.md](FASE4-RELATORIO.md) |
| 5 — interface | concluída (export estático) | [FASE5-RELATORIO.md](FASE5-RELATORIO.md) |

## Uso

```bash
python -m pip install -r requirements.txt
python -m pytest -q                       # 86 testes, offline
python -m stf coletar 7514886             # 11 requisições, ≥3 s entre elas, UA identificado
python -m stf buscar "prisao preventiva"
python -m stf diff <coleta_a> <coleta_b>
python -m stf reconstruir                 # recria o SQLite a partir dos blobs
python -m stf expandir 7514886 --profundidade 2   # resolve e coleta os processos relacionados
python -m stf grafo                       # lista de arestas + data/grafo.json
python -m stf cruzamentos                 # entidades em vários processos, relações, coincidências
python -m stf baixar-docs                 # documentos (cache por sha256) + texto por página
python -m stf buscar-docs "sisbajud"      # FTS5 no texto dos documentos
python -m stf extrair-assercoes --dry-run # Fase 4 (exige ANTHROPIC_API_KEY para rodar de verdade)
python -m stf exportar                    # JSON estático para a interface
cd web && npm ci && npm run build         # site estático em web/out
```

Fonte de verdade: `data/raw/blobs/` (conteúdo por sha256) e `data/raw/coletas/*.jsonl`.
`data/stf.sqlite` é projeção derivada.

## Política de coleta

Ver [FASE0-RELATORIO.md, seção 2](FASE0-RELATORIO.md). Resumo: user-agent identificado com
contato em toda requisição, uma requisição por vez, intervalo mínimo de 3 s, backoff em 429/5xx,
sem descoberta automática, teto duro por execução. O `robots.txt` do portal desaconselha acesso
automatizado a `/processos`; a exceção adotada e seus limites estão documentados no relatório.

## Versionamento

Duas branches permanentes e branches curtas por tarefa (adotado em 14/09/2026):

- `main` — branch padrão; o que está publicado. Só recebe merge de `develop`; cada push republica o site no GitHub Pages.
- `develop` — integração: as branches de tarefa nascem e voltam para cá; PRs miram `develop`.
- `<tipo>/<assunto-curto>` — uma por tarefa, criada a partir de `develop` e mesclada de volta com
  `--no-ff`. Tipos: `feat/` (funcionalidade), `fix/` (correção), `chore/` (dados, fila, manutenção),
  `docs/` (relatórios e documentação), `refactor/`.

Fluxo: `git switch -c feat/x develop` → commits → `git switch develop && git merge --no-ff feat/x`
→ quando `develop` estiver pronta para publicar, `git switch main && git merge --no-ff develop && git push`.
Mensagens de commit no imperativo, em português, com o escopo no início quando ajudar
(`Fase 4: …`, `Interface: …`).

## Preservação e verificação

O propósito é que os autos públicos continuem acessíveis, íntegros e verificáveis por qualquer pessoa, sem depender de um único provedor.

- **Originais versionados**: os blobs de `data/raw/blobs/` (páginas do portal e PDFs, nomeados pelo próprio sha256) e os registros de coleta estão no repositório. Clonar é espelhar.
- **Manifesto de integridade**: `web/public/data/integridade.json` lista URL de origem, data e sha256 de cada cópia; o hash do manifesto fica em `INTEGRIDADE.sha256`. `python -m stf verificar` confere os blobs locais. A página `/verificar` do site explica como qualquer pessoa confere um documento com o próprio STF.
- **O que mudou no portal**: `python -m stf vigiar` recoleta cada processo e registra em `CHANGELOG-PORTAL.md` (append-only) o que sumiu, apareceu ou mudou; a página `/mudancas` mostra o mesmo.
- **Reproduzir do zero**: [docs/REPRODUZIR.md](docs/REPRODUZIR.md). **Réplica do site**: `web/out/` é estático; sirva a pasta de onde quiser.
- **Neutralidade**: `tests/test_neutralidade.py` falha se algum texto gerado ou editorial contiver juízo sobre pessoas. O site registra o que consta nos autos; não conclui nada sobre ninguém.

