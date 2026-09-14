"use client";

import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { formatarData, formatarReais, type FluxoAresta, type FluxoAtor, type FluxosDados, type FluxoTransacao } from "@/lib/tipos";
import { useTelaLarga } from "@/lib/useTelaLarga";

/*
  Leitura do mapa:
  - Cada nó é uma pessoa (círculo) ou empresa (retângulo) citada pelo relatório; o tamanho é o volume que passa por ela.
    Borda dourada: também é parte nos processos do caso (a ficha leva à página da entidade).
  - Cada seta é a soma dos fluxos de A para B que o relatório descreve. Linha cheia: operação datada (extrato, escritura,
    nota fiscal). Linha fina: agregado ("26 lançamentos totalizando…"). Tracejado sem seta: escritura em que o texto não
    diz quem pagou a quem — só que os dois assinaram.
  - Nada aqui é conclusão: é o que o comunicante (banco, cooperativa, cartório, concessionária) relatou ao COAF, e
    cada fluxo mostra a página e o trecho literal de onde saiu.
*/

const ROTULO_SECAO: Record<string, string> = { suspeita: "comunicação de operação suspeita", automatica: "comunicação automática (critério objetivo)", especie: "operação em espécie (cartório)" };
const ROTULO_TIPO: Record<string, string> = {
  transferencia: "transferência", pix: "PIX", ted: "TED/DOC", boleto: "boleto", cdb_rdb: "CDB/RDB", cartao: "cartão", cheque: "cheque", tributo: "tributo",
  escritura_compra: "compra de imóvel (escritura)", escritura_doacao: "doação de imóvel (escritura)", alienacao_fiduciaria: "alienação fiduciária (dívida garantida)",
  compra_veiculo: "compra de veículo", pagamento_titulo: "pagamento de título", outros: "outros", escritura_sem_direcao: "escritura (direção não informada)",
};

type Filtros = { secoes: Record<string, boolean>; individuais: boolean; agregados: boolean; escrituras: boolean; valorMin: number; ano: string };

function lerTokens() {
  const cs = getComputedStyle(document.documentElement);
  const v = (nome: string, padrao: string) => cs.getPropertyValue(nome).trim() || padrao;
  return {
    fundo: v("--fundo", "#15181d"), folha: v("--folha", "#1d2127"), fio: v("--fio", "#343a44"), fioForte: v("--fio-forte", "#4a5261"),
    tinta: v("--tinta", "#e9e4d8"), tinta2: v("--tinta-2", "#a39f93"), fato: v("--fato", "#8fcba4"), alegacao: v("--alegacao", "#e4b35f"),
    fundamento: v("--fundamento", "#93b6e6"), marca: v("--marca", "#f4d27a"),
  };
}

function anoDe(t: { data: string | null; periodo_inicio: string | null }): string | null {
  const d = t.data ?? t.periodo_inicio;
  return d ? d.slice(0, 4) : null;
}

