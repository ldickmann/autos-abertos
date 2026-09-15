import { Suspense } from "react";
import { ListaDecisoes } from "@/components/ListaDecisoes";
import { PontosChave } from "@/components/PontosChave";
import { formatarData, getDecisoes, getGlossario, getProcessos, verbeteDe } from "@/lib/data";

export default function PaginaDecisoes() {
  const d = getDecisoes();
  const processos = getProcessos().filter((p) => p.coletado && p.incidente).map((p) => ({ incidente: p.incidente as number, rotulo: `${p.classe} ${p.numero}` }));
  const verbetes = Object.fromEntries(Object.entries(d.rotulos_resultado).map(([k, r]) => [k, verbeteDe(r.split(" (")[0]) ?? verbeteDe(k)]));
  const docs = new Set(d.itens.map((i) => i.documento_id)).size;
  const rotuloProc = new Map(processos.map((p) => [p.incidente, p.rotulo]));
  const por = (k: string) => d.itens.filter((i) => i.resultado === k).length;
  const conta = (f: (i: (typeof d.itens)[number]) => string | null | undefined) => {
    const m = new Map<string, number>();
    for (const i of d.itens) { const v = f(i); if (v) m.set(v, (m.get(v) ?? 0) + 1); }
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  };
  const ultima = d.itens.filter((i) => i.data).sort((a, b) => (b.data ?? "").localeCompare(a.data ?? ""))[0];
  const prisoes = d.itens.filter((i) => /pris[ãa]o preventiva/i.test(i.pedido)).length;
  const pediram = conta((i) => i.quem_pediu?.replace(/\s*\(.*$/, "").replace(/,.*$/, "")).filter(([q]) => !/^o próprio relator/i.test(q)).slice(0, 3);
  const decidiram = conta((i) => i.quem_decidiu?.replace(/\s*\(.*$/, "")).slice(0, 2);
  const pontos = [
    { texto: <>São <strong>{d.itens.length} pedidos</strong> em {docs} decisões, despachos e votos: {por("deferido")} aceitos, {por("indeferido")} negados, {por("parcialmente_deferido")} aceitos em parte, {por("referendado")} referendados pela Turma e {por("determinado_de_oficio")} determinados de ofício pelo relator.</> },
    { texto: <><strong>{prisoes} itens tratam de prisão preventiva</strong> (decretação, referendo, pedidos de revogação e condições de custódia).</> },
    ...(ultima ? [{ texto: <>Decisão mais recente: <strong>{formatarData(ultima.data)}</strong>, {rotuloProc.get(ultima.incidente) ?? ""} — {d.rotulos_resultado[ultima.resultado] ?? ultima.resultado}: {ultima.pedido.slice(0, 140)}{ultima.pedido.length > 140 ? "…" : ""}</>, fonte: { href: `/documento/${ultima.documento_id}#p-${ultima.pagina}`, rotulo: `${ultima.titulo_documento} p. ${ultima.pagina}` } }] : []),
    { texto: <>Quem mais pediu (fora o próprio relator): {pediram.map(([q, n]) => `${q} (${n})`).join(", ")}. Quem decidiu: {decidiram.map(([q, n]) => `${q} (${n})`).join(", ")}.</> },
  ];
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
      <PontosChave itens={pontos} nota="Contagens da própria lista; os rótulos de resultado são os do glossário. Use os filtros abaixo por processo, resultado e quem pediu." />
      <Suspense>
        <ListaDecisoes itens={d.itens} rotulos={d.rotulos_resultado} processos={processos} verbetes={verbetes} glossario={getGlossario()} />
      </Suspense>
    </div>
  );
}
