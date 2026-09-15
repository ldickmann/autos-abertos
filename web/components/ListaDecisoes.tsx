"use client";

import Link from "next/link";
import { Contagem, Vazio } from "@/components/Filtros";
import { useEffect, useMemo, useState } from "react";
import { Termo } from "@/components/Termo";
import type { Decisao, Verbete } from "@/lib/tipos";
import { formatarData } from "@/lib/tipos";

const COR_RESULTADO: Record<string, string> = {
  deferido: "bg-emerald-100 text-emerald-900 border-emerald-700",
  parcialmente_deferido: "bg-emerald-100 text-emerald-900 border-emerald-700",
  homologado: "bg-emerald-100 text-emerald-900 border-emerald-700",
  referendado: "bg-sky-100 text-sky-900 border-sky-800",
  determinado_de_oficio: "bg-sky-100 text-sky-900 border-sky-800",
  indeferido: "bg-amber-100 text-amber-900 border-amber-700",
  negado_seguimento: "bg-amber-100 text-amber-900 border-amber-700",
  nao_conhecido: "bg-amber-100 text-amber-900 border-amber-700",
  prejudicado: "bg-neutral-100 text-neutral-900 border-neutral-400",
  outro: "bg-neutral-100 text-neutral-900 border-neutral-400",
};

