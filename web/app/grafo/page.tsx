import { GrafoInterativo } from "@/components/GrafoInterativo";
import { getGrafo } from "@/lib/data";

export default function PaginaGrafo() {
  const g = getGrafo();
  const procs = g.nodes.filter((n) => n.tipo === "processo").length;
  const ents = g.nodes.filter((n) => n.tipo === "entidade").length;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Grafo <span className="text-base font-normal text-neutral-700">({procs} processos, {ents} entidades, {g.edges.length} arestas)</span></h1>
      <p className="text-sm text-neutral-700">
        Arestas entre processos vêm dos andamentos (prevenção, autuação). Arestas entre entidades e processos vêm do cadastro de partes, com o papel literal.
        Linhas tracejadas são coincidências de "Número de Origem", ligação fraca. Toda aresta tem proveniência no arquivo <code>grafo.json</code>.
        A tabela abaixo do grafo lista as mesmas arestas para leitura por teclado e leitor de tela.
      </p>
      <GrafoInterativo grafo={g} />
    </div>
  );
}
