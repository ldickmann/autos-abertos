# FASE 1 — Relatório: ingestão determinística

Executada em 14/09/2026. Zero LLM. 48 testes, todos verdes, rodando offline sobre os fixtures reais da Fase 0.

## 1. Decisões tomadas (itens delegados no gate da Fase 0)

| item | decisão | motivo |
|---|---|---|
| robots.txt | exceção confirmada pelo usuário; política da Fase 0 mantida e codificada em `stf/config.py` e `stf/coleta.py` | — |
| Ouvidoria | não enviar, por decisão do usuário | — |
| Python | **3.14.5**, o instalado | tudo roda; instalar 3.12 só para cumprir o número não agrega |
| Stack | httpx 0.28, selectolax, SQLite 3.50 com FTS5 (`unicode61 remove_diacritics 2`) | a stack sugerida, validada em campo. FTS5 acha "prisao preventiva" em "Prisão Preventiva" |
| `hash_natural` do andamento | `sha256(incidente, data, tipo, descricao, documentos, k)`, com `k` = ordinal entre itens idênticos contado **do mais antigo para o mais recente** | não existe campo `ordem` no HTML; há duplicatas exatas (cinco "Expedido(a)" em 05/03/2026). Contar do fim mantém o hash dos itens antigos estável quando o portal insere itens novos no topo. Testado em `tests/test_hash_natural.py` |
| Sessão Virtual | o fragmento `abaSessao.asp` é coletado e guardado como snapshot (é o que a casca declara), mas o JSON de `sistemas.stf.jus.br/repgeral/votacao?oi=N` **não é buscado** | outro host, outro robots.txt, e o endpoint é da Repercussão Geral (`tema=N`); o conteúdo útil (placar do referendo da liminar) está no RTF de `downloadTexto.asp`, que a Fase 3 vai baixar. Reavaliar se o RTF não trouxer os votos |
| Decisões, Pautas, Recursos | são **subconjuntos exatos** de Andamentos (verificado: 27/27 e 1/1). Viram flags `e_decisao`, `e_pauta`, `e_recurso` no andamento, não tabelas separadas. Se algum item de uma dessas abas não existir em Andamentos, entra como linha própria com `aba_origem` marcando a fonte | evita duplicar 28 linhas e mantém uma só proveniência canônica |
| Fonte de verdade | **blobs endereçados por sha256** (`data/raw/blobs/<sha256>.<ext>`) + **um JSONL por coleta** (`data/raw/coletas/<id>.jsonl`, uma linha por requisição). O SQLite é projeção: `python -m stf reconstruir` apaga e recria tudo a partir dos blobs | append-only literal: o mesmo conteúdo nunca é gravado duas vezes, e um blob que não confere com o próprio nome é erro. Foi executado e reproduziu contagens idênticas |
| Aba Andamentos com 3,6 MB | guardada íntegra; o parser ignora os 414 SVGs inline | a fonte fica intacta; dedup por conteúdo faz coletas idênticas custarem zero bytes extras |

## 2. O que foi construído

```
stf/
  config.py          UA, contato, bundle TLS, intervalos, teto de requisições
  coleta.py          ClienteEducado (≥3 s, backoff, 403 sem retentativa, teto) + coletar_incidente
  store.py           BlobStore (write-once por sha256) + RegistroColeta (JSONL append-only)
  db.py              schema SQLite + FTS5 + reconstrução
  ingest.py          registro + blobs → projeção; idempotente
  diff.py            diff entre duas coletas, direto dos blobs
  hashing.py         hash_natural de andamento e parte
  importar_fase0.py  registra os arquivos brutos da Fase 0 como a primeira coleta
  parse/
    casca.py         cabeçalho + URLs das 9 abas (lidas do script da própria página)
    informacoes.py   assunto, protocolo, origem, números de origem
    partes.py        papel literal + papel normalizado por tabela fixa + OAB + bloco
    andamentos.py    andamentos / decisões / pautas / recursos, links de documento, hint do portal
    peticoes.py, deslocamentos.py
    relacoes.py      relações entre processos por regex de andamentos padronizados
  __main__.py        CLI
tests/               48 testes; fixtures = HTML real da coleta de 14/09/2026 01:06 UTC
```

