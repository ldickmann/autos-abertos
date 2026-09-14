import Link from "next/link";
import { BadgeEpistemico, StatusProcessual } from "@/components/Badges";
import { formatarData, getAssercoes, getEntidades, getGrafo } from "@/lib/data";

export function generateStaticParams() {
  return getEntidades().map((e) => ({ id: String(e.id) }));
}

export default async function PaginaEntidade({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const ent = getEntidades().find((e) => e.id === Number(id));
  if (!ent) return <p>Entidade não encontrada.</p>;
  const grafo = getGrafo();
  const meuId = `entidade:${ent.id}`;
  const rotulo = new Map(grafo.nodes.map((n) => [n.id, n.rotulo]));
  const representa = grafo.edges.filter((e) => e.tipo === "representa" && e.origem === meuId);
  const representadoPor = grafo.edges.filter((e) => e.tipo === "representa" && e.destino === meuId);
  const assercoes = getAssercoes().filter((a) => a.entidades.some((x) => x.entidade_id === ent.id));

  return (
    <div className="space-y-6">
      <nav aria-label="Trilha" className="text-sm"><Link className="underline" href="/entidades">Entidades</Link> / {ent.nome}</nav>
      <header className="rounded-lg border border-neutral-300 bg-white p-5">
        <h1 className="text-2xl font-bold">{ent.nome}</h1>
        <p className="mt-1 text-sm text-neutral-700">
          {ent.tipo}{ent.natureza_provavel ? ` · ${ent.natureza_provavel.replace("_", " ")} (pelo sufixo do nome)` : ""} · origem: {ent.origem === "partes" ? "cadastro de partes do portal" : "citada em documento"}
          {ent.status_padrao ? ` · status: ${ent.status_padrao}` : ""}
        </p>
        <p className="mt-2 text-xs text-neutral-700">
          Identidade por {ent.chave.startsWith("oab:") ? "número de OAB" : "nome exato"}. Homônimos sem OAB podem estar agrupados; cada menção abaixo mostra o processo e o papel literal.
        </p>
      </header>

      <section aria-labelledby="st">
        <h2 id="st" className="text-lg font-bold">Status processual por processo</h2>
        {ent.mencoes.length === 0 ? <p className="text-sm">Não consta como parte em nenhum processo coletado.</p> : (
          <ul className="mt-2 space-y-1 text-sm">
            {ent.mencoes.map((m, i) => (
              <li key={i} className="flex flex-wrap items-center gap-2">
                <StatusProcessual status={m.status_processual} literal={m.papel_portal} />
                <Link className="underline" href={`/processo/${m.incidente}`}>{m.processo ?? `incidente ${m.incidente}`}</Link>
                <span className="text-xs text-neutral-600">({m.papel_portal})</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {(representa.length > 0 || representadoPor.length > 0) && (
        <section aria-labelledby="rep">
          <h2 id="rep" className="text-lg font-bold">Representação (conforme o agrupamento do portal)</h2>
          {representa.length > 0 && <p className="mt-1 text-sm">Representa: {Array.from(new Set(representa.map((e) => e.destino))).map((d) => <Link key={d} className="mr-3 underline" href={`/${d.replace(":", "/")}`}>{rotulo.get(d)}</Link>)}</p>}
          {representadoPor.length > 0 && <p className="mt-1 text-sm">Representado(a) por: {Array.from(new Set(representadoPor.map((e) => e.origem))).map((d) => <Link key={d} className="mr-3 underline" href={`/${d.replace(":", "/")}`}>{rotulo.get(d)}</Link>)}</p>}
        </section>
      )}

      <section aria-labelledby="as">
        <h2 id="as" className="text-lg font-bold">Quem diz o quê sobre esta entidade <span className="text-sm font-normal text-neutral-700">({assercoes.length} asserções)</span></h2>
        <p className="mt-1 text-sm text-neutral-700">
          Separado por natureza: o que o juízo registrou como fato, o que cada parte alegou e o que cada julgador adotou como fundamento. Cada item aponta o documento, a página e o trecho literal.
          Alegação não é fato, e fundamento é a razão declarada pelo julgador; nada aqui é conclusão do site.
        </p>
        {assercoes.length === 0 ? <p className="mt-2 text-sm text-neutral-700">Nenhuma asserção validada cita este nome.</p> : (
          <div className="mt-3 grid gap-4 lg:grid-cols-3">
            {(["fato_processual", "alegacao_parte", "fundamento_decisorio"] as const).map((tipo) => {
              const lista = assercoes.filter((a) => a.tipo_epistemico === tipo);
              const grupos = new Map<string, typeof lista>();
              for (const a of lista) { const k = tipo === "fato_processual" ? "registro nos autos" : (a.atribuida_a ?? "sem atribuição"); grupos.set(k, [...(grupos.get(k) ?? []), a]); }
              return (
                <div key={tipo} className="min-w-0">
                  <h3 className="flex items-center gap-2 text-sm font-semibold"><BadgeEpistemico tipo={tipo} /> {lista.length}</h3>
                  {lista.length === 0 && <p className="mt-1 text-xs text-neutral-600">nenhuma</p>}
                  <div className="mt-2 space-y-2">
                    {[...grupos.entries()].sort((a, b) => b[1].length - a[1].length).map(([quem, itens]) => (
                      <details key={quem} className="folha border border-neutral-300 bg-white p-2 text-sm" open={grupos.size === 1 && itens.length <= 6}>
                        <summary className="cursor-pointer font-medium">{quem} <span className="font-normal text-neutral-600">({itens.length})</span></summary>
                        <ul className="mt-2 space-y-2">
                          {itens.map((a) => (
                            <li key={a.id}>
                              <p className="leitura">{a.texto}</p>
                              <p className="text-xs text-neutral-700">{a.data_andamento ? <span className="font-mono">{formatarData(a.data_andamento)} · </span> : null}<Link className="toque underline" href={`/documento/${a.documento?.id}#p-${a.pagina}`}>{a.documento?.titulo}, p. {a.pagina}</Link></p>
                              <details className="text-xs text-neutral-700"><summary className="cursor-pointer">trecho literal</summary><blockquote className="leitura mt-1 border-l-2 border-neutral-400 pl-2">“{a.trecho_fonte}”</blockquote></details>
                            </li>
                          ))}
                        </ul>
                      </details>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
