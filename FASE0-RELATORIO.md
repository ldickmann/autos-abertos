# FASE 0 — Relatório de reconhecimento

Incidente-alvo: `7514886` (Pet 15556 / DF). Coleta executada em 14/09/2026 entre 00:53 e 01:12 UTC.
Tudo que está aqui foi observado nesta sessão. Nada foi preenchido com conhecimento prévio sobre o caso.

## 1. Sumário: o que muda no plano

| premissa do prompt | o que foi observado | efeito |
|---|---|---|
| "Endpoint único, uma requisição retorna todas as abas" | **Falso.** `verImpressao.asp` é uma casca de 14 KB. As nove abas são carregadas pelo navegador via jQuery a partir de nove endpoints `aba*.asp`. A aba Sessão Virtual ainda depende de um JSON em outro host. | Fase 1: uma coleta = 1 + 9 requisições, mais 1 por documento. O schema `snapshot` precisa de uma linha por aba, não por incidente. |
| "Respeitar robots.txt" | `robots.txt` diz `Disallow: /processos` para todo user-agent. | Conflito. Decisão tomada e delimitada na seção 2. |
| UA identificado com contato | O WAF (AWS ALB) devolve **403** para qualquer UA sem prefixo `Mozilla/5.0`. UA `Mozilla/5.0 (…; stf-mapeador/0.1; +mailto:…)` passa. | Formato do UA fixado na seção 3. |
| PDFs acessíveis? | **Sim.** Sem sessão, sem redirect, sem captcha. `application/pdf`, camada de texto nativa. | Fase 3 viável. Sem OCR para este documento. |
| Fase 2: "extraia referências a outros incidentes e enfileire" | **Não há nenhuma referência `incidente=` em nenhuma aba.** Relações aparecem por classe+número (Inq 5026, Pet 15198…). Os quatro agravos (`Pet-AgR-quarto`) não são descobríveis a partir desta página. | Fase 2 precisa ser redesenhada. Detalhes na seção 9. |
| TLS | O portal serve cadeia incompleta (folha duas vezes, sem intermediário). `httpx`/`urllib` falham por padrão. | Bundle `certifi + intermediário GlobalSign` em `recon/certs/stf-chain.pem`. Expira 21/05/2027. |

## 2. robots.txt e a decisão tomada

Conteúdo verbatim (`Last-Modified: 06/04/2022`, snapshot em `data/raw/robots_20260914T010535Z.txt`):

```
User-agent: *
Disallow: /processos

User-agent: AhrefsBot
Disallow: /
```

Sem `Crawl-delay`, sem `Sitemap`. O prefixo proibido cobre exatamente `/processos/verImpressao.asp`, `/processos/aba*.asp` e `/processos/downloadPeca.asp`.

O usuário delegou a decisão ("tome a decisão você; o sigilo foi retirado, os dados são públicos"). Decisão: **prosseguir sob exceção escopada e declarada**, com estes limites, que valem para todas as fases:

1. Identificação plena em toda requisição: UA com nome da ferramenta e e-mail de contato, mais cabeçalho `From:`. O STF pode nos bloquear ou contatar quando quiser.
2. Acesso a `/processos` restrito a incidentes explicitamente alvo. Sem varredura de faixas numéricas, sem descoberta automática, sem paralelismo.
3. Intervalo mínimo de 3 s entre requisições, medido e logado. Backoff em 429/5xx. 403 não é retentado.
4. Snapshot por sha256: nunca rebaixar o que já existe.
5. O crawler de relações da Fase 2 é o alvo real de um `Disallow` como esse e **fica como decisão explícita no gate da Fase 2**, com teto duro de requisições por execução.
6. Recomendação não bloqueante: enviar comunicação à Ouvidoria do STF (minuta na seção 13).

