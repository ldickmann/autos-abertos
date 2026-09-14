# FASE 2 — Relatório: grafo de processos e entidades

Executada em 14/09/2026. Zero LLM. 65 testes verdes, offline. 132 requisições ao portal nesta fase (97 na profundidade 1, 35 na 2), todas 200/302, intervalo mínimo 3 s, UA identificado.

## 1. Decisões tomadas

Você pediu "tudo que puder cruzar" e "o processo completo". Decisões derivadas disso:

| item | decisão | motivo |
|---|---|---|
| Nó do grafo | **processo por classe+número**, resolvido para o incidente principal via `listarProcessos.asp` (302 determinístico). Os incidentes de agravo (`Pet-AgR-primeiro…quarto`) continuam não enumeráveis pela página; a pesquisa web despachada para isso ainda não retornou e entra como anexo quando chegar | o portal não expõe `incidente=` em lugar nenhum além do próprio |
| Profundidade | **2, com coleta completa** (11 abas) de cada processo alcançado. A fronteira além disso é listada, não coletada. Para este caso: 10 processos coletados, 1 na fronteira (Pet 15719, profundidade 3) | profundidade 1 custou 97 requisições e a 2 custou 35; a 3 traria um único processo. Fechar em 2 dá o entorno completo do caso com custo previsível. `python -m stf expandir 7514886 --profundidade 3` coleta o que falta |
| Coletas recentes | reaproveitadas se a casca tem menos de 12 h | evita repetir 11 requisições por processo a cada execução; o `diff` cobre mudanças |
| Entidades canônicas | **advogado = OAB** (primeira do nome); **demais = nome normalizado** (maiúsculas, sem acentos). Placeholders ("SEM REPRESENTAÇÃO NOS AUTOS") excluídos | a OAB identifica a pessoa mesmo com grafia variável; nome exato é o único identificador disponível para as partes. Limitação declarada: homônimos sem OAB viram uma entidade; a tabela `entidade_mencao` preserva cada ocorrência para o leitor ver |
| `natureza_provavel` | só `pessoa_juridica`, só por sufixo societário explícito no nome (LTDA, S.A., EIRELI, PARTICIPAÇÕES…). Senão NULL | restrição 5: nada é deduzido sobre pessoas além do que o portal escreve |
| Representação | advogado (bloco N) representa a parte do bloco não-advogado imediatamente anterior, no mesmo incidente | é assim que o portal agrupa; verificado no fixture (Vorcaro no bloco 2, seus advogados no 3) |
| Ligação por "Número de Origem" | aresta `numero_origem`, marcada `fraco: true`, quando o campo cita um número puro igual ao de outro processo do grafo | o campo mistura números CNJ e números de classe sem dizer a classe; é pista, não relação declarada |
| Teto de redirect | o teto de requisições conta cada salto de redirect | um 302 é uma requisição a mais no portal; contar só o `get` mentia sobre a carga |
| Tabela `processo` | derivada na ingestão a partir dos registros de resolução (JSONL + blob); `reconstruir` a recria. O status `semente` é reconhecido pelo id do registro (`…-resolucoes-<incidente>`) | manter a regra "SQLite é projeção" |

## 2. Grafo: processos

Arestas declaradas em andamentos (cada uma com snapshot e andamento-fonte no `data/grafo.json`):

```
processo:Pet/15556 --relacao:justifica_prevencao--> processo:Inq/5026
processo:Pet/15556 --relacao:relacionado--> processo:Inq/5035
processo:Pet/15556 --relacao:relacionado--> processo:Pet/15198
processo:Pet/15556 --relacao:relacionado--> processo:Pet/15499
processo:Pet/15556 --relacao:relacionado--> processo:Pet/15504
processo:Pet/15556 --relacao:autuado_a_partir--> processo:Pet/16440
processo:Pet/15556 --relacao:autuado_a_partir--> processo:Pet/16441
processo:Inq/5026  --relacao:justifica_prevencao--> processo:Pet/15172
processo:Inq/5026  --relacao:autuado_a_partir--> processo:Pet/15612
processo:Inq/5035  --relacao:justifica_prevencao--> processo:Inq/5026
processo:Pet/15198 --relacao:justifica_prevencao--> processo:Rcl/88121
processo:Pet/15499 --relacao:justifica_prevencao--> processo:Inq/5026
processo:Pet/15504 --relacao:justifica_prevencao--> processo:Inq/5026
processo:Rcl/88121 --relacao:autuado_a_partir--> processo:Pet/15719
```

