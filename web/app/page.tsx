import Link from "next/link";
import { BadgeEpistemico, Carimbo, LegendaEpistemica, Publicidade } from "@/components/Badges";
import { formatarData, getMeta, getProcesso, getProcessos } from "@/lib/data";
import type { TipoEpistemico } from "@/lib/tipos";

/* A página inicial é a capa dos autos: o processo principal como folha de rosto, com o índice do que a base
   contém sobre ele. Cada linha do índice leva ao lugar certo. O que está fora da capa é o apenso (processos
   relacionados) e a legenda de leitura. */
export default function Home() {
  const meta = getMeta();
  const processos = getProcessos();
  const semente = getProcesso(meta.semente);
  const cab = semente.cabecalho;
  const decisoes = semente.andamentos.filter((a) => a.e_decisao).length;
  const documentos = semente.andamentos.reduce((n, a) => n + a.documentos.filter((d) => d.baixado).length, 0);
  const relacionados = processos.filter((p) => p.incidente !== meta.semente);
  const cont = semente.contagem_assercoes ?? { fato_processual: 0, alegacao_parte: 0, fundamento_decisorio: 0 };
  const totalAssercoes = Object.values(cont).reduce((a, b) => a + b, 0);

  const indice: { rotulo: string; valor: string | number; href: string; nota?: string }[] = [
    { rotulo: "Andamentos", valor: semente.andamentos.length, href: `/processo/${cab.incidente}#lt`, nota: `${decisoes} decisões` },
    { rotulo: "Documentos com texto", valor: documentos, href: `/processo/${cab.incidente}#lt` },
    { rotulo: "Partes", valor: semente.partes.length, href: `/processo/${cab.incidente}#partes` },
    { rotulo: "Petições", valor: semente.peticoes.length, href: `/processo/${cab.incidente}` },
    { rotulo: "Sessões virtuais", valor: semente.sessoes.length, href: `/processo/${cab.incidente}#sessoes` },
    { rotulo: "Asserções extraídas", valor: totalAssercoes, href: "/assercoes" },
  ];

  return (
    <div className="space-y-10">
      <section aria-labelledby="titulo-semente" className="capa">
        <div className="capa-verso" aria-hidden />
        <div className="capa-folha folha border border-neutral-300 bg-white">
          <header className="border-b border-neutral-300 px-5 pt-5 pb-4 sm:px-8">
            <p className="text-sm text-neutral-700">Supremo Tribunal Federal — autos públicos</p>
            <div className="mt-1 flex flex-wrap items-end gap-x-4 gap-y-2">
              <h1 id="titulo-semente" className="text-4xl leading-none sm:text-5xl">
                {cab.classe} {cab.numero}
              </h1>
              <div className="flex flex-wrap items-center gap-2 pb-1">
                <Publicidade valor={cab.publicidade} />
                {cab.natureza && <span className="rounded-sm border border-neutral-400 px-1.5 py-px text-xs">{cab.natureza}</span>}
                {cab.reu_preso ? <span className="alerta rounded-sm px-1.5 py-px text-xs font-semibold">réu preso</span> : null}
              </div>
            </div>
            <dl className="mt-3 grid gap-x-8 gap-y-1 text-sm sm:grid-cols-2">
              <div><dt className="inline text-neutral-700">Relator </dt><dd className="inline">{cab.relator ?? "—"}</dd></div>
              <div><dt className="inline text-neutral-700">Protocolo </dt><dd className="inline">{formatarData(cab.data_protocolo)}</dd></div>
              <div><dt className="inline text-neutral-700">Número único </dt><dd className="inline">{cab.numero_unico ?? "—"}</dd></div>
              <div><dt className="inline text-neutral-700">Último incidente </dt><dd className="inline">{cab.ultimo_incidente ?? "—"}</dd></div>
              <div className="sm:col-span-2"><dt className="inline text-neutral-700">Assunto </dt><dd className="inline leitura text-base">{cab.assuntos.join("; ") || "—"}</dd></div>
            </dl>
          </header>

          <div className="grid gap-6 px-5 py-5 sm:px-8 lg:grid-cols-[minmax(0,1fr)_280px]">
            <div>
              <h2 className="text-sm text-neutral-700">Índice do que a base tem sobre este processo</h2>
              <ol className="indice mt-2">
                {indice.map((i) => (
                  <li key={i.rotulo}>
                    <Link href={i.href} className="indice-linha">
                      <span className="indice-rotulo">{i.rotulo}{i.nota ? <span className="text-neutral-700"> ({i.nota})</span> : null}</span>
                      <span className="indice-pontos" aria-hidden />
                      <span className="indice-valor">{i.valor}</span>
                    </Link>
                  </li>
                ))}
              </ol>
              {totalAssercoes > 0 && (
                <p className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                  {(["fato_processual", "alegacao_parte", "fundamento_decisorio"] as TipoEpistemico[]).map((t) => (
                    <span key={t} className="flex items-center gap-1"><BadgeEpistemico tipo={t} /> {cont[t]}</span>
                  ))}
                </p>
              )}
            </div>
            <div className="flex flex-col gap-2 text-sm">
              <Link href={`/processo/${cab.incidente}`} className="botao-primario toque rounded px-4 py-2 text-center font-semibold">Abrir os autos</Link>
              <Link href="/linha-do-tempo" className="toque rounded border border-neutral-400 px-4 py-2 text-center hover:bg-neutral-100">Linha do tempo do caso</Link>
              <Link href="/grafo" className="toque rounded border border-neutral-400 px-4 py-2 text-center hover:bg-neutral-100">Grafo de ligações</Link>
              <Link href="/busca" className="toque rounded border border-neutral-400 px-4 py-2 text-center hover:bg-neutral-100">Buscar nos autos</Link>
              <p className="mt-2 text-xs text-neutral-700">
                <Carimbo snapshot={cab.snapshot} />{" "}
                <a className="underline" href={`https://portal.stf.jus.br/processos/detalhe.asp?incidente=${cab.incidente}`} rel="noreferrer">ver no portal do STF</a>
              </p>
            </div>
          </div>
        </div>
      </section>

      <section aria-labelledby="titulo-comecar">
        <h2 id="titulo-comecar" className="text-lg">Por onde começar</h2>
        <p className="text-sm text-neutral-700">Três perguntas que a base responde sem interpretar nada: cada resposta aponta para o documento ou o registro do portal de onde saiu.</p>
        <div className="mt-3 grid gap-3 md:grid-cols-3">
          <Link href={`/processo/${cab.incidente}`} className="folha block border border-neutral-300 bg-white p-4 no-underline">
            <span className="leitura block text-lg">Do que trata o processo?</span>
            <span className="mt-1 block text-sm text-neutral-700">O assunto cadastrado pelo STF, quem é o relator e a linha do tempo de tudo o que aconteceu nos autos.</span>
          </Link>
          <Link href={`/processo/${cab.incidente}#partes`} className="folha block border border-neutral-300 bg-white p-4 no-underline">
            <span className="leitura block text-lg">Quem participa, e em que papel?</span>
            <span className="mt-1 block text-sm text-neutral-700">As partes com o status literal do portal (investigado, requerido, interessado…) e seus advogados. Nenhum papel significa culpa.</span>
          </Link>
          <Link href="/decisoes" className="folha block border border-neutral-300 bg-white p-4 no-underline">
            <span className="leitura block text-lg">O que já foi decidido?</span>
            <span className="mt-1 block text-sm text-neutral-700">Pedido por pedido: quem pediu, o que pediu e o que o ministro ou a Turma decidiu, com o trecho do documento.</span>
          </Link>
        </div>
        <p className="mt-2 text-sm text-neutral-700">Termos difíceis aparecem sublinhados; clique para ver o significado, ou consulte o <Link className="underline" href="/glossario">glossário</Link>.</p>
      </section>

      <section aria-labelledby="titulo-relacionados">
        <h2 id="titulo-relacionados" className="text-lg">Apensos: processos relacionados, declarados nos próprios autos</h2>
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
