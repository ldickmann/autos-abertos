# Mapa do caso (gerado)

Gerado em 2026-09-14T15:12+00:00 por `python -m stf mapa`. Listagem determinística da base; sem interpretação. Use para achar lacunas: o que ainda não foi coletado, extraído ou ligado.

## Processos

| processo | incidente | publicidade | relator | profundidade | andamentos | partes | docs (com texto) | asserções | decisões (itens) | coletado em |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pet 15556 (semente) | 7514886 | Público | MIN. ANDRÉ MENDONÇA | 0 | 407 | 54 | 60 (60) | 1062 | 98 | 2026-09-14 |
| Inq 5026 | 7473347 | Público | MIN. ANDRÉ MENDONÇA | 1 | 656 | 72 | 70 (70) | 450 | 55 | 2026-09-14 |
| Inq 5035 | 7498168 | Público | MIN. ANDRÉ MENDONÇA | 1 | 48 | 16 | 6 (6) | 16 | 0 | 2026-09-14 |
| Pet 15198 | 7473336 | Público | MIN. ANDRÉ MENDONÇA | 1 | 405 | 115 | 57 (57) | 684 | 64 | 2026-09-14 |
| Pet 15499 | 7509111 | Público | MIN. ANDRÉ MENDONÇA | 1 | 41 | 12 | 10 (10) | 24 | 5 | 2026-09-14 |
| Pet 15504 | 7509527 | Público | MIN. ANDRÉ MENDONÇA | 1 | 44 | 29 | 13 (13) | 29 | 7 | 2026-09-14 |
| Pet 16440 | 7649959 | Sigiloso | MIN. ANDRÉ MENDONÇA | 1 | 3 | 0 | 0 (0) | 0 | 0 | 2026-09-14 |
| Pet 16441 | 7649960 | Sigiloso | MIN. ANDRÉ MENDONÇA | 1 | 3 | 0 | 0 (0) | 0 | 0 | 2026-09-14 |
| Pet 15172 | 7471355 | Sigiloso | MIN. DIAS TOFFOLI | 2 | 4 | 0 | 0 (0) | 0 | 0 | 2026-09-14 |
| Pet 15612 | 7522443 | Sigiloso | MIN. ANDRÉ MENDONÇA | 2 | 9 | 0 | 2 (2) | 44 | 9 | 2026-09-14 |
| Rcl 88121 | 7450195 | Público | MIN. ANDRÉ MENDONÇA | 2 | 259 | 20 | 8 (8) | 121 | 13 | 2026-09-14 |
| Pet 15719 | 7536897 | Sigiloso | MIN. ANDRÉ MENDONÇA | 3 | 4 | 0 | 0 (0) | 0 | 0 | 2026-09-14 |

## Relações declaradas nos andamentos

- Inq 5026 —autuado_a_partir→ Pet 15612 (2026-03-06)
- Inq 5026 —justifica_prevencao→ Pet 15172 (2025-12-22)
- Inq 5035 —justifica_prevencao→ Inq 5026 (2026-02-13)
- Pet 15198 —justifica_prevencao→ Rcl 88121 (2025-12-22)
- Pet 15499 —justifica_prevencao→ Inq 5026 (2026-02-23)
- Pet 15504 —justifica_prevencao→ Inq 5026 (2026-02-23)
- Pet 15556 —autuado_a_partir→ Pet 16440 (2026-07-20)
- Pet 15556 —autuado_a_partir→ Pet 16441 (2026-07-20)
- Pet 15556 —justifica_prevencao→ Inq 5026 (2026-02-27)
- Pet 15556 —relacionado→ Inq 5035 (2026-02-27)
- Pet 15556 —relacionado→ Pet 15198 (2026-02-27)
- Pet 15556 —relacionado→ Pet 15499 (2026-02-27)
- Pet 15556 —relacionado→ Pet 15504 (2026-02-27)
- Rcl 88121 —autuado_a_partir→ Pet 15719 (2026-03-18)

## Grafo (uso interno)

