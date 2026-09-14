# FASE 3 — Relatório: camada documental

Executada em 14/09/2026. Zero LLM. 86 testes verdes.

## 1. Resultado

| | |
|---|---|
| documentos conhecidos (11 processos) | **226**: 222 PDF via `downloadPeca.asp`, 1 RTF via `downloadTexto.asp`, 3 PDF de voto/relatório via `digital.stf.jus.br` |
| baixados | **226 de 226** |
| com camada de texto nativa | **226**; nenhum precisa de OCR |
| páginas de texto | 671 (944 mil caracteres, ~250 mil tokens) |
| chunks (por página, parágrafo numerado ou título) | 1 356 |
| com código de autenticação do STF no rodapé | 106 (os demais são certidões, intimações e o RTF, que não trazem o rodapé) |
| maior documento | Voto do relator no referendo: 53 páginas; a decisão de prisão preventiva de 04/03/2026: 48 páginas |
| tamanho dos PDFs em disco | 64 MB |
| requisições | 226 + 22 retentativas = 248, todas 200, ≥3 s, UA identificado |

## 2. Decisões

| item | decisão | motivo |
|---|---|---|
| Extração de texto | **pdfplumber** (MIT) | pypdf perdia espaços ("SOBSIGILO", "FURTADOPALHARES"), o que quebraria busca e extração semântica; pdfplumber preserva e é 4× mais rápido no PDF de amostra. `pdftotext` (xpdf) fica só como referência manual, por não ser portável |
| RTF | `striprtf` | único RTF do corpus: a decisão colegiada do referendo. Convertido para texto de página única |
| Camada de texto | página com ≥40 caracteres alfanuméricos; documento "com camada" se a maioria das páginas passa; senão `precisa_ocr=1` e nada é feito | OCR é decisão de custo; não apareceu nenhum caso |
| Chunking | quebra por página, por parágrafo numerado (`1.`, `2.` …) e por título em caixa alta (RELATÓRIO, VOTO, DECISÃO, DESPACHO, EMENTA…), máximo 1 800 caracteres, nunca no meio de linha; cada chunk guarda `pagina_inicio`, `pagina_fim` e `secao` | as decisões do STF numeram parágrafos; é a unidade natural para citar |
| Cache | um documento é identificado por `(endpoint, id_portal)`; com `sha256` preenchido nunca é rebaixado | restrição 3 |
| Rodada de download | registro JSONL próprio (`-documentos-`), multi-incidente; a ingestão deriva `documento.sha256/blob_path` dele, em qualquer ordem | `reconstruir` recria tudo dos blobs, inclusive isso (testado) |
| Sessão virtual | incorporada ao coletor: `votacao?oi=<incidente>` e `votacao?sessaoVirtual=<objeto>` (JSON de `sistemas.stf.jus.br`, o mesmo que a aba do portal carrega). Tabelas `objeto_incidente`, `lista_julgamento`, `voto`; os PDFs de voto e relatório entram em `documento` com endpoint `votos` | o achado da pesquisa web (seção 4) mostrou que é a única fonte pública do placar; nenhum outro dos 11 processos tem sessão virtual (404) |

## 3. O que falhou e como foi tratado

- **22 documentos vieram com HTTP 200 e corpo vazio** na primeira rodada (intimações, termos de disponibilização e três decisões, espalhados por 4 processos). Sem padrão de sigilo. Na retentativa, 80 s depois, todos vieram íntegros. O portal falha esporadicamente; o pipeline registra a resposta vazia como snapshot (auditável), deixa `sha256` nulo e a próxima rodada tenta de novo. Nada foi contornado.
- **A reconstrução do banco abortava** no registro de downloads porque a ingestão exigia um único incidente por registro. Corrigido com teste (`test_rodada_de_documentos_com_varios_incidentes_e_ingerida`). O erro só apareceu porque o resumo do comando escondia a exceção; a CLI passou a propagar o código de saída.
- A tabela `entidade` do banco de produção era anterior à coluna `origem`; como o banco é projeção, `reconstruir` resolveu.

## 4. Anexo: pesquisa web sobre incidentes de agravo (agente sem acesso ao portal)

Resultado da pesquisa despachada na Fase 2 (35 buscas, ~15 repositórios lidos, Wayback Machine, e o código-fonte do e-STF espelhado no GitHub):

- **Não existe endpoint público que liste os incidentes (AgR, ED…) com número.** `abaRecursos.asp` lista recursos só por nome e costuma voltar vazia (Content-Length 0), como aqui.
- Cada agravo tem, sim, um `SEQ_OBJETO_INCIDENTE` próprio no e-STF (tabela `RECURSO_PROCESSO`, cadeia `Pet-AgR` + sequência 1…4). Os canais que expõem esse id são: (a) o JSON `votacao?oi=` para incidentes que passaram por sessão virtual; (b) o índice de jurisprudência (`externo_seq_objeto_incidente`) para incidentes já julgados com acórdão.
- **Sondagem feita (3 requisições):** `votacao?oi=7514886` devolve só o Referendo (id 7519395, tipo IJ, principal 7514886); os quatro agravos não passaram por sessão virtual e não aparecem. `verImpressao.asp?incidente=7519395` responde 200, mas sem classe e número: o portal não renderiza objetos que não são processo. Conclusão: **os agravos ficam como andamentos até serem julgados**; quando forem, o índice de jurisprudência e o JSON de votação passam a expô-los. O sistema já sabe consumir o segundo.
- Não há API/dados abertos do STF com andamentos: DataJud não cobre o STF; Corte Aberta é painel Qlik de decisões agregadas; STF Digital tem só API de partes (processos principais).
- Vários projetos relatam que o portal devolve 403 para IPs de datacenter (GitHub Actions, GCP, Azure). Consequência para a Fase 5: **a coleta roda em máquina local ou residencial; o site é estático e pode ser hospedado em qualquer lugar**, com os JSON versionados no repositório.

## 5. Artefatos

```
stf/documentos.py   baixar_documentos, extrair_texto, chunkar, codigo_autenticacao, rtf_para_texto
stf/sessao.py       parse_objetos_incidente, parse_sessao_virtual; coleta.coletar_sessao_virtual
tests/test_documentos.py, tests/test_sessao.py   16 testes; fixtures: PDF real de 87 KB e os dois JSON reais
data/raw/coletas/*-documentos-*.jsonl, *-sessao-*.jsonl
CLI: baixar-docs, extrair-texto, buscar-docs, sessao, sessoes
```
