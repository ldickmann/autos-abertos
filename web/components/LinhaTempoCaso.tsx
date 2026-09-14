"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { LinhaTempo } from "@/lib/tipos";
import { formatarData } from "@/lib/tipos";

/* Todos os andamentos de todos os processos do caso, num fio só. A categoria é curadoria (rótulo derivado do tipo);
   o tipo literal do portal fica sempre visível. */
export function LinhaTempoCaso({ dados, processos }: { dados: LinhaTempo; processos: { incidente: number; rotulo: string }[] }) {
  const [categorias, setCategorias] = useState<Set<string>>(() => new Set(["decisao", "julgamento", "recurso"]));
  const [procs, setProcs] = useState<Set<number>>(() => new Set(processos.map((p) => p.incidente)));
  const [de, setDe] = useState("");
  const [ate, setAte] = useState("");
  const [soComDoc, setSoComDoc] = useState(false);

  const eventos = useMemo(
    () => dados.eventos.filter((e) => categorias.has(e.categoria) && procs.has(e.incidente) && (!de || e.data >= de) && (!ate || e.data <= ate) && (!soComDoc || e.documentos.length > 0)),
    [dados, categorias, procs, de, ate, soComDoc],
  );
  const porDia = useMemo(() => {
    const m = new Map<string, typeof eventos>();
    for (const e of eventos) m.set(e.data, [...(m.get(e.data) ?? []), e]);
    return [...m.entries()].sort((a, b) => b[0].localeCompare(a[0]));
  }, [eventos]);
  const totalPorCategoria = useMemo(() => {
    const c: Record<string, number> = {};
    for (const e of dados.eventos) c[e.categoria] = (c[e.categoria] ?? 0) + 1;
    return c;
  }, [dados]);

  const alternar = <T,>(s: Set<T>, v: T) => { const n = new Set(s); if (n.has(v)) n.delete(v); else n.add(v); return n; };

  return (
    <div className="grid gap-4 lg:grid-cols-[250px_minmax(0,1fr)]">
      <aside className="text-sm">
        <form className="folha space-y-3 border border-neutral-300 bg-white p-3 lg:sticky lg:top-3" onSubmit={(ev) => ev.preventDefault()} aria-label="Filtros da linha do tempo do caso">
          <fieldset>
            <legend className="font-medium">O que mostrar</legend>
            <ul className="mt-1 space-y-1">
              {dados.categorias.map((c) => (
                <li key={c.id}><label className="flex items-center gap-2"><input type="checkbox" checked={categorias.has(c.id)} onChange={() => setCategorias(alternar(categorias, c.id))} /> {c.rotulo} <span className="text-xs text-neutral-600">{totalPorCategoria[c.id] ?? 0}</span></label></li>
              ))}
            </ul>
          </fieldset>
          <fieldset>
            <legend className="font-medium">Processos</legend>
            <ul className="mt-1 space-y-1">
              {processos.map((p) => (
                <li key={p.incidente}><label className="flex items-center gap-2"><input type="checkbox" checked={procs.has(p.incidente)} onChange={() => setProcs(alternar(procs, p.incidente))} /> {p.rotulo}</label></li>
              ))}
            </ul>
          </fieldset>
          <div className="grid grid-cols-2 gap-2">
            <label className="flex flex-col"><span className="font-medium">De</span><input type="date" className="mt-1 rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={de} onChange={(ev) => setDe(ev.target.value)} /></label>
            <label className="flex flex-col"><span className="font-medium">Até</span><input type="date" className="mt-1 rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={ate} onChange={(ev) => setAte(ev.target.value)} /></label>
          </div>
          <label className="flex items-center gap-2"><input type="checkbox" checked={soComDoc} onChange={(ev) => setSoComDoc(ev.target.checked)} /> só com documento</label>
          <p role="status" className="text-neutral-700">{eventos.length} de {dados.eventos.length} andamentos, em {porDia.length} dias</p>
        </form>
      </aside>

      <ol className="linha-tempo relative ml-5 border-l-2 border-neutral-400 pl-5">
        {porDia.map(([dia, lista]) => (
          <li key={dia} data-decisao={lista.some((e) => e.e_decisao)} data-categoria={lista[0].categoria} className="relative mb-5">
            <time dateTime={dia} className="font-mono text-sm font-semibold">{formatarData(dia)}</time>
            <ul className="mt-1 space-y-2">
              {lista.map((e) => (
                <li key={e.andamento_id} className="folha border border-neutral-300 bg-white p-3">
                  <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-sm">
                    <Link className="rounded-sm bg-neutral-900 px-1.5 py-px text-xs font-semibold text-neutral-50" href={`/processo/${e.incidente}#andamento-${e.andamento_id}`}>{e.processo}</Link>
                    <span className="font-semibold">{e.tipo}</span>
                    {e.e_decisao && <span className="rounded-sm bg-blue-800 px-1.5 py-px text-xs font-medium text-white">decisão</span>}
                    {e.e_pauta && <span className="rounded-sm bg-neutral-700 px-1.5 py-px text-xs font-medium text-white">pauta</span>}
                    <span className="text-xs text-neutral-600">{dados.categorias.find((c) => c.id === e.categoria)?.rotulo}</span>
                  </div>
                  {e.descricao && <p className="leitura mt-1 text-sm">{e.descricao}</p>}
                  {e.peticao && <p className="mt-1 text-xs text-neutral-700">petição {e.peticao.numero}{e.peticao.recebido_por ? `, recebida por ${e.peticao.recebido_por}` : ""}</p>}
                  {e.documentos.length > 0 && (
                    <ul className="mt-2 flex flex-wrap gap-2 text-xs">
                      {e.documentos.map((d) => (
                        <li key={d.id}>{d.baixado ? <Link className="rounded border border-neutral-500 px-2 py-0.5 underline" href={`/documento/${d.id}`}>{d.rotulo}{d.paginas ? ` (${d.paginas} p.)` : ""}</Link> : <span className="rounded border border-neutral-400 px-2 py-0.5">{d.rotulo} (no portal)</span>}</li>
                      ))}
                      {e.assercoes > 0 && <li className="self-center text-neutral-600">{e.assercoes} asserções extraídas</li>}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          </li>
        ))}
        {porDia.length === 0 && <li className="text-sm">Nenhum andamento com esses filtros.</li>}
      </ol>
    </div>
  );
}
