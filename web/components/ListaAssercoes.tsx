"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { BadgeEpistemico } from "@/components/Badges";
import type { Assercao, TipoEpistemico } from "@/lib/tipos";
import { formatarData, nomeProprio } from "@/lib/tipos";
import { CampoProcurar, Contagem, MostrarMais, Vazio, casa, usePaginar } from "@/components/Filtros";

export function ListaAssercoes({ assercoes, processos }: { assercoes: Assercao[]; processos: { incidente: number; rotulo: string }[] }) {
  const [tipo, setTipo] = useState<"" | TipoEpistemico>("");
  const [inc, setInc] = useState("");
  const [de, setDe] = useState("");
  const [ate, setAte] = useState("");
  const [busca, setBusca] = useState("");
  const filtradas = useMemo(
    () =>
      assercoes.filter(
        (a) =>
          (!tipo || a.tipo_epistemico === tipo) &&
          (!inc || String(a.documento?.incidente) === inc) &&
          (!de || (a.data_andamento ?? "") >= de) &&
          (!ate || (a.data_andamento ?? "9999") <= ate) &&
          casa(busca, a.texto, a.atribuida_a, a.trecho_fonte, ...a.entidades.map((e) => e.nome)),
      ),
    [assercoes, tipo, inc, de, ate, busca],
  );
  const { visiveis, restantes, mais } = usePaginar(filtradas, 100);
  const ativo = !!(tipo || inc || de || ate || busca);
  const limpar = () => { setTipo(""); setInc(""); setDe(""); setAte(""); setBusca(""); };
  return (
    <div>
      <form className="grid grid-cols-2 gap-3 sm:flex sm:flex-wrap sm:items-end rounded border border-neutral-300 bg-white p-3 text-sm" onSubmit={(e) => e.preventDefault()} aria-label="Filtros das afirmações">
        <CampoProcurar valor={busca} onChange={setBusca} rotulo="Procurar" placeholder="ex.: prisão, Zettel, sigilo" className="col-span-2 sm:min-w-64 sm:grow" />
        <label className="col-span-2 flex flex-col sm:col-span-1"><span className="font-medium">Natureza</span>
          <select className="mt-1 w-full min-w-0 rounded border border-neutral-400 px-2 py-1" value={tipo} onChange={(e) => setTipo(e.target.value as "" | TipoEpistemico)}>
            <option value="">todos</option><option value="fato_processual">fato processual</option><option value="alegacao_parte">alegação de parte</option><option value="fundamento_decisorio">fundamento decisório</option>
          </select></label>
        <label className="col-span-2 flex flex-col sm:col-span-1"><span className="font-medium">Processo</span>
          <select className="mt-1 w-full min-w-0 rounded border border-neutral-400 px-2 py-1" value={inc} onChange={(e) => setInc(e.target.value)}>
            <option value="">todos</option>{processos.map((p) => <option key={p.incidente} value={String(p.incidente)}>{p.rotulo}</option>)}
          </select></label>
        <label className="flex flex-col"><span className="font-medium">De</span><input type="date" className="mt-1 w-full min-w-0 rounded border border-neutral-400 px-2 py-1" value={de} onChange={(e) => setDe(e.target.value)} /></label>
        <label className="flex flex-col"><span className="font-medium">Até</span><input type="date" className="mt-1 w-full min-w-0 rounded border border-neutral-400 px-2 py-1" value={ate} onChange={(e) => setAte(e.target.value)} /></label>
        <Contagem n={filtradas.length} total={assercoes.length} rotulo="afirmações" ativo={ativo} onLimpar={limpar} className="col-span-2" />
      </form>
      {filtradas.length === 0 && <div className="mt-3"><Vazio onLimpar={limpar} dica="Nenhuma afirmação com esses filtros." /></div>}
      <ol className="mt-3 space-y-2">
        {visiveis.map((a) => (
          <li key={a.id} className="rounded border border-neutral-300 bg-white p-3 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <BadgeEpistemico tipo={a.tipo_epistemico} />
              {a.data_andamento && <time dateTime={a.data_andamento} className="font-mono text-xs">{formatarData(a.data_andamento)}</time>}
              {a.documento && <span className="text-xs text-neutral-700">{processos.find((p) => p.incidente === a.documento?.incidente)?.rotulo}</span>}
            </div>
            <p className="mt-1">{a.texto}{a.atribuida_a ? <span className="text-neutral-700"> — atribuída a {a.atribuida_a}</span> : null}</p>
            <p className="text-xs text-neutral-700">
              fonte: <Link className="underline" href={`/documento/${a.documento?.id}#p-${a.pagina}`}>{a.documento?.titulo}, p. {a.pagina}</Link> — “{a.trecho_fonte}”
            </p>
            {a.entidades.length > 0 && <p className="text-xs">{a.entidades.map((e) => <Link key={e.entidade_id} className="mr-2 underline" href={`/entidade/${e.entidade_id}`} title={e.nome}>{nomeProprio(e.nome)}</Link>)}</p>}
          </li>
        ))}
      </ol>
      <div className="mt-3"><MostrarMais restantes={restantes} onMais={mais} rotulo="afirmações" /></div>
    </div>
  );
}
