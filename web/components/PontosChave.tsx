import Link from "next/link";
import type { ReactNode } from "react";
import { BadgeEpistemico } from "@/components/Badges";
import type { Prova } from "@/lib/tipos";

/*
  Bloco editorial que abre cada página: 3 a 6 frases curtas com número e fonte. Dois sabores:
  - `pontos` computados da base (contagens, datas) — a fonte é a própria página;
  - `pontos` curados (pontos_chave.json), que só chegam aqui com prova resolvida (documento, página, quem afirma).
*/
export type Ponto = { texto: ReactNode; provas?: Prova[]; fonte?: { href: string; rotulo: string } };

function rotuloProva(p: Prova): string {
  if (p.tipo === "comunicacao") return `${p.secao === "relatorio" ? "IPJ-A" : "RIF"} p. ${p.pagina}`;
  const t = (p.documento_titulo ?? "documento").replace(/ - .*$/, "");
  return `${t} p. ${p.pagina}`;
}

export function PontosChave({ titulo = "Pontos-chave", itens, nota, id = "pontos-chave" }: { titulo?: string; itens: Ponto[]; nota?: ReactNode; id?: string }) {
  if (!itens.length) return null;
  return (
    <section aria-labelledby={id} className="folha border border-neutral-300 bg-white p-4" style={{ borderLeft: "6px solid var(--marca)" }}>
      <h2 id={id} className="text-sm font-semibold uppercase tracking-wide text-neutral-700">{titulo}</h2>
      <ul className="mt-2 space-y-2">
        {itens.map((p, i) => (
          <li key={i} className="leitura text-base">
            {p.texto}
            {p.provas && p.provas.length > 0 && (
              <span className="ml-1 inline-flex flex-wrap gap-1 align-middle text-xs">
                {p.provas.map((pr, k) => (
                  <Link key={k} className="rounded border border-neutral-300 px-1.5 py-px no-underline hover:bg-neutral-100" href={`/documento/${pr.documento_id}#p-${pr.pagina}`}
                    title={pr.tipo === "assercao" ? `${pr.atribuida_a ?? "registro dos autos"}: ${pr.texto}` : pr.tipo === "documento" ? `${pr.atribuida_a ?? "peça"}: “${pr.trecho_fonte}”` : `${pr.comunicante ?? "comunicante"} ao COAF`}>
                    {pr.tipo === "assercao" ? <BadgeEpistemico tipo={pr.tipo_epistemico} /> : <span className="carimbo rounded-sm border px-1 text-[10px] font-medium">{pr.tipo === "documento" ? "peça" : pr.secao === "relatorio" ? "PF" : "COAF"}</span>} {rotuloProva(pr)}
                  </Link>
                ))}
              </span>
            )}
            {p.fonte && <> <Link className="text-xs underline" href={p.fonte.href}>{p.fonte.rotulo}</Link></>}
          </li>
        ))}
      </ul>
      {nota && <p className="mt-2 text-xs text-neutral-600">{nota}</p>}
    </section>
  );
}
