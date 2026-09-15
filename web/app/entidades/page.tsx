import Link from "next/link";
import { StatusProcessual } from "@/components/Badges";
import { PontosChave } from "@/components/PontosChave";
import { getEntidades, nomeProprio } from "@/lib/data";

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
      <PontosChave itens={pontos} nota="Clique num nome para ver o que os autos dizem sobre ele — quem diz, em qual documento — e, se estiver na rede de pagamentos, quanto recebeu ou pagou." />
      <div className="overflow-x-auto">
        <table className="tabela-responsiva w-full min-w-[720px] border-collapse text-sm">
          <thead><tr className="border-b border-neutral-400 text-left"><th scope="col" className="py-2 pr-3">Nome</th><th scope="col" className="py-2 pr-3">Tipo</th><th scope="col" className="py-2 pr-3">Processos e status</th><th scope="col" className="py-2 pr-3">Asserções</th></tr></thead>
          <tbody>
            {ents.map((e) => (
              <tr key={e.id} className="border-b border-neutral-200 align-top">
                <td data-rotulo="Nome" className="py-2 pr-3"><Link className="underline" href={`/entidade/${e.id}`} title={`No portal: ${e.nome}`}>{nomeProprio(e.nome)}</Link></td>
                <td data-rotulo="Tipo" className="py-2 pr-3">{e.tipo}{e.origem === "documento" ? " (terceiro mencionado)" : ""}</td>
                <td data-rotulo="Processos e status" className="py-2 pr-3">
                  <ul className="flex flex-wrap gap-1">
                    {e.mencoes.map((m, i) => (<li key={i} className="flex items-center gap-1"><StatusProcessual status={m.status_processual} literal={m.papel_portal} /><span className="text-xs">{m.processo}</span></li>))}
                  </ul>
                </td>
                <td data-rotulo="Asserções" className="py-2 pr-3">{e.assercoes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
