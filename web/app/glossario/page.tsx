import { PontosChave } from "@/components/PontosChave";
import { getGlossario } from "@/lib/data";

export default function PaginaGlossario() {
  const verbetes = [...getGlossario()].sort((a, b) => a.termo.localeCompare(b.termo, "pt-BR"));
  const basicos = ["Prisão preventiva", "Petição (Pet)", "Inquérito (Inq)", "Referendo", "Relator", "Sigilo"].filter((t) => verbetes.some((v) => v.termo.toLowerCase().startsWith(t.toLowerCase().split(" ")[0])));
  const pontos = [
    { texto: <><strong>{verbetes.length} termos</strong> explicados em linguagem comum: o que é uma Pet, um Inq, uma prisão preventiva, um referendo, um relator, um agravo.</> },
    { texto: <>Para começar: {basicos.map((t) => t.split(" (")[0]).join(", ")}. Nas outras páginas, os termos sublinhados abrem a mesma explicação sem sair do lugar.</> },
    { texto: <>As definições são gerais, do processo penal e do funcionamento do STF; não dizem nada sobre este caso nem sobre as pessoas envolvidas.</> },
  ];
  return (
    <div className="space-y-4">
      <header className="max-w-3xl">
        <h1 className="text-2xl">Glossário</h1>
        <p className="leitura mt-1">
          O que significam os termos que aparecem nos autos, explicados para quem não é da área. São definições gerais do processo penal
          e do funcionamento do STF; não dizem nada sobre este caso nem sobre as pessoas envolvidas.
        </p>
        <p className="mt-1 text-sm text-neutral-700">Texto editorial, curado e versionado com o código (<code>stf/curadoria/glossario.json</code>). Nas páginas, os termos sublinhados abrem a mesma explicação.</p>
      </header>
      <PontosChave titulo="O que você encontra aqui" itens={pontos} />
      <dl className="grid gap-3 md:grid-cols-2">
        {verbetes.map((v) => (
          <div key={v.termo} id={v.termo.toLowerCase().replace(/[^a-z0-9]+/g, "-")} className="folha border border-neutral-300 bg-white p-3">
            <dt className="font-semibold">{v.termo}</dt>
            <dd className="leitura mt-1 text-sm">{v.explicacao}{v.mais ? <span className="block mt-1 text-neutral-700">{v.mais}</span> : null}</dd>
            {v.formas.length > 0 && <dd className="mt-1 text-xs text-neutral-600">no portal e nos documentos: {v.formas.join(", ")}</dd>}
          </div>
        ))}
      </dl>
    </div>
  );
}
