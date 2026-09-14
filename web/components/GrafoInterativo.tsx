"use client";

import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ArestaGrafo, Grafo, NoGrafo } from "@/lib/tipos";

/*
  Leitura do grafo:
  - Processos são retângulos (o processo principal tem borda dupla). Entidades são círculos; o tamanho é o número de ligações.
  - A cor de uma entidade é o seu grupo curado (Polícia Federal, Ministério Público, STF…) ou, sem grupo, a sua natureza (pessoa, organização, advogado).
  - Cada tipo de ligação tem um traço próprio (legenda à esquerda). Clicar num nó abre a ficha à direita, com cada ligação e a sua fonte.
  - "Caminho": com um nó em foco, escolha um segundo nó para traçar o caminho mais curto entre os dois.
*/

type Visao = "processos" | "processos+partes" | "tudo";
type Disposicao = "forca" | "camadas";

const ROTULO_ARESTA: Record<string, string> = {
  relacao: "relação declarada em andamento",
  parte_em: "é parte em",
  representa: "advogado de",
  numero_origem: "número de origem coincide (fraco)",
  cita_processo: "documentos citam",
  citado_em: "citada em asserções de",
  afirma_em: "alega ou fundamenta em",
  co_citacao: "citadas na mesma asserção",
  relator_de: "relator de",
  votou_em: "votou em",
};

const CORES_GRUPO: Record<string, string> = {
  "Polícia Federal": "#d98c5f",
  "Ministério Público": "#c97ba0",
  "Supremo Tribunal Federal": "#93b6e6",
  "Outros tribunais e juízos": "#7fb3b0",
  "Reguladores e sistema financeiro": "#b8a96a",
  "Poder Legislativo e Executivo": "#9c8fd9",
  "Ordem dos Advogados": "#8fa1b3",
};
const CORES_NATUREZA: Record<string, string> = { pessoa: "#e9e4d8", parte: "#e9e4d8", organizacao: "#c9b98a", advogado: "#8fa1b3", ministro: "#93b6e6", orgao_publico: "#7fb3b0", desconhecido: "#7c786d" };

function corDaEntidade(n: NoGrafo): string {
  const grupo = n.dados.grupo as string | null;
  if (grupo && CORES_GRUPO[grupo]) return CORES_GRUPO[grupo];
  return CORES_NATUREZA[(n.dados.subtipo as string) ?? "desconhecido"] ?? "#7c786d";
}

function lerTokens() {
  const cs = getComputedStyle(document.documentElement);
  const v = (nome: string, padrao: string) => cs.getPropertyValue(nome).trim() || padrao;
  return {
    fundo: v("--fundo", "#15181d"), folha: v("--folha", "#1d2127"), fio: v("--fio", "#343a44"), fioForte: v("--fio-forte", "#4a5261"),
    tinta: v("--tinta", "#e9e4d8"), tinta2: v("--tinta-2", "#a39f93"), fato: v("--fato", "#8fcba4"), alegacao: v("--alegacao", "#e4b35f"),
    fundamento: v("--fundamento", "#93b6e6"), marca: v("--marca", "#f4d27a"),
  };
}

function hrefDoNo(n: NoGrafo): string | null {
  if (n.tipo === "processo") return n.dados.incidente ? `/processo/${n.dados.incidente}` : null;
  return `/entidade/${n.id.split(":")[1]}`;
}

