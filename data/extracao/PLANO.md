# Fase 4 pelo Claude Code: plano de retomada por etapas

Estado em 14/09/2026 ~01:00 (BRT): 55 de 226 documentos extraídos, 1041 asserções validadas e publicadas.
Os 17 subagentes lançados de uma vez estouraram o limite de uso da sessão (429, reset às 3h10 BRT).

## Regras, tiradas da documentação oficial do Claude Code

- `docs/en/costs`: o limite "session limit" é a janela de uso do plano, **compartilhada entre modelos**; trocar de modelo não destrava. Reduzir uso: modelos mais baratos para tarefas simples, contexto pequeno, tarefas menores, `/compact` com instrução de foco, `/clear` entre tarefas não relacionadas.
- `docs/en/sub-agents`: cada subagente tem contexto próprio; "running many subagents that each return detailed results can consume significant context" → cada um devolve só um resumo de poucas linhas. O parâmetro `model` por invocação aceita `sonnet`, `haiku`, `opus`. Limite padrão de concorrência é 20, mas o usuário fixou **7**.
- `docs/en/interactive-mode`: ao bater o limite no meio de uma tarefa, o Claude Code espera na sessão aberta e continua sozinho após o reset (v2.1.234+, ligado por padrão em sessões claude.ai).

## Etapas (uma leva por vez; só lançar a próxima quando a anterior terminar)

| leva | lotes | agentes | modelo | conteúdo |
|---|---|---|---|---|
| A | 11, 12, 13, 14, 15 (divididos em pedaços de ≤12 docs) | 7 | `sonnet` | intimações, certidões, termos: 155 documentos curtos |
| B | 4, 5, 6, 7, 8 | 5 | `sonnet` | decisões e despachos médios (11 documentos) |
| C | 3, 2, doc 55 | 3 | `opus` | decisão de 24 p., voto vogal de 42 p., decisão de prisão preventiva de 48 p. |
| D | 0, 1 | 2 | `opus` | voto do relator 53 p., decisão monocrática 42 p. |

Após cada leva: `python -m stf ingerir-extracao` → `python -m stf exportar` → commit e push (o GitHub Pages publica).
Ao final: `python scripts/extracao_status.py` deve mostrar 226/226; então atualizar FASE4-RELATORIO.md.

## Comandos

```bash
python scripts/extracao_status.py      # o que falta, por lote, com tamanho
python -m stf preparar-extracao        # regenera entradas só do que falta (idempotente)
python -m stf ingerir-extracao         # valida e persiste respostas em data/extracao/respostas/
python -m stf exportar && git add -A && git commit -m "..." && git push
```

Antes de retomar em sessão longa: `/compact Preservar o estado da Fase 4 (lotes pendentes, comandos) e as decisões de projeto; descartar saídas de ferramentas antigas.`
