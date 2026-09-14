import { Busca } from "@/components/Busca";
import { PontosChave } from "@/components/PontosChave";
import { getMeta, getProcessos } from "@/lib/data";

export default function PaginaBusca() {
  const processos = getProcessos().filter((p) => p.coletado && p.incidente).map((p) => ({ incidente: p.incidente as number, rotulo: `${p.classe} ${p.numero}` }));
  const meta = getMeta();
  const pontos = [
    { texto: <>Procura em <strong>{meta.contagens.busca} registros</strong>: andamentos de {processos.length} processos e o texto integral de {meta.contagens.documentos} documentos, página a página. Acentos são ignorados.</> },
    { texto: <>Bons pontos de partida: um nome (&quot;Zettel&quot;), uma empresa (&quot;Super Empreendimentos&quot;), um tema (&quot;prisão preventiva&quot;, &quot;liquidação&quot;), um número de e-Doc.</> },
    { texto: <>Cada resultado leva ao andamento ou à página exata do documento, onde o trecho pode ser conferido e o PDF, autenticado no STF.</> },
  ];
  return (
    <div className="space-y-4">
      <header className="max-w-3xl">
        <h1 className="text-2xl">Buscar nos autos</h1>
        <p className="leitura mt-1">Busca textual sobre os andamentos e o texto integral dos documentos baixados.</p>
      </header>
      <PontosChave titulo="O que você encontra aqui" itens={pontos} />
      <Busca processos={processos} />
    </div>
  );
}
