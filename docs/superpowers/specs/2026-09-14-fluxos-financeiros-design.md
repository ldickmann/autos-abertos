# Fluxos financeiros do caso Master — esquema, carga do RIF 140515 e mapa interativo

Data: 14/09/2026. Pedido do usuário: extrair todos os dados da Pet 15.645 / RIF 140515, criar o esquema e as tabelas no banco existente, organizar com boas práticas de análise de dados e construir um mapa completo e interativo dos pagamentos do caso Master.

## Premissa e limite

O RIF 140515 (COAF, 25/02/2026) **não registra pagamentos do Banco Master nem de Daniel Vorcaro**. Registra fluxos das entidades de Fabiano Campos Zettel (Igreja Batista da Lagoinha Belvedere, Moriah Asset, Super Empreendimentos, Pipe Participações); pessoas da família Vorcaro aparecem como remetentes para a igreja. Por isso o esquema é **genérico** (qualquer fluxo financeiro descrito em qualquer peça, com proveniência por página) e o RIF é a **primeira fonte carregada**. As demais peças do acervo (relatórios da PF, Pet 16.662, outros RIFs) entram depois no mesmo modelo, e só então o mapa cobre "tudo que o Master/Vorcaro pagou". O site diz isso com todas as letras.

Um RIF não é prova (RE 1.055.941; Rcl 61.944; aviso do próprio relatório). Cada registro carrega quem comunicou (banco, cooperativa, cartório, concessionária) e o trecho literal.

## 1. Proveniência (camada bruta)

- Os 6 PDFs da Pet 15.645 entram no pipeline existente como uma **coleta de documentos** (`data/raw/coletas/<ts>-documentos-acervo-7526458.jsonl`): uma linha `aba: acervo` para o arquivo `Pet16704-pt3.7z` (URL em docspublicos.stf.jus.br, sha256, blob) e seis linhas `aba: documento`, `endpoint: docspublicos`, `id_portal: Pet15645/<nnnnn>_<hash>`, `url` = endereço do arquivo no SharePoint do STF, `user_agent` = o UA Chrome usado (a exceção fica registrada). Blobs em `data/raw/blobs/<sha256>.pdf`.
- `python -m stf ingerir <registro>` cria as linhas em `documento`; `extrair-texto` preenche `documento_pagina`; `exportar` gera `/documento/<id>`. `reconstruir` continua provando que os blobs são a fonte.
- CPFs, RGs e endereços residenciais ficam só nos blobs. Nada disso entra em tabela nem no site.

## 2. Esquema (SQLite, `stf/db.py`)

Dinheiro em **centavos inteiros**; datas ISO `AAAA-MM-DD`; vocabulários fechados com `CHECK`; toda linha de fato tem `pagina` e `trecho_fonte` literal (verificado contra `documento_pagina` na carga, como as asserções).

| Tabela | O que é | Colunas principais |
|---|---|---|
| `fluxo_fonte` | a peça de onde os fluxos saíram | id, tipo (`rif`), identificador (`140515.2.9294.11521`), orgao (`COAF`), destinatario (`PF/SP`), emitido_em, documento_id → documento, incidente, curadoria_path, curadoria_sha256, carregado_em |
| `fluxo_ator` | pessoa física ou jurídica | id, chave UNIQUE (`cnpj:<14 dígitos>` ou `cpf:<6 dígitos do meio>`), nome, tipo (`pessoa_fisica`/`pessoa_juridica`), documento_mascarado (CNPJ completo; CPF no padrão `***.###.###-**` do Portal da Transparência), atividade, entidade_id → entidade (ligação com as partes do caso, por nome normalizado) |
| `fluxo_comunicacao` | uma comunicação do RIF (bloco numerado) | id, fonte_id, secao (`suspeita`/`automatica`/`especie`), numero (`1`, `2.1`, `3.4`…), segmento, comunicante, local, periodo_inicio, periodo_fim, valor_centavos, creditos_centavos, debitos_centavos, informacoes (literal), consideracoes (literal), pagina_inicio, pagina_fim |
| `fluxo_participacao` | quem aparece em cada comunicação e como | comunicacao_id, ator_id, papel (`titular`/`remetente`/`beneficiario`/`responsavel`/`procurador`/`vendedor`/`outros`) |
| `fluxo_transacao` | um fluxo de dinheiro | id, comunicacao_id, origem_ator_id, destino_ator_id, valor_centavos, data, periodo_inicio, periodo_fim, tipo (`pix`/`ted`/`boleto`/`cdb_rdb`/`cartao`/`cheque`/`tributo`/`escritura_compra`/`escritura_doacao`/`alienacao_fiduciaria`/`compra_veiculo`/`pagamento_titulo`/`outros`), natureza (`individual` = uma operação datada; `agregado` = "N lançamentos totalizando X"; `resumo_tipo` = total por tipo de transação no período), quantidade, bem_id, descricao, pagina, trecho_fonte |
| `fluxo_bem` | veículo ou imóvel objeto de uma comunicação | id, comunicacao_id, tipo (`veiculo`/`imovel`), descricao, valor_centavos, valor_referencia_centavos, data_negocio, identificacao (JSON: placa, chassi, NF, tabelião — **não exportado**) |
| `fluxo_ocorrencia` | o enquadramento normativo que motivou a comunicação | id, comunicacao_id, norma, codigo, descricao |