function normalizar(s: string): string {
  return s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

/* Verbetes cujas formas aparecem dentro do texto de uma condição (ex.: "recolhimento domiciliar noturno" → Recolhimento domiciliar). */
function verbetesNoTexto(texto: string, glossario: Verbete[]): Verbete[] {
  const t = normalizar(texto);
  const achados: Verbete[] = [];
  for (const v of glossario) {
    if (v.contexto !== "condicao") continue;   // só verbetes escritos para explicar condições de medidas cautelares
    if (v.formas.some((f) => f.length >= 6 && t.includes(normalizar(f))) && !achados.includes(v)) achados.push(v);
  }
  return achados.slice(0, 2);
}

export function ListaDecisoes({ itens, rotulos, processos, verbetes, glossario = [], compacta = false, incidenteFixo }: {
  itens: Decisao[]; rotulos: Record<string, string>; processos: { incidente: number; rotulo: string }[];
  verbetes: Record<string, Verbete | null>; glossario?: Verbete[]; compacta?: boolean; incidenteFixo?: number;
}) {
  const [processo, setProcesso] = useState<number | "">(incidenteFixo ?? "");
  const [resultado, setResultado] = useState("");
  const [quem, setQuem] = useState("");
  const [busca, setBusca] = useState("");
  const [limite, setLimite] = useState(compacta ? 8 : 40);

  // filtro inicial por URL (?processo=...&resultado=...), para links vindos de outras páginas
  useEffect(() => {
    if (incidenteFixo) return;
    const q = new URLSearchParams(window.location.search);
    if (q.get("processo")) setProcesso(Number(q.get("processo")));
    if (q.get("resultado")) setResultado(q.get("resultado")!);
  }, [incidenteFixo]);

  const quemLista = useMemo(() => Array.from(new Set(itens.map((i) => i.quem_pediu).filter(Boolean) as string[])).sort(), [itens]);
  const filtrados = useMemo(() => {
    const q = busca.trim().toLowerCase();
    return itens.filter((i) => (!processo || i.incidente === processo) && (!resultado || i.resultado === resultado) && (!quem || i.quem_pediu === quem)
      && (!q || `${i.pedido} ${i.decisao} ${i.quem_pediu ?? ""} ${i.quem_decidiu}`.toLowerCase().includes(q)));
  }, [itens, processo, resultado, quem, busca]);
  const rotuloProc = new Map(processos.map((p) => [p.incidente, p.rotulo]));
  const contagemResultado = useMemo(() => {
    const c: Record<string, number> = {};
    for (const i of filtrados) c[i.resultado] = (c[i.resultado] ?? 0) + 1;
    return c;
  }, [filtrados]);

  return (
    <div className="space-y-3">
      {!compacta && (
        <form className="folha grid min-w-0 gap-3 border border-neutral-300 bg-white p-3 text-sm sm:grid-cols-2 lg:grid-cols-4" onSubmit={(ev) => ev.preventDefault()} aria-label="Filtros das decisões">
          <label className="flex min-w-0 flex-col"><span className="font-medium">Processo</span>
            <select className="mt-1 w-full min-w-0 rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={processo} onChange={(ev) => setProcesso(ev.target.value ? Number(ev.target.value) : "")}>
              <option value="">todos</option>{processos.map((p) => <option key={p.incidente} value={p.incidente}>{p.rotulo}</option>)}</select></label>
          <label className="flex min-w-0 flex-col"><span className="font-medium">Resultado</span>
            <select className="mt-1 w-full min-w-0 rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={resultado} onChange={(ev) => setResultado(ev.target.value)}>
              <option value="">qualquer</option>{Object.entries(rotulos).map(([k, r]) => <option key={k} value={k}>{r}</option>)}</select></label>
          <label className="flex min-w-0 flex-col"><span className="font-medium">Quem pediu</span>
            <select className="mt-1 w-full min-w-0 max-w-full rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={quem} onChange={(ev) => setQuem(ev.target.value)}>
              <option value="">qualquer um</option>{quemLista.map((q) => <option key={q} value={q}>{q.length > 60 ? q.slice(0, 57) + "…" : q}</option>)}</select></label>
          <label className="flex min-w-0 flex-col"><span className="font-medium">Procurar no pedido ou na decisão</span>
            <input className="mt-1 w-full min-w-0 rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={busca} onChange={(ev) => setBusca(ev.target.value)} placeholder="ex.: prisão, prazo, sigilo" /></label>
          <Contagem n={filtrados.length} total={itens.length} rotulo="decisões" ativo={!!(processo || resultado || quem || busca)} onLimpar={() => { setProcesso(""); setResultado(""); setQuem(""); setBusca(""); }} className="sm:col-span-2 lg:col-span-4">
            {Object.keys(contagemResultado).length > 0 ? ": " + Object.entries(contagemResultado).sort((a, b) => b[1] - a[1]).map(([k, n]) => `${n} ${rotulos[k] ?? k}`).join(", ") : ""}
          </Contagem>
        </form>
      )}

      <ol className="space-y-2">
        {filtrados.slice(0, limite).map((i) => (
          <li key={i.id} className="folha border border-neutral-300 bg-white p-3 text-sm">
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
              <time dateTime={i.data ?? undefined} className="font-mono text-xs font-semibold">{formatarData(i.data)}</time>
              {!incidenteFixo && <Link className="rounded-sm bg-neutral-900 px-1.5 py-px text-xs font-semibold text-neutral-50" href={`/processo/${i.incidente}`}>{rotuloProc.get(i.incidente) ?? i.incidente}</Link>}
              <Termo verbete={verbetes[i.resultado] ?? null}><span className={`carimbo rounded-sm border px-1.5 py-px text-xs font-medium ${COR_RESULTADO[i.resultado] ?? COR_RESULTADO.outro}`}>{rotulos[i.resultado] ?? i.resultado}</span></Termo>
            </div>
            <dl className="mt-2 grid gap-x-4 gap-y-1 sm:grid-cols-[auto_1fr]">
              <dt className="text-neutral-700">Pedido</dt><dd className="leitura">{i.pedido}{i.quem_pediu ? <span className="text-neutral-700"> — por {i.quem_pediu}</span> : null}</dd>
              <dt className="text-neutral-700">Decisão</dt><dd className="leitura">{i.decisao}<span className="text-neutral-700"> — {i.quem_decidiu}</span></dd>
              {i.condicoes.length > 0 && (<><dt className="text-neutral-700">Condições</dt><dd><ul className="list-disc pl-5">{i.condicoes.map((c, k) => {
                const vs = verbetesNoTexto(c, glossario);
                return (
                  <li key={k}>{c}{vs.length > 0 && <span className="block text-xs text-neutral-700">em linguagem simples: {vs.map((v, j) => <span key={v.termo}>{j > 0 ? " " : ""}<Termo verbete={{ ...v, fonte: "glossario" }}>{v.termo.toLowerCase()}</Termo> — {v.explicacao}</span>)}</span>}</li>
                );
              })}</ul></dd></>)}
            </dl>
            <details className="mt-2 text-xs">
              <summary className="cursor-pointer text-neutral-700">Fonte: {i.titulo_documento ?? "documento"} {i.documento_id}, p. {i.pagina}</summary>
              <blockquote className="leitura mt-1 border-l-2 border-neutral-400 pl-3 text-sm">“{i.trecho_fonte}”</blockquote>
              <p className="mt-1 flex flex-wrap items-center gap-x-3 text-neutral-600">
                <Link className="toque underline" href={`/documento/${i.documento_id}#p-${i.pagina}`}>Abrir o documento na página {i.pagina}</Link>
                <span>Trecho literal, conferido automaticamente. Extração {i.prompt_version}, {i.modelo}.</span>
              </p>
            </details>
          </li>
        ))}
      </ol>
      {filtrados.length > limite && (
        <p className="text-sm">
          <button type="button" className="toque rounded border border-neutral-400 px-3 py-1 hover:bg-neutral-100" onClick={() => setLimite((l) => l + (compacta ? 8 : 40))}>Mostrar mais ({filtrados.length - limite} restantes)</button>
          {compacta && incidenteFixo ? <Link className="ml-3 underline" href={`/decisoes?processo=${incidenteFixo}`}>ver todas com filtros</Link> : null}
        </p>
      )}
      {filtrados.length === 0 && (itens.length === 0 ? <p className="text-sm text-neutral-700">Ainda não há decisões extraídas para este processo.</p> : <Vazio onLimpar={() => { setProcesso(""); setResultado(""); setQuem(""); setBusca(""); }} dica="Nenhuma decisão com esses filtros." />)}
    </div>
  );
}
