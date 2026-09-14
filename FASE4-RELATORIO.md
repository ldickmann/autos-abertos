# FASE 4 — Relatório: camada semântica (executada pelo Claude Code, sem API)

Construída em 14/09/2026 com 8 testes usando cliente simulado; **executada no mesmo dia pelo Claude Code** (plano Max, sem `ANTHROPIC_API_KEY`), com subagentes lendo os documentos e gravando um JSON por documento, validado pela mesma rotina que serviria à API. Resultado: **226 de 226 documentos, 2430 asserções validadas**, 20 descartadas por trecho não rastreável, nenhuma resposta rejeitada.

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

## 3. Como foi executado (sem API)

A rota original (`extrair-assercoes`, uma chamada à API por documento) ficou pronta mas não foi usada: não havia credencial e o custo estimado era de US$ 15 a 40. Em vez disso, dois comandos novos fazem o Claude Code cumprir o mesmo contrato:

```
preparar-extracao   grava data/extracao/entradas/<id>.entrada.md (instruções + schema + texto com [página N]) e MANIFEST.json,
                    só para os documentos ainda sem extração; agrupa em lotes por tamanho e gera LEVA-*.md
ingerir-extracao    lê data/extracao/respostas/<id>.json e passa pela MESMA validação da rota da API
                    (página existente, trecho literal, tipo epistêmico, JSON estrito); persiste só o que passou
```

Cada leva foi um conjunto de subagentes (`.claude/agents/extrator.md`, Opus; no máximo 7 por vez, sequenciais), cada um responsável por uma `LEVA-*.md` e devolvendo só um resumo de poucas linhas. O modelo gravado em `extracao.modelo` é `claude-code/claude-opus-5` e o `prompt_version` é o mesmo da rota da API (`extracao_v1-30ce0b328385`): as instruções do arquivo de entrada são o prompt versionado.

| leva | conteúdo | resultado |
|---|---|---|
| primeira tentativa | 17 subagentes de uma vez | 55 docs extraídos; estourou o limite de uso da sessão (429). Levou ao teto de 7 e ao plano em `data/extracao/PLANO.md` |
| A | 155 documentos curtos (intimações, certidões, termos, vistas) | 210/226 acumulados, 1410 asserções |
| B | 16 documentos longos (decisões, votos, acórdão) | 226/226, 2430 asserções |

Um problema de dados apareceu na leva B: o acórdão (doc 25) tinha o texto duplicado caractere a caractere por causa de negrito simulado no PDF, e a resposta não passou na validação de trecho. `stf/documentos.py` ganhou `dedupe_chars`, o texto foi reextraído e o documento reprocessado; a resposta antiga está em `data/extracao/respostas/_invalidas/`. Foi o único documento afetado.

## 4. Números

| | |
|---|---|
| documentos / páginas | 226 / 712 (média 3,2; máximo 53) |
| asserções válidas | **2430**: 1067 `fato_processual`, 646 `alegacao_parte`, 717 `fundamento_decisorio` |
| `atribuida_a` preenchido | 100 % das alegações e dos fundamentos (obrigatório); 7 fatos |
| descartadas | 20, todas por `trecho_nao_encontrado` (0,8 % do total produzido); nenhuma resposta rejeitada por schema ou JSON |
| entidades citadas | 3280 vínculos asserção↔entidade, 374 entidades distintas; 324 entidades novas com `origem='documento'` ("terceiro mencionado") |
| documento sem asserção | 1 (doc 60, "Comunicação assinada", 1 página sem conteúdo extraível) |
| distribuição por documento | 147 docs com 1–3 asserções; 29 com 4–10; 38 com 11–50; 11 com mais de 50 |

Por tipo de documento: decisões monocráticas (41 docs, 333 p.) concentram 1483 asserções; despachos (54) 305; intimações (72) 201; o voto do relator (53 p.) 189 e o voto vogal (42 p.) 95. Os cinco documentos mais densos: doc 55 (decisão de prisão preventiva, 209), doc 224 (voto, 189), doc 183 (132), doc 222 (96), doc 226 (95).

Reprodutibilidade: `python -m stf reconstruir` apaga a projeção e reingere todas as coletas a partir dos blobs; `ingerir-extracao` em seguida reproduziu as mesmas 2430 asserções (`chore/fase4-leva-b-reconstruir`, 14/09/2026).

## 5. Limitações conhecidas

- A cobertura de documentos longos depende do subagente ler todas as páginas; a validação garante que cada asserção aponta para um trecho real, não que nada ficou de fora. Auditoria por amostragem ainda não foi feita (backlog).
- Classificação de função do documento, propostas de alias entre entidades e pedidos/resultados por decisão (`ANALISE-DADOS.md`, itens 4.2–4.4) continuam pendentes.
- Documentos que exigiriam OCR não existem neste corpus (`sem_camada_texto: 0`); se aparecerem em novos processos, ficam fora até haver OCR.

## 6. Para repetir em novos documentos

```bash
python -m stf baixar-docs --incidente <N> && python -m stf extrair-texto
python -m stf preparar-extracao          # gera entradas e LEVA-*.md só do que falta
# lançar o subagente extrator para cada LEVA (≤7 por vez), esperar terminar
python -m stf ingerir-extracao && python -m stf exportar
```

A rota pela API (`extrair-assercoes`) continua disponível e usa a mesma validação e o mesmo `prompt_version`; misturar as duas rotas no mesmo corpus é seguro porque o cache é por `(documento, sha256, prompt_version, modelo)`.
