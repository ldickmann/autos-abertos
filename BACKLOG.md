# Fila de trabalho

Ordem de execução decidida em 14/09/2026. Cada item vira commit próprio; o site republica a cada push.

| # | item | estado | notas |
|---|---|---|---|
| 1 | Fase 4: extrair os 226 documentos via Claude Code | leva A feita (155 docs curtos); leva B (16 docs longos) em andamento; doc 25 reextraído após correção do texto | plano em `data/extracao/PLANO.md`; próximas levas com o subagente `extrator` (`.claude/agents/extrator.md`, `claude-opus-4-8`), que só é carregado em sessão nova |
| 2 | Análise dos dados e cruzamentos | feita: `ANALISE-DADOS.md`; C1–C4 em `stf/referencias.py`, C6–C9 no grafo e no export | pendentes da análise: classificação de função do documento por LLM (item 4.2), propostas de alias (4.3), pedidos/resultados por decisão (4.4) |
| 3 | Grafo: navegação e leitura visual | feito (commit f9cc78e) | legenda, camadas, busca, ficha com fontes, caminho mais curto, dois layouts; melhorar: rótulos sobrepostos em telas estreitas, painel como folha inferior no celular |
| 4 | Frontend: versão escura, minimalista, microinterações 3D | feito (padrão escuro, alternância, Newsreader + IBM Plex, folhas, carimbo) | revisar página inicial como "capa dos autos"; auditar contraste WCAG no tema escuro |
| 5 | Auditoria de links após o rename | feita | URL antiga do Pages devolve 404; `github.com/ldickmann/nao-definido` redireciona |
| 6 | Pet 15719 (profundidade 3) | coleta em andamento (`expandir --profundidade 3`) | depois: `baixar-docs --incidente 7536897`, `extrair-texto`, `preparar-extracao`, uma leva pequena |
| 7 | Atualizar `FASE4-RELATORIO.md` ao fechar a Fase 4 | a fazer | refletir execução pelo Claude Code, contagens e estatísticas de validação (descartes por trecho) |
| 8 | Texto duplicado em PDFs com negrito simulado | corrigido em `stf/documentos.py` (`dedupe_chars`) | só o doc 25 era afetado; resposta antiga guardada em `respostas/_invalidas/` |

## Restrições que valem para todos os itens

- Proveniência obrigatória; tipagem epistêmica; append-only; coleta educada; sem inferência sobre pessoas (ver `README.md`).
- No máximo 7 subagentes por vez; levas sequenciais; Opus para extração (pedido do usuário em 14/09).
- Nenhuma fase é dada como concluída com teste falhando.