Mais 9 arestas fracas `numero_origem` (Pet 15556 → Inq 5026, Inq 5035, Pet 15198, 15499, 15504; Inq 5026 → Pet 15172, Rcl 88121; Inq 5035 → Pet 15198; Pet 15198 → Rcl 88121), todas coincidindo com relações já declaradas, o que corrobora a leitura do campo.

Processos, com o que o portal devolveu:

| prof. | processo | incidente | publicidade | relator | partes | andamentos | docs | período dos andamentos |
|---|---|---|---|---|---|---|---|---|
| 0 | Pet 15556 | 7514886 | Público | André Mendonça | 56 | 407 | 57 | 27/02/2026 → 11/09/2026 |
| 1 | Inq 5026 | 7473347 | Público | André Mendonça | 72 | 656 | 70 | 22/12/2025 → 13/09/2026 |
| 1 | Inq 5035 | 7498168 | Público | André Mendonça | 17 | 48 | 6 | 09/02/2026 → 11/09/2026 |
| 1 | Pet 15198 | 7473336 | Público | André Mendonça | 115 | 405 | 57 | 22/12/2025 → 13/09/2026 |
| 1 | Pet 15499 | 7509111 | Público | André Mendonça | 22 | 41 | 10 | 22/02/2026 → 11/09/2026 |
| 1 | Pet 15504 | 7509527 | Público | André Mendonça | 32 | 44 | 13 | 23/02/2026 → 08/09/2026 |
| 1 | Pet 16440 | 7649959 | **Sigiloso** | André Mendonça | 0 | 3 | 0 | 20/07/2026 → 22/07/2026 |
| 1 | Pet 16441 | 7649960 | **Sigiloso** | André Mendonça | 0 | 3 | 0 | 20/07/2026 → 22/07/2026 |
| 2 | Rcl 88121 | 7450195 | Público | André Mendonça | 22 | 259 | 8 | 27/11/2025 → 25/08/2026 |
| 2 | Pet 15172 | 7471355 | **Sigiloso** | **Dias Toffoli** | 0 | 4 | 0 | 19/12/2025 → 22/12/2025 |
| 2 | Pet 15612 | 7522443 | **Sigiloso** | André Mendonça | 0 | 9 | 2 | 06/03/2026 → 17/03/2026 |
| 3 | Pet 15719 | 7536897 | fronteira, não coletado | | | | | |

Nos sigilosos o portal devolve casca com cabeçalho, aba Partes vazia e poucos andamentos genéricos. O sistema guarda exatamente isso. Nada foi tentado além do que a página pública serve.

Assuntos (campo do portal): Pet 15556 "Prisão Preventiva"; Inq 5026 "Crimes contra o Sistema Financeiro Nacional" e "Investigação Penal"; Rcl 88121 "Medidas Assecuratórias | Busca e Apreensão de Bens"; Inq 5035, Pet 15499, Pet 15504 "Investigação Penal"; Pet 15198 "Direito Processual Penal".

## 3. Grafo: entidades e cruzamentos

| | |
|---|---|
| nós | 246 (12 processos + 234 entidades: 65 partes, 169 advogados) |
| arestas | 563: 14 `relacao`, 9 `numero_origem`, 318 `parte_em`, 222 `representa` |
| entidades em 2 processos | 34 |
| entidades em 3 ou mais | 11 |
| pessoas jurídicas por sufixo explícito | 7 |

Entidades presentes em três ou mais processos, com o papel literal do portal em cada um (`python -m stf cruzamentos` lista todas as 45):

