"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { StatusProcessual } from "@/components/Badges";
import { CampoProcurar, Contagem, MostrarMais, Vazio, casa, usePaginar } from "@/components/Filtros";
import { nomeProprio, type Entidade } from "@/lib/tipos";

/*
  Quem é quem, com filtro: por nome, por papel nos autos (investigado, requerido…), por tipo e por processo.
  A ordem é a de quem mais aparece; cada linha vira cartão no celular (tabela-responsiva).
*/
const ROTULO_TIPO: Record<string, string> = { parte: "parte em processo", advogado: "advogado", orgao: "órgão", pessoa: "pessoa", empresa: "empresa" };

export function ListaEntidades({ entidades }: { entidades: Entidade[] }) {
  const [busca, setBusca] = useState("");
  const [status, setStatus] = useState("");
  const [tipo, setTipo] = useState("");
  const [processo, setProcesso] = useState("");
  const statusLista = useMemo(() => [...new Set(entidades.flatMap((e) => e.mencoes.map((m) => m.status_processual)))].sort(), [entidades]);
  const tipos = useMemo(() => [...new Set(entidades.map((e) => e.tipo))].sort(), [entidades]);
  const processos = useMemo(() => [...new Set(entidades.flatMap((e) => e.mencoes.map((m) => m.processo).filter((p): p is string => !!p)))].sort(), [entidades]);
  const filtradas = useMemo(() => entidades.filter((e) =>
    (!status || e.mencoes.some((m) => m.status_processual === status))
    && (!tipo || e.tipo === tipo)
    && (!processo || e.mencoes.some((m) => m.processo === processo))
    && casa(busca, e.nome, e.tipo, ...e.mencoes.map((m) => `${m.processo ?? ""} ${m.status_processual}`))), [entidades, busca, status, tipo, processo]);
  const { visiveis, restantes, mais } = usePaginar(filtradas, 80);
  const ativo = !!(busca || status || tipo || processo);
  const limpar = () => { setBusca(""); setStatus(""); setTipo(""); setProcesso(""); };
  return (
    <div className="space-y-3">
      <form className="folha grid min-w-0 gap-3 border border-neutral-300 bg-white p-3 text-sm sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_1fr]" onSubmit={(ev) => ev.preventDefault()} aria-label="Filtros de pessoas e órgãos">
        <CampoProcurar valor={busca} onChange={setBusca} rotulo="Procurar por nome" placeholder="ex.: Vorcaro, Banco Central, Super" className="sm:col-span-2 lg:col-span-1" />
        <label className="flex min-w-0 flex-col"><span className="font-medium">Papel nos autos</span>
          <select className="mt-1 w-full min-w-0 rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={status} onChange={(ev) => setStatus(ev.target.value)}>
            <option value="">qualquer</option>{statusLista.map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
        <label className="flex min-w-0 flex-col"><span className="font-medium">Tipo</span>
          <select className="mt-1 w-full min-w-0 rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={tipo} onChange={(ev) => setTipo(ev.target.value)}>
            <option value="">todos</option>{tipos.map((t) => <option key={t} value={t}>{ROTULO_TIPO[t] ?? t}</option>)}</select></label>
        <label className="flex min-w-0 flex-col"><span className="font-medium">Processo</span>
          <select className="mt-1 w-full min-w-0 rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={processo} onChange={(ev) => setProcesso(ev.target.value)}>
            <option value="">todos</option>{processos.map((p) => <option key={p} value={p}>{p}</option>)}</select></label>
        <Contagem n={filtradas.length} total={entidades.length} rotulo="nomes" ativo={ativo} onLimpar={limpar} className="sm:col-span-2 lg:col-span-4" />
      </form>
      {filtradas.length === 0 ? <Vazio onLimpar={limpar} dica="Nenhum nome com esses filtros." /> : (
        <div className="overflow-x-auto">
          <table className="tabela-responsiva w-full min-w-[720px] border-collapse text-sm">
            <thead><tr className="border-b border-neutral-400 text-left"><th scope="col" className="py-2 pr-3">Nome</th><th scope="col" className="py-2 pr-3">Tipo</th><th scope="col" className="py-2 pr-3">Processos e papel</th><th scope="col" className="py-2 pr-3">Afirmações</th></tr></thead>
            <tbody>
              {visiveis.map((e) => (
                <tr key={e.id} className="border-b border-neutral-200 align-top">
                  <td data-rotulo="Nome" className="py-2 pr-3"><Link className="underline" href={`/entidade/${e.id}`} title={`No portal: ${e.nome}`}>{nomeProprio(e.nome)}</Link></td>
                  <td data-rotulo="Tipo" className="py-2 pr-3">{ROTULO_TIPO[e.tipo] ?? e.tipo}{e.origem === "documento" ? " (citado em documento)" : ""}</td>
                  <td data-rotulo="Processos e papel" className="py-2 pr-3">
                    <ul className="flex flex-wrap gap-1">
                      {e.mencoes.map((m, i) => (<li key={i} className="flex items-center gap-1"><StatusProcessual status={m.status_processual} literal={m.papel_portal} /><span className="text-xs">{m.processo}</span></li>))}
                    </ul>
                  </td>
                  <td data-rotulo="Afirmações" data-vazio={e.assercoes ? undefined : "true"} className="py-2 pr-3 tabular-nums">{e.assercoes || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <MostrarMais restantes={restantes} onMais={mais} rotulo="nomes" />
    </div>
  );
}
