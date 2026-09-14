# Análise dos dados: o que existe, o que dá para cruzar, o que falta

Data: 14/09/2026. Base: `data/stf.sqlite` reconstruída a partir de 28 coletas (406 snapshots), 11 incidentes coletados, 226 documentos com texto (712 páginas), 1041 asserções de 55 documentos (Fase 4 em andamento).

## 1. O que a base tem hoje

| conjunto | volume | ligações já derivadas |
|---|---|---|
| processos | 12 resolvidos (11 coletados; Pet 15719 ficou na fronteira, profundidade 3) | 14 relações declaradas em andamentos (prevenção, autuação, "relacionado"); 9 coincidências fracas de número de origem |
| partes | 336 linhas → 234 entidades (63 partes, 171 advogados por OAB) | 45 entidades aparecem em mais de um processo; representação advogado→parte por bloco |
| andamentos | 1879 (42 tipos), 272 vínculos andamento→documento | subconjuntos decisão/pauta/recurso |
| petições | 689 | **nenhuma ligação** com andamentos ou documentos |
| deslocamentos | 397 entre 8 unidades | nenhuma ligação com andamentos |
| documentos | 226, 1417 chunks, FTS | 200 deles citam outros processos no texto; nada disso está estruturado |
| asserções | 1041 (469 fato, 373 alegação, 199 fundamento), 1518 citações de entidade | 206 entidades vindas de documentos **sem nenhuma aresta no grafo** |
| sessão virtual | 1 lista, 4 votos | não ligada a entidades de ministro |

Diagnóstico do grafo atual: 452 nós, 563 arestas, **206 nós isolados** (todas as entidades extraídas de documentos). As arestas existentes vêm só do cadastro de partes e das relações declaradas. É por isso que ele parece uma nuvem de pontos: metade dos nós não se liga a nada, e as ligações que existem são de um único tipo (quem é parte em quê).

## 2. Cruzamentos viáveis sem inferência (todos com ponteiro para documento/página ou andamento/snapshot)

Medidos sobre a base real antes de implementar:

| # | cruzamento | como | medição | decisão |
|---|---|---|---|---|
| C1 | documento → processo citado | regex de classe+número (`Pet 15556`, `Inq 5.026`, `HC 247450`…) por página | 200/226 documentos citam ≥1 processo; 465 citações a Pet, 154 a Inq, 103 a HC, 42 a Rcl, 16 a MS, 11 a ADPF | **fazer**. Tabela `documento_ref_processo`. Processos citados e não coletados entram no grafo como nós "externos" (HCs, precedentes), desligados por padrão na interface; não disparam coleta |
| C2 | documento → dispositivo legal | regex `art. N … do CPP/CP/CF/Lei X/AAAA/RISTF` por página | 55 dispositivos distintos; art. 319 CPP (48), art. 312 CPP, art. 4º Lei 9.613/1998, art. 2º Lei 12.850/2013… | **fazer**. Tabela `documento_ref_dispositivo`. Permite ver que decisões se apoiam na mesma base legal, sem dizer nada sobre pessoas |
| C3 | andamento ↔ petição | número em "Petição: 114945" casa com `peticao.numero` "114945/2026" do mesmo incidente | 646 andamentos com número; 629 casam com exatamente 1 petição; 0 ambíguos | **fazer**. Tabela `andamento_peticao`. Liga quem protocolou a petição (recebido_por) ao andamento |
| C4 | intimação → andamento a que se refere | bloco "Andamento(s): - <tipo> - dd/mm/aaaa" no texto da intimação, casado por (incidente, data, tipo) | 72 referências, 72 encontradas | **fazer**. Tabela `documento_ref_andamento` |
| C5 | número da comunicação (Nº 58028/2026) → petição | mesma chave de C3 | 72 documentos, **0** casam: é numeração própria de comunicações | não fazer |
| C6 | entidade citada em asserção → processo | `assercao_entidade` → asserção → documento → incidente | 1518 citações; 39 entidades de documento coincidem com partes | **fazer** no grafo (aresta `citado_em`, peso = nº de asserções, fonte = lista doc/página) |
| C7 | co-citação entidade ↔ entidade | duas entidades na mesma asserção | a medir na implementação | **fazer, com rótulo literal** ("citadas na mesma asserção, N vezes") e desligada por padrão para pessoas físicas. Não é "envolvimento": é coocorrência em uma frase do documento, com o trecho visível |
| C8 | ministro → processo | relator (cadastro), voto (sessão virtual), `atribuida_a` das asserções | 13 entidades de ministro hoje são variantes do mesmo nome ("MIN. ANDRÉ MENDONÇA", "Ministro André Mendonça", "ANDRÉ MENDONÇA") | **fazer**: chave canônica `ministro:<nome>` por regra (tira prefixos MIN./Ministro/Min. e sufixo "(relator)"); arestas `relator_de` e `votou_em` |
| C9 | linha do tempo unificada | todos os andamentos dos 11 processos numa só ordenação | 147 datas com andamentos em mais de um processo | **fazer**: export `linha_tempo.json` + página, com categorias de andamento curadas (decisão, petição, comunicação, movimentação interna, publicação) |
| C10 | deslocamentos como trajeto | unidades como nós, deslocamentos como arestas com data | 8 unidades | adiar: útil como visual próprio (sankey), não como parte do grafo principal |