CLI:

```
python -m stf coletar 7514886        # coleta educada + ingestão
python -m stf importar-fase0         # snapshots da Fase 0 como coleta
python -m stf ingerir <registro>     # projeta uma coleta já gravada
python -m stf reconstruir            # apaga a projeção e reingere tudo dos blobs
python -m stf diff <a> <b>           # compara duas coletas
python -m stf buscar "<termos>"      # FTS5 em andamentos
python -m stf status
```

## 3. Schema (o que mudou em relação ao mínimo proposto)

Tabelas: `coleta`, `snapshot`, `incidente`, `incidente_versao`, `parte`, `andamento`, `tipo_andamento`, `documento`, `andamento_documento`, `peticao`, `deslocamento`, `processo_relacao`, `andamento_fts`.

Mudanças e acréscimos, todos motivados por achados da Fase 0:

- `snapshot` tem **uma linha por aba**, não por incidente, com `coleta_id` agrupando as 11 requisições de uma coleta.
- `incidente` ganhou `publicidade`, `natureza`, `reu_preso`, `tipo_tramitacao`, `meio`, `relator_ultimo_incidente`, `ultimo_incidente`, `numeros_origem`, `descricao_procedencia`. `incidente_versao` guarda cada versão distinta do cabeçalho com o snapshot em que apareceu.
- `andamento` tem `posicao` (posição na lista servida), `aba_origem`, flags `e_decisao`/`e_pauta`/`e_recurso`, e `snapshot_first_seen`/`snapshot_last_seen`. Nada é apagado: item que sumir do portal fica com `last_seen` parado.
- `tipo_andamento` guarda a **explicação em linguagem simples que o próprio portal embute** por tipo (17 dos 33 tipos vistos têm). É texto oficial do STF, não da IA; serve para a legenda da interface.
- `documento` é único por `(endpoint, id_portal)`; `andamento_documento` liga com o rótulo. Os 72 links da aba Andamentos apontam para **57 documentos únicos** (decisão e vista à PGR citam o mesmo PDF). Campos `sha256`, `paginas`, `tem_camada_texto`, `texto_path`, `codigo_autenticacao`, `senha_autenticacao` ficam nulos até a Fase 3.
- `parte` guarda `papel_portal` (literal) e `papel` (mapeado por tabela fixa em `stf/parse/partes.py`, sem inferência), `oab` como lista, `bloco` (liga advogado à parte representada, como o portal agrupa) e `e_placeholder` para "SEM REPRESENTAÇÃO NOS AUTOS".
- `processo_relacao(incidente_origem, classe_destino, numero_destino, tipo, fonte_andamento_id)` substitui `incidente_relacao(origem, destino, tipo)`: o portal não expõe incidentes, só classe+número. A resolução para incidente é a Fase 2.

## 4. Gate: banco populado

Duas coletas ingeridas, ambas com 11 requisições e todas 200. (Houve uma terceira, às 01:43 UTC, cujo registro JSONL eu apaguei por descuido ao regenerar os registros com caminhos relativos; os blobs dela são idênticos aos das outras duas e continuam no store. A coleta das 01:49 foi feita para repor o registro. Total na Fase 1: 22 requisições, 20 delas a `/processos`.)

| coleta | origem | fetched_at (casca) |
|---|---|---|
| `20260914T010538Z-7514886` | arquivos brutos da Fase 0, importados | 01:05:38 UTC |
| `20260914T014912Z-7514886` | `python -m stf coletar 7514886` | 01:49:15 UTC |

Intervalos entre requisições da coleta nova: mínimo 3,0 s, máximo cerca de 5 s (a aba de 3,6 MB). UA identificado em todas.

Projeção resultante (idêntica antes e depois de `reconstruir`):

| tabela | linhas |
|---|---|
| snapshot | 22 |
| incidente | 1 (versões do cabeçalho: 1) |
| parte | 56 (1 requerente, 1 aut. policial, 14 requeridos, 2 interessados, 38 advogados) |
| andamento | 407 (27 decisões, 1 pauta) |
| tipo_andamento | 33 (17 com explicação do portal) |
| documento | 57 (56 PDF via `downloadPeca`, 1 RTF via `downloadTexto`) |
| andamento_documento | 72 |
| peticao | 113 |
| deslocamento | 90 |
| processo_relacao | 7 |

