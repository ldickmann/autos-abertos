# FASE 5 — Relatório: interface web

Construída em 14/09/2026. Next.js 16 (App Router), TypeScript, Tailwind 4, export estático: 479 páginas HTML em `web/out/`.

## 1. O que existe

| rota | conteúdo |
|---|---|
| `/` | Pet 15556: cabeçalho, contagens, carimbo "dados coletados em", link ao portal; tabela dos 11 processos relacionados com publicidade, relator, assunto e data de coleta; legenda dos três tipos epistêmicos |
| `/processo/[incidente]` | cabeçalho completo, relações declaradas (com link ao andamento-fonte), partes com **status processual literal** e OAB, sessões virtuais com placar por ministro, **linha do tempo filtrável** (tipo, período, só decisões, só com documento), petições e deslocamentos; cada andamento com explicação oficial do portal, documentos e carimbo de coleta |
| `/documento/[id]` | título, andamentos de origem, URL no portal, **código de autenticação do STF**, sha256, data do download; texto por página com âncoras `#p-N`; asserções por página com badge epistêmico e trecho-fonte |
| `/busca` | busca no cliente (MiniSearch) sobre 1 879 andamentos e 1 417 chunks de documentos, sem acentos, filtro por tipo e processo; resultado leva ao andamento ou à página |
| `/assercoes` | lista filtrável por tipo epistêmico, processo e data, com badge e legenda; hoje mostra o aviso de que a Fase 4 não rodou |
| `/grafo` | Cytoscape.js: processos (semente com borda vermelha, sigilosos em cinza), entidades em ≥N processos, advogados opcionais; **tabela equivalente das arestas** com proveniência, para teclado e leitor de tela |
| `/entidades`, `/entidade/[id]` | 234 entidades; status processual por processo, representação (advogado ↔ parte), asserções que a citam; aviso sobre homônimos |
| `/sobre` | método: proveniência, tipos, pessoas, política de coleta, limitações |

Dados: `python -m stf exportar` gera `web/public/data/` (6,1 MB de JSON: `meta`, `processos`, `processo/<inc>`, `documento/<id>`, `entidades`, `grafo`, `cruzamentos`, `busca`, `assercoes`). Cada item leva `snapshot = {id, fetched_at, sha256, url}`.

## 2. Requisitos do prompt, um a um

| requisito | onde |
|---|---|
| busca full-text sobre andamentos e texto de documentos | `/busca` |
| linha do tempo filtrável por incidente, data e tipo epistêmico | `/processo/[incidente]` (incidente, data, tipo de andamento); `/assercoes` (tipo epistêmico, processo, data) |
| grafo de incidentes e de entidades, biblioteca JS, sem banco de grafos | `/grafo`, Cytoscape.js sobre `grafo.json` |
| cada item linka para o documento-fonte e a página | andamentos → `/documento/[id]`; asserções → `/documento/[id]#p-N` com trecho literal |
| badge de tipo epistêmico com legenda | `BadgeEpistemico` + `LegendaEpistemica` em `/`, `/assercoes`, `/sobre` |
| carimbo "dados coletados em" em cada página | `Carimbo` no cabeçalho de cada processo, em cada andamento, em cada documento; rodapé com a data de geração da base |
| status processual sempre visível junto ao nome | `StatusProcessual` ao lado de cada parte e em cada menção de entidade; título mostra o literal do portal |
| estático onde der | tudo estático (`output: "export"`); a busca roda no navegador |

## 3. Acessibilidade (WCAG 2.1 AA)

- HTML semântico: `header`, `nav aria-label`, `main`, `section aria-labelledby`, tabelas com `th scope`, `dl` para pares rótulo/valor, `time datetime`.
- Link "Pular para o conteúdo"; foco visível em todo elemento interativo (`outline 2px` azul-escuro).
- Contraste: texto `neutral-900` sobre `neutral-50`/branco; badges com texto escuro sobre fundo claro e borda; nenhum significado só por cor (badges têm texto; decisão/sigiloso têm rótulo).
- Grafo: `role="img"` com `aria-label`, e tabela equivalente das arestas. Filtros com `label` e `role="status"` para a contagem.
- Sem `autoplay`, sem movimento (layout do grafo sem animação).
- Não verificado com ferramenta automatizada (axe/Lighthouse) nesta sessão; é o próximo passo ao publicar.

## 4. Problemas encontrados e tratados

- **Bug do Next 16.3 no Windows**: o export estático grava os payloads de prefetch de segmento como diretórios (`__next.busca/__PAGE__.txt`) porque troca só `/` por `.` e o caminho vem com `\`. O cliente pede o nome plano e recebe 404. `web/scripts/flatten-segments.mjs` roda após o build e renomeia (477 arquivos). Navegação funciona com ou sem a correção; a correção só elimina o ruído.
- Componentes de cliente não podem importar `node:fs`: tipos e formatadores foram separados em `lib/tipos.ts`; `lib/data.ts` é `server-only`.
- `@tailwindcss/typography` não está instalado; a página de método usa utilitários simples.

## 5. Como publicar

```bash
python -m stf exportar          # regenera web/public/data
cd web && npm ci && npm run build   # gera web/out (51 MB, 479 páginas)
```
`web/out` é servível por qualquer host estático (GitHub Pages, Netlify, S3). A coleta não roda em CI porque o portal do STF bloqueia IPs de datacenter; o fluxo é coletar localmente, `exportar`, commitar `web/public/data` e deixar o host construir. Verificado localmente com `python -m http.server` sobre `web/out`: início, busca, processo, documento, entidades e grafo renderizam; a busca por "prisao preventiva" retorna 100 resultados com página e trecho.
