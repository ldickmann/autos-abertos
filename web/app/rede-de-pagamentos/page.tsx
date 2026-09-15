import Link from "next/link";
import { PainelFluxos, type SituacaoAutos } from "@/components/TabelasDeFluxos";
import { formatarData, formatarReais, getEntidades, getFluxos, nomeProprio } from "@/lib/data";

/* Página de dados: o que o relatório diz sobre quem pagou quanto a quem, em tabelas com busca, filtros e ordenação.
   Primeiro o que é (e o que não é), depois os números-resumo, depois o painel de tabelas, depois como reproduzir. */
export default function PaginaRede() {
  const dados = getFluxos();
  const fonte = dados.fontes[0];
  if (!fonte) return <p className="text-sm text-neutral-700">Nenhuma fonte de fluxos carregada ainda.</p>;
  const fontes = dados.fontes;

  // situação nos autos: o status literal do portal para quem também é parte em algum processo do caso
  const entPorId = new Map(getEntidades().map((e) => [e.id, e]));
  const situacoes: Record<number, SituacaoAutos> = {};
  for (const a of dados.atores) {
    const e = a.entidade_id ? entPorId.get(a.entidade_id) : undefined;
    if (!e || !e.mencoes.length) continue;   // citada só em documentos: não é parte, não tem status
    const status = [...new Set(e.mencoes.map((m) => m.status_processual).filter(Boolean))];
    situacoes[a.id] = { entidade_id: e.id, status: status.join(" / ") || "parte", processos: [...new Set(e.mencoes.map((m) => m.processo).filter((p): p is string => !!p))] };
  }

  const atorPorId = new Map(dados.atores.map((a) => [a.id, a]));
  const semResumo = dados.transacoes.filter((t) => t.natureza !== "resumo_tipo" && t.situacao === "efetuado");
  const somaPor = (chave: (t: (typeof semResumo)[number]) => number | null) => {
    const m = new Map<number, number>();
    for (const t of semResumo) { const k = chave(t); if (k != null) m.set(k, (m.get(k) ?? 0) + t.valor_centavos); }
    return [...m.entries()].sort((x, y) => y[1] - x[1]).slice(0, 5).map(([id, v]) => ({ nome: atorPorId.get(id)?.nome ?? String(id), valor: v }));
  };
  const maisReceberam = somaPor((t) => t.destino_ator_id);
  const maisPagaram = somaPor((t) => t.origem_ator_id);
  const totalComunicado = dados.comunicacoes.reduce((s, c) => s + (c.valor_centavos ?? 0), 0);
  const totalDatado = semResumo.filter((t) => t.natureza === "individual").reduce((s, t) => s + t.valor_centavos, 0);
  const porAno = new Map<string, number>();
  for (const t of semResumo) { const a = (t.data ?? t.periodo_inicio ?? "").slice(0, 4); if (a) porAno.set(a, (porAno.get(a) ?? 0) + t.valor_centavos); }
  const partes = dados.atores.filter((a) => situacoes[a.id]).length;

  return (
    <div className="space-y-6">
      <header className="max-w-3xl">
        <h1 className="text-2xl">Rede de pagamentos</h1>
        <p className="mt-1 text-sm text-neutral-700">
          Quem pagou quanto a quem, segundo as peças dos autos, em tabelas com busca, filtros e ordenação. Cada linha aponta a página e o trecho de onde saiu. Fontes carregadas:
        </p>
        <ul className="mt-1 list-disc pl-5 text-sm text-neutral-700">
          {fontes.map((f) => (
            <li key={f.id}><strong>{f.identificador}</strong> ({f.orgao}{f.emitido_em ? `, ${formatarData(f.emitido_em)}` : ""}) — <Link className="underline" href={`/documento/${f.documento.id}`}>{f.documento.titulo ?? "documento"}</Link>{f.documento.paginas ? `, ${f.documento.paginas} p.` : ""} na <Link className="underline" href={`/processo/${f.incidente}`}>{f.processo}</Link></li>
          ))}
        </ul>
        <Link href="/rede-de-pagamentos/trajetos" className="folha mt-3 block max-w-3xl border border-neutral-300 bg-white p-4 no-underline" style={{ borderLeft: "6px solid var(--marca)" }}>
          <span className="leitura block text-lg">Como esse dinheiro se liga ao Banco Master e a Daniel Vorcaro?</span>
          <span className="mt-1 block text-sm text-neutral-700">Os caminhos do dinheiro, passo a passo: do caixa do banco à Super, da Super à igreja e aos fornecedores, e a ponta que ainda está no escuro — cada passo com quem afirma e onde está escrito.</span>
        </Link>
      </header>

      <PainelFluxos dados={dados} situacoes={situacoes} />

      <section aria-labelledby="resumo">
        <h2 id="resumo" className="text-lg">Em números</h2>
        <p className="text-xs text-neutral-600">Somas de operações datadas e agregados informados pelo comunicante (sem os resumos por tipo). Uma escritura conta pelo valor declarado.</p>
        <dl className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="folha border border-neutral-300 bg-white p-3"><dt className="text-xs text-neutral-700">Valor total das {dados.resumo.comunicacoes} comunicações</dt><dd className="mt-1 text-xl tabular-nums">{formatarReais(totalComunicado)}</dd><dd className="text-xs text-neutral-600">soma do que cada comunicante declarou (há sobreposição entre elas)</dd></div>
          <div className="folha border border-neutral-300 bg-white p-3"><dt className="text-xs text-neutral-700">Operações datadas</dt><dd className="mt-1 text-xl tabular-nums">{formatarReais(totalDatado)}</dd><dd className="text-xs text-neutral-600">{semResumo.filter((t) => t.natureza === "individual").length} transferências, escrituras e compras com data, efetuadas</dd></div>
          <div className="folha border border-neutral-300 bg-white p-3"><dt className="text-xs text-neutral-700">Pessoas e empresas</dt><dd className="mt-1 text-xl tabular-nums">{dados.resumo.atores}</dd><dd className="text-xs text-neutral-600">{partes} também são partes nos processos do caso</dd></div>
          <div className="folha border border-neutral-300 bg-white p-3"><dt className="text-xs text-neutral-700">Por ano</dt><dd className="mt-1 text-sm tabular-nums">{[...porAno.entries()].sort().map(([a, v]) => <span key={a} className="mr-3 inline-block">{a}: {formatarReais(v, true)}</span>)}</dd><dd className="text-xs text-neutral-600">operações datadas e agregados, pelo ano informado</dd></div>
        </dl>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <div className="folha border border-neutral-300 bg-white p-3 text-sm">
            <h3 className="font-semibold">Quem mais recebeu</h3>
            <ol className="mt-1 list-decimal space-y-0.5 pl-5">{maisReceberam.map((x) => <li key={x.nome}><a className="underline" href={`?q=${encodeURIComponent(x.nome)}#painel`} title="Abrir o painel já filtrado por este nome">{nomeProprio(x.nome)}</a> <span className="tabular-nums text-neutral-700">{formatarReais(x.valor)}</span></li>)}</ol>
          </div>
          <div className="folha border border-neutral-300 bg-white p-3 text-sm">
            <h3 className="font-semibold">Quem mais pagou</h3>
            <ol className="mt-1 list-decimal space-y-0.5 pl-5">{maisPagaram.map((x) => <li key={x.nome}><a className="underline" href={`?q=${encodeURIComponent(x.nome)}#painel`} title="Abrir o painel já filtrado por este nome">{nomeProprio(x.nome)}</a> <span className="tabular-nums text-neutral-700">{formatarReais(x.valor)}</span></li>)}</ol>
          </div>
        </div>
      </section>

      <section aria-labelledby="ressalvas" className="max-w-3xl text-sm">
        <h2 id="ressalvas" className="text-lg">Leia antes de tirar conclusões</h2>
        <details className="aviso-cartao mt-2 rounded border p-3 text-sm" open>
          <summary className="cursor-pointer font-semibold">O que estes dados são e não são</summary>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            <li>Não são prova: o RIF reúne o que bancos, cooperativas, cartórios e concessionárias comunicaram ao COAF por considerarem atípico ou por cruzar um limite objetivo — o próprio relatório avisa que RIFs &quot;por si sós, não constituem prova&quot; (RE 1.055.941; Rcl 61.944); a informação da PF é a leitura policial de mensagens de um celular, feita em 72 horas e, nas palavras da própria PF, sem &quot;caráter exaustivo&quot;. A PGR opinou pela nulidade da ordem que gerou essa análise; o Plenário decide em 15/09/2026.</li>
            <li>Cada fluxo tem uma <strong>situação</strong>: efetuado (a peça descreve o pagamento como feito), previsto (valor de contrato) ou cobrado (fatura emitida, pagamento não confirmado). Só os efetuados entram nas somas.</li>
            <li>Aparecer aqui não significa ser investigado: vendedores de imóveis, prestadores de serviço e doadores constam porque o comunicante os citou. A coluna &quot;situação nos autos&quot; mostra o status literal do portal do STF só para quem é parte em algum processo do caso.</li>
            <li>CPFs aparecem mascarados (***.###.###-**); RG, endereços e placas ficaram fora. Os nomes são os que constam no relatório.</li>
          </ul>
        </details>
      </section>

      <section aria-labelledby="dados" className="max-w-3xl text-sm">
        <h2 id="dados" className="text-lg">Baixar os dados</h2>
        <ul className="mt-2 flex flex-wrap gap-2">
          {[["fluxos_atores.csv", "pessoas e empresas"], ["fluxos.csv", "fluxos (transações)"], ["fluxos_comunicacoes.csv", "comunicações"], ["fluxos_bens.csv", "bens"], ["fluxos.json", "tudo, em JSON"]].map(([a, r]) => (
            <li key={a}><a className="toque rounded border border-neutral-400 px-3 py-1 underline hover:bg-neutral-100" href={`data/${a}`}>{a}</a> <span className="text-xs text-neutral-600">{r}</span></li>
          ))}
        </ul>
        <h3 className="mt-4 font-semibold">Dicionário de dados</h3>
        <p className="mt-1 text-neutral-700">Modelo em estrela: uma tabela de fatos (fluxos) e três de dimensões (pessoas/empresas, comunicações, bens), todas no banco <code>data/stf.sqlite</code> do repositório (tabelas <code>fluxo_*</code>). Valores em centavos inteiros no banco e em reais com ponto decimal nos CSV; datas ISO (AAAA-MM-DD).</p>
        <dl className="mt-2 grid gap-x-6 gap-y-1 sm:grid-cols-[max-content_1fr]">
          <dt className="font-medium">natureza</dt><dd><em>operação datada</em>: uma transação com data (extrato, escritura, nota fiscal); <em>agregado</em>: &quot;N lançamentos totalizando X&quot; num período, como o banco informou; <em>resumo por tipo</em>: total por tipo de transação no período (PIX, boleto…), que repete os agregados e por isso fica fora das somas.</dd>
          <dt className="font-medium">tipo de comunicação</dt><dd><em>suspeita</em>: o comunicante analisou e considerou atípico; <em>automática</em>: critério objetivo (ex.: valor declarado acima de 100% da avaliação fiscal), sem análise de mérito; <em>em espécie</em>: pagamento de R$ 100 mil ou mais comunicado por tabelião.</dd>
          <dt className="font-medium">papel no relatório</dt><dd>como a pessoa aparece na tabela &quot;Relacionados&quot; de cada comunicação: titular, remetente, beneficiário, responsável, procurador, vendedor, outros.</dd>
          <dt className="font-medium">situação nos autos</dt><dd>status processual literal do portal do STF (investigado, requerido, interessado…) quando a mesma pessoa é parte em algum processo do caso; ligação por nome exato.</dd>
          <dt className="font-medium">de / para não informado</dt><dd>o comunicante não nomeou a outra ponta (boletos, concessionária).</dd>
          <dt className="font-medium">valor de referência</dt><dd>avaliação fiscal ou valor venal informado pelo cartório; a razão declarado ÷ referência é o que dispara a comunicação automática.</dd>
          <dt className="font-medium">página e trecho</dt><dd>onde cada fluxo está no PDF; a carga no banco só aceita um fluxo se o trecho literal for encontrado na página indicada.</dd>
        </dl>
        <h3 className="mt-4 font-semibold">Consultas prontas (SQLite)</h3>
        <pre className="mt-1 overflow-x-auto rounded border border-neutral-300 bg-neutral-50 p-3 text-xs"><code>{`-- quem mais recebeu (sem resumos por tipo)
SELECT d.nome, SUM(t.valor_centavos)/100.0 AS reais, COUNT(*) AS fluxos
FROM fluxo_transacao t JOIN fluxo_ator d ON d.id = t.destino_ator_id
WHERE t.natureza != 'resumo_tipo' GROUP BY d.id ORDER BY reais DESC;

-- tudo o que envolve uma pessoa, com página e trecho
SELECT o.nome AS de, d.nome AS para, t.valor_centavos/100.0 AS reais, t.data, t.tipo, t.pagina, t.trecho_fonte
FROM fluxo_transacao t LEFT JOIN fluxo_ator o ON o.id = t.origem_ator_id LEFT JOIN fluxo_ator d ON d.id = t.destino_ator_id
WHERE o.nome LIKE '%ZETTEL%' OR d.nome LIKE '%ZETTEL%' ORDER BY t.valor_centavos DESC;

-- pessoas do relatório que também são partes nos autos
SELECT a.nome, a.documento_mascarado, e.nome AS entidade FROM fluxo_ator a JOIN entidade e ON e.id = a.entidade_id;`}</code></pre>
        <h3 className="mt-4 font-semibold">Como foi feito</h3>
        <p className="mt-1 text-neutral-700">
          O PDF (sha256 <code className="text-xs">{fonte.documento.sha256?.slice(0, 16)}…</code>) veio do pacote de autos publicado pelo STF em 14/09/2026. As tabelas &quot;Relacionados&quot; e as listas de principais remetentes e destinatários
          foram lidas por programa; os fluxos narrativos foram transcritos à mão com o trecho literal. O dataset curado (<code className="text-xs">{fonte.curadoria_path}</code>, sha256 <code className="text-xs">{fonte.curadoria_sha256.slice(0, 16)}…</code>)
          e os testes de consistência com os totais do documento estão no repositório; veja <Link className="underline" href="/verificar">como verificar</Link>.
        </p>
      </section>
    </div>
  );
}
