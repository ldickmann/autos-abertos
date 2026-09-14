import { Suspense } from "react";
import { ListaDecisoes } from "@/components/ListaDecisoes";
import { getDecisoes, getGlossario, getProcessos, verbeteDe } from "@/lib/data";

export default function PaginaDecisoes() {
  const d = getDecisoes();
  const processos = getProcessos().filter((p) => p.coletado && p.incidente).map((p) => ({ incidente: p.incidente as number, rotulo: `${p.classe} ${p.numero}` }));
  const verbetes = Object.fromEntries(Object.entries(d.rotulos_resultado).map(([k, r]) => [k, verbeteDe(r.split(" (")[0]) ?? verbeteDe(k)]));
  const docs = new Set(d.itens.map((i) => i.documento_id)).size;
  return (
    <div className="space-y-4">
      <header className="max-w-3xl">
        <h1 className="text-2xl">O que já foi decidido</h1>
        <p className="leitura mt-1">
          Cada decisão do STF responde a pedidos: alguém pede algo (a Polícia Federal, a Procuradoria, a defesa) e o ministro ou a Turma
          aceita, nega ou determina outra coisa. Esta página lista, pedido por pedido, o que foi pedido, quem pediu e o que foi decidido,
          em {d.itens.length} itens tirados de {docs} decisões, despachos e votos. Cada item mostra a página e o trecho literal do documento de onde saiu.
        </p>
        <p className="mt-1 text-sm text-neutral-700">
          Os textos são transcrições neutras do que o documento diz; não há resumo nem opinião. Clique num resultado sublinhado para ver o que a palavra significa.
        </p>
      </header>
      <Suspense>
        <ListaDecisoes itens={d.itens} rotulos={d.rotulos_resultado} processos={processos} verbetes={verbetes} glossario={getGlossario()} />
      </Suspense>
    </div>
  );
}