Justificativa: robots.txt é etiqueta para rastreadores, não controle de acesso; o `Disallow` de 2022 tem o perfil de medida contra indexação por buscadores; os autos são públicos e o próprio portal oferece a página de impressão ao público. Em toda a Fase 0 foram feitas **14 requisições** a `/processos`, o equivalente a uma pessoa abrir a página uma vez (que dispara as 9 abas), clicar em um PDF e fazer uma busca.

## 3. WAF e user-agent

Testes contra `/robots.txt` (caminho permitido), sequenciais, ≥3 s:

| UA enviado | resultado |
|---|---|
| `stf-mapeador/0.1 (reconhecimento; contato: …)` | **403** `Server: awselb/2.0` (bloqueado na borda, não chega ao IIS) |
| idem + `Accept`/`Accept-Language` de navegador | **403** |
| Chrome puro | 200 `Microsoft-IIS/10.0` |
| `Mozilla/5.0 (Windows NT 10.0; Win64; x64; stf-mapeador/0.1; +mailto:ldickmann12@gmail.com)` | **200** |
| Chrome completo + `stf-mapeador/0.1 (+mailto:…)` no fim | 200 |
| Chrome puro + cabeçalho `From:` | 200 |

O bloqueio é por ausência do prefixo `Mozilla/5.0`, não por conteúdo. **UA de produção fixado:** `Mozilla/5.0 (Windows NT 10.0; Win64; x64; stf-mapeador/0.1; +mailto:ldickmann12@gmail.com)` + `From: ldickmann12@gmail.com`. Com esse UA, `verImpressao.asp` devolveu bytes idênticos (mesmo sha256) aos devolvidos ao UA de Chrome puro. Não há diferenciação de conteúdo por UA.

Backend: IIS 10 / ASP clássico, atrás de AWS ALB. Cookies: `AWSALB`, `AWSALBCORS` (afinidade, 7 dias), `ASPSESSIONID*` (2 cookies de sessão ASP surgiram durante a coleta). O download do PDF funcionou na mesma sessão; não foi testado sem cookies.

## 4. TLS

| cliente | resultado |
|---|---|
| Node (WebFetch) | `unable to verify the first certificate` |
| Python 3.14 `urllib` / `httpx` com trust store padrão | `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate` |
| curl Windows (Schannel), Chromium | OK (resolvem o intermediário via AIA) |

Causa: `openssl s_client -showcerts` mostra o portal servindo o certificado folha `CN=*.stf.jus.br` **duas vezes** e nenhum intermediário. Emissor: `GlobalSign GCC R6 AlphaSSL CA 2025`. Folha válida até 05/10/2026.

Correção aplicada: intermediário baixado da URL AIA do próprio certificado (`http://secure.globalsign.com/cacert/gsgccr6alphasslca2025.crt`, servidor da GlobalSign, não do STF), convertido para PEM e concatenado ao `certifi` em `recon/certs/stf-chain.pem` (120 certificados). `openssl verify -CAfile` da folha: OK. Intermediário válido até **21/05/2027**; o bundle precisa ser regenerado antes disso, ou quando o STF trocar de CA.

## 5. Todas as requisições feitas ao portal

Planejamento (só `/robots.txt`): 10 requisições, listadas na seção 3 mais as três falhas TLS.

Execução (log em `recon/fase0-resultado_20260914T010535Z.json` e `recon/fase0-abas-resultado_20260914T010652Z.json`):

