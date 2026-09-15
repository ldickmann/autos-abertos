"use client";

import { useMemo, useState } from "react";
import { CampoProcurar, Contagem, Vazio, casa } from "@/components/Filtros";
import type { Verbete } from "@/lib/tipos";

/* Glossário com procura: pelo termo, pela explicação e pelas formas em que ele aparece nos autos. */
export function ListaGlossario({ verbetes }: { verbetes: Verbete[] }) {
  const [busca, setBusca] = useState("");
  const lista = useMemo(() => verbetes.filter((v) => casa(busca, v.termo, v.explicacao, v.mais, ...v.formas)), [verbetes, busca]);
  return (
    <div className="space-y-3">
      <form className="folha grid min-w-0 gap-3 border border-neutral-300 bg-white p-3 text-sm sm:grid-cols-[2fr_1fr] sm:items-end" onSubmit={(ev) => ev.preventDefault()} aria-label="Procurar no glossário">
        <CampoProcurar valor={busca} onChange={setBusca} rotulo="Procurar um termo" placeholder="ex.: preventiva, agravo, sigilo" />
        <Contagem n={lista.length} total={verbetes.length} rotulo="termos" ativo={!!busca} onLimpar={() => setBusca("")} />
      </form>
      {lista.length === 0 ? <Vazio onLimpar={() => setBusca("")} dica="Nenhum termo com essa palavra." /> : (
        <dl className="grid gap-3 md:grid-cols-2">
          {lista.map((v) => (
            <div key={v.termo} id={v.termo.toLowerCase().replace(/[^a-z0-9]+/g, "-")} className="folha border border-neutral-300 bg-white p-3">
              <dt className="font-semibold">{v.termo}</dt>
              <dd className="leitura mt-1 text-sm">{v.explicacao}{v.mais ? <span className="mt-1 block text-neutral-700">{v.mais}</span> : null}</dd>
              {v.formas.length > 0 && <dd className="mt-1 text-xs text-neutral-600">no portal e nos documentos: {v.formas.join(", ")}</dd>}
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}