Relações extraídas, cada uma apontando para o andamento-fonte:

```
justifica_prevencao → Inq 5026     (27/02/2026, Distribuído por prevenção)
relacionado         → Inq 5035, Pet 15198, Pet 15499, Pet 15504   (idem)
autuado_a_partir    → Pet 16440, Pet 16441   (20/07/2026, Certidão)
```

Busca FTS (`python -m stf buscar "prisao preventiva"`), sem acento na consulta:

```
2026-03-04 | Determinada a diligência [decisão] | …da Polícia Federal, DECRETO A [PRISÃO] [PREVENTIVA] DOS INVESTIGADOS: (i) DANIEL BUENO…  (snapshot 2)
```

## 5. Gate: diff

**Real**, entre as duas coletas (44 minutos de intervalo):

```
diff 20260914T010538Z-7514886 → 20260914T014912Z-7514886  (incidente 7514886)
  sem diferenças
  abas com bytes idênticos: casca, informacoes, partes, andamentos, decisoes, sessao, deslocamentos, peticoes, recursos, pautas
```

**Simulado**: uma coleta antiga fabricada a partir dos fixtures (corte em 25/08/2026: sem os andamentos posteriores, sem a última parte, sem as 6 petições e os 4 deslocamentos mais recentes), gravada no scratchpad, fora de `data/`:

```
diff SIMULADO-20260825-7514886 → 20260914T014912Z-7514886  (incidente 7514886)
  abas com bytes idênticos: casca, informacoes, decisoes, sessao, recursos, pautas
  +1 parte
    + ADV.(A/S) VICTOR HUGO PEIXOTO GONDIM TEIXEIRA LEITE (42085/GO)
  +13 andamentos
    + 2026-09-11 | Remessa | da Petição nº 114945/2026 para GABINETE MINISTRO ANDRÉ MENDONÇA
    + 2026-09-11 | Petição | Manifestação - Petição: 114945 Data: 11/09/2026, às 14:24:59
    + 2026-09-11 | Remessa | da Petição nº 114782/2026 para GABINETE MINISTRO ANDRÉ MENDONÇA
    + 2026-09-11 | Certidão | de retificação de autuação [1 doc]
    + 2026-09-11 | Petição | Manifestação - Petição: 114782 Data: 11/09/2026, às 10:53:37
    + 2026-09-09 | Petição | Petição Físico ou Sigiloso - Petição Sigilosa: 114070 Data: 09/09/2026, às 22:15:37
    + 2026-09-08 | Petição | 112941/2026 - 08/09/2026 - (Via Malote Digital)
    + 2026-09-04 | Petição | Petição Físico ou Sigiloso - Petição Sigilosa: 112079 Data: 04/09/2026, às 07:55:35
    + 2026-09-03 | Petição | Petição Físico ou Sigiloso - Petição Sigilosa: 111643 Data: 03/09/2026, às 13:44:09
    + 2026-08-28 | Vista à PGR |  [1 doc]
    + 2026-08-27 | Petição |
    + 2026-08-26 | Vista à PGR |  [1 doc]
    + 2026-08-26 | Despacho | Em 25/08/2026 [1 doc]
  +6 petições
    + 114945/2026 | peticionada 2026-09-11 | recebida 2026-09-11T15:09:12
    + 114782/2026 | peticionada 2026-09-11 | recebida 2026-09-11T11:03:54
    + 114070/2026 | peticionada 2026-09-09 | recebida 2026-09-09T22:15:42
    + 112941/2026 | peticionada 2026-09-08 | recebida 2026-09-08T11:24:23
    + 112079/2026 | peticionada 2026-09-04 | recebida 2026-09-04T07:55:42
    + 111643/2026 | peticionada 2026-09-03 | recebida 2026-09-03T13:44:13
  +4 deslocamentos
    + 2026-08-28 | GERÊNCIA DE PROCESSOS ORIGINÁRIOS CRIMINAIS → PROCURADORIA-GERAL DA REPÚBLICA | guia 24516/2026 | recebido None
    + 2026-08-28 | GABINETE MINISTRO ANDRÉ MENDONÇA → GERÊNCIA DE PROCESSOS ORIGINÁRIOS CRIMINAIS | guia 6174/2026 | recebido 2026-08-28
    + 2026-08-28 | PROCURADORIA-GERAL DA REPÚBLICA → GABINETE MINISTRO ANDRÉ MENDONÇA | guia 5394667/2026 | recebido 2026-08-28
    + 2026-08-26 | GERÊNCIA DE PROCESSOS ORIGINÁRIOS CRIMINAIS → PROCURADORIA-GERAL DA REPÚBLICA | guia 24144/2026 | recebido None
```