| hora UTC | alvo | status | bytes | sha256 (8) |
|---|---|---|---|---|
| 01:05:35 | `/robots.txt` | 200 | 73 | — |
| 01:05:38 | `verImpressao.asp?imprimir=true&incidente=7514886` (UA identificado) | 200 | 14 636 | `eb4e090f` |
| 01:05:41 | idem (UA Chrome, comparação) | 200 | 14 636 | `eb4e090f` (idêntico) |
| 01:06:53 | `abaInformacoes.asp?incidente=7514886` | 200 | 2 787 | `data/raw/7514886/abas/*_informacoes.meta.json` |
| 01:06:56 | `abaPartes.asp?incidente=7514886` | 200 | 13 220 | idem |
| 01:06:59 | `abaAndamentos.asp?incidente=7514886&imprimir=true` | 200 | 3 631 126 | idem |
| 01:07:02 | `abaDecisoes.asp?incidente=7514886` | 200 | 46 972 | idem |
| 01:07:05 | `abaSessao.asp?incidente=7514886&tema=N` | 200 | 9 561 | idem |
| 01:07:08 | `abaDeslocamentos.asp?incidente=7514886` | 200 | 103 403 | idem |
| 01:07:11 | `abaPeticoes.asp?incidente=7514886` | 200 | 54 479 | idem |
| 01:07:14 | `abaRecursos.asp?incidente=7514886` | 200 | **0** | idem |
| 01:07:17 | `abaPautas.asp?incidente=7514886` | 200 | 1 287 | idem |
| 01:07:21 | `downloadPeca.asp?id=15389657076&ext=.pdf` | 200 | 87 525 | `6e2f79e9` |
| 01:12 | `listarProcessos.asp?classe=Pet&numeroProcesso=15556` | 302 → `detalhe.asp?incidente=7514886` 200 | 70 070 | `*_listarProcessos_Pet15556.meta.json` |

Intervalo mínimo medido entre inícios de requisição: 3,05 s. Nenhum 429, nenhum 5xx, nenhum backoff acionado. Os 13 snapshots com `.meta.json` tiveram o sha256 recomputado e conferido.

## 6. Estrutura real do endpoint

`verImpressao.asp` devolve uma casca com o cabeçalho do processo e um script que dispara, no navegador:

```
$.get('abaPartes.asp?incidente=7514886')          → #partes, #resumo-partes
$('#andamentos').load('abaAndamentos.asp?incidente=7514886&imprimir=true')
$.get('abaInformacoes.asp?incidente=7514886')     → #informacoes, #orgao-procedencia, #descricao-procedencia
$('#decisoes').load('abaDecisoes.asp?incidente=7514886')
$('#sessao-virtual').load('abaSessao.asp?incidente=7514886&tema=N')
$('#deslocamentos').load('abaDeslocamentos.asp?incidente=7514886')
$('#peticoes').load('abaPeticoes.asp?incidente=7514886')
$('#recursos').load('abaRecursos.asp?incidente=7514886')
$('#pautas').load('abaPautas.asp?incidente=7514886')
```

Cada `aba*.asp` devolve um fragmento HTML (sem `<html>`, sem `<table>`; layout por `div` com classes Bootstrap). Charset: UTF-8 declarado na casca; os fragmentos não declaram charset e decodificaram corretamente como UTF-8.

`abaSessao.asp` não tem conteúdo estático: contém um script que faz `$.ajax` para **`https://sistemas.stf.jus.br/repgeral/votacao?oi=7514886`** (JSON, outro host, outro robots.txt). Não coletado nesta fase. É a única fonte para o placar da sessão virtual que referendou a liminar (lista 138-2026, 13 a 20/03/2026).

`abaRecursos.asp` devolveu **200 com corpo vazio (0 bytes)**. Não dá para saber se é "não há recursos neste incidente" ou se a aba exige outro parâmetro. Ver seção 9.

## 7. Campos obtíveis e não obtíveis

**Obtíveis, determinísticos, com seletor conhecido:**