633 nós, 1950 arestas. Por tipo de aresta: afirma_em 59, cita_processo 110, citado_em 493, co_citacao 709, numero_origem 9, parte_em 318, relacao 14, relator_de 12, representa 222, votou_em 4.

Entidades mais ligadas (grau, grupo curado, papéis, asserções que a citam):

- POLÍCIA FEDERAL — grau 92, parte, Polícia Federal, papéis ['autoridade_policial', 'interessado', 'reclamado'], 214 asserções, origem partes
- DANIEL BUENO VORCARO — grau 83, parte, papéis ['requerido', 'interessado', 'investigado', 'reclamante'], 112 asserções, origem partes
- Banco Master — grau 73, organizacao, papéis —, 84 asserções, origem documento
- Procuradoria-Geral da República — grau 64, orgao_publico, Ministério Público, papéis —, 151 asserções, origem documento
- DANIEL VORCARO — grau 44, pessoa, papéis —, 51 asserções, origem documento
- BELLINE SANTANA — grau 39, parte, papéis ['requerido'], 53 asserções, origem partes
- FABIANO CAMPOS ZETTEL — grau 38, parte, papéis ['requerido', 'interessado'], 79 asserções, origem partes
- PAULO SERGIO NEVES DE SOUZA — grau 38, parte, papéis ['requerido'], 39 asserções, origem partes
- MARILSON ROSENO DA SILVA — grau 27, parte, papéis ['requerido', 'investigado'], 34 asserções, origem partes
- ANDRÉ MENDONÇA — grau 27, ministro, Supremo Tribunal Federal, papéis —, 443 asserções, origem portal
- Banco Central do Brasil — grau 27, orgao_publico, Reguladores e sistema financeiro, papéis —, 28 asserções, origem documento
- LUIZ PHILLIPI MACHADO DE MORAES MOURAO — grau 22, parte, papéis ['requerido', 'investigado'], 39 asserções, origem partes
- HENRIQUE MOURA VORCARO — grau 22, parte, papéis ['interessado'], 30 asserções, origem partes
- FELIPE CANCADO VORCARO — grau 21, parte, papéis ['interessado'], 18 asserções, origem partes
- LEONARDO AUGUSTO FURTADO PALHARES — grau 20, parte, papéis ['requerido'], 21 asserções, origem partes
- MINISTÉRIO PÚBLICO FEDERAL — grau 20, parte, Ministério Público, papéis ['autor', 'requerente'], 47 asserções, origem partes
- JOAO CARLOS FALBO MANSUR — grau 20, parte, papéis ['interessado'], 8 asserções, origem partes
- Supremo Tribunal Federal — grau 20, orgao_publico, Supremo Tribunal Federal, papéis —, 66 asserções, origem documento
- Banco Central — grau 19, orgao_publico, Reguladores e sistema financeiro, papéis —, 39 asserções, origem documento
- PROCURADOR-GERAL DA REPÚBLICA — grau 18, parte, Ministério Público, papéis ['procurador'], 135 asserções, origem partes
- ANA CLAUDIA QUEIROZ DE PAIVA — grau 17, parte, papéis ['requerido'], 27 asserções, origem partes
- ASCENDINO MADUREIRA GARCIA — grau 17, parte, papéis ['interessado'], 2 asserções, origem partes
- LUIS FERNANDO DE ALMEIDA — grau 17, parte, papéis ['interessado'], 15 asserções, origem partes
- autoridade policial — grau 17, orgao_publico, papéis —, 30 asserções, origem documento
- ANGELO ANTONIO RIBEIRO DA SILVA — grau 15, parte, papéis ['interessado'], 0 asserções, origem partes
- CPI do Crime Organizado — grau 15, orgao_publico, papéis —, 28 asserções, origem documento
- ASTRALO 95 — grau 15, organizacao, papéis —, 8 asserções, origem documento
- SERGIO RODRIGUES LEONARDO — grau 14, advogado, papéis ['advogado'], 0 asserções, origem partes
- LUIZ ANTONIO BULL — grau 14, parte, papéis ['interessado'], 2 asserções, origem partes
- Secretaria Judiciária — grau 14, orgao_publico, Supremo Tribunal Federal, papéis —, 113 asserções, origem documento