function descreverFonte(e: ArestaGrafo): { texto: string; links: { href: string; rotulo: string }[] } {
  const f = (e.dados.fonte ?? {}) as Record<string, unknown>;
  const links: { href: string; rotulo: string }[] = [];
  if (Array.isArray(f.assercoes)) {
    for (const a of (f.assercoes as { documento_id: number; pagina: number }[]).slice(0, 6)) links.push({ href: `/documento/${a.documento_id}#p-${a.pagina}`, rotulo: `doc ${a.documento_id} p. ${a.pagina}` });
    return { texto: `${e.dados.n ?? (f.assercoes as unknown[]).length} asserção(ões)`, links };
  }
  if (Array.isArray(f.documentos)) {
    for (const d of (f.documentos as { documento_id: number; pagina: number }[]).slice(0, 6)) links.push({ href: `/documento/${d.documento_id}#p-${d.pagina}`, rotulo: `doc ${d.documento_id} p. ${d.pagina}` });
    return { texto: `${e.dados.n_docs} documento(s), ${e.dados.n_ocorrencias} ocorrência(s)`, links };
  }
  if (f.andamento) return { texto: `andamento ${String(f.andamento)}, snapshot ${String(f.snapshot)}`, links };
  if (f.parte_id) return { texto: `cadastro de partes, snapshot ${String(f.snapshot)}`, links };
  if (f.campo) return { texto: `campo "${String(f.campo)}", snapshot ${String(f.snapshot)}`, links };
  return { texto: JSON.stringify(f), links };
}