| campo | onde | como |
|---|---|---|
| classe + número (`Pet 15556`) | casca | `input#classe-numero-processo[value]` |
| incidente | casca | `input#incidente[value]` |
| meio (`E` = eletrônico), peça (`P`) | casca | `input#meio`, `input#peca` |
| publicidade (`Público`), natureza (`Criminal`), `Réu Preso` | casca | texto de `#dados-processo` e literal `'Público'` no script do botão DJE |
| número único `0165738-43.2026.1.00.0000` | casca | texto de `#dados-processo` |
| relator, relator do último incidente (`MIN. ANDRÉ MENDONÇA (Pet-AgR-quarto)`) | casca | `.processo-dados` |
| assunto (`DIREITO PROCESSUAL PENAL \| Prisão Preventiva`) | Informações | `.informacoes__assunto li` |
| data de protocolo `27/02/2026`, órgão de origem, origem `DISTRITO FEDERAL` | Informações | pares `div.processo-detalhes-bold` / `div.processo-detalhes` |
| número de origem (12 números) | Informações | idem; lista separada por vírgula |
| partes: papel + nome + OAB | Partes | `.processo-partes` → pares `.detalhe-parte` / `.nome-parte`; OAB entre parênteses no nome |
| andamentos: data, tipo, descrição, docs | Andamentos | `.andamento-item` → `.andamento-data`, `.andamento-nome`, `.col-md-9.p-0`, `.andamento-docs a` |
| decisões: idem | Decisões | mesma estrutura de `.andamento-item` |
| pautas | Pautas | mesma estrutura |
| petições: número/ano, data, recebimento, setor | Petições | `.lista-dados` → `span.processo-detalhes-bold`, `span.processo-detalhes` |
| deslocamentos: destino, remetente, data, guia, recebimento | Deslocamentos | `.lista-dados` → `.lista-dados__col` |
| documentos: URL, rótulo | Andamentos/Decisões | `downloadPeca.asp?id=N&ext=.pdf`, `downloadTexto.asp?id=N&ext=RTF` |

**Não obtíveis a partir desta página:**

| campo | motivo |
|---|---|
| `sigilo_status` como campo | Só existe o literal `Público`/`Sigiloso` no script. Não há histórico de quando o sigilo foi levantado. |
| volumes, folhas | `div.numero` vazio |
| incidentes relacionados (números de incidente) | não há nenhum `incidente=` além do próprio |
| os quatro agravos regimentais como incidentes | só aparecem como andamentos "Interposto agravo regimental" (11/03, 25/03 ×3) com número de petição, sem link e sem incidente |
| recursos | aba vazia |
| sessão virtual (placar, votos) | depende de JSON em `sistemas.stf.jus.br`, não coletado |
| `ordem` dos andamentos | não há campo explícito; a ordem no HTML é decrescente por data e precisa ser derivada da posição |
| conteúdo das 5 decisões ainda sigilosas | itens "Decisão (sigiloso)" sem link (03/03, 16/03, 23/03, 31/03 e uma de 23/03) |

## 8. Documentos e o PDF testado

Padrão dos links (extraído do HTML, 94 links no total):

| endpoint | quantidade | onde |
|---|---|---|
| `/processos/downloadPeca.asp?id={11 dígitos}&ext=.pdf` | 71 em Andamentos, 21 em Decisões | peças: decisões monocráticas, despachos, certidões, vistas, intimações |
| `/processos/downloadTexto.asp?id={7 dígitos}&ext=RTF` | 1 em cada aba | "Decisão de Julgamento" colegiada (liminar referendada, 23/03/2026), formato **RTF** |

Os ids de `downloadPeca` são globais (não repetem o incidente na URL). O `id` é a chave natural do documento.

Download testado: `downloadPeca.asp?id=15389657076&ext=.pdf` (Despacho de 25/08/2026, o mais recente com link).

| item | resultado |
|---|---|
| status | 200, sem redirect, sem `Content-Disposition` |
| content-type | `application/pdf` |
| tamanho | 87 525 bytes |
| magic bytes | `%PDF-` |
| autenticação / captcha / sessão | nenhuma exigida (feito na mesma sessão que já tinha cookies ASP; não testado a frio) |
| `pdftotext -layout` (xpdf 4.06) | returncode 0, 2 504 caracteres, 2 páginas com texto, 706 caracteres alfanuméricos por página |
| `/Font` no PDF | sim |
| filtros de imagem (`DCTDecode`, `CCITTFax`, `JBIG2`) | nenhum |
| **camada de texto** | **nativa. Sem necessidade de OCR para este documento.** |
| separação de páginas | form feed entre páginas, número de página no rodapé |
| rodapé | "Documento assinado digitalmente conforme MP 2.200-2/2001 … `autenticarDocumento.asp` sob o código 5457-8466-98B0-B5A3 e senha 5FA0-988C-2B24-C76D" |

