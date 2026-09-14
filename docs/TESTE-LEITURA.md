# Roteiro de teste de leitura com pessoas leigas

Objetivo: descobrir onde o site deixa de ser entendido por quem não é da área jurídica, sem explicar nada antes. Duas ou três pessoas bastam para achar os problemas maiores. Duração: 20 a 30 minutos por pessoa, no celular ou no computador.

## Como conduzir

1. Não explique o site. Diga só: "é um site que mostra o que está nos autos de processos do STF". Peça que a pessoa pense em voz alta.
2. Anote o que a pessoa diz e onde trava, sem ajudar. Só ajude se ela pedir duas vezes.
3. Ao final, faça as perguntas de encerramento.

## Tarefas (uma de cada vez)

| # | tarefa | o que observar | onde fica a resposta |
|---|---|---|---|
| 1 | "Do que trata o processo principal?" | encontra o assunto na capa? entende "Prisão Preventiva" sem clicar no termo? | capa → assunto; termo "prisão preventiva" no glossário |
| 2 | "Quem está sendo investigado, e quem é advogado?" | acha a lista de partes? entende que "investigado" e "requerido" são status, não culpa? | página do processo → Partes; termos clicáveis |
| 3 | "O que a Polícia Federal pediu e o que o ministro decidiu sobre prisão?" | usa a página Decisões e os filtros? entende "deferido" e "indeferido"? abre a fonte? | Decisões → filtro "quem pediu" + busca "prisão" |
| 4 | "Em que dia o STF confirmou (referendou) uma decisão do relator?" | acha o resultado "referendado"? entende o termo? | Decisões → filtro resultado |
| 5 | "Quais condições uma pessoa teve de cumprir em vez de ficar presa?" | acha as condições num item de decisão? a linha "em linguagem simples" ajuda? | Decisões → condições |
| 6 | "Mostre uma frase do documento original que sustenta uma dessas informações." | abre "Fonte" e chega ao documento na página certa? | qualquer item → Fonte → documento |
| 7 | "Quais outros processos estão ligados ao principal, e por quê?" | usa a capa (apensos)? acha a relação declarada na página do processo? | capa → apensos → página do processo |
| 8 | "O que significa 'Vista à PGR'?" | clica no termo na linha do tempo? entende a explicação do portal? | linha do tempo → termo |

## Perguntas de encerramento

- Em uma frase: o que este site é? (Se a resposta for "um resumo do caso", a comunicação falhou: é uma base do que está nos autos, com fonte em cada item.)
- Alguma informação pareceu opinião do site, e não do documento? Qual?
- Houve alguma palavra que você não entendeu e não conseguiu descobrir o significado?
- O que você faria com este site?

## Como registrar

Copie a tabela abaixo para cada pessoa e preencha com "conseguiu / conseguiu com dificuldade / não conseguiu" e uma observação.

| tarefa | resultado | observação (o que travou, o que disse) |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |
| 6 | | |
| 7 | | |
| 8 | | |

## O que fazer com o resultado

- Palavra não entendida → verbete novo em `stf/curadoria/glossario.json` (só termos gerais, nada sobre o caso) e, se for um tipo de andamento, checar se o portal tem explicação própria.
- Tarefa não concluída por não achar a página → mudar a capa ("Por onde começar") ou a navegação, não o conteúdo.
- Informação lida como opinião → rever o texto da página (títulos e introduções), nunca as transcrições, que são literais.
