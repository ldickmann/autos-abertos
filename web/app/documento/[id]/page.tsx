import Link from "next/link";
import { BadgeEpistemico, Carimbo } from "@/components/Badges";
import { PontosChave } from "@/components/PontosChave";
import { ConversaWhats } from "@/components/ConversaWhats";
import { ReguaDePaginas } from "@/components/ReguaDePaginas";
import { formatarData, formatarDataHora, getDocumento, getMeta, listarDocumentos } from "@/lib/data";

export function generateStaticParams() {
  return listarDocumentos().map((id) => ({ id: String(id) }));
}

export default async function PaginaDocumento({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const d = getDocumento(id);
  const m = d.meta;
  const meta = getMeta();
  const porPagina = new Map<number, typeof d.assercoes>();
  for (const a of d.assercoes) porPagina.set(a.pagina, [...(porPagina.get(a.pagina) ?? []), a]);

  // "Em resumo": que peça é, quem fala nela, e uma afirmação de cada tipo para dar o tom
  const porTipo = (t: string) => d.assercoes.filter((a) => a.tipo_epistemico === t);
  const vozes = (t: string) => { const m = new Map<string, number>(); for (const a of porTipo(t)) if (a.atribuida_a) { const k = a.atribuida_a.replace(/\s*\(.*$/, ""); m.set(k, (m.get(k) ?? 0) + 1); } return [...m.entries()].sort((x, y) => y[1] - x[1]).slice(0, 3).map(([q, n]) => `${q} (${n})`); };
  const exemplo = (t: string) => porTipo(t).sort((a, b) => b.texto.length - a.texto.length)[Math.floor(porTipo(t).length / 2)];
  const andamento = m.andamentos[0];
  const nProc = d.referencias?.processos?.length ?? 0, nDisp = d.referencias?.dispositivos?.length ?? 0;
  const resumo = [
    { texto: <><strong>{m.titulo ?? "Documento"}</strong>{m.funcao && meta.funcoes_documento?.[m.funcao] && m.funcao !== "outro" ? ` (${meta.funcoes_documento[m.funcao]})` : ""}, {m.paginas ?? d.paginas.length} páginas{andamento ? <>, juntado em {formatarData(andamento.data)} no andamento &quot;{andamento.tipo}&quot; do <Link className="underline" href={`/processo/${m.incidente}`}>processo {m.incidente}</Link></> : null}.{m.codigo_autenticacao ? " Tem código de autenticação do STF." : ""}</> },
    ...(d.assercoes.length ? [{ texto: <><strong>{d.assercoes.length} afirmações</strong> extraídas: {porTipo("fato_processual").length} fatos, {porTipo("alegacao_parte").length} alegações{vozes("alegacao_parte").length ? ` (${vozes("alegacao_parte").join(", ")})` : ""} e {porTipo("fundamento_decisorio").length} fundamentos{vozes("fundamento_decisorio").length ? ` (${vozes("fundamento_decisorio").join(", ")})` : ""}.</> }] : [{ texto: <>Nenhuma afirmação foi extraída desta peça ainda; o texto por página está abaixo e é pesquisável.</> }]),
    ...(["alegacao_parte", "fundamento_decisorio", "fato_processual"].map(exemplo).filter(Boolean).slice(0, 2).map((a) => ({ texto: <><BadgeEpistemico tipo={a!.tipo_epistemico} /> {a!.atribuida_a ? <strong>{a!.atribuida_a}: </strong> : null}{a!.texto}</>, fonte: { href: `#p-${a!.pagina}`, rotulo: `p. ${a!.pagina}` } }))),
    ...(nProc || nDisp ? [{ texto: <>Cita {nDisp} dispositivos legais e {nProc} processos.</>, fonte: { href: "#refs", rotulo: "ver referências" } }] : []),
    ...(d.conversas ? [{ texto: <>Em <strong>{d.conversas.paginas.length} páginas</strong> a PF descreve conversas do aparelho de {d.conversas.aparelho}; o site as reconstitui como no aplicativo, frase por frase, com a página e o trecho de cada balão.</>, fonte: { href: `#p-${d.conversas.paginas[0].n}`, rotulo: "ver a primeira" } }] : []),
  ];
  // páginas com conversa: sequências consecutivas viram um "aparelho" (ConversaWhats) no lugar dos cartões de página
  const conversaPorPagina = new Map((d.conversas?.paginas ?? []).map((p) => [p.n, p]));
  const blocos: ({ tipo: "pagina"; p: (typeof d.paginas)[number] } | { tipo: "conversa"; paginas: NonNullable<typeof d.conversas>["paginas"]; textos: typeof d.paginas })[] = [];
  for (const p of d.paginas) {
    const c = conversaPorPagina.get(p.n);
    const ultimo = blocos[blocos.length - 1];
    if (c && ultimo?.tipo === "conversa" && ultimo.textos[ultimo.textos.length - 1].n === p.n - 1) { ultimo.paginas.push(c); ultimo.textos.push(p); }
    else if (c) blocos.push({ tipo: "conversa", paginas: [c], textos: [p] });
    else blocos.push({ tipo: "pagina", p });
  }

  return (
    <div className="space-y-6">
      <nav aria-label="Trilha" className="text-sm">
        <Link className="underline" href="/">Início</Link> / <Link className="underline" href={`/processo/${m.incidente}`}>processo {m.incidente}</Link> / documento {m.id}
      </nav>
      <header className="rounded-lg border border-neutral-300 bg-white p-5">
        <h1 className="text-2xl font-bold">{m.titulo ?? "Documento"} <span className="text-base font-normal text-neutral-700">({m.formato.toUpperCase()}, {m.paginas ?? d.paginas.length} página{(m.paginas ?? d.paginas.length) === 1 ? "" : "s"})</span></h1>
        {m.funcao && meta.funcoes_documento?.[m.funcao] && m.funcao !== "outro" && (
          <p className="mt-1 text-xs text-neutral-700">função: {meta.funcoes_documento[m.funcao]} <span title="derivada do título literal do portal por regra curada (stf/curadoria/funcoes_documento.json)">(curadoria)</span></p>
        )}
        <dl className="mt-3 grid gap-x-8 gap-y-1 text-sm sm:grid-cols-2">
          {m.andamentos.map((a) => (
            <div key={a.id}><dt className="inline font-semibold">Andamento: </dt><dd className="inline"><Link className="underline" href={`/processo/${a.incidente}#andamento-${a.id}`}>{formatarData(a.data)} · {a.tipo}</Link></dd></div>
          ))}
          <div><dt className="inline font-semibold">Fonte: </dt><dd className="inline"><a className="underline break-all" href={m.url} rel="noreferrer">{m.url}</a></dd></div>
          {m.codigo_autenticacao && (
            <div className="sm:col-span-2">
              <dt className="inline font-semibold">Autenticação no STF: </dt>
              <dd className="inline">código {m.codigo_autenticacao}{m.senha_autenticacao ? `, senha ${m.senha_autenticacao}` : ""} em <a className="underline" href="http://www.stf.jus.br/portal/autenticacao/autenticarDocumento.asp" rel="noreferrer">autenticarDocumento.asp</a></dd>
            </div>
          )}
          <div className="sm:col-span-2"><dt className="inline font-semibold">sha256: </dt><dd className="inline break-all font-mono text-xs">{m.sha256}</dd></div>
        </dl>
        <details className="text-xs">
          <summary className="cursor-pointer text-neutral-700">Como verificar este documento</summary>
          <p className="mt-1">Baixe o arquivo pela URL de origem acima e calcule o hash: <code>Get-FileHash .\arquivo.{m.formato} -Algorithm SHA256</code> (Windows), <code>shasum -a 256 arquivo.{m.formato}</code> (macOS) ou <code>sha256sum arquivo.{m.formato}</code> (Linux). O resultado deve ser igual ao sha256 acima.{m.codigo_autenticacao ? " Ou use o código de autenticação no portal do STF." : ""} <Link className="underline" href="/verificar">Mais formas de conferir.</Link></p>
        </details>
        <div className="mt-3 flex flex-wrap gap-4">
          <Carimbo snapshot={m.snapshot} prefixo="documento baixado em" />
          {!m.tem_texto && <span className="alerta rounded px-2 py-0.5 text-xs font-semibold">sem camada de texto (OCR pendente)</span>}
        </div>
      </header>

      <PontosChave titulo="Em resumo" itens={resumo} nota="Os exemplos são afirmações extraídas do próprio documento, com página; a lista completa vem abaixo." />

      {d.referencias && (d.referencias.processos.length > 0 || d.referencias.dispositivos.length > 0 || d.referencias.andamentos_citados.length > 0) && (
        <section aria-labelledby="refs" className="folha border border-neutral-300 bg-white p-4 text-sm">
          <h2 id="refs" className="text-lg">O que este documento cita</h2>
          <p className="text-xs text-neutral-700">Encontrado no texto por padrão literal (classe e número de processo; artigo e diploma). Cada item leva à página.</p>
          <div className="mt-2 grid gap-4 md:grid-cols-3">
            {d.referencias.processos.length > 0 && (
              <div>
                <h3 className="font-semibold">Processos</h3>
                <ul className="mt-1 space-y-0.5">
                  {agrupar(d.referencias.processos, (x) => `${x.classe} ${x.numero}`).map(([k, xs]) => (
                    <li key={k}>{xs[0].incidente ? <Link className="underline" href={`/processo/${xs[0].incidente}`}>{k}</Link> : k}
                      <span className="text-xs text-neutral-600"> p. {xs.map((x) => <a key={x.pagina} className="underline" href={`#p-${x.pagina}`} title={x.trecho}>{x.pagina}</a>).reduce<React.ReactNode[]>((acc, el, i) => (i ? [...acc, ", ", el] : [el]), [])}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {d.referencias.dispositivos.length > 0 && (
              <div>
                <h3 className="font-semibold">Dispositivos legais</h3>
                <ul className="mt-1 space-y-0.5">
                  {agrupar(d.referencias.dispositivos, (x) => x.dispositivo).map(([k, xs]) => (
                    <li key={k}>{k}
                      <span className="text-xs text-neutral-600"> p. {xs.map((x) => <a key={x.pagina} className="underline" href={`#p-${x.pagina}`} title={x.trecho}>{x.pagina}</a>).reduce<React.ReactNode[]>((acc, el, i) => (i ? [...acc, ", ", el] : [el]), [])}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {d.referencias.andamentos_citados.length > 0 && (
              <div>
                <h3 className="font-semibold">Andamentos a que se refere</h3>
                <ul className="mt-1 space-y-0.5">
                  {d.referencias.andamentos_citados.map((a) => (
                    <li key={a.andamento_id}><Link className="underline" href={`/processo/${a.incidente}#andamento-${a.andamento_id}`}>{formatarData(a.data_citada)} {a.tipo_citado}</Link></li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>
      )}

      {d.assercoes.length > 0 && (
        <section aria-labelledby="ass">
          <h2 id="ass" className="text-lg font-bold">Asserções extraídas ({d.assercoes.length})</h2>
          <p className="text-sm text-neutral-700">Cada uma aponta a página e o trecho literal de onde saiu. Modelo {d.assercoes[0].modelo}, prompt {d.assercoes[0].prompt_version}.</p>
        </section>
      )}

      <section aria-labelledby="texto">
        <h2 id="texto" className="text-lg font-bold">Texto por página</h2>
        {d.paginas.length === 0 && <p className="text-sm">Texto não extraído.</p>}
        {d.conversas && <p className="text-sm text-neutral-700">Nas páginas em que a PF descreve conversas do celular, o texto aparece como no aplicativo (lado direito: o aparelho analisado). É reconstituição a partir da prosa da PF, não a captura de tela; o texto literal de cada página fica logo abaixo de cada aparelho.</p>}
        {blocos.map((b) => b.tipo === "conversa" ? (
          <ConversaWhats key={`c-${b.paginas[0].n}`} aparelho={d.conversas!.aparelho} fonte={d.conversas!.fonte} paginas={b.paginas} textos={b.textos} assercoes={porPagina} />
        ) : (
          <article key={b.p.n} id={`p-${b.p.n}`} className="mt-4 scroll-mt-20 rounded border border-neutral-300 bg-white">
            <h3 className="border-b border-neutral-200 px-4 py-2 text-sm font-semibold">Página {b.p.n}</h3>
            {(porPagina.get(b.p.n) ?? []).length > 0 && (
              <ul className="space-y-2 border-b border-neutral-200 bg-neutral-50 px-4 py-3 text-sm" aria-label={`Asserções da página ${b.p.n}`}>
                {(porPagina.get(b.p.n) ?? []).map((a) => (
                  <li key={a.id} id={`assercao-${a.id}`} className="flex gap-2">
                    <BadgeEpistemico tipo={a.tipo_epistemico} />
                    <div>
                      <p>{a.texto}{a.atribuida_a ? <span className="text-neutral-700"> — atribuída a {a.atribuida_a}</span> : null}</p>
                      <p className="text-xs text-neutral-700">trecho-fonte: “{a.trecho_fonte}”</p>
                      {a.entidades.length > 0 && (
                        <p className="flex flex-wrap gap-x-3 gap-y-1 text-xs">{a.entidades.map((e) => <Link key={e.entidade_id} className="toque underline" href={`/entidade/${e.entidade_id}`}>{e.nome}</Link>)}</p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <pre className="overflow-x-auto whitespace-pre-wrap px-4 py-3 font-sans text-sm leading-relaxed">{b.p.texto}</pre>
          </article>
        ))}
      </section>
      <ReguaDePaginas total={d.paginas.length} />
      <p className="text-xs text-neutral-600">Base gerada com o texto extraído automaticamente do PDF; em caso de dúvida, consulte o original no portal. Extraído em {formatarDataHora(m.baixado_em)}.</p>
    </div>
  );
}

function agrupar<T>(itens: T[], chave: (x: T) => string): [string, T[]][] {
  const m = new Map<string, T[]>();
  for (const x of itens) m.set(chave(x), [...(m.get(chave(x)) ?? []), x]);
  return [...m.entries()];
}