export function RedeDePagamentos({ dados }: { dados: FluxosDados }) {
  const ref = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const telaLarga = useTelaLarga();
  const [filtros, setFiltros] = useState<Filtros>({ secoes: { suspeita: true, automatica: true, especie: true }, individuais: true, agregados: true, escrituras: true, valorMin: 0, ano: "todos" });
  const [foco, setFoco] = useState<{ tipo: "ator"; id: number } | { tipo: "aresta"; chave: string } | null>(null);
  const [busca, setBusca] = useState("");
  const [tema, setTema] = useState(0);
  const [paineis, setPaineis] = useState<{ filtros: boolean | null; legenda: boolean | null }>({ filtros: null, legenda: null });
  const filtrosAbertos = paineis.filtros ?? telaLarga;
  const legendaAberta = paineis.legenda ?? telaLarga;

  useEffect(() => {
    const obs = new MutationObserver(() => setTema((t) => t + 1));
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-tema"] });
    return () => obs.disconnect();
  }, []);

  const atorPorId = useMemo(() => new Map(dados.atores.map((a) => [a.id, a])), [dados]);
  const comPorId = useMemo(() => new Map(dados.comunicacoes.map((c) => [c.id, c])), [dados]);
  const txPorId = useMemo(() => new Map(dados.transacoes.map((t) => [t.id, t])), [dados]);
  const anos = useMemo(() => [...new Set(dados.transacoes.map(anoDe).filter((a): a is string => !!a))].sort(), [dados]);

  // Transações visíveis: sem os resumos por tipo (repetem os agregados), respeitando seção, natureza, valor e ano.
  const visivel = useMemo(() => {
    const min = filtros.valorMin * 100;
    const tx = dados.transacoes.filter((t) => {
      if (t.natureza === "resumo_tipo") return false;
      if (!filtros.secoes[t.secao]) return false;
      if (t.natureza === "individual" && !filtros.individuais) return false;
      if (t.natureza === "agregado" && !filtros.agregados) return false;
      if (t.valor_centavos < min) return false;
      if (filtros.ano !== "todos" && anoDe(t) !== filtros.ano) return false;
      return true;
    });
    const pares = new Map<string, FluxoAresta>();
    for (const t of tx) {
      if (t.origem_ator_id == null || t.destino_ator_id == null) continue;
      const k = `${t.origem_ator_id}>${t.destino_ator_id}`;
      const e = pares.get(k) ?? { origem: t.origem_ator_id, destino: t.destino_ator_id, dirigida: true, valor_centavos: 0, n: 0, transacoes: [], naturezas: [], tipos: [], secoes: [] };
      e.valor_centavos += t.valor_centavos; e.n += 1; e.transacoes.push(t.id);
      if (!e.naturezas.includes(t.natureza)) e.naturezas.push(t.natureza);
      if (!e.tipos.includes(t.tipo)) e.tipos.push(t.tipo);
      if (!e.secoes.includes(t.secao)) e.secoes.push(t.secao);
      pares.set(k, e);
    }
    const arestas = [...pares.values()];
    if (filtros.escrituras) {
      for (const e of dados.grafo.arestas) {
        if (e.dirigida) continue;
        const c = e.comunicacao_id ? comPorId.get(e.comunicacao_id) : undefined;
        if (!c || !filtros.secoes[c.secao] || e.valor_centavos < min) continue;
        if (filtros.ano !== "todos" && (c.periodo_inicio ?? "").slice(0, 4) !== filtros.ano) continue;
        arestas.push(e);
      }
    }
    const volume = new Map<number, number>();
    for (const e of arestas) { volume.set(e.origem, (volume.get(e.origem) ?? 0) + e.valor_centavos); volume.set(e.destino, (volume.get(e.destino) ?? 0) + e.valor_centavos); }
    const nos = dados.atores.filter((a) => volume.has(a.id));
    // fluxos com uma ponta não informada (boletos, concessionária) não viram aresta, mas contam na ficha do ator
    const soltas = tx.filter((t) => t.origem_ator_id == null || t.destino_ator_id == null);
    return { tx, arestas, nos, volume, soltas };
  }, [dados, filtros, comPorId]);

  const chaveAresta = (e: FluxoAresta) => `${e.dirigida ? "d" : "u"}:${e.origem}>${e.destino}:${e.comunicacao_id ?? ""}`;

  const aplicarFoco = useCallback((cy: Core, f: typeof foco) => {
    cy.batch(() => {
      cy.elements().removeClass("apagado realce vizinho");
      if (!f) return;
      if (f.tipo === "ator") {
        const no = cy.getElementById(`a${f.id}`);
        if (no.empty()) return;
        const viz = no.closedNeighborhood();
        cy.elements().not(viz).addClass("apagado");
        viz.edges().addClass("realce"); viz.nodes().addClass("vizinho");
      } else {
        const ar = cy.getElementById(f.chave);
        if (ar.empty()) return;
        const viz = ar.connectedNodes().union(ar);
        cy.elements().not(viz).addClass("apagado");
        ar.addClass("realce"); viz.nodes().addClass("vizinho");
      }
    });
  }, []);

  useEffect(() => {
    if (!ref.current) return;
    const t = lerTokens();
    const maxVol = Math.max(1, ...visivel.nos.map((a) => visivel.volume.get(a.id) ?? 0));
    const elementos: ElementDefinition[] = [
      ...visivel.nos.map((a) => ({
        data: {
          id: `a${a.id}`, label: a.nome, tipo: a.tipo, parte: !!a.entidade_id,
          tam: 16 + 44 * Math.sqrt((visivel.volume.get(a.id) ?? 0) / maxVol),
          cor: a.tipo === "pessoa_fisica" ? t.fato : a.tipo === "pessoa_juridica" ? t.fundamento : t.tinta2,
        },
      })),
      ...visivel.arestas.map((e) => ({
        data: {
          id: chaveAresta(e), source: `a${e.origem}`, target: `a${e.destino}`, dirigida: e.dirigida,
          natureza: e.dirigida ? (e.naturezas.includes("individual") ? "individual" : "agregado") : "escritura",
          peso: 1 + Math.min(9, Math.log10(Math.max(1, e.valor_centavos / 100)) - 3),
          label: e.valor_centavos >= 100_000_00 ? formatarReais(e.valor_centavos, true) : "",
        },
      })),
    ];
    const cy = cytoscape({ container: ref.current, elements: elementos, style: construirEstilo(t, !telaLarga), layout: { name: "preset" }, wheelSensitivity: 0.2, minZoom: 0.15, maxZoom: 4 });
    cy.layout({ name: "cose", animate: false, nodeRepulsion: () => 250000, nodeOverlap: 40, idealEdgeLength: () => 140, edgeElasticity: () => 60, gravity: 0.6, numIter: 1500, coolingFactor: 0.96, padding: 28, randomize: true, componentSpacing: 120 } as cytoscape.LayoutOptions).run();
    cyRef.current = cy;
    cy.on("tap", "node", (ev) => { const f = { tipo: "ator" as const, id: Number(ev.target.id().slice(1)) }; setFoco(f); aplicarFoco(cy, f); });
    cy.on("tap", "edge", (ev) => { const f = { tipo: "aresta" as const, chave: ev.target.id() }; setFoco(f); aplicarFoco(cy, f); });
    cy.on("tap", (ev) => { if (ev.target === cy) { setFoco(null); aplicarFoco(cy, null); } });
    return () => { cy.destroy(); cyRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visivel]);

  useEffect(() => {
    const cy = cyRef.current; if (!cy) return;
    cy.style().fromJson(construirEstilo(lerTokens(), !telaLarga)).update();
  }, [tema, telaLarga]);

  const centrarEm = (id: number) => {
    const cy = cyRef.current; if (!cy) return;
    const no = cy.getElementById(`a${id}`); if (no.empty()) return;
    cy.animate({ center: { eles: no }, zoom: Math.max(cy.zoom(), telaLarga ? 1.1 : 0.8) }, { duration: 350 });
    const f = { tipo: "ator" as const, id }; setFoco(f); aplicarFoco(cy, f);
  };
  const limpar = () => { setFoco(null); if (cyRef.current) aplicarFoco(cyRef.current, null); };

  const sugestoes = useMemo(() => {
    const q = busca.trim().toLowerCase();
    if (q.length < 2) return [];
    return visivel.nos.filter((a) => a.nome.toLowerCase().includes(q)).slice(0, 8);
  }, [busca, visivel]);

  // Ficha do ator: todos os fluxos visíveis em que ele aparece, inclusive os de ponta não informada.
  const focoAtor = foco?.tipo === "ator" ? atorPorId.get(foco.id) : undefined;
  const txDoAtor = useMemo(() => {
    if (!focoAtor) return [];
    return visivel.tx.filter((t) => t.origem_ator_id === focoAtor.id || t.destino_ator_id === focoAtor.id).sort((a, b) => b.valor_centavos - a.valor_centavos);
  }, [focoAtor, visivel]);
  const escriturasDoAtor = useMemo(() => {
    if (!focoAtor) return [];
    return visivel.arestas.filter((e) => !e.dirigida && (e.origem === focoAtor.id || e.destino === focoAtor.id));
  }, [focoAtor, visivel]);
  const focoAresta = foco?.tipo === "aresta" ? visivel.arestas.find((e) => chaveAresta(e) === foco.chave) : undefined;

  const linhasTabela = useMemo(() => [...visivel.tx].sort((a, b) => b.valor_centavos - a.valor_centavos), [visivel]);

  return (
    <div className="grid gap-3 lg:grid-cols-[230px_minmax(0,1fr)_320px]">
      <aside className="min-w-0 space-y-3 text-sm">
        <details className="folha border border-neutral-300 bg-white p-3" open={filtrosAbertos} onToggle={(ev) => { const aberto = ev.currentTarget.open; setPaineis((p) => ({ ...p, filtros: aberto })); }}>
          <summary className="toque cursor-pointer font-semibold">Filtros</summary>
          <form className="mt-2 space-y-3" onSubmit={(ev) => { ev.preventDefault(); if (sugestoes[0]) centrarEm(sugestoes[0].id); }}>
            <label className="block"><span className="font-medium">Encontrar</span>
              <input className="mt-1 w-full rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={busca} onChange={(ev) => setBusca(ev.target.value)} placeholder="pessoa ou empresa…" />
              {sugestoes.length > 0 && busca && (
                <ul className="mt-1 max-h-40 overflow-auto rounded border border-neutral-300 bg-white">
                  {sugestoes.map((a) => <li key={a.id}><button type="button" className="w-full px-2 py-1 text-left hover:bg-neutral-100" onClick={() => { centrarEm(a.id); setBusca(""); }}>{a.nome}</button></li>)}
                </ul>
              )}
            </label>
            <fieldset className="space-y-1"><legend className="font-medium">Tipo de comunicação</legend>
              {Object.entries(ROTULO_SECAO).map(([k, r]) => (
                <label key={k} className="flex items-center gap-2"><input type="checkbox" checked={filtros.secoes[k]} onChange={(ev) => setFiltros({ ...filtros, secoes: { ...filtros.secoes, [k]: ev.target.checked } })} /> {r}</label>
              ))}
            </fieldset>
            <fieldset className="space-y-1"><legend className="font-medium">Mostrar</legend>
              <label className="flex items-center gap-2"><input type="checkbox" checked={filtros.individuais} onChange={(ev) => setFiltros({ ...filtros, individuais: ev.target.checked })} /> operações datadas</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={filtros.agregados} onChange={(ev) => setFiltros({ ...filtros, agregados: ev.target.checked })} /> agregados (&quot;N lançamentos totalizando…&quot;)</label>
              <label className="flex items-center gap-2"><input type="checkbox" checked={filtros.escrituras} onChange={(ev) => setFiltros({ ...filtros, escrituras: ev.target.checked })} /> escrituras sem direção informada</label>
            </fieldset>
            <label className="block"><span className="font-medium">Valor mínimo: {formatarReais(filtros.valorMin * 100, true)}</span>
              <input type="range" min={0} max={7} step={1} className="mt-1 w-full" value={Math.log10(Math.max(1, filtros.valorMin))} onChange={(ev) => { const p = Number(ev.target.value); setFiltros({ ...filtros, valorMin: p === 0 ? 0 : 10 ** p }); }} aria-label="Valor mínimo (potências de dez)" />
            </label>
            <label className="block"><span className="font-medium">Ano</span>
              <select className="mt-1 w-full rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={filtros.ano} onChange={(ev) => setFiltros({ ...filtros, ano: ev.target.value })}>
                <option value="todos">todos</option>{anos.map((a) => <option key={a} value={a}>{a}</option>)}
              </select></label>
            <div className="flex gap-2">
              <button type="button" className="rounded border border-neutral-400 px-2 py-1 hover:bg-neutral-100" onClick={() => cyRef.current?.fit(undefined, 24)}>Ajustar à tela</button>
              <button type="button" className="rounded border border-neutral-400 px-2 py-1 hover:bg-neutral-100" onClick={limpar}>Limpar</button>
            </div>
          </form>
        </details>
        <details className="folha border border-neutral-300 bg-white p-3" open={legendaAberta} onToggle={(ev) => { const aberto = ev.currentTarget.open; setPaineis((p) => ({ ...p, legenda: aberto })); }}>
          <summary className="toque cursor-pointer font-semibold">Legenda</summary>
          <ul className="mt-2 space-y-1 text-xs">
            <li><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full align-middle" style={{ background: "var(--fato)" }} /> pessoa física (CPF mascarado)</li>
            <li><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm align-middle" style={{ background: "var(--fundamento)" }} /> empresa ou fundo (CNPJ)</li>
            <li><span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full border-2 align-middle" style={{ borderColor: "var(--marca)" }} /> também é parte nos processos do caso</li>
            <li>tamanho do nó: volume que passa por ele nos fluxos visíveis</li>
          </ul>
          <ul className="mt-2 space-y-1 border-t border-neutral-200 pt-2 text-xs">
            <li><span className="legenda-linha" style={{ borderTop: "3px solid var(--tinta)" }} /> operação datada (extrato, escritura, nota fiscal) →</li>
            <li><span className="legenda-linha" style={{ borderTop: "1.5px solid var(--tinta-2)" }} /> agregado informado pelo banco →</li>
            <li><span className="legenda-linha" style={{ borderTop: "2px dashed var(--alegacao)" }} /> escritura: os dois assinaram, o texto não diz quem pagou</li>
            <li>largura: proporcional ao valor (escala logarítmica)</li>
          </ul>
        </details>
      </aside>

      <div className="order-first min-w-0 lg:order-none">
        <div ref={ref} className="grafo-canvas h-[70svh] min-h-[380px] w-full rounded border border-neutral-300 bg-white lg:h-[64vh] lg:min-h-[440px]" role="img" aria-label="Mapa interativo dos fluxos financeiros; a tabela ao final da página contém as mesmas transações" />
        <p role="status" className="mt-1 text-xs text-neutral-600">{visivel.nos.length} pessoas e empresas, {visivel.arestas.length} ligações, {visivel.tx.length} fluxos. Toque num nó ou numa seta para ver a ficha; toque no fundo para sair do foco.</p>
      </div>

      <aside className="min-w-0 text-sm">
        {focoAtor ? (
          <FichaAtor ator={focoAtor} tx={txDoAtor} escrituras={escriturasDoAtor} atorPorId={atorPorId} comPorId={comPorId} onFechar={limpar} onIr={centrarEm} />
        ) : focoAresta ? (
          <FichaAresta aresta={focoAresta} atorPorId={atorPorId} txPorId={txPorId} comPorId={comPorId} onFechar={limpar} onIr={centrarEm} />
        ) : (
          <div className="folha border border-neutral-300 bg-white p-3 text-neutral-700">
            <p>Clique numa pessoa ou empresa para ver quanto entrou e saiu, com cada fluxo, a página do relatório e o trecho literal. Clique numa seta para ver só os fluxos daquele par.</p>
            <p className="mt-2">Os valores são os que o comunicante relatou ao COAF; um RIF não é prova. Quem aparece aqui não é, por isso, investigado.</p>
          </div>
        )}
      </aside>

      <details className="folha border border-neutral-300 bg-white p-3 text-sm lg:col-span-3">
        <summary className="cursor-pointer font-semibold">Tabela dos fluxos visíveis ({linhasTabela.length}) — <a className="underline" href="data/fluxos.csv">baixar tudo em CSV</a></summary>
        <div className="mt-2 max-h-[480px] overflow-auto">
          <table className="w-full min-w-[820px] border-collapse">
            <thead><tr className="border-b text-left"><th scope="col" className="py-1 pr-3">De</th><th scope="col" className="py-1 pr-3">Para</th><th scope="col" className="py-1 pr-3 text-right">Valor</th><th scope="col" className="py-1 pr-3">Quando</th><th scope="col" className="py-1 pr-3">Tipo</th><th scope="col" className="py-1 pr-3">Fonte</th></tr></thead>
            <tbody>
              {linhasTabela.map((t) => (
                <tr key={t.id} className="border-b border-neutral-100 align-top">
                  <td className="py-1 pr-3">{nomeOu(t.origem_ator_id, atorPorId, "não informado")}</td>
                  <td className="py-1 pr-3">{nomeOu(t.destino_ator_id, atorPorId, "não informado")}</td>
                  <td className="py-1 pr-3 text-right tabular-nums">{formatarReais(t.valor_centavos)}</td>
                  <td className="py-1 pr-3 whitespace-nowrap">{quando(t)}</td>
                  <td className="py-1 pr-3">{ROTULO_TIPO[t.tipo] ?? t.tipo}{t.natureza === "agregado" ? ` · ${t.quantidade ?? "?"} lançamentos` : ""}</td>
                  <td className="py-1 pr-3 text-xs text-neutral-700"><Link className="underline" href={`/documento/${t.documento_id}#p-${t.pagina}`}>p. {t.pagina}</Link> · com. {comPorId.get(t.comunicacao_id)?.numero}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

function nomeOu(id: number | null, atores: Map<number, FluxoAtor>, padrao: string): string {
  return id == null ? padrao : (atores.get(id)?.nome ?? padrao);
}

function quando(t: FluxoTransacao): string {
  if (t.data) return formatarData(t.data);
  if (t.periodo_inicio && t.periodo_fim) return `${formatarData(t.periodo_inicio)} – ${formatarData(t.periodo_fim)}`;
  return "—";
}

function LinhaFluxo({ t, atorPorId, comPorId, ponto, onIr }: { t: FluxoTransacao; atorPorId: Map<number, FluxoAtor>; comPorId: Map<number, FluxosDados["comunicacoes"][number]>; ponto?: number; onIr: (id: number) => void }) {
  const outroId = ponto != null && t.origem_ator_id === ponto ? t.destino_ator_id : t.origem_ator_id;
  const saida = ponto != null && t.origem_ator_id === ponto;
  return (
    <li className="text-xs">
      <span className="font-medium tabular-nums">{formatarReais(t.valor_centavos)}</span>
      {ponto != null ? <span> {saida ? "→ para" : "← de"} {outroId == null ? <span className="text-neutral-600">não informado</span> : <button type="button" className="underline" onClick={() => onIr(outroId)}>{atorPorId.get(outroId)?.nome}</button>}</span> : null}
      <span className="block text-neutral-700">{ROTULO_TIPO[t.tipo] ?? t.tipo}{t.natureza === "agregado" ? `, ${t.quantidade ?? "?"} lançamentos` : ""} · {quando(t)}{t.descricao ? ` · ${t.descricao}` : ""}</span>
      <span className="block text-neutral-600">
        {comPorId.get(t.comunicacao_id)?.comunicante ?? "comunicante não informado"} · <Link className="underline" href={`/documento/${t.documento_id}#p-${t.pagina}`}>p. {t.pagina}</Link>
        <details className="inline"><summary className="inline cursor-pointer underline"> trecho</summary><q className="block border-l-2 border-neutral-300 pl-2 italic">{t.trecho_fonte}</q></details>
      </span>
    </li>
  );
}

function FichaAtor({ ator, tx, escrituras, atorPorId, comPorId, onFechar, onIr }: { ator: FluxoAtor; tx: FluxoTransacao[]; escrituras: FluxoAresta[]; atorPorId: Map<number, FluxoAtor>; comPorId: Map<number, FluxosDados["comunicacoes"][number]>; onFechar: () => void; onIr: (id: number) => void }) {
  const entradas = tx.filter((t) => t.destino_ator_id === ator.id).reduce((s, t) => s + t.valor_centavos, 0);
  const saidas = tx.filter((t) => t.origem_ator_id === ator.id).reduce((s, t) => s + t.valor_centavos, 0);
  return (
    <section className="folha folha-inferior border border-neutral-300 bg-white p-3" aria-label={`Ficha de ${ator.nome}`}>
      <button type="button" className="toque float-right -mr-1 -mt-1 rounded px-2 text-lg leading-none text-neutral-600 hover:bg-neutral-100 lg:hidden" aria-label="Fechar ficha" onClick={onFechar}>×</button>
      <p className="text-xs text-neutral-600">{ator.tipo === "pessoa_fisica" ? "pessoa física" : ator.tipo === "pessoa_juridica" ? "pessoa jurídica" : "citada só pelo nome"}{ator.documento_mascarado ? ` · ${ator.documento_mascarado}` : ""}</p>
      <h2 className="text-lg leading-tight">{ator.nome}</h2>
      {ator.atividade && <p className="mt-1 text-xs text-neutral-700">atividade informada: {ator.atividade.toLowerCase()}</p>}
      {ator.papeis.length > 0 && <p className="mt-1 text-xs text-neutral-700">aparece como: {ator.papeis.join(", ")}</p>}
      <p className="mt-2 text-xs"><span className="tabular-nums">entrou {formatarReais(entradas)}</span> · <span className="tabular-nums">saiu {formatarReais(saidas)}</span> (fluxos visíveis)</p>
      {ator.entidade_id && <p className="mt-2"><Link className="rounded border border-neutral-400 px-2 py-0.5 text-xs underline hover:bg-neutral-100" href={`/entidade/${ator.entidade_id}`}>Também é parte no caso: abrir página</Link></p>}
      <h3 className="mt-3 text-sm font-semibold">Fluxos ({tx.length})</h3>
      <ul className="mt-1 space-y-2 pr-1 lg:max-h-[46vh] lg:overflow-auto">
        {tx.map((t) => <LinhaFluxo key={t.id} t={t} atorPorId={atorPorId} comPorId={comPorId} ponto={ator.id} onIr={onIr} />)}
        {escrituras.map((e) => {
          const outro = e.origem === ator.id ? e.destino : e.origem;
          const c = e.comunicacao_id ? comPorId.get(e.comunicacao_id) : undefined;
          return (
            <li key={`esc${e.comunicacao_id}-${outro}`} className="text-xs">
              <span className="font-medium tabular-nums">{formatarReais(e.valor_centavos)}</span> — escritura com <button type="button" className="underline" onClick={() => onIr(outro)}>{atorPorId.get(outro)?.nome}</button>
              <span className="block text-neutral-700">o texto do cartório não diz quem pagou a quem · {c?.periodo_inicio ? formatarData(c.periodo_inicio) : ""}</span>
              {c && <span className="block text-neutral-600">{c.comunicante} · <Link className="underline" href={`/documento/${c.documento_id}#p-${c.pagina_inicio}`}>p. {c.pagina_inicio}</Link> · {c.informacoes?.slice(0, 160)}</span>}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function FichaAresta({ aresta, atorPorId, txPorId, comPorId, onFechar, onIr }: { aresta: FluxoAresta; atorPorId: Map<number, FluxoAtor>; txPorId: Map<number, FluxoTransacao>; comPorId: Map<number, FluxosDados["comunicacoes"][number]>; onFechar: () => void; onIr: (id: number) => void }) {
  const c = aresta.comunicacao_id ? comPorId.get(aresta.comunicacao_id) : undefined;
  return (
    <section className="folha folha-inferior border border-neutral-300 bg-white p-3" aria-label="Ficha da ligação">
      <button type="button" className="toque float-right -mr-1 -mt-1 rounded px-2 text-lg leading-none text-neutral-600 hover:bg-neutral-100 lg:hidden" aria-label="Fechar ficha" onClick={onFechar}>×</button>
      <p className="text-xs text-neutral-600">{aresta.dirigida ? "fluxos de" : "escritura entre"}</p>
      <h2 className="text-base leading-tight">
        <button type="button" className="underline" onClick={() => onIr(aresta.origem)}>{atorPorId.get(aresta.origem)?.nome}</button>
        {aresta.dirigida ? " → " : " e "}
        <button type="button" className="underline" onClick={() => onIr(aresta.destino)}>{atorPorId.get(aresta.destino)?.nome}</button>
      </h2>
      <p className="mt-1 text-sm tabular-nums">{formatarReais(aresta.valor_centavos)}{aresta.dirigida ? ` em ${aresta.n} fluxo(s)` : ""}</p>
      {aresta.dirigida ? (
        <ul className="mt-2 space-y-2 pr-1 lg:max-h-[50vh] lg:overflow-auto">
          {aresta.transacoes.map((id) => { const t = txPorId.get(id); return t ? <LinhaFluxo key={id} t={t} atorPorId={atorPorId} comPorId={comPorId} onIr={onIr} /> : null; })}
        </ul>
      ) : c ? (
        <div className="mt-2 text-xs text-neutral-700">
          <p>{c.comunicante} · {c.periodo_inicio ? formatarData(c.periodo_inicio) : ""} · <Link className="underline" href={`/documento/${c.documento_id}#p-${c.pagina_inicio}`}>p. {c.pagina_inicio}</Link></p>
          <p className="mt-1">{c.informacoes}</p>
          {c.bens.map((b) => <p key={b.id} className="mt-1">{b.tipo}: {b.descricao}{b.valor_referencia_centavos ? ` · valor de referência ${formatarReais(b.valor_referencia_centavos)}` : ""}</p>)}
        </div>
      ) : null}
    </section>
  );
}

function construirEstilo(t: ReturnType<typeof lerTokens>, compacto = false): cytoscape.StylesheetJson {
  return [
    { selector: "node", style: { "background-color": "data(cor)", width: "data(tam)", height: "data(tam)", label: "data(label)", "font-family": "IBM Plex Sans, system-ui, sans-serif", "font-size": 10, color: t.tinta, "text-wrap": "ellipsis", "text-max-width": "130px", "text-valign": "bottom", "text-margin-y": 3, "text-background-color": t.fundo, "text-background-opacity": 0.75, "text-background-padding": "1px", "min-zoomed-font-size": compacto ? 7 : 5, "border-width": 0, "overlay-opacity": 0 } },
    { selector: "node[tipo = 'pessoa_juridica']", style: { shape: "round-rectangle" } },
    { selector: "node[?parte]", style: { "border-width": 3, "border-color": t.marca } },
    { selector: `node[tam < ${compacto ? 30 : 22}]`, style: { "text-opacity": 0 } },
    { selector: "node.vizinho", style: { "text-opacity": 1 } },
    { selector: "edge", style: { width: "data(peso)", "line-color": t.tinta2, "curve-style": "bezier", "target-arrow-shape": "triangle", "target-arrow-color": t.tinta2, "arrow-scale": 0.9, label: "data(label)", "font-size": 9, color: t.tinta2, "text-background-color": t.fundo, "text-background-opacity": 0.7, "text-background-padding": "1px", "text-rotation": "autorotate", "min-zoomed-font-size": 7, "overlay-opacity": 0, opacity: 0.8 } },
    { selector: "edge[natureza = 'individual']", style: { "line-color": t.tinta, "target-arrow-color": t.tinta, color: t.tinta, opacity: 0.95 } },
    { selector: "edge[natureza = 'escritura']", style: { "line-style": "dashed", "line-color": t.alegacao, "target-arrow-shape": "none", color: t.alegacao, opacity: 0.8 } },
    { selector: ".apagado", style: { opacity: 0.12, "text-opacity": 0 } },
    { selector: "edge.realce", style: { opacity: 1, "line-color": t.marca, "target-arrow-color": t.marca, "z-index": 5 } },
    { selector: "node.vizinho", style: { opacity: 1 } },
    { selector: "node:selected", style: { "border-width": 3, "border-color": t.marca } },
  ];
}