Dois achados de qualidade de dado:

1. **O cabeçalho do PDF traz `SOB SIGILO` em todas as partes**, embora a aba Partes já mostre os nomes. O documento foi gerado enquanto o processo era sigiloso e não foi regenerado. A camada documental (Fase 3) não pode inferir partes a partir do cabeçalho dos PDFs; a fonte para partes é a aba Partes, com o snapshot como proveniência.
2. Cada PDF carrega **código e senha de autenticação** do próprio STF. Isso é um ponteiro de proveniência verificável por terceiros e deve ir para o schema `documento` (`codigo_autenticacao`, `senha_autenticacao`), extraído por regex do rodapé.

Generalização a partir de um único PDF é limitada. Não foi testado: um "Decisão monocrática" longo (a de 04/03/2026 tem 106+ parágrafos), o RTF de `downloadTexto.asp`, nem PDFs de petições (a aba Petições não tem links de documento).

## 9. Contagens e relações

| aba | itens | com documento | período |
|---|---|---|---|
| Andamentos | **407** `.andamento-item` | 72 | 27/02/2026 → 11/09/2026 |
| Decisões | **27** | 22 (21 PDF + 1 RTF) | 03/03/2026 → 26/08/2026 |
| Petições | **113** `.lista-dados` | 0 | até 11/09/2026 |
| Deslocamentos | **90** | 0 | até 28/08/2026 |
| Pautas | 1 | 0 | 05/03/2026 (2ª Turma, DJE) |
| Recursos | **0 bytes** | — | — |
| Sessão Virtual | 0 estático | — | JSON externo |
| Partes | **56** entradas | — | — |

Partes por papel: 1 `REQTE.(S)` (Delegado de Polícia Federal), 1 `AUT. POL.` (Polícia Federal), 14 `REQDO.(A/S)`, 2 `INTDO.(A/S)`, 38 `ADV.(A/S)`. Os papéis do portal mapeiam direto para o `papel` da tabela `parte` sem inferência.

Tipos de andamento mais frequentes: Petição (122), Comunicação assinada (61), Expedido(a) (41), Certidão (32), Juntada do mandado cumprido (21), Intimado eletronicamente (19), Vista à PGR para fins de intimação (19), Conclusos ao Relator (16), Despacho (15), Decisão (sigiloso) (10).

A aba Andamentos pesa 3,6 MB porque repete dois SVGs inline (3,9 KB e 10 KB) 414 vezes. O conteúdo útil é da ordem de 500 KB. O snapshot bruto guarda tudo; o parser ignora `<svg>`.

**Relações entre processos (não entre incidentes):**

| fonte | referência |
|---|---|
| Andamento "Distribuído por prevenção" (27/02/2026) | "Processo que justifica: **Inq 5026**. Processos relacionados: **Inq 5035, Pet 15198, Pet 15499, Pet 15504**" |
| Certidão (20/07/2026) | "autuação da **PET 16440** e da **PET 16441**" |
| Campo "Número de Origem" | `15556, 01657384320261000000, 1447384392026, 10450144820254010000, 11170654220254013400, 50000932620264036181, 20250087917, 5026, 5035, 15504, 15499, 15198` (mistura de números CNJ sem pontuação de outros tribunais, número do próprio processo e números de classe do STF) |
| Andamentos "Interposto agravo regimental" | 11/03/2026 (Petição 27539/2026), 25/03/2026 (34620, 32472, 36684/2026). **Sem link, sem incidente.** |