| entidade | tipo | processos | papéis literais |
|---|---|---|---|
| DANIEL BUENO VORCARO | parte | 7 | REQDO.(A/S) em Pet 15556, 15499, 15504; INTDO.(A/S) em Pet 15198, Inq 5026; INVEST.(A/S) em Inq 5035; e Rcl 88121 |
| SERGIO RODRIGUES LEONARDO | advogado | 7 | ADV.(A/S) |
| POLÍCIA FEDERAL | parte | 6 | AUT. POL. em 5; INTDO.(A/S) em Pet 15504 |
| FABIANO CAMPOS ZETTEL | parte | 5 | REQDO.(A/S) em 3; INTDO.(A/S) em 2 |
| ENGELS AUGUSTO MUNIZ | advogado | 5 | ADV.(A/S) |
| THIAGO MACHADO DE CARVALHO | advogado | 5 | ADV.(A/S) |
| DELEGADO DE POLÍCIA FEDERAL | parte | 4 | REQTE.(S), AUT. POL., AUTOR(A/S)(ES) |
| LUIZ PHILLIPI MACHADO DE MORAES MOURAO | parte | 3 | REQDO.(A/S) em 2; INVEST.(A/S) em Inq 5035 |
| CLAUDEMIR JOSE DA COSTA JUNIOR | advogado | 3 | ADV.(A/S) |
| FLAVIA MORTARI LOTFI | advogado | 3 | ADV.(A/S) |
| LUCILA DEL MONACO ANTUNES LEITE | advogado | 3 | ADV.(A/S) |

O que isso é e o que não é: a mesma pessoa aparece com papéis processuais diferentes em processos diferentes (investigado no inquérito, requerido na petição, interessado em outra). O sistema registra os papéis literais e as arestas com proveniência; não junta isso em nenhuma conclusão sobre a pessoa.

## 4. O que foi construído

```
stf/resolver.py    url_resolucao + interpretar_resolucao (302 → incidente; lista → múltiplos; nada → não encontrado)
stf/expandir.py    BFS com fila, profundidade, teto, reaproveitamento de coleta recente, retomável após teto
stf/entidades.py   entidade + entidade_mencao, determinístico e idempotente
stf/grafo.py       construir_grafo (JSON para a interface), formatar_arestas, cruzamentos, formatar_cruzamentos
stf/ingest.py      upsert_processo; deriva `processo` dos registros de resolução; marca a semente
tests/portal_falso.py   portal simulado com httpx.MockTransport (resoluções, cascas, abas)
tests/test_resolver.py, test_expandir.py, test_grafo.py   17 testes novos
data/grafo.json    246 nós, 563 arestas, cada aresta com `fonte`
```

CLI nova: `expandir <incidente> [--profundidade N] [--teto N]`, `entidades`, `grafo`, `cruzamentos`.

Correções feitas nesta fase, com teste: OAB em formatos como `30814/A/MT`, `141073A/RS`, `32957 A/PB`, `5922-A/AP` não era separada do nome (12 advogados afetados; agora 169/169 com chave por OAB). Todos os papéis vistos nos 11 processos (`INVEST.(A/S)`, `AUTOR(A/S)(ES)`, `PROC.(A/S)(ES)`…) estão na tabela fixa; nenhum caiu em `desconhecido`.

## 5. O que ficou de fora e por quê

- **Agravos regimentais como incidentes próprios**: sem fonte. Pesquisa web em andamento (agente sem acesso ao portal).
- **Profundidade 3** (Pet 15719): um comando.
- **Entidades a partir de documentos** (pessoas citadas em decisões, e não só partes): é a Fase 4, com LLM e tipagem epistêmica.
- **Órgãos dos deslocamentos** (PGR, gabinetes) como nós: dado disponível na tabela `deslocamento`, não posto no grafo para não misturar entidades processuais com trâmite interno. Fácil de acrescentar se a interface pedir.

## 6. Próximo passo, já em execução

Fase 3 (documentos): 223 documentos únicos conhecidos nos 11 processos, 221 PDF e 2 RTF. Download com cache por sha256, extração de texto por página, código de autenticação do STF por documento, chunking por seção. A Fase 0 já mostrou PDF acessível sem sessão e com camada de texto; a Fase 3 confirma isso em escala e detecta qualquer PDF escaneado.
