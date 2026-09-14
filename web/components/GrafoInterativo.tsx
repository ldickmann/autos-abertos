"use client";

import cytoscape from "cytoscape";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Grafo } from "@/lib/tipos";

type Modo = "processos" | "processos+partes" | "tudo";

export function GrafoInterativo({ grafo }: { grafo: Grafo }) {
  const ref = useRef<HTMLDivElement>(null);
  const [modo, setModo] = useState<Modo>("processos+partes");
  const [minProcessos, setMinProcessos] = useState(2);
  const [selecionado, setSelecionado] = useState<string | null>(null);

  const visivel = useMemo(() => {
    const mencoesPorEntidade = new Map<string, Set<string>>();
    for (const e of grafo.edges) if (e.tipo === "parte_em") mencoesPorEntidade.set(e.origem, new Set([...(mencoesPorEntidade.get(e.origem) ?? []), e.destino]));
    const nos = grafo.nodes.filter((n) => {
      if (n.tipo === "processo") return true;
      if (modo === "processos") return false;
      const sub = n.dados.subtipo as string;
      if (modo === "processos+partes" && sub === "advogado") return false;
      return (mencoesPorEntidade.get(n.id)?.size ?? 0) >= minProcessos;
    });
    const ids = new Set(nos.map((n) => n.id));
    const arestas = grafo.edges.filter((e) => ids.has(e.origem) && ids.has(e.destino) && (modo === "tudo" || e.tipo !== "representa"));
    return { nos, arestas };
  }, [grafo, modo, minProcessos]);

  useEffect(() => {
    if (!ref.current) return;
    const cy = cytoscape({
      container: ref.current,
      elements: [
        ...visivel.nos.map((n) => ({ data: { id: n.id, label: n.rotulo, tipo: n.tipo, sub: (n.dados.subtipo as string) ?? "", pub: (n.dados.publicidade as string) ?? "", prof: n.dados.profundidade as number | null } })),
        ...visivel.arestas.map((e, i) => ({ data: { id: `e${i}`, source: e.origem, target: e.destino, tipo: e.tipo, sub: (e.dados.subtipo as string) ?? (e.dados.papel_portal as string) ?? "", fraco: !!e.dados.fraco } })),
      ],
      style: [
        { selector: "node", style: { label: "data(label)", "font-size": 9, "text-wrap": "wrap", "text-max-width": "90px", "text-valign": "bottom", "text-margin-y": 4, color: "#171717", "background-color": "#a3a3a3", width: 18, height: 18 } },
        { selector: "node[tipo = 'processo']", style: { shape: "round-rectangle", "background-color": "#1d4ed8", width: 46, height: 26, "font-size": 10, "font-weight": "bold", color: "#0a0a0a", "text-valign": "center", "text-margin-y": 0 } },
        { selector: "node[tipo = 'processo'][pub = 'Sigiloso']", style: { "background-color": "#404040" } },
        { selector: "node[tipo = 'processo'][prof = 0]", style: { "border-width": 3, "border-color": "#b91c1c" } },
        { selector: "node[sub = 'advogado']", style: { "background-color": "#d4d4d4", width: 12, height: 12 } },
        { selector: "edge", style: { width: 1, "line-color": "#a3a3a3", "curve-style": "bezier", "target-arrow-shape": "none" } },
        { selector: "edge[tipo = 'relacao']", style: { width: 2.5, "line-color": "#1d4ed8", "target-arrow-shape": "triangle", "target-arrow-color": "#1d4ed8", label: "data(sub)", "font-size": 8, "text-rotation": "autorotate", "text-background-color": "#fff", "text-background-opacity": 1, "text-background-padding": "2px" } },
        { selector: "edge[fraco]", style: { "line-style": "dashed", "line-color": "#737373" } },
        { selector: "edge[tipo = 'representa']", style: { "line-color": "#d4d4d4", "line-style": "dotted" } },
        { selector: ":selected", style: { "border-width": 3, "border-color": "#f59e0b" } },
      ],
      layout: { name: "cose", animate: false, nodeRepulsion: () => 12000, idealEdgeLength: () => 90, padding: 20 },
      wheelSensitivity: 0.2,
    });
    cy.on("tap", "node", (ev) => setSelecionado(ev.target.id()));
    return () => cy.destroy();
  }, [visivel]);

  const rotulo = new Map(grafo.nodes.map((n) => [n.id, n.rotulo]));
  const selecionadoNo = grafo.nodes.find((n) => n.id === selecionado);
  const href = (id: string) => `/${id.replace(":", "/").replace("processo/", "processo/")}`;

  return (
    <div className="space-y-3">
      <form className="flex flex-wrap items-end gap-3 rounded border border-neutral-300 bg-white p-3 text-sm" onSubmit={(e) => e.preventDefault()} aria-label="Opções do grafo">
        <label className="flex flex-col"><span className="font-medium">Mostrar</span>
          <select className="mt-1 rounded border border-neutral-400 px-2 py-1" value={modo} onChange={(e) => setModo(e.target.value as Modo)}>
            <option value="processos">só processos</option><option value="processos+partes">processos e partes</option><option value="tudo">tudo, com advogados</option>
          </select></label>
        <label className="flex flex-col"><span className="font-medium">Entidades presentes em pelo menos</span>
          <select className="mt-1 rounded border border-neutral-400 px-2 py-1" value={minProcessos} onChange={(e) => setMinProcessos(Number(e.target.value))}>
            <option value={1}>1 processo</option><option value={2}>2 processos</option><option value={3}>3 processos</option></select></label>
        <p role="status" className="text-neutral-700">{visivel.nos.length} nós, {visivel.arestas.length} arestas</p>
      </form>
      <div ref={ref} className="h-[560px] w-full rounded border border-neutral-300 bg-white" role="img" aria-label="Grafo interativo de processos e entidades; a tabela abaixo contém as mesmas informações" />
      {selecionadoNo && (
        <p className="text-sm">Selecionado: <Link className="underline" href={selecionadoNo.tipo === "processo" ? `/processo/${selecionadoNo.dados.incidente}` : href(selecionadoNo.id)}>{selecionadoNo.rotulo}</Link></p>
      )}
      <details className="rounded border border-neutral-300 bg-white p-3 text-sm">
        <summary className="cursor-pointer font-semibold">Tabela de arestas ({visivel.arestas.length})</summary>
        <div className="mt-2 max-h-[420px] overflow-auto">
          <table className="w-full border-collapse">
            <thead><tr className="border-b text-left"><th scope="col" className="py-1 pr-3">Origem</th><th scope="col" className="py-1 pr-3">Relação</th><th scope="col" className="py-1 pr-3">Destino</th><th scope="col" className="py-1 pr-3">Fonte</th></tr></thead>
            <tbody>
              {visivel.arestas.map((e, i) => (
                <tr key={i} className="border-b border-neutral-100">
                  <td className="py-1 pr-3">{rotulo.get(e.origem)}</td>
                  <td className="py-1 pr-3">{e.tipo}{e.dados.subtipo ? `: ${String(e.dados.subtipo)}` : e.dados.papel_portal ? `: ${String(e.dados.papel_portal)}` : ""}{e.dados.fraco ? " (fraca)" : ""}</td>
                  <td className="py-1 pr-3">{rotulo.get(e.destino)}</td>
                  <td className="py-1 pr-3 text-xs text-neutral-700">{JSON.stringify(e.dados.fonte)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