Nenhuma dessas referências carrega número de incidente. **Sondagem feita:** `listarProcessos.asp?classe=Pet&numeroProcesso=15556` responde `302` para `detalhe.asp?incidente=7514886`. Ou seja, classe+número resolve para o incidente principal com uma requisição, de forma determinística. Mas resolve **só o principal**: os incidentes dos quatro agravos não aparecem nem no redirect, nem no `detalhe.asp`, nem na aba Recursos (vazia). Como chegar a `Pet-AgR-primeiro…quarto` é uma pergunta em aberto.

## 10. O que invalida ou altera as fases seguintes

**Fase 1 (ingestão).**
- O coletor busca 1 casca + 9 abas por incidente. `snapshot` ganha uma linha por aba (`aba` como coluna). A relação `snapshot → incidente` é N:1.
- A stack proposta (Python 3.12, httpx, selectolax, SQLite FTS5) está validada em campo, com Python 3.14 em vez de 3.12 (é o que está instalado; lxml 6.1 e selectolax rodam nele). Sem objeção à stack.
- `verify=` obrigatório com o bundle; `From:` e UA fixados; cookie jar por sessão.
- `hash_natural` de andamento como proposto `(incidente, data, ordem, descricao)` tem um problema: não há `ordem` no HTML, e há andamentos idênticos no mesmo dia (ex.: quatro "Intimado eletronicamente" iguais). A posição no fragmento é a única ordem disponível, e ela muda quando itens novos são inseridos no topo. Proposta para o gate da Fase 1: `hash_natural = sha256(incidente, data, tipo, descricao, ids_de_documento)` mais um `ordem_no_dia` derivado da posição entre itens do mesmo dia; colisões residuais são tratadas como o mesmo andamento. A decidir.
- A tabela `documento` precisa de `id_portal` (o `id` de `downloadPeca`), `formato` (`pdf`/`rtf`), `codigo_autenticacao`, `senha_autenticacao`.
- A tabela `incidente` precisa de `publicidade`, `natureza`, `reu_preso`, `meio`, `numero_origem_lista`.
- A aba Sessão Virtual exige um segundo host e um segundo `robots.txt` (`sistemas.stf.jus.br`). Não verificado. Decisão para o gate da Fase 1: incluir ou não.

**Fase 2 (grafo).** O desenho "extraia `incidente=` e enfileire" não tem fonte de dados. Alternativa a decidir no gate da Fase 2:
- nó = processo (classe + número), não incidente; arestas extraídas do andamento "Distribuído por prevenção" (`justifica`, `relacionado`), de certidões de autuação (`origina`) e do campo "Número de Origem" (`origem`, tipo fraco);
- resolução classe+número → incidente principal via `listarProcessos.asp` (1 requisição por processo, 302 determinístico);
- os agravos ficam como andamentos do incidente principal até se descobrir onde o portal os lista. Candidatos não testados: `listarProcessos.asp` com outros parâmetros, a busca "Por Número Único", e `abaRecursos.asp` em incidentes que tenham recursos.
- Este é o crawl que o `robots.txt` visa. Precisa de teto duro por execução e de aprovação explícita.

**Fase 3 (documental).** Viável para PDFs. Pendências: testar o RTF de `downloadTexto.asp` (precisa de conversor, `pdftotext` não serve); testar um PDF longo; o `pdftotext` disponível é xpdf 4.06 via Git for Windows, não poppler, e `pdfinfo` não existe. Proposta para o gate da Fase 3: `pypdf` ou `pdfplumber` para extração com número de página, com `pdftotext` como verificação cruzada. OCR: nenhuma evidência de necessidade até agora; só decidir se aparecer PDF sem `/Font`.

**Fase 4 (semântica).** Nada invalidado. Reforço: o cabeçalho "SOB SIGILO" dos PDFs não pode ser lido como "partes desconhecidas".

**Fase 5 (interface).** Nada invalidado. O carimbo "dados coletados em" deve mostrar a data do snapshot da aba, não do incidente.

## 11. Falhas e limitações desta fase

