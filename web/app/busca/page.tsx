import { Busca } from "@/components/Busca";
import { getProcessos } from "@/lib/data";

export default function PaginaBusca() {
  const processos = getProcessos().filter((p) => p.coletado && p.incidente).map((p) => ({ incidente: p.incidente as number, rotulo: `${p.classe} ${p.numero}` }));
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Busca</h1>
      <p className="text-sm text-neutral-700">Busca textual sobre os andamentos e o texto integral dos documentos baixados. Acentos são ignorados. Cada resultado leva ao andamento ou à página do documento.</p>
      <Busca processos={processos} />
    </div>
  );
}
