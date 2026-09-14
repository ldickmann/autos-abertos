import Link from "next/link";
import { StatusProcessual } from "@/components/Badges";
import { getEntidades } from "@/lib/data";

export default function PaginaEntidades() {
  const ents = getEntidades().slice().sort((a, b) => b.mencoes.length - a.mencoes.length || a.nome.localeCompare(b.nome));
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Entidades <span className="text-base font-normal text-neutral-700">({ents.length}: partes, advogados e citados em documentos)</span></h1>
      <p className="text-sm text-neutral-700">Status processual sempre literal do portal do STF. Nenhum rótulo é atribuído pelo sistema.</p>
      <div className="overflow-x-auto">
        <table className="tabela-responsiva w-full min-w-[720px] border-collapse text-sm">
          <thead><tr className="border-b border-neutral-400 text-left"><th scope="col" className="py-2 pr-3">Nome</th><th scope="col" className="py-2 pr-3">Tipo</th><th scope="col" className="py-2 pr-3">Processos e status</th><th scope="col" className="py-2 pr-3">Asserções</th></tr></thead>
          <tbody>
            {ents.map((e) => (
              <tr key={e.id} className="border-b border-neutral-200 align-top">
                <td data-rotulo="Nome" className="py-2 pr-3"><Link className="underline" href={`/entidade/${e.id}`}>{e.nome}</Link></td>
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
