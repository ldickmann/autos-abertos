import Link from "next/link";
import { RedeDePagamentos } from "@/components/RedeDePagamentos";
import { formatarData, formatarReais, getFluxos } from "@/lib/data";

const ROTULO_SECAO: Record<string, string> = {
  suspeita: "comunicações de operações suspeitas (o comunicante analisou e considerou atípico)",
  automatica: "comunicações automáticas (critério objetivo, sem análise de mérito)",
  especie: "operações em espécie comunicadas por cartório (sem análise de mérito)",
};

/* A página diz primeiro o que este mapa é e o que não é; depois o mapa; depois cada comunicação do relatório,
   com o texto literal do comunicante. Tudo aponta para a página do documento de onde saiu. */
export default function PaginaRede() {
  const dados = getFluxos();
  const fonte = dados.fontes[0];
  const atorPorId = new Map(dados.atores.map((a) => [a.id, a]));
  const secoes = ["suspeita", "automatica", "especie"] as const;

  return (
    <div className="space-y-6">
      <header className="max-w-3xl">
        <h1 className="text-2xl">Rede de pagamentos</h1>
        {fonte ? (
          <>
            <p className="mt-1 text-sm text-neutral-700">
              O que o <strong>RIF nº {fonte.identificador}</strong> do {fonte.orgao} ({fonte.emitido_em ? formatarData(fonte.emitido_em) : ""}) descreve sobre quem pagou quanto a quem,
              reorganizado em {dados.resumo.atores} pessoas e empresas, {dados.resumo.comunicacoes} comunicações e {dados.resumo.transacoes} fluxos
              ({dados.resumo.individuais} operações datadas, {dados.resumo.agregadas} agregados). O relatório é a peça 2 da{" "}
              <Link className="underline" href={`/processo/${fonte.incidente}`}>{fonte.processo}</Link>, cujo sigilo foi levantado em 14/09/2026; a íntegra está em{" "}
              <Link className="underline" href={`/documento/${fonte.documento.id}`}>{fonte.documento.titulo ?? `documento ${fonte.documento.id}`}</Link> ({fonte.documento.paginas} páginas).
            </p>
            <div className="aviso-cartao mt-3 rounded border p-3 text-sm">
              <p className="font-semibold">O que este mapa não é</p>
              <ul className="mt-1 list-disc space-y-1 pl-5">
                <li>Não é prova: um RIF reúne comunicações de bancos, cooperativas, cartórios e concessionárias ao COAF sobre operações que <em>eles</em> consideraram atípicas ou que cruzaram um limite objetivo. O próprio relatório avisa que RIFs &quot;por si sós, não constituem prova&quot; (RE 1.055.941; Rcl 61.944).</li>
                <li>Não registra pagamentos do Banco Master nem de Daniel Vorcaro. Os fluxos giram em torno de entidades ligadas a Fabiano Campos Zettel; pessoas da família Vorcaro aparecem como remetentes para a igreja. O esquema de dados é genérico e receberá as outras peças do acervo.</li>
                <li>Aparecer aqui não significa ser investigado: vendedores de imóveis, prestadores de serviço e doadores constam porque o comunicante os citou.</li>
                <li>CPFs aparecem mascarados (***.###.###-**); RG, endereços e placas ficaram fora. O nome de cada pessoa é o que consta no relatório.</li>
              </ul>
            </div>
          </>
        ) : (
          <p className="mt-1 text-sm text-neutral-700">Nenhuma fonte de fluxos carregada ainda.</p>
        )}
      </header>

      {fonte && <RedeDePagamentos dados={dados} />}

      {fonte && (
        <section aria-labelledby="coms" className="space-y-3">
          <h2 id="coms" className="text-lg">As {dados.resumo.comunicacoes} comunicações, uma a uma</h2>
          <p className="max-w-3xl text-sm text-neutral-700">
            Cada bloco é uma comunicação do relatório, com o texto literal do comunicante (&quot;Informações adicionais&quot;) e o enquadramento normativo que ele invocou.
            Os valores dos cartórios são os declarados nas escrituras; o valor de referência é a avaliação fiscal.
          </p>
          {secoes.map((s) => {
            const coms = dados.comunicacoes.filter((c) => c.secao === s);
            if (!coms.length) return null;
            return (
              <div key={s}>
                <h3 className="mt-4 text-base font-semibold">{ROTULO_SECAO[s]} ({coms.length})</h3>
                <div className="mt-2 grid gap-3 md:grid-cols-2">
                  {coms.map((c) => {
                    const titular = c.titular_ator_id ? atorPorId.get(c.titular_ator_id) : undefined;
                    const tx = dados.transacoes.filter((t) => t.comunicacao_id === c.id && t.natureza !== "resumo_tipo");
                    return (
                      <article key={c.id} className="folha border border-neutral-300 bg-white p-4 text-sm" id={`com-${c.secao}-${c.numero}`}>
                        <p className="text-xs text-neutral-600">{c.segmento} · item {c.numero} · <Link className="underline" href={`/documento/${c.documento_id}#p-${c.pagina_inicio}`}>p. {c.pagina_inicio}{c.pagina_fim !== c.pagina_inicio ? `–${c.pagina_fim}` : ""}</Link></p>
                        <h4 className="text-base leading-tight">{titular?.nome ?? "titular não informado"}</h4>
                        <p className="mt-1 text-xs text-neutral-700">
                          {c.comunicante ?? "comunicante não informado"}{c.local ? `, ${c.local}` : ""} · {c.periodo_inicio ? formatarData(c.periodo_inicio) : ""}{c.periodo_fim && c.periodo_fim !== c.periodo_inicio ? ` a ${formatarData(c.periodo_fim)}` : ""}
                        </p>
                        <p className="mt-2 tabular-nums">
                          <span className="font-semibold">{formatarReais(c.valor_centavos)}</span>
                          {c.creditos_centavos != null && <span className="text-neutral-700"> · entradas {formatarReais(c.creditos_centavos)} · saídas {formatarReais(c.debitos_centavos)}</span>}
                        </p>
                        {tx.length > 0 && <p className="mt-1 text-xs text-neutral-700">{tx.length} fluxo(s) extraído(s); {c.participacoes.length} pessoas/empresas relacionadas.</p>}
                        {c.bens.map((b) => (
                          <p key={b.id} className="mt-1 text-xs">{b.tipo === "veiculo" ? "veículo" : "imóvel"}: {b.descricao}{b.valor_referencia_centavos ? ` · referência ${formatarReais(b.valor_referencia_centavos)}` : ""}</p>
                        ))}
                        {c.informacoes && (
                          <details className="mt-2">
                            <summary className="cursor-pointer text-xs underline">texto do comunicante</summary>
                            <q className="mt-1 block whitespace-pre-line border-l-2 border-neutral-300 pl-2 text-xs italic">{c.informacoes}</q>
                            {c.consideracoes && <q className="mt-1 block whitespace-pre-line border-l-2 border-neutral-300 pl-2 text-xs italic">{c.consideracoes}</q>}
                          </details>
                        )}
                        {c.ocorrencias.length > 0 && (
                          <p className="mt-2 text-xs text-neutral-600">enquadramento: {c.ocorrencias.map((o) => `${o.norma}${o.codigo ? `, ${o.codigo}` : ""}`).join("; ")}</p>
                        )}
                      </article>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </section>
      )}

      {fonte && (
        <section aria-labelledby="metodo" className="max-w-3xl text-sm text-neutral-700">
          <h2 id="metodo" className="text-lg text-neutral-900">Como foi feito</h2>
          <p className="mt-1">
            O PDF do relatório (sha256 <code className="text-xs">{fonte.documento.sha256?.slice(0, 16)}…</code>) veio do pacote de autos publicado pelo STF em 14/09/2026. As tabelas
            &quot;Relacionados&quot; e as listas de principais remetentes e destinatários foram lidas por programa; os fluxos narrativos (transferências datadas, escrituras, notas fiscais) foram transcritos
            à mão. Cada fluxo guarda a página e o trecho literal, e a carga só acontece se todo trecho for encontrado na página indicada. O dataset curado
            (<code className="text-xs">{fonte.curadoria_path}</code>, sha256 <code className="text-xs">{fonte.curadoria_sha256.slice(0, 16)}…</code>) e as tabelas estão no repositório;{" "}
            <a className="underline" href="data/fluxos.csv">fluxos.csv</a> tem uma linha por fluxo.
          </p>
        </section>
      )}
    </div>
  );
}
