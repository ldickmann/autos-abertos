import Link from "next/link";
import { Carimbo, LegendaEpistemica, Publicidade } from "@/components/Badges";
import { formatarData, getMeta, getProcesso, getProcessos } from "@/lib/data";

export default function Home() {
  const meta = getMeta();
  const processos = getProcessos();
  const semente = getProcesso(meta.semente);
  const cab = semente.cabecalho;
  const decisoes = semente.andamentos.filter((a) => a.e_decisao).length;
  const relacionados = processos.filter((p) => p.incidente !== meta.semente);

  return (
    <div className="space-y-8">
      <section aria-labelledby="titulo-semente" className="rounded-lg border border-neutral-300 bg-white p-5">
        <div className="flex flex-wrap items-baseline gap-3">
          <h1 id="titulo-semente" className="text-2xl font-bold">
            {cab.classe} {cab.numero}
          </h1>
          <Publicidade valor={cab.publicidade} />
          {cab.natureza && <span className="text-sm text-neutral-700">{cab.natureza}</span>}
          {cab.reu_preso ? <span className="alerta rounded px-2 py-0.5 text-xs font-semibold">Réu preso</span> : null}
        </div>
        <dl className="mt-3 grid gap-x-8 gap-y-1 text-sm sm:grid-cols-2">
          <div><dt className="inline font-semibold">Número único: </dt><dd className="inline">{cab.numero_unico ?? "—"}</dd></div>
          <div><dt className="inline font-semibold">Relator: </dt><dd className="inline">{cab.relator ?? "—"}</dd></div>
          <div><dt className="inline font-semibold">Protocolo: </dt><dd className="inline">{formatarData(cab.data_protocolo)}</dd></div>
          <div><dt className="inline font-semibold">Último incidente: </dt><dd className="inline">{cab.ultimo_incidente ?? "—"}</dd></div>
          <div className="sm:col-span-2"><dt className="inline font-semibold">Assunto: </dt><dd className="inline">{cab.assuntos.join("; ") || "—"}</dd></div>
        </dl>
        <ul className="mt-4 flex flex-wrap gap-4 text-sm">
          <li><span className="font-semibold">{semente.andamentos.length}</span> andamentos</li>
          <li><span className="font-semibold">{decisoes}</span> decisões</li>
          <li><span className="font-semibold">{semente.partes.length}</span> partes</li>
          <li><span className="font-semibold">{semente.peticoes.length}</span> petições</li>
          <li><span className="font-semibold">{semente.sessoes.length}</span> sessões virtuais</li>
        </ul>
        <div className="mt-4 flex flex-wrap items-center gap-4">
          <Link href={`/processo/${cab.incidente}`} className="botao-primario rounded px-4 py-2 text-sm font-semibold">
            Abrir linha do tempo
          </Link>
          <Carimbo snapshot={cab.snapshot} />
          <a className="text-sm underline" href={`https://portal.stf.jus.br/processos/detalhe.asp?incidente=${cab.incidente}`} rel="noreferrer">
            Ver no portal do STF
          </a>
        </div>
      </section>

      <section aria-labelledby="titulo-relacionados">
        <h2 id="titulo-relacionados" className="text-lg font-bold">Processos relacionados, declarados nos próprios autos</h2>
        <p className="text-sm text-neutral-700">
          Extraídos dos andamentos de distribuição por prevenção e certidões de autuação. Cada um foi coletado por completo.
          Processos sigilosos mostram só o que o portal público devolve.
        </p>
        <div className="mt-3 overflow-x-auto">
          <table className="tabela-responsiva w-full min-w-[640px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-neutral-400 text-left">
                <th scope="col" className="py-2 pr-3">Processo</th>
                <th scope="col" className="py-2 pr-3">Publicidade</th>
                <th scope="col" className="py-2 pr-3">Relator</th>
                <th scope="col" className="py-2 pr-3">Assunto</th>
                <th scope="col" className="py-2 pr-3">Andamentos</th>
                <th scope="col" className="py-2 pr-3">Coletado em</th>
              </tr>
            </thead>
            <tbody>
              {relacionados.map((p) => (
                <tr key={`${p.classe}${p.numero}`} className="border-b border-neutral-200">
                  <td data-rotulo="Processo" className="py-2 pr-3 font-medium">
                    {p.coletado && p.incidente ? <Link className="underline" href={`/processo/${p.incidente}`}>{p.classe} {p.numero}</Link> : `${p.classe} ${p.numero}`}
                  </td>
                  <td data-rotulo="Publicidade" className="py-2 pr-3"><Publicidade valor={p.publicidade} /></td>
                  <td data-rotulo="Relator" className="py-2 pr-3">{p.relator ?? "—"}</td>
                  <td data-rotulo="Assunto" className="py-2 pr-3">{(p.assuntos ?? []).join("; ") || "—"}</td>
                  <td data-rotulo="Andamentos" className="py-2 pr-3">{p.contagens?.andamentos ?? "—"}</td>
                  <td data-rotulo="Coletado em" className="py-2 pr-3">{p.coletado_em ? formatarData(p.coletado_em) : "não coletado"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="titulo-legenda">
        <h2 id="titulo-legenda" className="sr-only">Legenda dos tipos de asserção</h2>
        <LegendaEpistemica descricoes={meta.tipos_epistemicos} />
      </section>
    </div>
  );
}
