import { LegendaEpistemica } from "@/components/Badges";
import { ListaAssercoes } from "@/components/ListaAssercoes";
import { PontosChave } from "@/components/PontosChave";
import { getAssercoes, getMeta, getProcessos } from "@/lib/data";

export default function PaginaAssercoes() {
  const meta = getMeta();
  const assercoes = getAssercoes();
  const processos = getProcessos().filter((p) => p.coletado && p.incidente);
  const por = (t: string) => assercoes.filter((a) => a.tipo_epistemico === t).length;
  const top = (t: string) => { const m = new Map<string, number>(); for (const a of assercoes) if (a.tipo_epistemico === t && a.atribuida_a) { const k = a.atribuida_a.replace(/\s*\(.*$/, ""); m.set(k, (m.get(k) ?? 0) + 1); } return [...m.entries()].sort((x, y) => y[1] - x[1]).slice(0, 3); };
  const docs = new Set(assercoes.map((a) => a.documento?.id)).size;
  const pontos = [
    { texto: <><strong>{assercoes.length} afirmações</strong> extraídas de {docs} documentos, cada uma com página e trecho literal conferido: {por("fato_processual")} fatos processuais, {por("alegacao_parte")} alegações de partes e {por("fundamento_decisorio")} fundamentos de decisão.</> },
    { texto: <>Quem mais alega: {top("alegacao_parte").map(([q, n]) => `${q} (${n})`).join(", ")}. Quem mais fundamenta: {top("fundamento_decisorio").map(([q, n]) => `${q} (${n})`).join(", ")}.</> },
    { texto: <>Uma alegação é a versão de quem a faz; um fundamento é o que o ministro afirma ao decidir; um fato processual é um registro do processo. A lista separa os três e diz quem fala.</> },
  ];
  return (
    <div className="space-y-4">
      <header className="max-w-3xl">
        <h1 className="text-2xl">O que os documentos afirmam, e quem afirma</h1>
        <p className="leitura mt-1">Cada afirmação foi extraída de uma peça dos autos e só entrou aqui se o trecho literal foi encontrado na página indicada.</p>
      </header>
      <PontosChave itens={pontos} />
      <LegendaEpistemica descricoes={meta.tipos_epistemicos} />
      {assercoes.length === 0 ? (
        <p className="rounded border border-amber-700 bg-amber-50 p-3 text-sm">
          A camada semântica (Fase 4) ainda não foi executada: nenhuma afirmação foi extraída dos documentos. Tudo o que o site
          mostra até aqui vem diretamente do portal, sem modelo de linguagem.
        </p>
      ) : (
        <ListaAssercoes assercoes={assercoes} processos={processos.map((p) => ({ incidente: p.incidente as number, rotulo: `${p.classe} ${p.numero}` }))} />
      )}
    </div>
  );
}
