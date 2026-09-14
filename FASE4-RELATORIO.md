# FASE 4 — Relatório: camada semântica (construída; execução bloqueada por credencial)

Construída em 14/09/2026, com 8 testes usando cliente simulado. **Não executada contra a API**: não há `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` nem perfil do `ant auth login` nesta máquina. É a única coisa que depende de você nesta fase, porque envolve custo.

## 1. O que está pronto

```
stf/prompts/extracao_v1.md   prompt versionado; prompt_version = extracao_v1-30ce0b328385 (nome + sha256 do conteúdo)
stf/semantica.py             schema Pydantic (Extracao → AssercaoExtraida → EntidadeCitada), validação, cache, persistência
tabelas: extracao, assercao, assercao_entidade; entidade.origem ('partes' | 'documento')
CLI: extrair-assercoes [--documentos 55,4,39] [--limite N] [--dry-run] [--modelo] [--effort]; assercoes
```

Fluxo por documento: texto por página com marcadores `[página N]` → uma chamada à API (Opus 5, saída estruturada por JSON Schema, streaming, prompt com cache) → resposta bruta gravada em blob → validação determinística → persistência só do que passou.

## 2. Como as restrições viram código

| restrição | mecanismo | teste |
|---|---|---|
| 1. Proveniência obrigatória; saída sem ponteiro é **descartada, não revisada** | cada asserção precisa de `pagina` existente e `trecho_fonte` (≤300 caracteres) presente literalmente na página, comparado sem diferença de espaço ou caixa. O que falha vai para `extracao.descartadas_json` com o motivo e não entra em `assercao` | `test_validar_descarta_sem_ponteiro_rastreavel` |
| 2. Tipagem epistêmica em exatamente um de três tipos; sem confiança, não entra | `Literal["fato_processual","alegacao_parte","fundamento_decisorio"]` no schema; `CHECK` na tabela; o prompt manda omitir na dúvida. Qualquer outro valor rejeita a resposta inteira (`schema_invalido`) | `test_validar_rejeita_json_malformado_e_tipo_invalido` |
| JSON estrito, malformado é rejeitado, não remendado | `json.loads` + `model_validate`; falha → `extracao.status = rejeitada:<motivo>`, zero asserções | `test_resposta_malformada_registra_rejeicao_e_nao_persiste_nada` |
| cache por documento e versão do prompt | chave `(documento, sha256 do blob, prompt_version, modelo)`; reprocessa só se algo mudar | `test_cache_nao_reprocessa_sem_mudanca` |
| resolução canônica de entidades | nome normalizado → `entidade` existente (partes) ou nova com `origem='documento'` (status "terceiro mencionado") | `test_entidades_resolvem_para_canonicas_ou_viram_terceiro_mencionado` |
| 5. Nada sobre conduta, caráter ou intenção | o prompt proíbe explicitamente; o schema não tem campo para conclusão; `atribuida_a` obriga a alegação a ter autor | (estrutural) |

## 3. Calibração proposta (3 documentos), pendente de credencial

| id | documento | páginas | por que |
|---|---|---|---|
| 55 | Decisão monocrática de 04/03/2026 (prisão preventiva), Pet 15556 | 48 | o documento central; mistura alegações da PF, provas apontadas e dispositivo |
| 4 | Despacho de 25/08/2026, Pet 15556 | 2 | caso mínimo: um fato processual, uma vista à PGR |
| 39 | Decisão de Julgamento do referendo (RTF), Pet 15556 | 1 | texto colegiado curto; testa `fundamento_decisorio` atribuído à Turma |

`python -m stf extrair-assercoes --documentos 55,4,39` roda a calibração e `python -m stf assercoes` lista o resultado para você avaliar o prompt. Estimativa (4 caracteres por token): 25 mil tokens de entrada; custo abaixo de US$ 2.

Corpus inteiro (226 documentos, ~250 mil tokens de texto): entrada ~US$ 2 (prompt em cache), saída e raciocínio adaptativo entre US$ 10 e US$ 35. **Estimativa: US$ 15 a 40 no Opus 5.** Com Sonnet 5 cai para cerca de um terço; a escolha é sua.

## 4. Para rodar

```bash
export ANTHROPIC_API_KEY=...        # ou `ant auth login`
python -m stf extrair-assercoes --documentos 55,4,39
python -m stf assercoes
# depois de calibrar o prompt (nova versão = extracao_v2.md; a v1 fica no histórico):
python -m stf extrair-assercoes
python -m stf exportar && cd web && npm run build
```

Nada muda nas fases anteriores nem na interface: as páginas de asserções, entidades e documentos já leem `assercoes.json` e hoje mostram, com destaque, que a camada semântica ainda não foi executada.
