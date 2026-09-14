"use client";

import Link from "next/link";
import MiniSearch from "minisearch";
import { useEffect, useMemo, useState } from "react";
import { formatarData } from "@/lib/tipos";

type Entrada = {
  tipo: "andamento" | "documento"; id: number; incidente: number; data?: string; titulo: string; texto: string;
  decisao?: boolean; documento_id?: number; pagina?: number; secao?: string | null;
};

const semAcento = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

export function Busca({ processos }: { processos: { incidente: number; rotulo: string }[] }) {
  const [indice, setIndice] = useState<MiniSearch<Entrada> | null>(null);
  const [entradas, setEntradas] = useState<Map<string, Entrada>>(new Map());
  const [q, setQ] = useState("");
  const [tipo, setTipo] = useState("");
  const [inc, setInc] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    fetch("/data/busca.json")
      .then((r) => r.json())
      .then((dados: Entrada[]) => {
        const ms = new MiniSearch<Entrada>({
          fields: ["titulo", "texto"], storeFields: [], idField: "chave",
          processTerm: (t) => semAcento(t), searchOptions: { prefix: true, fuzzy: 0.1, processTerm: (t) => semAcento(t) },
        });
        const mapa = new Map<string, Entrada>();
        const docs = dados.map((d) => { const chave = `${d.tipo}:${d.id}`; mapa.set(chave, d); return { ...d, chave }; });
        ms.addAll(docs as unknown as Entrada[]);
        setEntradas(mapa); setIndice(ms);
      })
      .catch((e) => setErro(String(e)));
  }, []);

  const resultados = useMemo(() => {
    if (!indice || q.trim().length < 2) return [];
    return indice.search(q).map((r) => ({ score: r.score, e: entradas.get(String(r.id))! })).filter((r) => r.e && (!tipo || r.e.tipo === tipo) && (!inc || String(r.e.incidente) === inc)).slice(0, 100);
  }, [indice, entradas, q, tipo, inc]);

  const rotulo = (i: number) => processos.find((p) => p.incidente === i)?.rotulo ?? `incidente ${i}`;
  const destacar = (texto: string) => {
    const termos = q.trim().split(/\s+/).filter((t) => t.length > 1).map(semAcento);
    const idx = termos.length ? semAcento(texto).indexOf(termos[0]) : -1;
    const ini = Math.max(0, idx - 120);
    const trecho = texto.slice(ini, ini + 320);
    return (ini > 0 ? "…" : "") + trecho + (ini + 320 < texto.length ? "…" : "");
  };

  return (
    <div>
      <form className="flex flex-wrap items-end gap-3 rounded border border-neutral-300 bg-white p-3 text-sm" onSubmit={(e) => e.preventDefault()} role="search">
        <label className="flex grow flex-col"><span className="font-medium">Termos</span>
          <input type="search" className="mt-1 rounded border border-neutral-400 px-2 py-1" value={q} onChange={(e) => setQ(e.target.value)} placeholder="ex.: prisão preventiva, SISBAJUD, agravo" autoFocus /></label>
        <label className="flex flex-col"><span className="font-medium">Onde</span>
          <select className="mt-1 rounded border border-neutral-400 px-2 py-1" value={tipo} onChange={(e) => setTipo(e.target.value)}><option value="">andamentos e documentos</option><option value="andamento">só andamentos</option><option value="documento">só documentos</option></select></label>
        <label className="flex flex-col"><span className="font-medium">Processo</span>
          <select className="mt-1 rounded border border-neutral-400 px-2 py-1" value={inc} onChange={(e) => setInc(e.target.value)}><option value="">todos</option>{processos.map((p) => <option key={p.incidente} value={String(p.incidente)}>{p.rotulo}</option>)}</select></label>
        <p role="status" className="text-neutral-700">{!indice ? (erro ? `erro ao carregar o índice: ${erro}` : "carregando índice…") : q.trim().length < 2 ? "digite ao menos 2 caracteres" : `${resultados.length} resultado(s)`}</p>
      </form>
      <ol className="mt-3 space-y-2">
        {resultados.map(({ e }) => (
          <li key={`${e.tipo}:${e.id}`} className="rounded border border-neutral-300 bg-white p-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded bg-neutral-200 px-2 py-0.5 text-xs font-semibold">{e.tipo}</span>
              <span className="text-xs text-neutral-700">{rotulo(e.incidente)}</span>
              {e.data && <time className="font-mono text-xs" dateTime={e.data}>{formatarData(e.data)}</time>}
              {e.decisao && <span className="rounded bg-blue-800 px-2 py-0.5 text-xs font-semibold text-white">decisão</span>}
            </div>
            <p className="mt-1 font-medium">
              {e.tipo === "andamento" ? (
                <Link className="underline" href={`/processo/${e.incidente}#andamento-${e.id}`}>{e.titulo}</Link>
              ) : (
                <Link className="underline" href={`/documento/${e.documento_id}#p-${e.pagina}`}>{e.titulo} · p. {e.pagina}{e.secao ? ` · ${e.secao}` : ""}</Link>
              )}
            </p>
            <p className="mt-1 whitespace-pre-line text-neutral-800">{destacar(e.texto)}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}