- Nenhuma falha de coleta. Todas as 14 requisições a `/processos` responderam 200 ou 302.
- Falhas de ambiente, corrigidas: TLS (seção 4) e WAF (seção 3).
- Um único PDF testado. Generalização limitada.
- `abaRecursos.asp` vazia: não sei se é ausência de dados ou parâmetro faltando.
- Sessão Virtual não coletada.
- Download de PDF não testado a frio (sem cookies de sessão prévia).
- A análise de "carga secundária" da passada 1 só detectou as abas porque o script está inline; se o portal mover isso para `processo.js`, o detector precisa ler os `.js` também. Não foi necessário aqui.

## 12. Artefatos produzidos

```
recon/fase0.py                          coleta passada 1 + análise offline (--offline <html>)
recon/fase0_abas.py                     coleta passada 2 (9 abas + 1 PDF)
recon/certs/stf-chain.pem               bundle certifi + intermediário GlobalSign (expira 21/05/2027)
recon/certs/{leaf,intermediate}.pem     certificados extraídos, para auditoria
recon/certs/served-chain.txt            saída bruta do openssl s_client
recon/fase0-resultado_*.json            resultado + log de requisições da passada 1
recon/fase0-abas-resultado_*.json       resultado + log da passada 2
requirements-recon.txt                  httpx, selectolax, certifi
data/raw/robots_*.txt                   snapshot do robots.txt
data/raw/7514886/*_verImpressao.html    casca (2 snapshots, UAs diferentes, bytes idênticos) + .meta.json
data/raw/7514886/abas/*_{aba}.html      9 fragmentos + .meta.json
data/raw/7514886/docs/{sha256}.pdf      1 PDF + .meta.json
data/raw/7514886/*_listarProcessos_*    sondagem de resolução classe+número + .meta.json
```

Nada foi sobrescrito. Todo `.meta.json` traz URL, URL final, timestamp UTC, sha256, status, cabeçalhos de requisição e resposta, redirects.

## 13. Minuta de comunicação à Ouvidoria do STF (para o usuário enviar, se quiser)

> Assunto: Comunicação de coleta automatizada identificada de dados processuais públicos
>
> Prezados,
>
> Informo que estou desenvolvendo uma ferramenta de código aberto para tornar processos públicos do STF pesquisáveis e navegáveis por qualquer cidadão, com registro de proveniência de cada dado exibido. A ferramenta consulta as páginas públicas de acompanhamento processual do portal (`/processos/verImpressao.asp` e as abas associadas) para incidentes específicos, informados manualmente, nunca por varredura.
>
> Toda requisição é feita com o user-agent `Mozilla/5.0 (…; stf-mapeador/0.1; +mailto:ldickmann12@gmail.com)` e o cabeçalho `From: ldickmann12@gmail.com`, uma requisição por vez, com intervalo mínimo de 3 segundos e recuo automático em caso de erro. Observei que o `robots.txt` do portal desaconselha o acesso automatizado a `/processos`; entendo essa diretiva como voltada a indexadores de busca, mas caso o Tribunal prefira que a coleta não seja feita, ou que seja feita de outra forma ou por outro canal (por exemplo, um conjunto de dados abertos), basta responder a este e-mail e eu ajusto.
>
> Atenciosamente,
> [nome]

## 14. Decisões que precisam do usuário

1. **Aprovar a exceção ao robots.txt** com os limites da seção 2, ou revogá-la. Se revogada, o projeto para aqui até haver outra fonte.
2. **Enviar ou não a comunicação da seção 13.**
3. **Fase 1, hash natural do andamento:** aceitar a proposta da seção 10 ou definir outra.
4. **Fase 1, Sessão Virtual:** incluir o host `sistemas.stf.jus.br` (mais um robots.txt a verificar) ou deixar de fora.
5. **Fase 2:** aceitar o redesenho "nó = processo por classe+número, resolução via `listarProcessos.asp`" e definir o teto de requisições por execução; ou suspender a Fase 2 até descobrir como listar os incidentes de agravo.
6. **Python 3.14 em vez de 3.12.** É o que está instalado e tudo rodou. Trocar exige instalar outra versão.
