import Link from "next/link";
import { PontosChave } from "@/components/PontosChave";
import { getMudancas } from "@/lib/data";
import { formatarDataHora } from "@/lib/tipos";

/* O que mudou no portal entre uma cópia e outra: só "sumiu", "apareceu", "mudou", com as duas cópias nomeadas. */
export default function PaginaMudancas() {
  const historico = [...getMudancas()].reverse();
  const totalRodadas = historico.length;
  const somaMud = (r: (typeof historico)[number]) => r.processos.reduce((n, p) => n + p.resumo.sumiu + p.resumo.apareceu + p.resumo.mudou, 0);
  const ultima = historico[0];
  const totalMudancas = historico.reduce((n, r) => n + somaMud(r), 0);
  const sumiram = historico.reduce((n, r) => n + r.processos.reduce((m, p) => m + p.resumo.sumiu, 0), 0);
  const pontos = [
    { texto: <><strong>{totalRodadas} rodadas</strong> de recoleta{ultima ? `; a última em ${formatarDataHora(ultima.em)}, com ${ultima.processos.length} processos e ${somaMud(ultima) === 0 ? "nenhuma mudança" : `${somaMud(ultima)} mudança(s)`}` : ""}.</> },
    { texto: <>No total, {totalMudancas} mudanças detectadas; <strong>{sumiram === 0 ? "nada sumiu do portal" : `${sumiram} item(ns) sumiram do portal`}</strong> entre uma cópia e outra.</> },
    { texto: <>O que isso vigia: se um andamento, uma parte ou uma petição desaparecer, ou se um processo virar sigiloso, fica registrado aqui com as duas cópias nomeadas.</> },
  ];
  return (
    <div className="space-y-6">
      <header className="max-w-3xl">
        <h1 className="text-2xl">O que mudou no portal</h1>
        <p className="leitura mt-1">
          De tempos em tempos, cada processo é copiado de novo do portal do STF e comparado com a cópia anterior. Se um andamento,
          uma parte ou uma petição deixar de aparecer, ou se um campo do cabeçalho mudar (por exemplo, o processo virar sigiloso),
          isso fica registrado aqui, com as duas cópias nomeadas. Nada é interpretado: a lista diz o que sumiu, o que apareceu e o que mudou.
        </p>
        <p className="mt-1 text-sm text-neutral-700">
          {totalRodadas} rodada(s) de verificação até agora. O registro completo, que só cresce, está em <code>CHANGELOG-PORTAL.md</code> no repositório.
          Para conferir uma cópia com o próprio STF, veja <Link className="underline" href="/verificar">Verificar</Link>.
        </p>
      </header>
      <PontosChave itens={pontos} />

      {historico.length === 0 && <p className="text-sm">Ainda não houve recoleta depois da primeira cópia.</p>}

      {historico.map((rodada) => {
        const total = rodada.processos.reduce((n, p) => n + p.resumo.sumiu + p.resumo.apareceu + p.resumo.mudou, 0);
        return (
          <section key={rodada.em} className="folha border border-neutral-300 bg-white p-4">
            <h2 className="text-lg">{formatarDataHora(rodada.em)} <span className="text-sm font-normal text-neutral-700">{rodada.processos.length} processos recoletados, {total === 0 ? "nenhuma mudança" : `${total} mudança(s)`}</span></h2>
            <ul className="mt-2 space-y-2 text-sm">
              {rodada.processos.map((p) => (
                <li key={p.incidente}>
                  <span className="font-semibold"><Link className="underline" href={`/processo/${p.incidente}`}>{p.processo}</Link></span>
                  {p.mudancas.length === 0 ? (
                    <span className="text-neutral-700"> — sem mudanças (cópias {p.antes ?? "—"} → {p.depois})</span>
                  ) : (
                    <>
                      <span className="text-neutral-700"> — {p.resumo.apareceu} apareceu, {p.resumo.sumiu} sumiu, {p.resumo.mudou} mudou (cópias {p.antes ?? "—"} → {p.depois})</span>
                      <ul className="mt-1 list-disc pl-6">
                        {p.mudancas.map((m, i) => (
                          <li key={i}><span className={`rounded-sm border px-1 text-xs ${m.mudanca === "sumiu" ? "border-amber-700 bg-amber-100 text-amber-900" : m.mudanca === "apareceu" ? "border-emerald-700 bg-emerald-100 text-emerald-900" : "border-sky-800 bg-sky-100 text-sky-900"}`}>{m.o_que} {m.mudanca}</span> {m.item}</li>
                        ))}
                      </ul>
                    </>
                  )}
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