Processos citados nos documentos e não coletados (77), por número de ligações: ADPF 395 (3), HC 79812 (3), HC 171438 (3), HC 232643 (3), HC 247450 (3), HC 247792 (3), HC 254442 (3), MS 25668 (3), AC 4005 (1), ADI 5526 (1), ADI 7083 (1), ADPF 424 (1), AP 933 (1), HC 82647 (1), HC 232627 (1), Inq 2411 (1), Inq 2842 (1), Inq 3305 (1), Inq 4342 (1), Inq 4787 (1), MS 23595 (1), Pet 3825 (1), Pet 6554 (1), Pet 13488 (1), Pet 13884 (1).

## Documentos por função

- Inq 5026: intimacao 30, decisao 20, despacho 10, termo 4, vista 3, certidao 3
- Pet 15556: decisao 24, intimacao 18, vista 6, certidao 4, termo 2, despacho 2, voto 2, acordao 1, relatorio 1
- Pet 15198: decisao 22, intimacao 19, vista 6, certidao 5, despacho 4, termo 1
- Pet 15504: decisao 4, termo 3, certidao 2, vista 2, intimacao 2
- Pet 15499: decisao 3, certidao 2, intimacao 2, termo 2, vista 1
- Rcl 88121: certidao 3, decisao 3, vista 1, intimacao 1
- Inq 5035: certidao 2, intimacao 2, despacho 2
- Pet 15612: decisao 2

## Decisões: itens pedido → resultado

Total por resultado: determinado de ofício 120, deferido (aceito) 61, outro 27, indeferido (negado) 19, referendado pelo colegiado 12, prejudicado (perdeu o objeto) 8, deferido em parte 3, não conhecido 1.

Quem mais pediu (campo literal `quem_pediu`, top 12):
- o próprio relator, de ofício: 91
- o próprio relator (de ofício): 29
- Polícia Federal: 17
- Polícia Federal (representação, e-Doc. 1); decisão submetida a referendo pelo relator: 8
- Procurador-Geral da República: 7
- autoridade policial: 4
- Fernando Alves Vieira: 4
- Polícia Federal, com manifestação favorável do Procurador-Geral da República: 4
- Ministro André Mendonça (relator), que submeteu a decisão cautelar a referendo: 3
- Roberto de Oliveira Campos Neto: 3
- defesa de Felipe Cançado Vorcaro (e-Doc. 500): 3
- Fabiano Campos Zettel (e-Doc. 287): 2

Linha do tempo das decisões com resultado deferido/indeferido/referendado (data, processo, resultado, pedido):

