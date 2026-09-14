import { LinhaTempoCaso } from "@/components/LinhaTempoCaso";
import { getLinhaTempo, getProcessos } from "@/lib/data";

export default function PaginaLinhaDoTempo() {
  const lt = getLinhaTempo();
  const processos = getProcessos().filter((p) => p.coletado && p.incidente).map((p) => ({ incidente: p.incidente as number, rotulo: `${p.classe} ${p.numero}` }));
  const decisoes = lt.eventos.filter((e) => e.e_decisao).length;
  return (
    <div className="space-y-4">
      <header className="max-w-3xl">
        <h1 className="text-2xl">Linha do tempo do caso</h1>
        <p className="mt-1 text-sm text-neutral-700">
          Os {lt.eventos.length} andamentos dos {processos.length} processos coletados, num fio só, do mais recente ao mais antigo; {decisoes} são decisões.
          Começa mostrando decisões, julgamentos e recursos; marque as outras categorias para ver petições, comunicações e a movimentação interna.
          A categoria é um rótulo curado sobre o tipo literal do portal, que fica sempre visível.
        </p>
      </header>
      <LinhaTempoCaso dados={lt} processos={processos} />
    </div>
  );
}