export function GrafoInterativo({ grafo, semente }: { grafo: Grafo; semente: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [visao, setVisao] = useState<Visao>("processos+partes");
  const [minProcessos, setMinProcessos] = useState(2);
  const [disposicao, setDisposicao] = useState<Disposicao>("forca");
  const [camadas, setCamadas] = useState({ citacoes: true, coocorrencia: false, externos: false, ministros: true, assercoes: true });
  const [foco, setFoco] = useState<string | null>(null);
  const [destino, setDestino] = useState<string | null>(null);
  const [caminho, setCaminho] = useState<string[] | null>(null);
  const [busca, setBusca] = useState("");
  const [modoCaminho, setModoCaminho] = useState(false);
  const [tema, setTema] = useState(0);
  const focoRef = useRef<string | null>(null);
  const modoCaminhoRef = useRef(false);
  useEffect(() => { focoRef.current = foco; }, [foco]);
  useEffect(() => { modoCaminhoRef.current = modoCaminho; }, [modoCaminho]);

  useEffect(() => {
    const obs = new MutationObserver(() => setTema((t) => t + 1));
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-tema"] });
    return () => obs.disconnect();
  }, []);

  const porId = useMemo(() => new Map(grafo.nodes.map((n) => [n.id, n])), [grafo]);

  const visivel = useMemo(() => {
    const procsPorEntidade = new Map<string, Set<string>>();
    for (const e of grafo.edges) {
      if (e.tipo === "parte_em" || e.tipo === "citado_em" || e.tipo === "afirma_em") {
        procsPorEntidade.set(e.origem, new Set([...(procsPorEntidade.get(e.origem) ?? []), e.destino]));
      }
    }
    const tiposAtivos = new Set(["relacao", "parte_em", "numero_origem", "representa"]);
    if (camadas.citacoes) tiposAtivos.add("cita_processo");
    if (camadas.coocorrencia) tiposAtivos.add("co_citacao");
    if (camadas.ministros) { tiposAtivos.add("relator_de"); tiposAtivos.add("votou_em"); }
    if (camadas.assercoes) { tiposAtivos.add("citado_em"); tiposAtivos.add("afirma_em"); }
    const nos = grafo.nodes.filter((n) => {
      if (n.tipo === "processo") return camadas.externos || !n.dados.externo;
      if (visao === "processos") return false;
      const sub = n.dados.subtipo as string;
      if (sub === "ministro") return camadas.ministros;
      if (sub === "advogado" && visao !== "tudo") return false;
      if (n.dados.origem === "documento" && !camadas.assercoes) return false;
      return (procsPorEntidade.get(n.id)?.size ?? 0) >= minProcessos;
    });
    const ids = new Set(nos.map((n) => n.id));
    const arestas = grafo.edges.filter((e) => ids.has(e.origem) && ids.has(e.destino) && tiposAtivos.has(e.tipo) && (visao === "tudo" || e.tipo !== "representa"));
    // entidades que ficaram sem aresta depois dos filtros saem
    const grau = new Map<string, number>();
    for (const e of arestas) { grau.set(e.origem, (grau.get(e.origem) ?? 0) + 1); grau.set(e.destino, (grau.get(e.destino) ?? 0) + 1); }
    const nosFinais = nos.filter((n) => n.tipo === "processo" ? (!n.dados.externo || (grau.get(n.id) ?? 0) > 0) : (grau.get(n.id) ?? 0) > 0);
    const idsFinais = new Set(nosFinais.map((n) => n.id));
    return { nos: nosFinais, arestas: arestas.filter((e) => idsFinais.has(e.origem) && idsFinais.has(e.destino)), grau };
  }, [grafo, visao, minProcessos, camadas]);

  const contagens = useMemo(() => {
    const c: Record<string, number> = {};
    for (const e of visivel.arestas) c[e.tipo] = (c[e.tipo] ?? 0) + 1;
    return c;
  }, [visivel]);

  const aplicarFoco = useCallback((cy: Core, id: string | null, cam: string[] | null) => {
    cy.batch(() => {
      cy.elements().removeClass("apagado realce caminho");
      if (cam && cam.length > 1) {
        cy.elements().addClass("apagado");
        for (let i = 0; i < cam.length; i++) {
          cy.getElementById(cam[i]).removeClass("apagado").addClass("caminho");
          if (i > 0) cy.edges().filter((e) => (e.source().id() === cam[i - 1] && e.target().id() === cam[i]) || (e.source().id() === cam[i] && e.target().id() === cam[i - 1])).removeClass("apagado").addClass("caminho");
        }
        return;
      }
      if (!id) return;
      const no = cy.getElementById(id);
      if (no.empty()) return;
      const viz = no.closedNeighborhood();
      cy.elements().not(viz).addClass("apagado");
      viz.edges().addClass("realce");
    });
  }, []);

  useEffect(() => {
    if (!ref.current) return;
    const t = lerTokens();
    const elementos: ElementDefinition[] = [
      ...visivel.nos.map((n) => ({
        data: {
          id: n.id, label: n.rotulo, tipo: n.tipo, sub: (n.dados.subtipo as string) ?? "", externo: !!n.dados.externo,
          semente: n.tipo === "processo" && n.dados.incidente === semente, pub: (n.dados.publicidade as string) ?? "",
          cor: n.tipo === "processo" ? (n.dados.externo ? t.fio : t.tinta) : corDaEntidade(n),
          // width "label" faz o Cytoscape tratar o nó como oculto (pfValue 0) e não desenha as arestas; largura explícita
          tam: n.tipo === "processo" ? 18 + n.rotulo.length * 8.5 : Math.min(44, 14 + 4 * Math.sqrt(visivel.grau.get(n.id) ?? 1)),
          pesoRotulo: (visivel.grau.get(n.id) ?? 0),
        },
      })),
      ...visivel.arestas.map((e, i) => ({
        data: {
          id: `e${i}`, source: e.origem, target: e.destino, tipo: e.tipo, sub: (e.dados.subtipo as string) ?? "",
          peso: Math.min(4.5, 1.5 + Math.log2(Number(e.dados.n ?? e.dados.n_docs ?? 1))),
        },
      })),
    ];
    const cy = cytoscape({
      container: ref.current,
      elements: elementos,
      style: construirEstilo(t),
      layout: { name: "preset" },
      wheelSensitivity: 0.2,
      minZoom: 0.15, maxZoom: 4,
    });
    const raiz = cy.getElementById(visivel.nos.find((n) => n.tipo === "processo" && n.dados.incidente === semente)?.id ?? "");
    const layout = disposicao === "camadas" && !raiz.empty()
      ? cy.layout({ name: "breadthfirst", roots: [raiz.id()], circle: true, spacingFactor: 1.15, animate: false, padding: 24 })
      : cy.layout({ name: "cose", animate: false, nodeRepulsion: () => 200000, nodeOverlap: 30, idealEdgeLength: (e: cytoscape.EdgeSingular) => (e.data("tipo") === "relacao" ? 170 : 100), edgeElasticity: () => 80, gravity: 0.5, numIter: 1600, coolingFactor: 0.96, padding: 24, randomize: true, componentSpacing: 100 } as cytoscape.LayoutOptions);
    layout.run();
    cyRef.current = cy;
    cy.on("tap", "node", (ev) => {
      const id = ev.target.id();
      const atual = focoRef.current;
      if (modoCaminhoRef.current && atual && atual !== id) {
        const r = cy.elements().aStar({ root: cy.getElementById(atual), goal: cy.getElementById(id), weight: () => 1, directed: false });
        const ids = r.found ? r.path.filter((el) => el.isNode()).map((el) => el.id()) : null;
        setCaminho(ids); setDestino(id); setModoCaminho(false);
        aplicarFoco(cy, atual, ids);
        return;
      }
      setFoco(id); setCaminho(null); setDestino(null);
      aplicarFoco(cy, id, null);
    });
    cy.on("tap", (ev) => { if (ev.target === cy) { setFoco(null); setCaminho(null); setDestino(null); aplicarFoco(cy, null, null); } });
    return () => { cy.destroy(); cyRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visivel, disposicao, semente]);

  // troca de tema: só as cores mudam, as posições ficam
  useEffect(() => {
    const cy = cyRef.current; if (!cy || tema === 0) return;
    cy.style().fromJson(construirEstilo(lerTokens())).update();
    cy.batch(() => { cy.nodes().forEach((n) => { const t = lerTokens(); if (n.data("tipo") === "processo") n.data("cor", n.data("externo") ? t.fio : t.tinta); }); });
  }, [tema]);

  const centrarEm = (id: string) => {
    const cy = cyRef.current; if (!cy) return;
    const no = cy.getElementById(id); if (no.empty()) return;
    cy.animate({ center: { eles: no }, zoom: Math.max(cy.zoom(), 1.2) }, { duration: 350 });
    no.select(); setFoco(id); setCaminho(null); setDestino(null); setModoCaminho(false); aplicarFoco(cy, id, null);
  };

  const sugestoes = useMemo(() => {
    const q = busca.trim().toLowerCase();
    if (q.length < 2) return [];
    return visivel.nos.filter((n) => n.rotulo.toLowerCase().includes(q)).slice(0, 8);
  }, [busca, visivel]);

  const focoNo = foco ? porId.get(foco) : undefined;
  const ligacoes = useMemo(() => {
    if (!foco) return [];
    return visivel.arestas.filter((e) => e.origem === foco || e.destino === foco).map((e) => ({ e, outro: e.origem === foco ? e.destino : e.origem, saida: e.origem === foco }));
  }, [foco, visivel]);
  const ligacoesPorTipo = useMemo(() => {
    const m = new Map<string, typeof ligacoes>();
    for (const l of ligacoes) m.set(l.e.tipo, [...(m.get(l.e.tipo) ?? []), l]);
    return [...m.entries()];
  }, [ligacoes]);

  return (
    <div className="grid gap-3 lg:grid-cols-[230px_minmax(0,1fr)_300px]">
      <aside className="space-y-3 text-sm">
        <details className="folha border border-neutral-300 bg-white p-3" open>
          <summary className="cursor-pointer font-semibold">Filtros</summary>
          <form className="mt-2 space-y-3" onSubmit={(ev) => { ev.preventDefault(); if (sugestoes[0]) centrarEm(sugestoes[0].id); }}>
            <label className="block">
              <span className="font-medium">Encontrar</span>
              <input list="nos-grafo" className="mt-1 w-full rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={busca} onChange={(ev) => setBusca(ev.target.value)} placeholder="nome, processo…" />
              <datalist id="nos-grafo">{sugestoes.map((n) => <option key={n.id} value={n.rotulo} />)}</datalist>
              {sugestoes.length > 0 && busca && (
                <ul className="mt-1 max-h-40 overflow-auto rounded border border-neutral-300 bg-white">
                  {sugestoes.map((n) => (
                    <li key={n.id}><button type="button" className="w-full px-2 py-1 text-left hover:bg-neutral-100" onClick={() => { centrarEm(n.id); setBusca(""); }}>{n.rotulo} <span className="text-xs text-neutral-600">{n.tipo === "processo" ? "processo" : String(n.dados.subtipo)}</span></button></li>
                  ))}
                </ul>
              )}
            </label>
            <label className="block"><span className="font-medium">Mostrar</span>
              <select className="mt-1 w-full rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={visao} onChange={(ev) => setVisao(ev.target.value as Visao)}>
                <option value="processos">só processos</option><option value="processos+partes">processos e pessoas/órgãos</option><option value="tudo">tudo, com advogados</option>
              </select></label>
            <label className="block"><span className="font-medium">Entidades ligadas a pelo menos</span>
              <select className="mt-1 w-full rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={minProcessos} onChange={(ev) => setMinProcessos(Number(ev.target.value))}>
                <option value={1}>1 processo</option><option value={2}>2 processos</option><option value={3}>3 processos</option></select></label>
            <fieldset className="space-y-1">
              <legend className="font-medium">Camadas</legend>
              {([["assercoes", "citações em asserções"], ["citacoes", "citações entre processos"], ["ministros", "ministros (relator, votos)"], ["coocorrencia", "coocorrência na mesma asserção"], ["externos", "processos citados não coletados"]] as const).map(([k, r]) => (
                <label key={k} className="flex items-center gap-2"><input type="checkbox" checked={camadas[k]} onChange={(ev) => setCamadas({ ...camadas, [k]: ev.target.checked })} /> {r}</label>
              ))}
            </fieldset>
            <label className="block"><span className="font-medium">Disposição</span>
              <select className="mt-1 w-full rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={disposicao} onChange={(ev) => setDisposicao(ev.target.value as Disposicao)}>
                <option value="forca">por força das ligações</option><option value="camadas">em camadas, a partir do processo principal</option></select></label>
            <div className="flex gap-2">
              <button type="button" className="rounded border border-neutral-400 px-2 py-1 hover:bg-neutral-100" onClick={() => cyRef.current?.fit(undefined, 24)}>Ajustar à tela</button>
              <button type="button" className="rounded border border-neutral-400 px-2 py-1 hover:bg-neutral-100" onClick={() => { setFoco(null); setCaminho(null); setDestino(null); setModoCaminho(false); if (cyRef.current) { cyRef.current.elements().unselect(); aplicarFoco(cyRef.current, null, null); } }}>Limpar</button>
            </div>
          </form>
        </details>
        <details className="folha border border-neutral-300 bg-white p-3" open>
          <summary className="cursor-pointer font-semibold">Legenda</summary>
          <ul className="mt-2 space-y-1 text-xs">
            <li><span className="mr-1 inline-block rounded-sm bg-neutral-900 px-1 text-[10px] font-semibold text-neutral-50">Pet 15556</span> processo (borda dupla: principal)</li>
            <li><span className="mr-1 inline-block rounded-sm border border-dashed border-neutral-400 px-1 text-[10px]">HC 79812</span> processo citado, não coletado</li>
            {Object.entries(CORES_GRUPO).map(([g, c]) => <li key={g}><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full align-middle" style={{ background: c }} /> {g}</li>)}
            <li><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full align-middle" style={{ background: CORES_NATUREZA.pessoa }} /> pessoa ou parte sem grupo</li>
            <li><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full align-middle" style={{ background: CORES_NATUREZA.organizacao }} /> organização</li>
            <li><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full align-middle" style={{ background: CORES_NATUREZA.advogado }} /> advogado</li>
          </ul>
          <ul className="mt-2 space-y-1 border-t border-neutral-200 pt-2 text-xs">
            {Object.entries(ROTULO_ARESTA).filter(([k]) => contagens[k]).map(([k, r]) => (
              <li key={k}><span className="legenda-linha" style={estiloLinha(k)} />{r} <span className="text-neutral-600">({contagens[k]})</span></li>
            ))}
          </ul>
        </details>
      </aside>

      <div className="min-w-0">
        <div ref={ref} className="grafo-canvas h-[62vh] min-h-[420px] w-full rounded border border-neutral-300 bg-white" role="img" aria-label="Grafo interativo de processos e entidades; a tabela ao final da página contém as mesmas ligações" />
        <p role="status" className="mt-1 text-xs text-neutral-600">{visivel.nos.length} nós, {visivel.arestas.length} ligações. Clique num nó para ver a ficha; clique no fundo para sair do foco.</p>
      </div>

      <aside className="text-sm">
        {focoNo ? (
          <div className="folha border border-neutral-300 bg-white p-3">
            <p className="text-xs text-neutral-600">{focoNo.tipo === "processo" ? (focoNo.dados.externo ? "processo citado, não coletado" : "processo") : `${String(focoNo.dados.subtipo)}${focoNo.dados.grupo ? `, ${String(focoNo.dados.grupo)}` : ""}`}</p>
            <h2 className="text-lg leading-tight">{focoNo.rotulo}</h2>
            {focoNo.tipo === "processo" && !focoNo.dados.externo && <p className="mt-1 text-xs text-neutral-700">relator {String(focoNo.dados.relator ?? "—")}, {String(focoNo.dados.publicidade ?? "")}</p>}
            {focoNo.tipo === "entidade" && (
              <p className="mt-1 text-xs text-neutral-700">
                {(focoNo.dados.papeis as string[])?.length ? `papéis: ${(focoNo.dados.papeis as string[]).join(", ")}. ` : ""}
                {Number(focoNo.dados.n_assercoes) > 0 ? `${String(focoNo.dados.n_assercoes)} asserções citam este nome.` : ""}
                {focoNo.dados.origem === "documento" ? " Mencionada só em documentos (terceiro mencionado)." : ""}
              </p>
            )}
            <div className="mt-2 flex flex-wrap gap-2">
              {hrefDoNo(focoNo) && <Link className="rounded border border-neutral-400 px-2 py-0.5 text-xs underline hover:bg-neutral-100" href={hrefDoNo(focoNo)!}>Abrir página</Link>}
              <button type="button" className={`rounded border px-2 py-0.5 text-xs ${modoCaminho ? "border-amber-700 bg-amber-100" : "border-neutral-400 hover:bg-neutral-100"}`} onClick={() => setModoCaminho((m) => !m)}>
                {modoCaminho ? "agora clique no segundo nó" : "Traçar caminho até…"}
              </button>
            </div>
            {caminho && destino && (
              <p className="mt-2 rounded bg-neutral-100 p-2 text-xs">
                Caminho: {caminho.map((id, i) => <span key={id}>{i > 0 ? " → " : ""}<button type="button" className="underline" onClick={() => centrarEm(id)}>{porId.get(id)?.rotulo ?? id}</button></span>)}
              </p>
            )}
            {caminho === null && destino && <p className="mt-2 text-xs">Sem caminho entre os dois nós com as camadas ativas.</p>}
            <h3 className="mt-3 text-sm font-semibold">Ligações ({ligacoes.length})</h3>
            <div className="mt-1 max-h-[46vh] space-y-2 overflow-auto pr-1">
              {ligacoesPorTipo.map(([tipo, ls]) => (
                <details key={tipo} open={ls.length <= 8}>
                  <summary className="cursor-pointer text-xs font-medium"><span className="legenda-linha" style={estiloLinha(tipo)} />{ROTULO_ARESTA[tipo] ?? tipo} ({ls.length})</summary>
                  <ul className="mt-1 space-y-1 pl-2">
                    {ls.map(({ e, outro, saida }, i) => {
                      const f = descreverFonte(e);
                      const sub = (e.dados.subtipo as string) ?? (e.dados.papel_portal as string) ?? (e.dados.tipo_voto as string) ?? "";
                      return (
                        <li key={i} className="text-xs">
                          <button type="button" className="underline" onClick={() => centrarEm(outro)}>{porId.get(outro)?.rotulo ?? outro}</button>
                          {sub ? <span className="text-neutral-600"> {saida ? "" : "← "}{sub.replace(/_/g, " ")}</span> : null}
                          <span className="block text-neutral-600">fonte: {f.texto}{f.links.map((l) => <span key={l.href}> <Link className="underline" href={l.href}>{l.rotulo}</Link></span>)}</span>
                        </li>
                      );
                    })}
                  </ul>
                </details>
              ))}
            </div>
          </div>
        ) : (
          <div className="folha border border-neutral-300 bg-white p-3 text-neutral-700">
            <p>Clique num nó para abrir a ficha: papéis, quantas asserções o citam e cada ligação com a sua fonte (documento e página, andamento ou cadastro).</p>
            <p className="mt-2">Toda ligação vem do portal ou de uma asserção validada contra o texto; nada é sugerido por modelo.</p>
          </div>
        )}
      </aside>

      <details className="folha border border-neutral-300 bg-white p-3 text-sm lg:col-span-3">
        <summary className="cursor-pointer font-semibold">Tabela das ligações visíveis ({visivel.arestas.length})</summary>
        <div className="mt-2 max-h-[420px] overflow-auto">
          <table className="w-full border-collapse">
            <thead><tr className="border-b text-left"><th scope="col" className="py-1 pr-3">Origem</th><th scope="col" className="py-1 pr-3">Ligação</th><th scope="col" className="py-1 pr-3">Destino</th><th scope="col" className="py-1 pr-3">Fonte</th></tr></thead>
            <tbody>
              {visivel.arestas.slice(0, 800).map((e, i) => (
                <tr key={i} className="border-b border-neutral-100">
                  <td className="py-1 pr-3">{porId.get(e.origem)?.rotulo}</td>
                  <td className="py-1 pr-3">{ROTULO_ARESTA[e.tipo] ?? e.tipo}{e.dados.subtipo ? ` (${String(e.dados.subtipo).replace(/_/g, " ")})` : e.dados.papel_portal ? ` (${String(e.dados.papel_portal)})` : ""}</td>
                  <td className="py-1 pr-3">{porId.get(e.destino)?.rotulo}</td>
                  <td className="py-1 pr-3 text-xs text-neutral-700">{descreverFonte(e).texto}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {visivel.arestas.length > 800 && <p className="mt-1 text-xs text-neutral-600">Mostrando as 800 primeiras; o arquivo grafo.json tem todas.</p>}
        </div>
      </details>
    </div>
  );
}

function construirEstilo(t: ReturnType<typeof lerTokens>): cytoscape.StylesheetJson {
  return [
        { selector: "node", style: { "background-color": "data(cor)", width: "data(tam)", height: "data(tam)", label: "data(label)", "font-family": "IBM Plex Sans, system-ui, sans-serif", "font-size": 10, color: t.tinta, "text-wrap": "ellipsis", "text-max-width": "120px", "text-valign": "bottom", "text-margin-y": 3, "text-background-color": t.fundo, "text-background-opacity": 0.75, "text-background-padding": "1px", "min-zoomed-font-size": 5, "border-width": 0, "overlay-opacity": 0 } },
        { selector: "node[pesoRotulo < 2]", style: { "text-opacity": 0 } },
        { selector: "node[tipo = 'processo']", style: { shape: "round-rectangle", width: "data(tam)", height: 30, "z-index": 10, "background-color": "data(cor)", color: t.fundo, "font-size": 14, "font-weight": 600, "min-zoomed-font-size": 0, "text-valign": "center", "text-margin-y": 0, "text-opacity": 1, "text-background-opacity": 0, "text-max-width": "200px", "text-wrap": "none" } },
        { selector: "node[tipo = 'processo'][pub = 'Sigiloso']", style: { "background-color": t.tinta2 } },
        { selector: "node[tipo = 'processo'][?externo]", style: { "background-color": t.folha, color: t.tinta2, "border-width": 1, "border-color": t.fioForte, "border-style": "dashed", "font-weight": 400 } },
        { selector: "node[tipo = 'processo'][?semente]", style: { "border-width": 4, "border-color": t.marca, "border-style": "double", "font-size": 16, height: 36 } },
        { selector: "edge", style: { width: "data(peso)", "line-color": t.tinta2, "curve-style": "haystack", "haystack-radius": 0.4, "target-arrow-shape": "none", "overlay-opacity": 0, opacity: 0.75 } },
        { selector: "edge[tipo = 'relacao']", style: { "curve-style": "bezier", "line-color": t.tinta, width: 3, "target-arrow-shape": "triangle", "target-arrow-color": t.tinta, "arrow-scale": 1, opacity: 0.95 } },
        { selector: "edge[tipo = 'numero_origem']", style: { "curve-style": "bezier", "line-style": "dashed", "line-color": t.fioForte, width: 1.5 } },
        { selector: "edge[tipo = 'representa']", style: { "line-style": "dotted", "line-color": t.fioForte, width: 1.5 } },
        { selector: "edge[tipo = 'cita_processo']", style: { "curve-style": "bezier", "line-style": "dashed", "line-color": t.alegacao, "target-arrow-shape": "vee", "target-arrow-color": t.alegacao, "arrow-scale": 0.8, opacity: 0.7 } },
        { selector: "edge[tipo = 'citado_em']", style: { "line-color": t.fato, opacity: 0.55 } },
        { selector: "edge[tipo = 'afirma_em'][sub = 'alegacao_parte']", style: { "line-color": t.alegacao } },
        { selector: "edge[tipo = 'afirma_em'][sub = 'fundamento_decisorio']", style: { "line-color": t.fundamento } },
        { selector: "edge[tipo = 'co_citacao']", style: { "line-style": "dotted", "line-color": t.fato, opacity: 0.45 } },
        { selector: "edge[tipo = 'relator_de']", style: { "curve-style": "bezier", "line-color": t.fundamento, width: 2 } },
        { selector: "edge[tipo = 'votou_em']", style: { "curve-style": "bezier", "line-style": "dashed", "line-color": t.fundamento, width: 1.5 } },
        { selector: ".apagado", style: { opacity: 0.08, "text-opacity": 0 } },
        { selector: "node.realce, edge.realce", style: { opacity: 1 } },
        { selector: "edge.realce", style: { "line-color": t.marca, "target-arrow-color": t.marca, width: 2.5, opacity: 1 } },
        { selector: "edge.caminho", style: { "line-color": t.marca, "target-arrow-color": t.marca, width: 3.5, opacity: 1, "curve-style": "bezier" } },
        { selector: "node.caminho", style: { "border-width": 3, "border-color": t.marca, "text-opacity": 1, opacity: 1 } },
        { selector: "node:selected", style: { "border-width": 3, "border-color": t.marca, "text-opacity": 1 } },
  ];
}

function estiloLinha(tipo: string): React.CSSProperties {
  const base: React.CSSProperties = { borderTopStyle: "solid", borderTopColor: "var(--fio-forte)" };
  switch (tipo) {
    case "relacao": return { ...base, borderTopColor: "var(--tinta-2)", borderTopWidth: 3 };
    case "numero_origem": return { ...base, borderTopStyle: "dashed", borderTopColor: "var(--fio)" };
    case "representa": return { ...base, borderTopStyle: "dotted", borderTopColor: "var(--fio)" };
    case "cita_processo": return { ...base, borderTopStyle: "dashed", borderTopColor: "var(--alegacao)" };
    case "citado_em": return { ...base, borderTopColor: "var(--fato)" };
    case "afirma_em": return { ...base, borderTopColor: "var(--alegacao)" };
    case "co_citacao": return { ...base, borderTopStyle: "dotted", borderTopColor: "var(--fato)" };
    case "relator_de": return { ...base, borderTopColor: "var(--fundamento)", borderTopWidth: 3 };
    case "votou_em": return { ...base, borderTopStyle: "dashed", borderTopColor: "var(--fundamento)" };
    default: return base;
  }
}
