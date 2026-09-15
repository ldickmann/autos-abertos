import { ListaEntidades } from "@/components/ListaEntidades";
import { PontosChave } from "@/components/PontosChave";
import { getEntidades } from "@/lib/data";

export default function PaginaEntidades() {
  const ents = getEntidades().slice().sort((a, b) => b.mencoes.length - a.mencoes.length || a.nome.localeCompare(b.nome));
  const comStatus = (s: string) => ents.filter((e) => e.mencoes.some((m) => m.status_processual === s));
  const investigados = comStatus("investigado"), requeridos = comStatus("requerido"), interessados = comStatus("interessado");
  const advogados = ents.filter((e) => e.tipo === "advogado").length;
  const citadas = ents.filter((e) => e.origem === "documento").length;
  const maisCitadas = [...ents].sort((a, b) => b.assercoes - a.assercoes).slice(0, 5);
  const pontos = [
    { texto: <><strong>{ents.length} pessoas, empresas e órgãos</strong>: {ents.length - advogados - citadas} partes cadastradas no portal, {advogados} advogados e {citadas} citados só em documentos.</> },
    { texto: <>Com status literal do portal: <strong>{investigados.length} investigados</strong> ({investigados.slice(0, 6).map((e) => e.nome).join(", ")}{investigados.length > 6 ? "…" : ""}), {requeridos.length} requeridos e {interessados.length} interessados.</> },
    { texto: <>Mais citados nas afirmações extraídas dos documentos: {maisCitadas.map((e) => `${e.nome} (${e.assercoes})`).join(", ")}.</> },
  ];
  return (
    <div className="space-y-4">
      <header className="max-w-3xl">
        <h1 className="text-2xl">Quem é quem no caso</h1>
        <p className="leitura mt-1">Todas as pessoas, empresas e órgãos que aparecem nos autos, com o status literal do portal do STF em cada processo (investigado, requerido, interessado, advogado). Nenhum rótulo é atribuído pelo site; um papel não significa culpa.</p>
      </header>
      <PontosChave itens={pontos} nota="Procure por nome ou filtre por papel, tipo e processo. Clique num nome para ver o que os autos dizem sobre ele — quem diz, em qual documento — e, se estiver na rede de pagamentos, quanto recebeu ou pagou." />
      <ListaEntidades entidades={ents} />
    </div>
  );
}
