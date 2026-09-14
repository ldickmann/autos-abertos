# Fila de trabalho

Ordem de execução decidida em 14/09/2026. Cada item vira commit próprio; o site republica a cada push.

| # | item | estado | notas |
|---|---|---|---|
| 1 | Fase 4: extrair os 226 documentos via Claude Code | feita (14/09/2026): 226/226 docs, 2430 asserções (646 alegações, 1067 fatos, 717 fundamentos), 6 descartadas por trecho | plano em `data/extracao/PLANO.md`; próximas levas com o subagente `extrator` (`.claude/agents/extrator.md`, `claude-opus-4-8`), que só é carregado em sessão nova |
| 2 | Análise dos dados e cruzamentos | feita: `ANALISE-DADOS.md`; C1–C4 em `stf/referencias.py`, C6–C9 no grafo e no export; 4.2 e 4.3 feitos sem modelo (14/09, seção 6) | pendente: 4.4 pedidos/resultados por decisão (prompt v2 + ~95 docs via subagentes `extrator`) |
| 3 | Grafo: navegação e leitura visual | feito (commit f9cc78e); folha inferior e rótulos compactos no celular feitos (14/09) | legenda, camadas, busca, ficha com fontes, caminho mais curto, dois layouts; em tela estreita rótulo só para 5+ ligações, vizinhos do foco sempre rotulados |
| 4 | Frontend: versão escura, minimalista, microinterações 3D | feito; contraste WCAG auditado; página inicial como "capa dos autos" (14/09) | — |
| 5 | Auditoria de links após o rename | feita | URL antiga do Pages devolve 404; `github.com/ldickmann/nao-definido` redireciona |
| 6 | Pet 15719 (profundidade 3) | feita: coleta `20260914T071922Z-7536897` ingerida | processo **sigiloso**: o portal devolve 4 andamentos, 0 partes, 0 documentos; nada a baixar ou extrair |
| 7 | Atualizar `FASE4-RELATORIO.md` ao fechar a Fase 4 | feito (14/09/2026) | execução pelo Claude Code, números, limitações, como repetir |
| 9 | Responsividade | feita (14/09/2026): nav em trilho até `lg`, tabelas viram folhas abaixo de `md`, grafo com canvas primeiro e ficha como folha inferior, filtros recolhidos no celular, formulários em grade | nenhuma página estoura a largura em 375/768; checar em aparelho real |
| 10 | Versionamento | feito (14/09/2026): `develop` padrão, `main` publica, branches `feat/`, `fix/`, `chore/`, `docs/` | convenção no `README.md` |
| 8 | Texto duplicado em PDFs com negrito simulado | corrigido em `stf/documentos.py` (`dedupe_chars`) | só o doc 25 era afetado; resposta antiga guardada em `respostas/_invalidas/` |

## Restrições que valem para todos os itens

- Proveniência obrigatória; tipagem epistêmica; append-only; coleta educada; sem inferência sobre pessoas (ver `README.md`).
- No máximo 7 subagentes por vez; levas sequenciais; Opus para extração (pedido do usuário em 14/09).
- Nenhuma fase é dada como concluída com teste falhando.
