import Link from "next/link";
import { PontosChave } from "@/components/PontosChave";
import { getProcessos, getReferencias } from "@/lib/data";

export default function PaginaReferencias() {
  const r = getReferencias();
  const rotulo = new Map(getProcessos().map((p) => [p.incidente, `${p.classe} ${p.numero}`]));
  const porDiploma = new Map<string, typeof r.dispositivos>();
  for (const d of r.dispositivos) porDiploma.set(d.diploma, [...(porDiploma.get(d.diploma) ?? []), d]);
  const diplomas = [...porDiploma.entries()].sort((a, b) => b[1].reduce((n, x) => n + x.documentos.length, 0) - a[1].reduce((n, x) => n + x.documentos.length, 0));
  const internos = r.processos_citados.filter((p) => p.incidente);
  const externos = r.processos_citados.filter((p) => !p.incidente);
  const topDiplomas = diplomas.slice(0, 4).map(([d, lista]) => `${d} (${lista.reduce((n, x) => n + x.documentos.length, 0)})`);
  const topDisp = [...r.dispositivos].sort((a, b) => b.documentos.length - a.documentos.length).slice(0, 3).map((d) => `${d.dispositivo} (${d.documentos.length})`);
  const pontos = [
    { texto: <><strong>{r.dispositivos.length} dispositivos legais</strong> citados; as leis mais invocadas: {topDiplomas.join(", ")}.</> },
    { texto: <>Artigos mais citados: {topDisp.join(", ")} — é a base legal em que as decisões se apoiam (prisão preventiva, medidas cautelares, competência).</> },
    { texto: <><strong>{r.processos_citados.length} processos citados</strong> no texto: {internos.length} são deste caso e {externos.length} são precedentes e habeas corpus de fora dele, ainda não coletados.</> },
  ];

  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <h1 className="text-2xl">Referências nos documentos</h1>
        <p className="mt-1 text-sm text-neutral-700">
          O que o texto dos documentos cita, extraído por expressão regular, com página e trecho: {r.dispositivos.length} dispositivos legais e {r.processos_citados.length} processos
          ({internos.length} deste caso, {externos.length} externos, como habeas corpus e precedentes). Serve para ver quais decisões se apoiam na mesma base legal e o que cada peça menciona.
        </p>
      </header>
      <PontosChave itens={pontos} />

      <section aria-labelledby="disp">
        <h2 id="disp" className="text-lg">Dispositivos legais citados</h2>
        <div className="mt-2 grid gap-3 md:grid-cols-2">
          {diplomas.map(([diploma, lista]) => (
            <details key={diploma} className="folha border border-neutral-300 bg-white p-3 text-sm" open={lista.length <= 6}>
              <summary className="cursor-pointer font-semibold">{diploma} <span className="font-normal text-neutral-600">{lista.length} artigo(s), {lista.reduce((n, x) => n + x.documentos.length, 0)} citação(ões) em documentos</span></summary>
              <ul className="mt-2 space-y-1">
                {lista.sort((a, b) => b.documentos.length - a.documentos.length).map((d) => (
                  <li key={d.dispositivo} className="flex flex-wrap items-baseline gap-x-2">
                    <span className="font-medium">art. {d.artigo}</span>
                    <span className="text-xs text-neutral-600">{d.documentos.length} doc(s)</span>
                    <span className="text-xs">
                      {d.documentos.slice(0, 8).map((x, i) => <span key={x.documento_id}>{i > 0 ? ", " : ""}<Link className="underline" href={`/documento/${x.documento_id}#p-${x.pagina}`}>{x.titulo ?? "doc"} {x.documento_id} ({rotulo.get(x.incidente) ?? x.incidente}, p. {x.pagina})</Link></span>)}
                      {d.documentos.length > 8 ? ` e mais ${d.documentos.length - 8}` : ""}
                    </span>
                  </li>
                ))}
              </ul>
            </details>
          ))}
        </div>
      </section>

      <section aria-labelledby="proc">
        <h2 id="proc" className="text-lg">Processos citados no texto</h2>
        <div className="mt-2 grid gap-3 md:grid-cols-2">
          <div className="folha border border-neutral-300 bg-white p-3 text-sm">
            <h3 className="font-semibold">Deste caso</h3>
            <div className="overflow-x-auto"><table className="mt-2 w-full border-collapse">
              <thead><tr className="border-b text-left"><th scope="col" className="py-1 pr-3">Processo</th><th scope="col" className="py-1 pr-3">Documentos</th><th scope="col" className="py-1 pr-3">Citado por</th></tr></thead>
              <tbody>{internos.map((p) => (
                <tr key={`${p.classe}${p.numero}`} className="border-b border-neutral-100">
                  <td className="py-1 pr-3"><Link className="underline" href={`/processo/${p.incidente}`}>{p.classe} {p.numero}</Link></td>
                  <td className="py-1 pr-3">{p.n_docs} ({p.n_ocorrencias} menções)</td>
                  <td className="py-1 pr-3 text-xs">{p.citado_por.map((i) => rotulo.get(i) ?? i).join(", ")}</td>
                </tr>
              ))}</tbody>
            </table></div>
          </div>
          <div className="folha border border-neutral-300 bg-white p-3 text-sm">
            <h3 className="font-semibold">Externos <span className="font-normal text-neutral-600">(não coletados: HCs, precedentes, outros feitos)</span></h3>
            <div className="overflow-x-auto"><table className="mt-2 w-full border-collapse">
              <thead><tr className="border-b text-left"><th scope="col" className="py-1 pr-3">Processo</th><th scope="col" className="py-1 pr-3">Documentos</th><th scope="col" className="py-1 pr-3">Citado por</th></tr></thead>
              <tbody>{externos.map((p) => (
                <tr key={`${p.classe}${p.numero}`} className="border-b border-neutral-100">
                  <td className="py-1 pr-3">{p.classe} {p.numero}</td>
                  <td className="py-1 pr-3">{p.n_docs} ({p.n_ocorrencias})</td>
                  <td className="py-1 pr-3 text-xs">{p.citado_por.map((i) => rotulo.get(i) ?? i).join(", ")}</td>
                </tr>
              ))}</tbody>
            </table></div>
          </div>
        </div>
      </section>
    </div>
  );
}
