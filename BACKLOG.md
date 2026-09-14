# Fila de trabalho

Ordem de execução decidida em 14/09/2026. Cada item vira commit próprio; o site republica a cada push.

| # | item | estado | notas |
|---|---|---|---|
| 1 | Fase 4: extrair os 226 documentos via Claude Code | feita (14/09/2026): 226/226 docs, 2430 asserções (646 alegações, 1067 fatos, 717 fundamentos), 6 descartadas por trecho | plano em `data/extracao/PLANO.md`; próximas levas com o subagente `extrator` (`.claude/agents/extrator.md`, `claude-opus-4-8`), que só é carregado em sessão nova |
| 2 | Análise dos dados e cruzamentos | feita: `ANALISE-DADOS.md`; C1–C4 em `stf/referencias.py`, C6–C9 no grafo e no export; 4.2, 4.3 e 4.4 feitos (14/09, seção 6): 251 itens pedido → resultado em 81 decisões | revisar as 26 propostas de alias (decisão humana) |
| 3 | Grafo: navegação e leitura visual | feito (commit f9cc78e); folha inferior e rótulos compactos no celular feitos (14/09) | legenda, camadas, busca, ficha com fontes, caminho mais curto, dois layouts; em tela estreita rótulo só para 5+ ligações, vizinhos do foco sempre rotulados |
| 4 | Frontend: versão escura, minimalista, microinterações 3D | feito; contraste WCAG auditado; página inicial como "capa dos autos" (14/09) | — |
| 5 | Auditoria de links após o rename | feita | URL antiga do Pages devolve 404; `github.com/ldickmann/nao-definido` redireciona |
| 6 | Pet 15719 (profundidade 3) | feita: coleta `20260914T071922Z-7536897` ingerida | processo **sigiloso**: o portal devolve 4 andamentos, 0 partes, 0 documentos; nada a baixar ou extrair |
| 7 | Atualizar `FASE4-RELATORIO.md` ao fechar a Fase 4 | feito (14/09/2026) | execução pelo Claude Code, números, limitações, como repetir |
| 9 | Responsividade | feita (14/09/2026): nav em trilho até `lg`, tabelas viram folhas abaixo de `md`, grafo com canvas primeiro e ficha como folha inferior, filtros recolhidos no celular, formulários em grade | nenhuma página estoura a largura em 375/768; checar em aparelho real |
| 10 | Versionamento | feito (14/09/2026): `develop` padrão, `main` publica, branches `feat/`, `fix/`, `chore/`, `docs/` | convenção no `README.md` |
| 8 | Texto duplicado em PDFs com negrito simulado | corrigido em `stf/documentos.py` (`dedupe_chars`) | só o doc 25 era afetado; resposta antiga guardada em `respostas/_invalidas/` |
| 11 | Camada para leigos | feita (14/09): página Decisões, glossário (48 verbetes) com termos clicáveis (`Termo`) na capa, nas partes, nos resultados e nos tipos de andamento das duas linhas do tempo (explicação do portal primeiro, glossário depois); condições de medidas cautelares com "em linguagem simples"; roteiro de teste em `docs/TESTE-LEITURA.md` | aplicar o roteiro com 2–3 pessoas e voltar com os achados |

## Restrições que valem para todos os itens

- Proveniência obrigatória; tipagem epistêmica; append-only; coleta educada; sem inferência sobre pessoas (ver `README.md`).
- No máximo 7 subagentes por vez; levas sequenciais; Opus para extração (pedido do usuário em 14/09).
- Nenhuma fase é dada como concluída com teste falhando.

## Missão registrada em 14/09/2026 (pedido do usuário)

O sistema existe para que qualquer pessoa consiga consultar e verificar o que está nos autos públicos deste caso, e para que esses autos não desapareçam nem sejam alterados sem que se perceba. O que torna isso possível não é opinião, é engenharia: cópias com hash, fontes em cada item e nenhuma conclusão sobre pessoas (é isso que deixa a base difícil de contestar). Tarefas derivadas, para executar em ordem:

| # | tarefa | por quê | como |
|---|---|---|---|
| 12 | Manifesto público de integridade | **feito (14/09)**: `integridade.json` (406+ snapshots, 226 documentos, registros de coleta) + `INTEGRIDADE.sha256`; `python -m stf verificar` (320 blobs conferidos, 0 divergentes); página `/verificar`; caixa "como verificar" em cada documento | gerar `INTEGRIDADE.json` (sha256 de cada snapshot, blob e documento, com data de coleta e URL de origem) na exportação; página `/verificar` explicando como conferir um documento: baixar de novo no portal, calcular o sha256, comparar; ou usar o código de autenticação do STF |
| 13 | Carimbo de tempo independente | ferramenta pronta (`scripts/carimbar.py`, OpenTimestamps); carimbar a cada publicação e completar as provas com `--upgrade` horas depois | ancorar o hash do manifesto numa prova pública de tempo (OpenTimestamps sobre a Bitcoin, gratuito, verificável offline) a cada publicação; guardar as provas `.ots` no repositório |
| 14 | Espelhos e cópias fora do GitHub | parcial: originais no repositório (16) e `README` explica a réplica; falta a *release* versionada e a cópia no Internet Archive | publicar o conjunto completo (sqlite, JSON, blobs dos documentos, registros de coleta) como *release* versionada; enviar cópia ao Internet Archive (item com metadados) e, se viável, ao IPFS; documentar em `README.md` como qualquer pessoa hospeda uma cópia (site estático + dados) |
| 15 | Vigilância de mudanças no portal | **feito (14/09)**: `python -m stf vigiar` recoleta, compara e registra em `CHANGELOG-PORTAL.md` + `mudancas.json`; página `/mudancas`; primeira rodada executada | recoleta periódica (local, por causa do bloqueio a datacenters) com `python -m stf diff`; registrar num `CHANGELOG-PORTAL.md` só o que mudou (andamento que sumiu, documento que deixou de baixar, publicidade que virou sigilo), com as datas dos dois snapshots; página "O que mudou" no site |
| 16 | Documentos completos no repositório | **feito (14/09)**: blobs versionados (90 MB: 225 PDFs, 91 páginas HTML, JSON das sessões); clonar é espelhar | avaliar tamanho total; se couber, versionar os blobs (ou usar Git LFS / release); caso contrário, garantir que o item 14 os cubra |
| 17 | Reprodutibilidade por terceiros | **feito (14/09)**: `docs/REPRODUZIR.md` (coletar → reconstruir → reingerir → exportar → verificar) | roteiro em `docs/REPRODUZIR.md`: coletar, reconstruir, reingerir as respostas versionadas, exportar; testes que comparam contagens e hashes com os publicados |
| 18 | Guarda-corpos de neutralidade | **feito (14/09)**: `tests/test_neutralidade.py` varre fatos, itens de decisão, glossário e textos das páginas; nomes de crimes previstos em lei ("organização criminosa") não contam | teste automatizado que falha se textos gerados (asserções, decisões, glossário) contiverem termos de juízo sobre pessoas fora de citação literal; revisão periódica das introduções das páginas |

Regra que vale para todas: nada aqui é sobre condenar alguém; é sobre garantir que o registro público continue público, íntegro e legível.
