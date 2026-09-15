import Link from "next/link";
import { Aviso } from "@/components/Aviso";
import { LegendaEpistemica, Publicidade } from "@/components/Badges";
import { PontosChave } from "@/components/PontosChave";
import { formatarData, formatarDataHora, getAvisos, getCronologia, getFluxos, getLinhaTempo, getMeta, getPontosChave, getProcesso, getProcessos, getTrajetos } from "@/lib/data";

/* A capa é a folha de rosto dos autos: o título do caso e um sumário — como o índice de um processo físico, com o
   número à direita — que leva às seis perguntas que o site responde. Depois, o que se sabe (pontos-chave, cada um
   com prova), o que aconteceu por último e a lista dos processos. Nada aqui é conclusão do site. */
export default function Home() {
  const meta = getMeta();
  const processos = getProcessos();
  const semente = getProcesso(meta.semente);
  const cab = semente.cabecalho;
  const avisos = getAvisos();
  const pontos = getPontosChave().inicio ?? [];
  const fluxos = getFluxos();
  const totalAssercoes = meta.contagens.assercoes ?? 0;
  const totalDocs = processos.reduce((n, p) => n + (p.contagens?.documentos ?? 0), 0);

  // últimos acontecimentos: decisões e despachos mais recentes em qualquer processo, pela linha do tempo unificada
  const lt = getLinhaTempo().eventos;
  const ultimos = lt.filter((e) => e.e_decisao || /despacho|decis/i.test(e.tipo)).sort((a, b) => (b.data ?? "").localeCompare(a.data ?? "")).slice(0, 6);
  const ultimaColeta = Object.values(meta.coletado_em).filter(Boolean).sort().at(-1);

  const trajetos = getTrajetos().trajetos.length;
  const cronologia = getCronologia().total;
  const perguntas = [
    { href: "/rede-de-pagamentos/trajetos", titulo: "Por onde o dinheiro passou?", texto: "Do caixa do Master à Super, à igreja e aos fornecedores, passo a passo, com quem afirma cada passo.", valor: `${trajetos} caminhos` },
    { href: "/rede-de-pagamentos", titulo: "Quem recebeu, quanto, de quem?", texto: "Tabelas com busca e filtros; cada linha aponta a página do relatório.", valor: `${fluxos.resumo.atores} pessoas e empresas` },
    { href: "/decisoes", titulo: "O que o STF já decidiu?", texto: "Pedido por pedido: quem pediu, o que pediu, o que o ministro ou a Turma decidiu, com o trecho.", valor: `${meta.contagens.decisoes ?? 0} pedidos` },
    { href: "/entidades", titulo: "Quem é quem no caso?", texto: "Investigados, requeridos, interessados, advogados e órgãos, com o papel que o portal registra.", valor: `${meta.contagens.entidades} nomes` },
    { href: "/cronologia", titulo: "O que aconteceu, e quando?", texto: "Registros do portal, datas escritas nos documentos e decisões, numa só linha.", valor: `${cronologia} acontecimentos` },
    { href: "/verificar", titulo: "Como conferir tudo isso?", texto: "Cada documento tem código de autenticação do STF e hash; qualquer pessoa refaz a base.", valor: `${totalDocs} documentos` },
  ];

  return (
    <div className="space-y-8">
      {avisos.map((a) => <Aviso key={a.id} aviso={a} />)}

      {/* folha de rosto: título e sumário dos autos */}
      <div className="capa max-w-3xl">
        <div className="capa-verso" aria-hidden="true" />
        <section className="capa-folha rounded border border-neutral-300 bg-white p-5 sm:p-7" aria-labelledby="titulo-caso">
          <p className="text-sm text-neutral-700">Autos públicos do Supremo Tribunal Federal{ultimaColeta ? `, lidos em ${formatarDataHora(ultimaColeta)}` : ""}</p>
          <h1 id="titulo-caso" className="mt-1 text-3xl leading-tight sm:text-4xl">O caso Banco Master no STF</h1>
          <p className="leitura mt-3">
            {processos.length} processos, {totalDocs} documentos e {totalAssercoes} afirmações extraídas dos textos, cada uma com quem afirma, o documento e a página.
            O site não conclui nada: mostra o que os autos dizem, quem diz e onde está escrito, para qualquer pessoa conferir.
          </p>
          <h2 className="mt-6 text-base text-neutral-700">Sumário</h2>
          <ol className="indice mt-1">
            {perguntas.map((q) => (
              <li key={q.href}>
                <Link href={q.href} className="indice-linha">
                  <span className="indice-rotulo">{q.titulo}</span>
                  <span className="indice-pontos" aria-hidden="true" />
                  <span className="indice-valor text-sm">{q.valor}</span>
                </Link>
                <p className="-mt-1 mb-1 pr-16 font-sans text-sm text-neutral-700">{q.texto}</p>
              </li>
            ))}
          </ol>
          <p className="mt-4 text-sm text-neutral-700">Palavras difíceis aparecem <span className="termo">sublinhadas</span>; clique para ver o significado, ou consulte o <Link className="underline" href="/glossario">glossário</Link>.</p>
        </section>
      </div>

      <PontosChave titulo={`O que os autos dizem, em ${["", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze", "doze"][pontos.length] ?? pontos.length} pontos`} itens={pontos.map((p) => ({ texto: p.texto, provas: p.provas }))}
        nota="Cada frase é uma síntese do que está escrito nas peças; os selos levam ao documento e à página, e dizem quem afirma. Alegação não é condenação: ninguém foi julgado." />

      <section aria-labelledby="titulo-ultimos">
        <h2 id="titulo-ultimos" className="text-lg">Últimas decisões e despachos nos autos</h2>
        <ol className="mt-2 divide-y divide-neutral-200 border-y border-neutral-300">
          {ultimos.map((e) => (
            <li key={e.andamento_id} className="grid gap-x-4 py-2 text-sm sm:grid-cols-[7rem_8rem_1fr]">
              <span className="tabular-nums text-neutral-600">{e.data ? formatarData(e.data) : "—"}</span>
              <Link className="underline" href={`/processo/${e.incidente}#lt`}>{e.processo}</Link>
              <span>
                <span className="font-medium">{e.tipo}</span>{e.descricao ? <span className="text-neutral-700"> — {e.descricao.replace(/\s+/g, " ").slice(0, 220)}{e.descricao.length > 220 ? "…" : ""}</span> : null}
                {e.documentos?.length ? <span> · <Link className="underline" href={`/documento/${e.documentos[0].id}`}>peça</Link></span> : null}
              </span>
            </li>
          ))}
        </ol>
        <p className="mt-2 text-sm"><Link className="underline" href="/linha-do-tempo">Linha do tempo completa</Link> · <Link className="underline" href="/mudancas">o que mudou no portal</Link></p>
      </section>

      <section aria-labelledby="titulo-processos">
        <h2 id="titulo-processos" className="text-lg">Os processos</h2>
        <p className="text-sm text-neutral-700">
          O principal é a <Link className="underline" href={`/processo/${cab.incidente}`}>{cab.classe} {cab.numero}</Link> (relator {cab.relator ?? "—"}; protocolo {formatarData(cab.data_protocolo)}). Os demais são
          declarados como relacionados nos próprios autos (distribuição por prevenção, certidões de autuação) ou entraram pelo levantamento de sigilo. Processos sigilosos mostram só o que o portal devolve.
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
                <th scope="col" className="py-2 pr-3">Documentos</th>
                <th scope="col" className="py-2 pr-3">Coletado em</th>
              </tr>
            </thead>
            <tbody>
              {[...processos].sort((a, b) => (b.contagens?.andamentos ?? 0) - (a.contagens?.andamentos ?? 0)).map((p) => (
                <tr key={`${p.classe}${p.numero}`} className={`border-b border-neutral-200 ${p.incidente === meta.semente ? "font-medium" : ""}`}>
                  <td data-rotulo="Processo" className="py-2 pr-3">
                    {p.coletado && p.incidente ? <Link className="underline" href={`/processo/${p.incidente}`}>{p.classe} {p.numero}</Link> : `${p.classe} ${p.numero}`}
                    {p.incidente === meta.semente ? <span className="ml-1 text-xs text-neutral-600">(principal)</span> : null}
                  </td>
                  <td data-rotulo="Publicidade" className="py-2 pr-3"><Publicidade valor={p.publicidade} /></td>
                  <td data-rotulo="Relator" className="py-2 pr-3">{p.relator ?? "—"}</td>
                  <td data-rotulo="Assunto" className="py-2 pr-3">{(p.assuntos ?? []).join("; ") || "—"}</td>
                  <td data-rotulo="Andamentos" className="py-2 pr-3 tabular-nums">{p.contagens?.andamentos ?? "—"}</td>
                  <td data-rotulo="Documentos" className="py-2 pr-3 tabular-nums">{p.contagens?.documentos ?? "—"}</td>
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