## 3. Correções de qualidade encontradas

- Papéis de Reclamação sem mapeamento: `RECLTE.(S)`, `RECLDO.(A/S)`, `BENEF.(A/S)` aparecem como `desconhecido:…` → mapear para reclamante, reclamado, beneficiário.
- `processo.profundidade` só é preenchida para a semente; o grafo recalcula por BFS mas a tabela fica NULL → preencher na reconstrução.
- Variantes de órgãos no mesmo papel ("Procuradoria-Geral da República" / "Procuradoria-Geral de República" [erro de digitação no documento] / "PROCURADOR-GERAL DA REPÚBLICA" [parte]) → **não fundir**: são nomes literais com fonte. Em vez disso, um agrupamento curado e versionado (`stf/curadoria/grupos.json`: Polícia Federal, Ministério Público Federal, STF, Justiça Federal, reguladores, defesa) para colorir e filtrar o grafo, marcado como curadoria, não como fato do portal.
- Índices ausentes para as consultas de exportação: `parte(incidente)`, `documento(incidente)`, `documento_pagina(documento_id)`, `assercao_entidade(entidade_id)`, `andamento(tipo)`, `peticao(incidente)`.
- Pet 15719 (incidente 7536897, autuada a partir da Rcl 88121) está resolvida mas não coletada por estar na profundidade 3. O usuário pediu o caso completo → coletar (13 requisições educadas).

## 4. O que um LLM pode fazer aqui, e o que não pode

Pode, dentro das restrições (saída sempre com ponteiro, validada de forma determinística, tipada):

1. **Extração de asserções** (Fase 4, em curso): a única camada semântica persistida.
2. **Classificação de documentos por função** (decisão, voto, intimação, certidão, ofício, manifestação) quando o título do portal é genérico ("Despacho", "Petição") — proposta do modelo, validada por regra simples (o título literal permanece; a função vira campo separado com `origem='llm'` e versão do prompt). Útil para filtros. Fila.
3. **Propostas de alias de entidade** (mesmo órgão escrito de formas diferentes): o modelo só propõe pares com os dois trechos-fonte; nada é fundido sem regra determinística (OAB igual, nome normalizado igual) ou curadoria explícita no repositório. Fila.
4. **Tabela de pedidos e resultados** por decisão (o que foi pedido, o que foi decidido, por quem), como asserções `fato_processual` com campos estruturados. É a extensão natural da Fase 4 depois que ela terminar. Fila.

Não pode, e o schema impede: resumos narrativos, conexões "prováveis" entre pessoas, qualquer juízo sobre conduta. Os cruzamentos da seção 2 são todos determinísticos justamente para que o grafo mostre ligações com fonte, e não ligações sugeridas por modelo.

## 5. Ordem de execução

1. `stf/referencias.py` (C1–C4) + tabelas + testes; entra em `reconstruir`.
2. Entidades: chave de ministro (C8), papéis de Rcl, grupos curados, índices, profundidade.
3. Grafo: arestas `citado_em`, `cita_processo`, `co_citacao`, `relator_de`, `votou_em`; nós externos; remoção de isolados; contagens por nó.
4. Export: `linha_tempo.json`, `referencias.json` (dispositivos → documentos), campos novos em `processo/<inc>.json` e `documento/<id>.json`.
5. Interface do grafo (item 3 da fila) sobre esses dados; depois a versão escura (item 4).

