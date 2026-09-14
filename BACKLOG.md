# Fila de trabalho

Ordem de execução decidida em 14/09/2026. Cada item vira commit próprio; o site republica a cada push.

| # | item | estado | notas |
|---|---|---|---|
| 1 | Fase 4: extrair os 171 documentos restantes via Claude Code | leva A em andamento (155 docs curtos, 7 subagentes `sonnet`) | plano em `data/extracao/PLANO.md`; depois levas B, C, D |
| 2 | Análise completa dos dados: o que dá para cruzar, o que falta no banco, o que um LLM pode ampliar | a fazer (prioridade do usuário) | produto: `ANALISE-DADOS.md` com achados + implementação dos cruzamentos viáveis (novas tabelas/projeções, export para o grafo) |
| 3 | Grafo: navegação e leitura visual | a fazer | hoje é difícil entender as ligações; precisa de legenda, foco por nó, filtros por tipo de relação, caminhos entre entidades, layout que separe processos de pessoas/órgãos |
| 4 | Frontend: versão escura, minimalista, com microinterações 3D | a fazer | tema escuro como padrão do sistema, toggle; transições e profundidade sutis (hover/foco/expansão), sem comprometer acessibilidade nem contraste |
| 5 | Auditoria de links e botões após o rename | feita em 14/09 | código-fonte, dados exportados e HTML publicado não citam mais o repositório antigo; a URL antiga do Pages devolve 404 (GitHub não redireciona Pages) e `github.com/ldickmann/nao-definido` redireciona (301) para o novo |
| 6 | Atualizar `FASE4-RELATORIO.md` ao fechar a Fase 4 | a fazer | refletir execução pelo Claude Code, contagens e estatísticas de validação |

## Restrições que valem para todos os itens

- Proveniência obrigatória; tipagem epistêmica; append-only; coleta educada; sem inferência sobre pessoas (ver `README.md`).
- No máximo 7 subagentes por vez; levas sequenciais; `sonnet`/`haiku` para tarefas simples.
- Nenhuma fase é dada como concluída com teste falhando.
