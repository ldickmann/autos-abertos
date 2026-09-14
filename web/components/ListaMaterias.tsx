"use client";

import { useMemo, useState } from "react";
import type { Materia } from "@/lib/tipos";
import { formatarData } from "@/lib/tipos";

const CASA: Record<string, string> = { senado: "Senado Federal", camara: "Câmara dos Deputados" };
const TIPO: Record<string, string> = { REQ: "requerimento em comissão", RQS: "requerimento ao Plenário do Senado", PFS: "proposta de fiscalização (Senado)", PL: "projeto de lei",
  PFC: "proposta de fiscalização e controle (Câmara)", RCP: "requerimento de CPI (Câmara)", RIC: "requerimento de informação", PDL: "projeto de decreto legislativo" };

export function ListaMaterias({ materias }: { materias: Materia[] }) {
  const [casa, setCasa] = useState("");
  const [sigla, setSigla] = useState("");
  const [busca, setBusca] = useState("");
  const siglas = useMemo(() => Array.from(new Set(materias.map((m) => m.sigla).filter(Boolean) as string[])).sort(), [materias]);
  const lista = useMemo(() => {
    const q = busca.trim().toLowerCase();
    return materias.filter((m) => (!casa || m.casa === casa) && (!sigla || m.sigla === sigla) && (!q || `${m.ementa} ${m.autor ?? ""} ${m.identificacao ?? ""}`.toLowerCase().includes(q)));
  }, [materias, casa, sigla, busca]);
  return (
    <div className="space-y-3">
      <form className="folha grid min-w-0 gap-3 border border-neutral-300 bg-white p-3 text-sm sm:grid-cols-3" onSubmit={(ev) => ev.preventDefault()} aria-label="Filtros das matérias">
        <label className="flex min-w-0 flex-col"><span className="font-medium">Casa</span>
          <select className="mt-1 w-full rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={casa} onChange={(ev) => setCasa(ev.target.value)}>
            <option value="">as duas</option><option value="senado">Senado Federal</option><option value="camara">Câmara dos Deputados</option></select></label>
        <label className="flex min-w-0 flex-col"><span className="font-medium">Tipo</span>
          <select className="mt-1 w-full rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={sigla} onChange={(ev) => setSigla(ev.target.value)}>
            <option value="">todos</option>{siglas.map((s) => <option key={s} value={s}>{s} — {TIPO[s] ?? s}</option>)}</select></label>
        <label className="flex min-w-0 flex-col"><span className="font-medium">Procurar na ementa ou no autor</span>
          <input className="mt-1 w-full rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={busca} onChange={(ev) => setBusca(ev.target.value)} placeholder="ex.: Banco Central, convocação, sigilo" /></label>
        <p role="status" className="text-neutral-700 sm:col-span-3">{lista.length} de {materias.length} matérias</p>
      </form>
      <ol className="space-y-2">
        {lista.map((m) => (
          <li key={`${m.casa}-${m.codigo}`} className="folha border border-neutral-300 bg-white p-3 text-sm">
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
              <time dateTime={m.data ?? undefined} className="font-mono text-xs font-semibold">{formatarData(m.data)}</time>
              <span className="rounded-sm bg-neutral-900 px-1.5 py-px text-xs font-semibold text-neutral-50">{CASA[m.casa]}</span>
              <a className="font-semibold underline" href={m.url} rel="noreferrer">{m.identificacao ?? `${m.sigla} ${m.numero}/${m.ano}`}</a>
              {m.sigla && <span className="text-xs text-neutral-600">{TIPO[m.sigla] ?? m.sigla}</span>}
            </div>
            <p className="leitura mt-1">{m.ementa}</p>
            <p className="mt-1 text-xs text-neutral-700">{m.autor ? `Autor: ${m.autor}. ` : ""}{m.comissao ? `Comissão: ${m.comissao}. ` : ""}Encontrada pelas consultas: {m.consultas.map((c) => c.split(":")[1]).join(", ")}.</p>
          </li>
        ))}
      </ol>
    </div>
  );
}
