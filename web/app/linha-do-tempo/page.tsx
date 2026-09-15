import { LinhaTempoCaso } from "@/components/LinhaTempoCaso";
import { PontosChave } from "@/components/PontosChave";
import { explicacoesPortalTodas, formatarData, getLinhaTempo, getProcessos, verbetesParaTipos } from "@/lib/data";

export default function PaginaLinhaDoTempo() {
  const lt = getLinhaTempo();
  const processos = getProcessos().filter((p) => p.coletado && p.incidente).map((p) => ({ incidente: p.incidente as number, rotulo: `${p.classe} ${p.numero}` }));
  const decisoes = lt.eventos.filter((e) => e.e_decisao).length;
  const verbetes = verbetesParaTipos(new Set(lt.eventos.map((e) => e.tipo)), explicacoesPortalTodas());
  const ordenados = [...lt.eventos].filter((e) => e.data).sort((a, b) => (b.data ?? "").localeCompare(a.data ?? ""));
  const ultimo = ordenados[0];
  const ultimaDecisao = ordenados.find((e) => e.e_decisao);
  const porProcesso = new Map<string, number>();
  for (const e of lt.eventos) porProcesso.set(e.processo, (porProcesso.get(e.processo) ?? 0) + 1);
  const maisMovido = [...porProcesso.entries()].sort((a, b) => b[1] - a[1])[0];
  const pontos = [
    { texto: <><strong>{lt.eventos.length} andamentos</strong> em {processos.length} processos, de {ordenados.at(-1)?.data ? formatarData(ordenados.at(-1)!.data) : "—"} a {ultimo ? formatarData(ultimo.data) : "—"}; {decisoes} são decisões.</> },
    ...(ultimaDecisao ? [{ texto: <>Última decisão registrada: <strong>{formatarData(ultimaDecisao.data)}</strong>, {ultimaDecisao.processo} — {ultimaDecisao.tipo}{ultimaDecisao.descricao ? `: ${ultimaDecisao.descricao.replace(/\s+/g, " ").slice(0, 160)}` : ""}.</>, fonte: { href: `/processo/${ultimaDecisao.incidente}#lt`, rotulo: "abrir no processo" } }] : []),
    ...(maisMovido ? [{ texto: <>Processo com mais movimentação: <strong>{maisMovido[0]}</strong> ({maisMovido[1]} andamentos).</> }] : []),
  ];
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
      <PontosChave itens={pontos} />
      <LinhaTempoCaso dados={lt} processos={processos} verbetes={verbetes} />
    </div>
  );
}
