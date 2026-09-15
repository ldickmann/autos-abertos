import Link from "next/link";
import { BadgeEpistemico } from "@/components/Badges";
import { formatarData, formatarReais, getFluxos, getTrajetos, type Prova } from "@/lib/data";

/*
  Os caminhos do dinheiro, passo a passo. Cada passo tem "de", "para", valor, quando, como — e as provas: asserções dos
  autos (documento, página, quem afirma) e comunicações do RIF (página, comunicante). O exportador recusa passo sem prova.
  Método: seguir o dinheiro é uma questão de nomes; anotar de onde veio cada afirmação; fontes primárias; o outro lado
  (contrapontos) e o que falta (lacunas) aparecem em cada trajeto. Nada aqui é conclusão do site.
*/

function reais(texto: string | null): string | null {
  if (!texto) return null;
  const [i, c] = texto.split(",");
  return formatarReais(parseInt(i.replace(/\./g, ""), 10) * 100 + parseInt(c ?? "0", 10));
}

function QuemDiz({ p }: { p: Prova }) {
  if (p.tipo === "assercao") return <><BadgeEpistemico tipo={p.tipo_epistemico} /> <span className="font-medium">{p.atribuida_a ?? "registro dos autos"}</span></>;
  if (p.tipo === "documento") return <><span className="carimbo rounded-sm border px-1.5 py-px text-xs font-medium">peça</span> <span className="font-medium">{p.atribuida_a ?? "documento"}</span></>;
  return <><span className="carimbo rounded-sm border px-1.5 py-px text-xs font-medium">{p.secao === "relatorio" ? "PF" : "COAF"}</span> <span className="font-medium">{p.comunicante ?? "comunicante"}</span></>;
}

function LinkProva({ p }: { p: Prova }) {
  const rotulo = p.tipo === "comunicacao" ? `${p.secao === "relatorio" ? "IPJ-A" : "RIF"} p. ${p.pagina}` : `${p.documento_titulo?.replace(/ - .*$/, "") ?? "documento"} p. ${p.pagina}`;
  return <Link className="underline" href={`/documento/${p.documento_id}#p-${p.pagina}`}>{rotulo}</Link>;
}

function Provas({ provas }: { provas: Prova[] }) {
  return (
    <ul className="mt-2 space-y-1 text-xs">
      {provas.map((p, i) => (
        <li key={i} className="border-l-2 border-neutral-300 pl-2">
          <QuemDiz p={p} /> · <LinkProva p={p} />
          {p.tipo === "assercao" && <details className="inline"><summary className="inline cursor-pointer underline"> o que diz</summary><span className="block leitura text-sm">{p.texto}</span><q className="block italic text-neutral-700">{p.trecho_fonte}</q></details>}
          {p.tipo === "documento" && <q className="block italic text-neutral-700">{p.trecho_fonte}</q>}
          {p.tipo === "comunicacao" && (
            <details className="inline"><summary className="inline cursor-pointer underline"> {p.n_transacoes ? `${p.n_transacoes} fluxo(s), ${formatarReais(p.valor_centavos)}` : `comunicação ${p.numero}`}</summary>
              <ul className="mt-1 space-y-0.5 text-neutral-700">
                {p.transacoes.map((t) => <li key={t.id}><span className="tabular-nums">{formatarReais(t.valor_centavos)}</span> · {t.data ? formatarData(t.data) : `${t.periodo_inicio ? formatarData(t.periodo_inicio) : ""}–${t.periodo_fim ? formatarData(t.periodo_fim) : ""}`} · <q className="italic">{t.trecho_fonte}</q></li>)}
              </ul>
            </details>
          )}
        </li>
      ))}
    </ul>
  );
}