Índices: `fluxo_transacao(origem_ator_id)`, `(destino_ator_id)`, `(comunicacao_id)`; `fluxo_participacao(ator_id)`.

## 3. Dataset curado (camada de extração)

`data/curadoria/fluxos/rif-140515.json`: um JSON com `fonte`, `atores`, `comunicacoes[]` (cada uma com `participacoes`, `transacoes`, `bens`, `ocorrencias`). Extração assistida: `stf/fluxos.py` tem parsers para os blocos regulares do RIF (tabelas "Relacionados"; listas "Principais remetentes/destinatários": `NOME - DOC ( ATIVIDADE ) - N lançamento(s) no total de: R$X`), usados para gerar as entradas repetitivas; os fluxos narrativos (TEDs datadas, escrituras) são transcritos à mão com `trecho_fonte`. O arquivo é o artefato congelado; o hash dele fica em `fluxo_fonte`.

Validação na carga (`python -m stf ingerir-fluxos data/curadoria/fluxos/rif-140515.json`): campos obrigatórios, enums, inteiros, datas ISO, chaves de ator resolvidas, e **cada `trecho_fonte` presente na página indicada** (comparação sem espaços, porque o texto do PDF tem espaços dentro de palavras). Falha = nada é gravado.

Testes (`tests/test_fluxos.py`): esquema; validador rejeita registro ruim; carga de um fixture pequeno; verificação de trecho; consistência do dataset real (soma dos TEDs de Zettel para a Super = R$ 9.180.000; 4 veículos = R$ 4.950.000; créditos da igreja = R$ 28.493.311,91; Luzom = 23.118.509,79 + 13.800.000); export tem a forma esperada e não vaza `identificacao` nem CPF completo.

## 4. Exportação (camada de análise)

`exportar` grava `fluxos.json` — `{fontes, atores, comunicacoes, transacoes, grafo: {nos, arestas}}`, arestas agregadas por par (origem, destino) com soma, contagem e ids das transações — e `saidas` grava `fluxos.csv` (uma linha por transação, com página e trecho) para quem quiser abrir em planilha ou pandas.

## 5. Página de dados (site)

**Revisão de 14/09 (noite), pedido do usuário:** o "mapa" é de tabelas, não de grafo. Nenhum grafo é renderizado para o usuário (a página `/grafo` e o Cytoscape saíram do site; `grafo.json` continua como ferramenta interna). A página `/rede-de-pagamentos` passa a ser: cabeçalho (o que é e não é) → "Em números" (fichas numéricas: total comunicado, operações datadas, pessoas, por ano, quem mais recebeu/pagou) → painel com **uma busca e quatro abas** (Pessoas e empresas · Fluxos · Comunicações · Bens), cada aba com filtros próprios, ordenação por coluna e linha expansível com página e trecho; coluna "situação nos autos" (status literal do portal) para quem é parte no caso → downloads (5 CSV + JSON), dicionário de dados, consultas SQL prontas e método. A navegação do site foi reagrupada em 6 seções (Início · Rede de pagamentos · Acontecimentos · Autos · Quem é quem · Ajuda) com segunda linha contextual.

<details><summary>Desenho original (grafo), substituído</summary>



Página `/rede-de-pagamentos` (nav: "Fluxos"), com:
- cabeçalho que diz o que é (RIF 140515, Pet 15.645), o que não é (não é prova; Master/Vorcaro não aparecem como pagadores) e de onde veio (documento, páginas, hash);
- **grafo** (Cytoscape, já dependência): nós = atores (forma por PF/PJ, tamanho pelo volume), arestas = fluxos agregados por par (largura pelo valor, rótulo em R$); filtros: seção, natureza (individual/agregado), valor mínimo, ano, busca por nome; clique no nó ou na aresta abre painel com as transações (valor, data, tipo, página, trecho literal) e link para a página do documento;
- **tabela** das transações (ordenável) e link para o CSV;
- as comunicações como fichas, com o texto literal do comunicante em bloco recolhível.

Funciona em 375 px (grafo com altura limitada, tabela responsiva já existente).

</details>

## 6. Fora do escopo

Ingerir os 7.773 arquivos do acervo; o "jornal" (capa, editorias, matérias) desenhado antes desta troca de foco — fica registrado em `BACKLOG.md`.

## Plano de execução

1. Proveniência: gravar blobs + registro da coleta de documentos; `ingerir`; `extrair-texto`; conferir `/documento/<id>` no export.
2. Esquema + validador + carga (`stf/fluxos.py`, `stf/db.py`, CLI), com testes primeiro.
3. Dataset `rif-140515.json` (parsers para as listas + transcrição com trechos) e testes de consistência.
4. Export `fluxos.json` / `fluxos.csv` + testes.
5. Página `/rede-de-pagamentos` + nav; build; verificação no navegador (desktop e 375 px).
6. `exportar`, carimbo, commit; PR `feat/fluxos-rif-140515` → `develop`.
