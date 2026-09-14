"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { Andamento } from "@/lib/tipos";
import { formatarData, formatarDataHora } from "@/lib/tipos";

export function LinhaDoTempo({ andamentos, explicacoes }: { andamentos: Andamento[]; explicacoes: Record<string, string | null> }) {
  const [tipo, setTipo] = useState("");
  const [soDecisoes, setSoDecisoes] = useState(false);
  const [soComDoc, setSoComDoc] = useState(false);
  const [de, setDe] = useState("");
  const [ate, setAte] = useState("");

  const tipos = useMemo(() => Array.from(new Set(andamentos.map((a) => a.tipo))).sort(), [andamentos]);
  const filtrados = useMemo(
    () =>
      andamentos.filter(
        (a) =>
          (!tipo || a.tipo === tipo) &&
          (!soDecisoes || a.e_decisao) &&
          (!soComDoc || a.documentos.length > 0) &&
          (!de || a.data >= de) &&
          (!ate || a.data <= ate),
      ),
    [andamentos, tipo, soDecisoes, soComDoc, de, ate],
  );

  return (
    <div>
      <form className="mt-3 flex flex-wrap items-end gap-3 rounded border border-neutral-300 bg-white p-3 text-sm" onSubmit={(e) => e.preventDefault()} aria-label="Filtros da linha do tempo">
        <label className="flex flex-col">
          <span className="font-medium">Tipo de andamento</span>
          <select className="mt-1 rounded border border-neutral-400 px-2 py-1" value={tipo} onChange={(e) => setTipo(e.target.value)}>
            <option value="">todos</option>
            {tipos.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
        <label className="flex flex-col"><span className="font-medium">De</span><input type="date" className="mt-1 rounded border border-neutral-400 px-2 py-1" value={de} onChange={(e) => setDe(e.target.value)} /></label>
        <label className="flex flex-col"><span className="font-medium">Até</span><input type="date" className="mt-1 rounded border border-neutral-400 px-2 py-1" value={ate} onChange={(e) => setAte(e.target.value)} /></label>
        <label className="flex items-center gap-2"><input type="checkbox" checked={soDecisoes} onChange={(e) => setSoDecisoes(e.target.checked)} /> só decisões</label>
        <label className="flex items-center gap-2"><input type="checkbox" checked={soComDoc} onChange={(e) => setSoComDoc(e.target.checked)} /> só com documento</label>
        <p role="status" className="text-neutral-700">{filtrados.length} de {andamentos.length}</p>
      </form>

      <ol className="linha-tempo relative mt-4 ml-5 border-l-2 border-neutral-400 pl-5">
        {filtrados.map((a) => (
          <li key={a.id} id={`andamento-${a.id}`} data-decisao={a.e_decisao} className="relative mb-4 scroll-mt-20">
            <div className="rounded border border-neutral-300 bg-white p-3">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <time dateTime={a.data} className="font-mono text-sm font-semibold">{formatarData(a.data)}</time>
                <span className="font-semibold">{a.tipo}</span>
                {a.e_decisao && <span className="rounded bg-blue-800 px-2 py-0.5 text-xs font-semibold text-white">decisão</span>}
                {a.e_pauta && <span className="rounded bg-neutral-700 px-2 py-0.5 text-xs font-semibold text-white">pauta</span>}
              </div>
              {a.descricao && <p className="mt-1 text-sm">{a.descricao}</p>}
              {explicacoes[a.tipo] && (
                <p className="mt-1 text-xs text-neutral-700"><span className="font-medium">Explicação do portal do STF:</span> {explicacoes[a.tipo]}</p>
              )}
              {a.documentos.length > 0 && (
                <ul className="mt-2 flex flex-wrap gap-2 text-sm">
                  {a.documentos.map((d) => (
                    <li key={d.id}>
                      {d.baixado ? (
                        <Link className="rounded border border-neutral-500 px-2 py-0.5 underline" href={`/documento/${d.id}`}>
                          {d.rotulo} ({d.formato.toUpperCase()}{d.paginas ? `, ${d.paginas} p.` : ""})
                        </Link>
                      ) : (
                        <a className="rounded border border-neutral-500 px-2 py-0.5 underline" href={d.url} rel="noreferrer">{d.rotulo} (no portal)</a>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              <p className="mt-2 text-xs text-neutral-600">
                coletado em {a.snapshot ? formatarDataHora(a.snapshot.fetched_at) : "—"} · id {a.hash}
              </p>
            </div>
          </li>
        ))}
      </ol>
      {filtrados.length === 0 && <p className="mt-3 text-sm">Nenhum andamento corresponde aos filtros.</p>}
    </div>
  );
}