function Barras({ titulo, nota, itens }: { titulo: string; nota: string; itens: { rotulo: string; valor: number }[] }) {
  const max = Math.max(1, ...itens.map((i) => i.valor));
  return (
    <figure className="folha border border-neutral-300 bg-white p-4">
      <figcaption className="text-sm font-semibold">{titulo}</figcaption>
      <ol className="mt-2 space-y-1.5">
        {itens.map((i) => (
          <li key={i.rotulo} className="grid grid-cols-[minmax(0,10rem)_1fr_auto] items-center gap-2 text-xs sm:grid-cols-[minmax(0,14rem)_1fr_auto]" title={`${i.rotulo}: ${formatarReais(i.valor)}`}>
            <span className="truncate">{i.rotulo}</span>
            <span className="h-2.5 rounded-sm" style={{ width: `${Math.max(1, (100 * i.valor) / max)}%`, background: "var(--fundamento)" }} aria-hidden />
            <span className="tabular-nums text-neutral-700">{formatarReais(i.valor, true)}</span>
          </li>
        ))}
      </ol>
      <p className="mt-2 text-xs text-neutral-600">{nota}</p>
    </figure>
  );
}

export default function PaginaTrajetos() {
  const { trajetos, cruzamentos } = getTrajetos();
  const fluxos = getFluxos();
  const atorPorId = new Map(fluxos.atores.map((a) => [a.id, a]));
  const igreja = fluxos.atores.find((a) => a.chave === "cnpj:57391420000163");
  const superId = fluxos.atores.find((a) => a.chave === "cnpj:31446245000170")?.id;
  const saidasIgreja = new Map<number, number>();
  for (const t of fluxos.transacoes) if (igreja && t.origem_ator_id === igreja.id && t.natureza === "agregado" && t.destino_ator_id != null && t.destino_ator_id !== igreja.id) saidasIgreja.set(t.destino_ator_id, (saidasIgreja.get(t.destino_ator_id) ?? 0) + t.valor_centavos);
  const topSaidas = [...saidasIgreja.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10).map(([id, v]) => ({ rotulo: atorPorId.get(id)?.nome ?? String(id), valor: v }));
  const comprasPorMes = new Map<string, number>();
  for (const t of fluxos.transacoes) if (superId && t.origem_ator_id === superId && (t.tipo === "escritura_compra" || t.tipo === "escritura_doacao") && t.data) comprasPorMes.set(t.data.slice(0, 7), (comprasPorMes.get(t.data.slice(0, 7)) ?? 0) + t.valor_centavos);
  const compras = [...comprasPorMes.entries()].sort().map(([m, v]) => ({ rotulo: m.replace(/(\d{4})-(\d{2})/, "$2/$1"), valor: v }));

  return (
    <div className="space-y-8">
      <nav aria-label="Trilha" className="text-sm"><Link className="underline" href="/rede-de-pagamentos">Rede de pagamentos</Link> / Os caminhos do dinheiro</nav>
      <header className="max-w-3xl">
        <h1 className="text-2xl">Os caminhos do dinheiro</h1>
        <p className="mt-1 leitura text-base">
          Do caixa do Banco Master a quem recebeu — passo a passo, com quem afirma cada passo e onde está escrito. Quem pagou, quanto, quando, para quem, por qual
          caminho; onde a ligação com o Master e com Daniel Vorcaro está documentada; o que a defesa responde; e o que ainda ninguém sabe.
        </p>
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer font-semibold">Como ler esta página</summary>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-neutral-700">
            <li>Cada passo tem uma prova. <BadgeEpistemico tipo="alegacao_parte" /> é o que uma parte alega (Polícia Federal, Procuradoria, defesa); <BadgeEpistemico tipo="fundamento_decisorio" /> é o que um ministro afirma ao decidir; <BadgeEpistemico tipo="fato_processual" /> é um registro do processo; <span className="carimbo rounded-sm border px-1.5 py-px text-xs font-medium">COAF</span> é o que um banco, cooperativa, cartório ou concessionária comunicou — e o COAF avisa que um RIF, por si só, não é prova; <span className="carimbo rounded-sm border px-1.5 py-px text-xs font-medium">PF</span> é a leitura policial de mensagens de um celular, que a própria PF chama de não exaustiva.</li>
            <li>Alegação não é condenação. Ninguém aqui foi julgado; a Constituição presume a inocência até o trânsito em julgado. Os contrapontos trazem o que as defesas e o relator dizem nos próprios autos.</li>
            <li>Onde a fonte não diz, a página não diz: cada trajeto termina com o que falta.</li>
            <li>Os nomes são os que constam nas peças; CPFs não aparecem.</li>
          </ul>
        </details>
      </header>

      <section aria-labelledby="indice">
        <h2 id="indice" className="text-lg">{["", "Uma pergunta, um trajeto", "Duas perguntas, dois trajetos", "Três perguntas, três trajetos", "Quatro perguntas, quatro trajetos", "Cinco perguntas, cinco trajetos", "Seis perguntas, seis trajetos", "Sete perguntas, sete trajetos"][trajetos.length] ?? `${trajetos.length} trajetos`}</h2>
        <ol className="mt-2 grid gap-3 md:grid-cols-2">
          {trajetos.map((t, i) => (
            <li key={t.id}>
              <a href={`#${t.id}`} className="folha block h-full border border-neutral-300 bg-white p-4 no-underline">
                <span className="text-xs text-neutral-600">{i + 1}</span>
                <span className="leitura block text-lg">{t.pergunta}</span>
                <span className="mt-1 block text-sm text-neutral-700">{t.titulo} · {t.passos.length} passos</span>
              </a>
            </li>
          ))}
        </ol>
      </section>

      {trajetos.map((t, i) => (
        <section key={t.id} id={t.id} aria-labelledby={`h-${t.id}`} className="scroll-mt-4">
          <p className="text-xs text-neutral-600">Trajeto {i + 1}</p>
          <h2 id={`h-${t.id}`} className="text-xl">{t.titulo}</h2>
          <p className="mt-2 max-w-3xl leitura text-base">{t.resumo}</p>
          <p className="mt-1 max-w-3xl text-xs text-neutral-600">Quem afirma: {t.quem_afirma}</p>
          <ol className="trilha mt-4 space-y-3">
            {t.passos.map((p, j) => (
              <li key={j} className="folha relative border border-neutral-300 bg-white p-4 pl-12">
                <span className="absolute left-3 top-4 flex h-6 w-6 items-center justify-center rounded-full border border-neutral-400 text-xs font-semibold" aria-hidden>{j + 1}</span>
                <p className="text-sm"><span className="font-semibold">{p.de}</span> <span className="text-neutral-600">→</span> <span className="font-semibold">{p.para}</span></p>
                <p className="mt-1 flex flex-wrap items-baseline gap-x-3">
                  {p.valor && <span className="text-xl tabular-nums">{reais(p.valor)}</span>}
                  {p.quando && <span className="text-xs text-neutral-600">{p.quando}</span>}
                </p>
                <p className="mt-1 text-sm">{p.como}</p>
                <Provas provas={p.provas} />
              </li>
            ))}
          </ol>
          {t.contrapontos.length > 0 && (
            <div className="mt-3 max-w-3xl rounded border border-neutral-300 p-3 text-sm" style={{ borderLeft: "6px solid var(--alegacao)" }}>
              <h3 className="font-semibold">O outro lado, nos próprios autos</h3>
              <ul className="mt-1 space-y-2">
                {t.contrapontos.map((c, k) => <li key={k}><span className="font-medium">{c.quem}:</span> {c.o_que}<Provas provas={c.provas} /></li>)}
              </ul>
            </div>
          )}
          {t.lacunas && <p className="mt-3 max-w-3xl text-sm text-neutral-700"><span className="font-semibold">O que falta:</span> {t.lacunas}</p>}
        </section>
      ))}

      {cruzamentos.map((cz) => (
        <section key={cz.id} aria-labelledby={`h-${cz.id}`}>
          <h2 id={`h-${cz.id}`} className="text-xl">{cz.titulo}</h2>
          <p className="mt-1 max-w-3xl text-sm text-neutral-700">{cz.explicacao}</p>
          <div className="mt-3 grid gap-x-6 gap-y-2 md:grid-cols-[auto_1fr_1fr]">
            <div className="hidden text-xs font-semibold text-neutral-600 md:block">data</div>
            <div className="hidden text-xs font-semibold text-neutral-600 md:block">o que a Procuradoria e o BC descrevem (autos)</div>
            <div className="hidden text-xs font-semibold text-neutral-600 md:block">o que os cartórios comunicaram (RIF)</div>
            {[...cz.eventos].sort((a, b) => a.data.localeCompare(b.data)).map((ev, i) => (
              <div key={i} className="contents">
                <div className="text-xs tabular-nums text-neutral-600 md:pt-2">{formatarData(ev.data)}</div>
                <div className={`folha border border-neutral-300 bg-white p-2 text-sm ${ev.lado === "autos" ? "" : "md:col-start-3"}`}>
                  <span className="mr-1 text-xs text-neutral-600 md:hidden">{ev.lado === "autos" ? "autos:" : "cartórios:"}</span>{ev.texto}
                  <Provas provas={[ev.prova]} />
                </div>
                {ev.lado === "autos" && <div className="hidden md:block" />}
              </div>
            ))}
          </div>
        </section>
      ))}

      <section aria-labelledby="graficos">
        <h2 id="graficos" className="text-xl">Dois recortes em barras</h2>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <Barras titulo="Para onde foi o dinheiro da igreja (dez/2024–dez/2025)" nota="Os dez maiores destinatários agregados pelo Banco do Brasil; os 20 somam R$ 11,5 mi. Fora daqui: R$ 8,3 mi em pagamentos de títulos e R$ 4,3 mi em CDB." itens={topSaidas} />
          <Barras titulo="Imóveis comprados ou doados pela Super, por mês da escritura" nota="Valores declarados nas escrituras comunicadas ao COAF; as compras de 2022 (R$ 65,5 mi) e a de 2023 (R$ 30,9 mi) não têm direção informada e ficam fora." itens={compras} />
        </div>
      </section>

      <section aria-labelledby="metodo" className="max-w-3xl text-sm">
        <h2 id="metodo" className="text-xl">Como esta página foi apurada</h2>
        <p className="mt-1 text-neutral-700">
          Seguimos três regras de manuais de jornalismo investigativo: &quot;seguir o dinheiro é uma questão de nomes&quot; — por isso a base começa por uma tabela de pessoas e empresas;
          &quot;anote de onde veio cada afirmação de fato&quot; — por isso cada passo aponta documento, página e quem afirma, e um passo sem prova não é publicado; e &quot;nunca tome o
          que outro veículo publicou como provado&quot; — por isso só entram peças dos autos e o relatório do COAF, nunca notícias. As fontes: GIJN,{" "}
          <a className="underline" href="https://gijn.org/resource/introduction-investigative-journalism-following-money/" rel="noreferrer">Following the Money</a> (Patrucic e Cosic, 2024) e{" "}
          <a className="underline" href="https://gijn.org/resource/introduction-investigative-journalism-fact-checking/" rel="noreferrer">Fact-Checking</a> (Elba, 2024).
        </p>
        <p className="mt-2 text-neutral-700">
          O outro lado: as respostas das defesas e as ressalvas do relator vêm dos próprios autos (não há entrevistas nesta página). O que a imprensa publicou como versão da igreja
          ou de empresas não entra por não constar dos autos. As tabelas completas, com filtros, estão em <Link className="underline" href="/rede-de-pagamentos">Rede de pagamentos</Link>;
          o arquivo curado dos trajetos (<code className="text-xs">stf/curadoria/trajetos.json</code>) está no repositório, e o exportador confere cada prova contra o banco antes de publicar.
        </p>
      </section>
    </div>
  );
}
