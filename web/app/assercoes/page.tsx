import { LegendaEpistemica } from "@/components/Badges";
import { ListaAssercoes } from "@/components/ListaAssercoes";
import { getAssercoes, getMeta, getProcessos } from "@/lib/data";

export default function PaginaAssercoes() {
  const meta = getMeta();
  const assercoes = getAssercoes();
  const processos = getProcessos().filter((p) => p.coletado && p.incidente);
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Asserções <span className="text-base font-normal text-neutral-700">({assercoes.length})</span></h1>
      <LegendaEpistemica descricoes={meta.tipos_epistemicos} />
      {assercoes.length === 0 ? (
        <p className="rounded border border-amber-700 bg-amber-50 p-3 text-sm">
          A camada semântica (Fase 4) ainda não foi executada: nenhuma asserção foi extraída dos documentos. Tudo o que o site
          mostra até aqui vem diretamente do portal, sem modelo de linguagem.
        </p>
      ) : (
        <ListaAssercoes assercoes={assercoes} processos={processos.map((p) => ({ incidente: p.incidente as number, rotulo: `${p.classe} ${p.numero}` }))} />
      )}
    </div>
  );
}