## 6. Decisões tomadas na execução (14/09/2026)

- **4.2 (função do documento):** feito sem modelo. Os títulos do portal já são específicos (Intimação, Despacho, Decisão monocrática, Vista à PGR, Certidão, Termo, Voto, Relatório, Acórdão); a única ambiguidade, o despacho que decide, é resolvida pela marcação `e_decisao` do próprio portal. Mapa curado em `stf/curadoria/funcoes_documento.json` (`stf/funcoes.py`); exportado em `documento.meta.funcao`.
- **4.3 (aliases):** feito em três camadas, nenhuma com modelo. (a) Chave forte em `stf/aliases.py`: sem acentos, pontuação, hífens; "S.A."/"S/A" viram "SA" — junta "LTDA." com "LTDA", "Procuradoria-Geral" com "Procuradoria Geral" (563 → 544 entidades). (b) Lista curada `stf/curadoria/aliases.json`, cada entrada com motivo (assinaturas sem espaço, erro de digitação, sigla). (c) `python -m stf aliases-propor` gera `data/curadoria/aliases-propostos.json` com pares parecidos (difflib ≥ 0,9) para decisão humana; pares entre pessoas são marcados e nunca fundidos por código.
- **4.4 (pedidos e resultados por decisão):** feito em 14/09. Prompt `stf/prompts/decisao_v1.md`, módulo `stf/decisoes.py`, tabela `decisao_item`, mesma validação literal da Fase 4 (página existe, trecho ≤300 caracteres presente na página). 81 documentos decisórios (41 decisões monocráticas, 36 despachos marcados como decisão pelo portal, acórdão, decisão de julgamento, voto e voto vogal) → **251 itens** pedido → resultado: 120 determinado de ofício, 61 deferidos, 27 outro, 19 indeferidos, 12 referendados, 8 prejudicados, 3 deferidos em parte, 1 não conhecido; 8 itens descartados pela conferência literal. 7 subagentes Opus em uma leva; cada resposta bruta guardada como blob. Interface: página **Decisões** (filtros por processo, resultado, quem pediu e busca), seção "O que foi decidido" em cada processo.
- **Camada para leigos (pedido do usuário em 14/09):** glossário editorial de 32 verbetes (`stf/curadoria/glossario.json`, só termos gerais, nada sobre o caso) com componente `Termo` (nota ao clicar, funciona por toque); "Por onde começar" na capa com as três perguntas que a base responde sem interpretar (do que trata, quem participa e em que papel, o que foi decidido). Limite mantido: nenhum resumo narrativo; o que se lê são transcrições neutras com fonte.

## 7. Análise com e sem modelo: o que foi acrescentado em 14/09 (segunda rodada)

Critério: onde uma regra determinística dá o mesmo resultado que um modelo daria, a regra ganha (reproduzível, testável, sem custo). O modelo fica para o que exige leitura (asserções, pedidos → resultados).

- **Cronologia dos fatos segundo os documentos** (`stf/datas.py`): 354 das 2430 asserções trazem data no trecho literal; 334 com uma data só entram na cronologia com o tipo epistêmico e a atribuição. É o "o que aconteceu e quando" que faltava, sem narrativa: cada ponto é uma frase do documento com página.
- **Fontes oficiais externas** (`stf/externas.py`): o caso passa por Banco Central e Senado; as páginas oficiais são copiadas com hash e histórico, no mesmo regime de vigilância do portal do STF.
- **Saídas abertas** (`stf/saidas.py`): CSV e feed Atom para quem quer analisar em planilha ou acompanhar sem visitar o site.
- **Quem diz o quê**: a página de cada entidade separa fato, alegação (por quem alega) e fundamento (por julgador). É a apresentação mais honesta do material extraído: mostra a disputa sem arbitrá-la.

Ideias avaliadas e não feitas, com motivo: busca semântica por embeddings (exige modelo em tempo de consulta; a busca por texto já cobre); detecção de "contradições" entre documentos (viraria juízo do site; o que se faz é justapor, com fonte); resumo por processo (proibido pelo escopo: narrativa).

