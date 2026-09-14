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
        <h2 id="as" className="text-lg font-bold">Asserções que citam esta entidade ({assercoes.length})</h2>
        {assercoes.length === 0 ? <p className="text-sm text-neutral-700">Nenhuma ainda. A camada semântica ainda não foi executada sobre os documentos, ou nenhuma asserção validada cita este nome.</p> : (
          <ul className="mt-2 space-y-2 text-sm">
            {assercoes.map((a) => (
              <li key={a.id} className="rounded border border-neutral-300 bg-white p-3">
                <div className="flex flex-wrap items-center gap-2"><BadgeEpistemico tipo={a.tipo_epistemico} />{a.data_andamento && <span className="font-mono text-xs">{formatarData(a.data_andamento)}</span>}</div>
                <p className="mt-1">{a.texto}{a.atribuida_a ? <span className="text-neutral-700"> — atribuída a {a.atribuida_a}</span> : null}</p>
                <p className="text-xs text-neutral-700">fonte: <Link className="underline" href={`/documento/${a.documento?.id}#p-${a.pagina}`}>{a.documento?.titulo}, p. {a.pagina}</Link> — “{a.trecho_fonte}”</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
