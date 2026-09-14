import { GrafoInterativo } from "@/components/GrafoInterativo";
import { getGrafo, getMeta } from "@/lib/data";

export default function PaginaGrafo() {
  const g = getGrafo();
  const meta = getMeta();
  const procs = g.nodes.filter((n) => n.tipo === "processo" && !n.dados.externo).length;
  const externos = g.nodes.filter((n) => n.tipo === "processo" && n.dados.externo).length;
  const ents = g.nodes.filter((n) => n.tipo === "entidade").length;
  return (
    <div className="space-y-4">
      <header className="max-w-3xl">
        <h1 className="text-2xl">Grafo do caso</h1>
        <p className="mt-1 text-sm text-neutral-700">
          {procs} processos coletados, {externos} processos citados nos documentos, {ents} pessoas, órgãos e organizações, {g.edges.length} ligações.
          Cada ligação vem de um lugar verificável: um andamento, o cadastro de partes, uma página de documento ou uma asserção
          validada contra o texto. Nada é inferido. A ficha de cada nó mostra a fonte de cada traço.
        </p>
      </header>
      <GrafoInterativo grafo={g} semente={meta.semente} />
    </div>
  );
}
