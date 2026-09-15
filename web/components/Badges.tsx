import type { Snapshot, TipoEpistemico } from "@/lib/tipos";
import { formatarDataHora } from "@/lib/tipos";

export const TIPOS: Record<TipoEpistemico, { rotulo: string; classe: string; abreviacao: string }> = {
  fato_processual: { rotulo: "Fato processual", abreviacao: "fato", classe: "bg-emerald-100 text-emerald-900 border-emerald-700" },
  alegacao_parte: { rotulo: "Alegação de parte", abreviacao: "alegação", classe: "bg-amber-100 text-amber-900 border-amber-700" },
  fundamento_decisorio: { rotulo: "Fundamento decisório", abreviacao: "fundamento", classe: "bg-sky-100 text-sky-900 border-sky-800" },
};

export function BadgeEpistemico({ tipo }: { tipo: TipoEpistemico }) {
  const t = TIPOS[tipo];
  return (
    <span
      className={`carimbo rounded-sm border px-1.5 py-px text-xs font-medium ${t.classe}`}
      title={t.rotulo}
    >
      {t.abreviacao}
      <span className="sr-only"> ({t.rotulo})</span>
    </span>
  );
}

export function LegendaEpistemica({ descricoes }: { descricoes: Record<TipoEpistemico, string> }) {
  return (
    <details className="folha border border-neutral-300 bg-white p-3 text-sm">
      <summary className="cursor-pointer font-semibold">O que significam os três tipos de afirmação</summary>
      <dl className="mt-2 space-y-2">
        {(Object.keys(TIPOS) as TipoEpistemico[]).map((k) => (
          <div key={k} className="flex gap-3">
            <dt className="shrink-0"><BadgeEpistemico tipo={k} /></dt>
            <dd>
              <span className="font-medium">{TIPOS[k].rotulo}.</span> {descricoes[k]}
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-2 text-neutral-700">
        Toda afirmação aponta para o documento e a página de onde foi extraída, com o trecho literal. O sistema nunca
        conclui nada sobre conduta, caráter ou intenção de qualquer pessoa; se o modelo não consegue classificar
        com segurança, a afirmação é descartada.
      </p>
    </details>
  );
}

export function Carimbo({ snapshot, prefixo = "dados coletados em" }: { snapshot: Snapshot; prefixo?: string }) {
  if (!snapshot) return <span className="text-xs text-neutral-600">{prefixo}: —</span>;
  return (
    <span className="text-xs text-neutral-700" title={`snapshot ${snapshot.id} · sha256 ${snapshot.sha256}`}>
      {prefixo} {formatarDataHora(snapshot.fetched_at)}
    </span>
  );
}

export function StatusProcessual({ status, literal }: { status: string; literal?: string }) {
  return (
    <span
      className="inline-block rounded-full border border-neutral-500 bg-neutral-50 px-2 py-0.5 text-xs font-medium text-neutral-900"
      title={literal ? `no portal do STF: ${literal}` : undefined}
    >
      {status}
    </span>
  );
}

export function Publicidade({ valor }: { valor: string | null | undefined }) {
  if (!valor) return null;
  const sig = valor.toLowerCase().startsWith("sigil");
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${sig ? "bg-neutral-800 text-white" : "bg-emerald-700 text-white"}`}>
      {valor}
    </span>
  );
}