- None · Pet 15556 · referendado · referendo da prisão preventiva do investigado Daniel Bueno Vorcaro, decretada na decisão monocrática submetida à Turma (doc 224 p. 53)
- None · Pet 15556 · referendado · referendo da prisão preventiva do investigado Fabiano Campos Zettel, decretada na decisão monocrática submetida à Turma (doc 224 p. 53)
- None · Pet 15556 · referendado · referendo da prisão preventiva do investigado Marilson Roseno da Silva, decretada na decisão monocrática submetida à Turma (doc 224 p. 53)
- None · Pet 15556 · referendado · referendo das medidas cautelares diversas da prisão impostas ao investigado Paulo Sérgio Neves de Souza na decisão monocrática submetida à T (doc 224 p. 53)
- None · Pet 15556 · referendado · referendo das medidas cautelares diversas da prisão impostas ao investigado Belline Santana na decisão monocrática submetida à Turma (doc 224 p. 53)
- None · Pet 15556 · referendado · referendo das medidas cautelares diversas da prisão impostas ao investigado Leonardo Augusto Furtado Palhares na decisão monocrática submeti (doc 224 p. 53)
- None · Pet 15556 · referendado · referendo das medidas cautelares diversas da prisão impostas à investigada Ana Claudia Queiroz de Paiva na decisão monocrática submetida à T (doc 224 p. 53)
- None · Pet 15556 · referendado · referendo da suspensão, por tempo indeterminado, das atividades das sociedades empresárias Varajo Consultoria Empresarial Sociedade Unipesso (doc 224 p. 53)
- None · Pet 15556 · referendado · referendo da decisão monocrática do relator que decretou medidas cautelares contra os investigados, em especial a prisão preventiva de Danie (doc 226 p. 42)
- 2025-12-09 · Rcl 88121 · parcialmente_deferido · liminar de imediata suspensão das investigações perante o Juízo Federal de primeiro grau (Inquérito Policial nº 1096304-87.2025.4.01.3400 e  (doc 222 p. 23)
- 2025-12-09 · Rcl 88121 · deferido · acesso aos autos, com fundamento na Súmula Vinculante nº 14 (doc. 52) (doc 222 p. 23)
- 2025-12-27 · Inq 5026 · nao_conhecido · embargos de declaração opostos pelo Banco Central do Brasil e Ailton de Aquino Santos (doc 123 p. 1)
- 2026-01-06 · Pet 15198 · deferido · encampação parcial da manifestação da Procuradoria da República em São Paulo de 27.10.2025, com as retificações posteriores, e deferimento d (doc 183 p. 19)
- 2026-01-06 · Pet 15198 · deferido · quebra de sigilo bancário e fiscal dos investigados, no período de 20.10.2020 a 21.10.2025 (doc 183 p. 19)
- 2026-01-06 · Pet 15198 · deferido · sequestro e bloqueio de bens e valores dos investigados, conforme individualização apresentada pela autoridade policial (doc 183 p. 19)
- 2026-01-08 · Pet 15198 · parcialmente_deferido · pedido complementar de busca e apreensão em relação às 39 pessoas físicas e jurídicas elencadas na manifestação, nos endereços indicados pel (doc 188 p. 5)
- 2026-01-08 · Pet 15198 · indeferido · busca e apreensão no endereço 1 do alvo n. 2 (Daniel Bueno Vorcaro, R. Dr. Ibsen da Costa Manso, 141, São Paulo/SP) (doc 188 p. 5)
- 2026-01-08 · Pet 15198 · indeferido · busca e apreensão em relação ao alvo n. 12 (André Felipe de Oliveira Seixas Maia) (doc 188 p. 5)
- 2026-01-08 · Pet 15198 · indeferido · busca e apreensão em relação ao alvo n. 33 (Banco Master) (doc 188 p. 5)
- 2026-01-13 · Pet 15198 · deferido · expedição de mandado de busca pessoal sobre Fabiano Campos Zettel e seus pertences, no local em que ele seja encontrado (Pet. 2475/2026, e-d (doc 186 p. 6)
- 2026-01-13 · Pet 15198 · deferido · decretação da prisão temporária de Fabiano Campos Zettel pelo prazo mínimo de um dia (doc 186 p. 7)
- 2026-01-13 · Pet 15198 · deferido · decretação da proibição de deixar o país do investigado Fabiano Campos Zettel (doc 186 p. 7)
- 2026-01-13 · Pet 15198 · deferido · expedição de mandado de busca pessoal sobre Nelson Sequeiros Rodriguez Tanure e seus pertences, no local em que ele seja encontrado (doc 186 p. 7)
- 2026-01-14 · Pet 15198 · deferido · autorização para que a Procuradoria-Geral da República realize a extração e análise de todo o acervo probatório colhido nos autos, com poste (doc 185 p. 2)
- 2026-01-16 · Inq 5026 · deferido · nova prorrogação do prazo para conclusão das investigações por mais 60 (sessenta) dias (doc 121 p. 1)
- 2026-02-19 · Inq 5026 · deferido · autorização para a apresentação do investigado Daniel Bueno Vorcaro a fim de prestar depoimento perante a Comissão de Assuntos Econômicos do (doc 105 p. 6)
- 2026-02-19 · Inq 5026 · deferido · consignação de que a custódia do depoente, durante sua permanência nas dependências do Congresso Nacional, ficará sob responsabilidade da Po (doc 105 p. 6)
- 2026-02-26 · Inq 5026 · deferido · extensão dos efeitos da decisão de 26/02/2026 para afastar a obrigatoriedade de comparecimento do peticionário à CPI do Crime Organizado, tr (doc 97 p. 5)
- 2026-02-26 · Inq 5026 · deferido · garantia, caso o peticionário opte por comparecer ao ato, dos direitos ao silêncio, à assistência por advogado, de não ser submetido ao comp (doc 97 p. 6)
- 2026-02-26 · Inq 5026 · deferido · recebimento da petição como tutela incidental de urgência ou habeas corpus preventivo, com expedição de salvo-conduto para que os requerente (doc 104 p. 5)
- 2026-02-26 · Inq 5026 · deferido · garantia, caso os requerentes optem por comparecer ao ato, dos direitos ao silêncio, à assistência por advogado, de não serem submetidos ao  (doc 104 p. 5)
- 2026-02-27 · Pet 15198 · deferido · autorização e salvo-conduto para que Fabiano Campos Zettel não compareça aos atos convocatórios da CPI do Crime Organizado (Requerimentos n. (doc 169 p. 7)
- 2026-03-02 · Inq 5026 · parcialmente_deferido · garantia do direito de não comparecer à sessão da CPI do Crime Organizado designada para sua oitiva (Petição nº 22049/2026) (doc 95 p. 17)
- 2026-03-02 · Inq 5026 · deferido · subsidiariamente, convolação do requerimento de convocação em convite, nos termos realizados em relação ao atual presidente do Banco Central (doc 95 p. 16)
- 2026-03-02 · Inq 5026 · deferido · garantia expressa de direitos ao requerente caso venha a comparecer à audiência designada, na qualidade de convidado ou convocado (doc 95 p. 17)
- 2026-03-03 · Pet 15556 · indeferido · dilação do prazo para que as providências aguardem a manifestação da Procuradoria-Geral da República sobre os pedidos cautelares (doc 55 p. 3)
- 2026-03-03 · Pet 15556 · deferido · prisão preventiva de Daniel Bueno Vorcaro (doc 55 p. 40)
- 2026-03-03 · Pet 15556 · deferido · prisão preventiva de Fabiano Campos Zettel (doc 55 p. 40)
- 2026-03-03 · Pet 15556 · deferido · prisão preventiva de Luiz Phillipi Machado de Moraes Mourão (doc 55 p. 40)
- 2026-03-03 · Pet 15556 · deferido · prisão preventiva de Marilson Roseno da Silva (doc 55 p. 40)
- 2026-03-03 · Pet 15556 · deferido · medidas cautelares diversas da prisão em relação a Paulo Sérgio Neves de Souza, incluindo suspensão do exercício de função pública (doc 55 p. 40)
- 2026-03-03 · Pet 15556 · deferido · medidas cautelares diversas da prisão em relação a Belline Santana, incluindo suspensão do exercício de função pública (doc 55 p. 41)
- 2026-03-03 · Pet 15556 · deferido · medidas cautelares diversas da prisão em relação a Leonardo Augusto Furtado Palhares (doc 55 p. 41)
- 2026-03-03 · Pet 15556 · deferido · medidas cautelares diversas da prisão em relação a Ana Claudia Queiroz de Paiva (doc 55 p. 41)
- 2026-03-03 · Pet 15556 · deferido · suspensão das atividades de Varajo Consultoria Empresarial Sociedade Unipessoal Ltda (doc 55 p. 42)
- 2026-03-03 · Pet 15556 · deferido · suspensão das atividades de Moriah Asset Empreendimentos e Participações Ltda (doc 55 p. 42)
- 2026-03-03 · Pet 15556 · deferido · suspensão das atividades de Super Empreendimentos e Participações S.A. (doc 55 p. 42)
- 2026-03-03 · Pet 15556 · deferido · suspensão das atividades de King Participações Imobiliárias Ltda (doc 55 p. 42)
- 2026-03-03 · Pet 15556 · deferido · suspensão das atividades de King Motors Locação de Veículos e Participações Ltda (doc 55 p. 42)
- 2026-03-03 · Pet 15556 · deferido · vista temporária dos autos aos advogados habilitados que, na qualidade de defensores dos investigados, vierem a formular tal requerimento (doc 55 p. 47)
- 2026-03-03 · Inq 5026 · deferido · garantia do direito de não comparecer às sessões da CPI do Crime Organizado, inclusive a designada para 04 de março de 2026 (Petição nº 2361 (doc 94 p. 5)
- 2026-03-03 · Inq 5026 · deferido · atribuição da custódia do convocado à Polícia Legislativa do Senado Federal durante o depoimento (Petição nº 23955/2026, e-Doc. 446) (doc 94 p. 6)
- 2026-03-04 · Pet 15556 · deferido · autorização para que, após a conclusão dos atos cartorários, os custodiados presos preventivamente sejam conduzidos diretamente ao sistema p (doc 54 p. 3)
- 2026-03-05 · Pet 15556 · deferido · transferência do investigado preso Daniel Bueno Vorcaro para a Penitenciária Federal em Brasília (PFBRA) (doc 47 p. 4)
- 2026-03-05 · Inq 5026 · deferido · acesso, pela defesa, aos dados telemáticos referidos na informação da autoridade policial (e-Doc. 444) (doc 93 p. 2)
- 2026-03-06 · Pet 15612 · deferido · instauração de inquérito policial para averiguação da origem dos vazamentos de informações dos aparelhos do investigado para a imprensa (doc 215 p. 6)
- 2026-03-09 · Pet 15556 · deferido · ingresso de cópias impressas dos autos nas visitas dos advogados (doc 45 p. 3)
- 2026-03-09 · Pet 15556 · deferido · garantia do direito de os advogados tomarem notas escritas durante os encontros (doc 45 p. 3)
- 2026-03-13 · Pet 15556 · deferido · concessão de salvo-conduto para afastar a obrigatoriedade de comparecimento de Ana Cláudia Queiroz de Paiva perante a CPMI do Crime Organiza (doc 43 p. 5)
- 2026-03-18 · Inq 5026 · deferido · nova prorrogação do prazo do inquérito para a realização de diligências (doc 85 p. 2)
- 2026-03-20 · Pet 15556 · referendado · referendo da liminar concedida pelo Relator (doc 39 p. 1)
- 2026-03-23 · Pet 15556 · referendado · referendo da decisão cautelar que decretou a prisão preventiva dos investigados Daniel Bueno Vorcaro, Fabiano Campos Zettel e Marilson Rosen (doc 25 p. 6)
- 2026-03-23 · Pet 15556 · referendado · referendo da decisão cautelar que impôs medidas cautelares diversas da prisão aos investigados Paulo Sérgio Neves de Souza, Belline Santana, (doc 25 p. 6)
- 2026-04-02 · Pet 15556 · deferido · afastamento da obrigatoriedade de comparecimento do peticionante à CPI do Crime Organizado para prestar depoimento, convocado pelo Requerime (doc 31 p. 5)
- 2026-04-28 · Pet 15499 · deferido · instauração de PET sigilosa em apartado, vinculada ao INQ 5026, para apurar eventuais crimes de embaraço à investigação sobre organização cr (doc 197 p. 2)
- 2026-04-30 · Inq 5026 · deferido · autorização para Alberto Felix de Oliveira Neto deslocar-se até a cidade de Passos/MG, a fim de comparecer à cerimônia de velório e sepultam (doc 75 p. 4)
- 2026-04-30 · Pet 15504 · deferido · instauração de PET sigilosa em apartado, vinculada ao INQ 5026, para apurar eventuais crimes de corrupção ativa e passiva, organização crimi (doc 211 p. 1)
- 2026-05-19 · Pet 15198 · indeferido · restituição de 13 armas de fogo, carregadores e munições apreendidos na residência de Fernando Alves Vieira em cumprimento de mandado de bus (doc 157 p. 12)
- 2026-05-19 · Pet 15198 · indeferido · restituição dos veículos Mitsubishi Pajero HPE 3.2D e Land Rover Range Rover SVR apreendidos, mediante imposição de restrição de inalienabil (doc 157 p. 12)
- 2026-05-19 · Pet 15198 · indeferido · revogação das medidas cautelares assecuratórias decretadas em desfavor de Maurício Antonio Quadrado, Luis Fernando de Almeida e Flávio Aguet (doc 158 p. 10)
- 2026-05-19 · Pet 15198 · indeferido · restituição dos bens e valores apreendidos durante o cumprimento de mandado de busca e apreensão nas residências de Maurício Antonio Quadrad (doc 158 p. 10)
- 2026-05-19 · Pet 15198 · indeferido · revogação integral das medidas cautelares assecuratórias patrimoniais impostas a Felipe Cançado Vorcaro (doc 159 p. 10)
- 2026-05-19 · Pet 15198 · indeferido · restituição dos bens de titularidade de Felipe Cançado Vorcaro apreendidos em cumprimento de mandado de busca e apreensão em sua residência (doc 159 p. 10)
- 2026-05-19 · Pet 15198 · indeferido · subsidiariamente, limitação das constrições patrimoniais ao montante de R$ 1.604.420,41 (doc 159 p. 10)
- 2026-05-29 · Pet 15556 · deferido · declaração da extinção da punibilidade de PHILLIPI MACHADO DE MORAES MOURÃO, em razão do falecimento do investigado, com esteio no art. 107, (doc 22 p. 5)
- 2026-05-29 · Pet 15556 · deferido · arquivamento das investigações em face do investigado falecido PHILLIPI MACHADO DE MORAES MOURÃO (doc 22 p. 5)
- 2026-05-29 · Pet 15556 · indeferido · revisão das medidas constritivas (sequestro e bloqueio de bens) determinadas contra Henrique Moura Vorcaro, com reconhecimento das circunstâ (doc 23 p. 5)
- 2026-06-03 · Pet 15556 · indeferido · desbloqueio das contas bancárias de titularidade de Marilson Roseno da Silva, inclusive a conta destinada ao recebimento de sua aposentadori (doc 21 p. 6)
- 2026-06-03 · Pet 15556 · deferido · pedido subsidiário de que os valores mensalmente pagos a Marilson Roseno da Silva a título de aposentadoria sejam depositados em conta de ti (doc 21 p. 6)
- 2026-06-11 · Pet 15198 · deferido · instauração de procedimento autônomo perante o STF, na classe Inquérito (INQ), com traslado do apuratório oriundo da 8ª Vara Criminal Federa (doc 149 p. 5)
- 2026-06-11 · Pet 15198 · deferido · manutenção da PET nº 15.198 em tramitação apartada, com escopo restrito ao processamento e acompanhamento das medidas cautelares em curso ou (doc 149 p. 5)
- 2026-06-12 · Inq 5026 · deferido · autorização para Alberto Felix de Oliveira Neto deslocar-se à Capital Federal para atendimento de intimação para prestar declarações nos aut (doc 72 p. 3)
- 2026-07-13 · Pet 15504 · deferido · prorrogação de prazo para a realização de diligências complementares para a ultimação das investigações (doc 207 p. 2)
- 2026-07-20 · Pet 15198 · indeferido · restituição dos seis veículos automotores apreendidos na residência de Henrique Moura Vorcaro em cumprimento de mandado de busca e apreensão (doc 144 p. 13)
- 2026-07-20 · Pet 15198 · indeferido · pedido subsidiário de devolução da posse dos veículos apreendidos mediante nomeação de Henrique Moura Vorcaro como fiel depositário (doc 144 p. 12)
- 2026-07-20 · Pet 15198 · indeferido · restituição dos dois veículos apreendidos na residência de Thiago Assumpção Henriques em cumprimento de mandado de busca e apreensão em 14/0 (doc 144 p. 13)
- 2026-07-20 · Pet 15198 · indeferido · restituição da posse dos dois veículos apreendidos a Thiago Assumpção Henriques na condição de fiel depositário (doc 144 p. 12)
- 2026-07-22 · Pet 15499 · deferido · prorrogação de prazo para a realização de diligências complementares nas investigações (e-Doc. 44) (doc 194 p. 1)
- 2026-07-23 · Pet 15556 · indeferido · autorização para que o contato de Fabiano Campos Zettel com seus procuradores seja feito em sala reservada (doc 12 p. 4)
- 2026-07-23 · Pet 15556 · indeferido · autorização para que o estabelecimento prisional permita a entrada de aparelho televisor na cela de Fabiano Campos Zettel (doc 12 p. 4)
- 2026-07-24 · Pet 15556 · deferido · compartilhamento de elementos informativos constantes de processos judiciais relacionados à Operação Compliance Zero, para instrução de inve (doc 11 p. 5)
- 2026-07-24 · Pet 15556 · deferido · autorização para oitiva do investigado DANIEL BUENO VORCARO, com fixação de data e local, para instrução dos Inquéritos Administrativos nº 1 (doc 13 p. 8)
- 2026-07-24 · Pet 15556 · deferido · fixação da forma de realização da oitiva, preferencialmente presencial nas dependências do estabelecimento prisional, subsidiariamente por v (doc 13 p. 9)
- 2026-07-24 · Pet 15556 · deferido · prévia intimação da defesa técnica do investigado para acompanhamento da oitiva (doc 13 p. 9)
- 2026-08-25 · Inq 5026 · deferido · prorrogação de prazo para a realização de diligências complementares nas investigações (e-Doc. 1031) (doc 68 p. 3)
- 2026-09-04 · Pet 15504 · deferido · prorrogação de prazo para a realização de diligências complementares nas investigações (e-Doc. 91) (doc 203 p. 2)

## Asserções

Por tipo: alegacao_parte 646, fato_processual 1067, fundamento_decisorio 717.
Quem mais afirma (`atribuida_a`, top 12): Ministro André Mendonça (relator) 292, Ministro André Mendonça 236, Polícia Federal 164, Procuradoria da República em São Paulo 81, Procuradoria-Geral da República 71, Ministro Gilmar Mendes 67, Ministro Dias Toffoli (Relator) 59, Ministério Público Federal 35, Ministro Dias Toffoli 26, Ministro Dias Toffoli (relator) 25, Procurador-Geral da República 23, Comissão de Valores Mobiliários (CVM) 14.

## Referências nos documentos

Dispositivos legais mais citados: art. 270 CPC (72 docs), art. 5 Lei 11.419/2006 (72 docs), art. 5 CF (14 docs), art. 319 CPP (6 docs), art. 4 Lei 9.613/1998 (6 docs), art. 120 CPP (5 docs), art. 125 CPP (5 docs), art. 2 Lei 12.850/2013 (5 docs), art. 1 Lei 9.613/1998 (4 docs), art. 312 CPP (4 docs), art. 4 Lei 7.492/1986 (4 docs), art. 6 Lei 7.492/1986 (4 docs), art. 282 CPP (3 docs), art. 317 CP (3 docs), art. 320 CPP (3 docs).

## Lacunas conhecidas

- 5 processo(s) sigiloso(s): o portal só devolve cabeçalho e andamentos genéricos
- 77 processo(s) citados em documentos e não coletados (a maioria são precedentes; os que importam ao caso aparecem no topo da lista acima)
- 53 proposta(s) de alias de entidade aguardando decisão humana (data/curadoria/aliases-propostos.json)

