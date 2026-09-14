"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { BadgeEpistemico } from "@/components/Badges";
import { useTelaLarga } from "@/lib/useTelaLarga";
import type { CronologiaDados, EventoCronologia, TipoEpistemico } from "@/lib/tipos";
import { formatarData } from "@/lib/tipos";

/* O que aconteceu, quando e segundo quem. Três origens, cada uma com sua marca:
   registro do portal (o que o STF registrou), o que os documentos dizem (com o tipo epistêmico e a quem é atribuído)
   e as decisões (pedido → resultado). Nada é fundido: cada linha mantém a origem e a fonte. */
const ROTULO_FONTE: Record<string, string> = { andamento: "registro do portal", assercao: "o documento diz", decisao: "decisão" };

export function Cronologia({ dados, processos, rotulosResultado }: { dados: CronologiaDados; processos: { incidente: number; rotulo: string }[]; rotulosResultado: Record<string, string> }) {
  const [tipos, setTipos] = useState<Set<string>>(() => new Set(["andamento", "assercao", "decisao"]));
  const [tipoEp, setTipoEp] = useState<"" | TipoEpistemico>("");
  const [procs, setProcs] = useState<Set<number>>(() => new Set(processos.map((p) => p.incidente)));
  const [de, setDe] = useState(dados.inicio_do_caso);
  const [ate, setAte] = useState("");
  const [busca, setBusca] = useState("");
  const [incluirReferencias, setIncluirReferencias] = useState(false);
  const [limite, setLimite] = useState(150);
  const telaLarga = useTelaLarga();
  const [filtrosAbertos, setFiltrosAbertos] = useState<boolean | null>(null);

  const alternar = <T,>(s: Set<T>, v: T) => { const n = new Set(s); if (n.has(v)) n.delete(v); else n.add(v); return n; };

  const eventos = useMemo(() => {
    const q = busca.trim().toLowerCase();
    return dados.eventos.filter((e) => tipos.has(e.tipo) && procs.has(e.incidente) && (!tipoEp || e.tipo !== "assercao" || e.tipo_epistemico === tipoEp)
      && (incluirReferencias || e.contexto === "caso") && (!de || e.data >= de) && (!ate || e.data <= ate)
      && (!q || `${e.texto} ${e.atribuida_a ?? ""} ${e.quem_pediu ?? ""} ${e.quem_decidiu ?? ""}`.toLowerCase().includes(q)));
  }, [dados, tipos, procs, tipoEp, de, ate, busca, incluirReferencias]);
  const porDia = useMemo(() => {
    const m = new Map<string, EventoCronologia[]>();
    for (const e of eventos) m.set(e.data, [...(m.get(e.data) ?? []), e]);
    return [...m.entries()].sort((a, b) => b[0].localeCompare(a[0]));
  }, [eventos]);
  let mostrados = 0;

  return (
    <div className="grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
      <aside className="min-w-0 text-sm">
        <details className="folha border border-neutral-300 bg-white p-3 lg:sticky lg:top-3" open={filtrosAbertos ?? telaLarga} onToggle={(ev) => setFiltrosAbertos(ev.currentTarget.open)}>
          <summary className="toque cursor-pointer font-semibold">Filtros <span className="font-normal text-neutral-600">· {eventos.length} de {dados.total}</span></summary>
          <form className="mt-2 space-y-3" onSubmit={(ev) => ev.preventDefault()} aria-label="Filtros da cronologia">
            <fieldset>
              <legend className="font-medium">Origem</legend>
              {(["andamento", "assercao", "decisao"] as const).map((t) => (
                <label key={t} className="flex items-center gap-2"><input type="checkbox" checked={tipos.has(t)} onChange={() => setTipos(alternar(tipos, t))} /> {ROTULO_FONTE[t]} <span className="text-xs text-neutral-600">{dados.eventos.filter((e) => e.tipo === t).length}</span></label>
              ))}
            </fieldset>
            <label className="block"><span className="font-medium">Quando é "o documento diz", de que tipo</span>
              <select className="mt-1 w-full rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={tipoEp} onChange={(ev) => setTipoEp(ev.target.value as "" | TipoEpistemico)}>
                <option value="">qualquer</option><option value="fato_processual">fato processual</option><option value="alegacao_parte">alegação de parte</option><option value="fundamento_decisorio">fundamento decisório</option>
              </select></label>
            <fieldset>
              <legend className="font-medium">Processos</legend>
              <ul className="mt-1 grid grid-cols-2 gap-x-2 gap-y-1 lg:grid-cols-1">
                {processos.map((p) => <li key={p.incidente}><label className="flex items-center gap-2"><input type="checkbox" checked={procs.has(p.incidente)} onChange={() => setProcs(alternar(procs, p.incidente))} /> {p.rotulo}</label></li>)}
              </ul>
            </fieldset>
            <div className="grid grid-cols-2 gap-2">
              <label className="flex min-w-0 flex-col"><span className="font-medium">De</span><input type="date" className="mt-1 w-full rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={de} onChange={(ev) => setDe(ev.target.value)} /></label>
              <label className="flex min-w-0 flex-col"><span className="font-medium">Até</span><input type="date" className="mt-1 w-full rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={ate} onChange={(ev) => setAte(ev.target.value)} /></label>
            </div>
            <label className="flex items-center gap-2"><input type="checkbox" checked={incluirReferencias} onChange={(ev) => setIncluirReferencias(ev.target.checked)} /> incluir datas de jurisprudência e leis citadas (antes de {formatarData(dados.inicio_do_caso)})</label>
            <label className="block"><span className="font-medium">Procurar</span><input className="mt-1 w-full rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={busca} onChange={(ev) => setBusca(ev.target.value)} placeholder="ex.: liquidação, prisão, sigilo" /></label>
          </form>
        </details>
      </aside>

      <ol className="linha-tempo relative ml-5 min-w-0 border-l-2 border-neutral-400 pl-5">
        {porDia.map(([dia, lista]) => {
          if (mostrados >= limite) return null;
          mostrados += lista.length;
          return (
            <li key={dia} data-decisao={lista.some((e) => e.tipo === "decisao" || e.categoria === "decisao")} className="relative mb-5">
              <time dateTime={dia} className="font-mono text-sm font-semibold">{formatarData(dia)}</time>
              <ul className="mt-1 space-y-2">
                {lista.map((e, i) => (
                  <li key={i} className="folha border border-neutral-300 bg-white p-3 text-sm">
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
                      <span className={`rounded-sm px-1.5 py-px font-medium ${e.tipo === "andamento" ? "bg-neutral-900 text-neutral-50" : e.tipo === "decisao" ? "bg-blue-800 text-white" : "border border-neutral-400"}`}>{ROTULO_FONTE[e.tipo]}</span>
                      <Link className="underline" href={`/processo/${e.incidente}`}>{e.processo}</Link>
                      {e.tipo === "assercao" && e.tipo_epistemico && <BadgeEpistemico tipo={e.tipo_epistemico} />}
                      {e.tipo === "assercao" && e.atribuida_a && <span className="text-neutral-700">segundo {e.atribuida_a}</span>}
                      {e.tipo === "decisao" && e.resultado && <span className="rounded-sm border border-neutral-400 px-1.5 py-px">{rotulosResultado[e.resultado] ?? e.resultado}</span>}
                      {e.contexto === "referencia" && <span className="text-neutral-600">referência citada</span>}
                    </div>
                    <p className="leitura mt-1">{e.texto}{e.tipo === "decisao" && e.quem_decidiu ? <span className="text-neutral-700"> — {e.quem_decidiu}</span> : null}</p>
                    {e.tipo === "assercao" && (
                      <details className="mt-1 text-xs">
                        <summary className="cursor-pointer text-neutral-700">Fonte: {e.titulo_documento ?? "documento"} {e.documento_id}, p. {e.pagina} (data “{e.literal}” no trecho)</summary>
                        <blockquote className="leitura mt-1 border-l-2 border-neutral-400 pl-3 text-sm">“{e.trecho_fonte}”</blockquote>
                        <Link className="toque underline" href={`/documento/${e.documento_id}#p-${e.pagina}`}>Abrir o documento na página {e.pagina}</Link>
                      </details>
                    )}
                    {e.tipo === "decisao" && <p className="mt-1 text-xs text-neutral-700"><Link className="toque underline" href={`/documento/${e.documento_id}#p-${e.pagina}`}>{e.titulo_documento ?? "documento"} {e.documento_id}, p. {e.pagina}</Link></p>}
                    {e.tipo === "andamento" && <p className="mt-1 text-xs text-neutral-700"><Link className="toque underline" href={`/processo/${e.incidente}#andamento-${e.andamento_id}`}>ver no processo</Link></p>}
                  </li>
                ))}
              </ul>
            </li>
          );
        })}
        {eventos.length === 0 && <li className="text-sm">Nada com esses filtros.</li>}
      </ol>
      {eventos.length > limite && <p className="text-sm lg:col-start-2"><button type="button" className="toque rounded border border-neutral-400 px-3 py-1 hover:bg-neutral-100" onClick={() => setLimite((l) => l + 150)}>Mostrar mais ({eventos.length - limite} restantes)</button></p>}
    </div>
  );
}