O sentido inverso lista os mesmos itens como removidos (`tests/test_diff.py`).

## 6. O que funcionou, o que falhou, o que ficou de fora

**Funcionou.** Coleta, parsing das 9 abas, hash estável, ingestão idempotente, reconstrução a partir dos blobs, diff, FTS. Todos os 48 testes passam; pyflakes limpo.

**Falhou durante o desenvolvimento e foi corrigido (registrado porque muda o entendimento do portal):**
- `selectolax`: `node.css()` inclui o próprio nó, o que fazia o parser de Informações ignorar todos os campos. Corrigido lendo filhos diretos.
- A aba Partes tem um segundo bloco `#partes-resumidas` que reutiliza a classe `.processo-partes` com texto "X E OUTRO(A/S)". O parser agora se restringe a `#todas-partes`; se esse id sumir, levanta erro em vez de ler o resumo como parte.
- O ícone de mapa em Deslocamentos carrega `processo-detalhes-bold`; o destino é lido só de `span`.
- Meu primeiro desenho fazia as abas Decisões/Pautas avançarem o `snapshot_last_seen` do andamento para o snapshot delas; agora só a aba Andamentos avança, para a proveniência apontar sempre ao lugar canônico.

**Fora de escopo, por decisão:**
- download de documentos (Fase 3); `documento` já tem as colunas.
- JSON da Sessão Virtual (ver seção 1).
- resolução de classe+número para incidente (Fase 2).
- pacote instalável (`pyproject.toml`): a CLI roda com `python -m stf` a partir da raiz; empacotar antes de haver segundo usuário é prematuro.

## 7. Estado do repositório

`git init` feito, remote `origin` apontando para o repositório que você criou. `.gitignore` exclui `data/raw/blobs/`, `data/raw/7514886/`, o SQLite e os resultados brutos da Fase 0; os fixtures em `tests/fixtures/` (3,9 MB, HTML público do portal) e `recon/certs/stf-chain.pem` são versionados. Commit e push desta fase feitos ao fim deste relatório.

## 8. Para a Fase 2 (gate)

O que a Fase 1 entrega à Fase 2: `processo_relacao` com 7 arestas por classe+número, e a sondagem da Fase 0 mostrando que `listarProcessos.asp?classe=X&numeroProcesso=N` redireciona (302) para o incidente principal. Um agente de pesquisa está buscando na internet, sem tocar no portal, se existe forma de enumerar os incidentes de agravo; o resultado entra como anexo deste relatório ou abre o relatório da Fase 2.

Decisões que precisam de você antes da Fase 2:
1. **Escopo do grafo:** nó = processo (classe+número), com resolução de cada um para o incidente principal por `listarProcessos.asp` (1 requisição por processo, 7 para este caso). Os incidentes de agravo ficam pendentes da pesquisa.
2. **Profundidade e teto:** padrão proposto profundidade 1 (só os 7 processos relacionados, sem seguir as relações deles) e teto de 100 requisições por execução. Profundidade 2 sobre um caso com 7 vizinhos, cada um com 10 abas, passa de 700 requisições.
3. **Coletar as abas dos processos relacionados ou só resolver o incidente?** Resolver custa 1 requisição por processo; coletar custa 11. Proposta: só resolver na Fase 2 e coletar sob demanda depois.
