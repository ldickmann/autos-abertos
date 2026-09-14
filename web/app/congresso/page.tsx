import { ListaMaterias } from "@/components/ListaMaterias";
import { PontosChave } from "@/components/PontosChave";
import { formatarData, getLegislativo } from "@/lib/data";

export default function PaginaCongresso() {
  const materias = getLegislativo();
  const senado = materias.filter((m) => m.casa === "senado").length;
  const camara = materias.filter((m) => m.casa === "camara").length;
  const porSigla = new Map<string, number>();
  for (const m of materias) if (m.sigla) porSigla.set(m.sigla, (porSigla.get(m.sigla) ?? 0) + 1);
  const siglas = [...porSigla.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4).map(([s, n]) => `${n} ${s}`);
  const datadas = materias.filter((m) => m.data).sort((a, b) => (b.data ?? "").localeCompare(a.data ?? ""));
  const recente = datadas[0];
  const cpi = materias.filter((m) => /CPI|comiss[ãa]o parlamentar de inqu[ée]rito/i.test(m.ementa)).length;
  const pontos = [
    { texto: <><strong>{materias.length} matérias</strong> ({senado} no Senado, {camara} na Câmara): {siglas.join(", ")}.</> },
    { texto: <>{cpi} mencionam CPI ou comissão parlamentar de inquérito; as demais são requerimentos de informação, convocações e propostas de fiscalização.</> },
    ...(recente ? [{ texto: <>Mais recente: <strong>{formatarData(recente.data)}</strong>, {recente.identificacao ?? `${recente.sigla} ${recente.numero}/${recente.ano}`} — {recente.ementa.slice(0, 160)}{recente.ementa.length > 160 ? "…" : ""}</>, fonte: { href: recente.url, rotulo: "tramitação" } }] : []),
  ];
  return (
    <div className="space-y-4">
      <header className="max-w-3xl">
        <h1 className="text-2xl">O caso no Congresso Nacional</h1>
        <p className="leitura mt-1">
          O que Senado e Câmara fizeram, em requerimentos e propostas oficiais, sobre o caso: convocações, pedidos de informação ao Banco Central,
          pedidos de CPI, propostas de fiscalização. São {materias.length} matérias ({senado} do Senado, {camara} da Câmara), obtidas pelas APIs oficiais de dados abertos
          das duas Casas com buscas por palavra-chave, cada uma com o link para a tramitação.
        </p>
        <p className="mt-1 text-sm text-neutral-700">
          As ementas são as do próprio Congresso; o site não as interpreta. A busca da Câmara por palavra-chave alcança menos matérias que a do Senado; as consultas são repetidas a cada rodada e as respostas ficam guardadas com hash.
        </p>
      </header>
      <PontosChave itens={pontos} />
      <ListaMaterias materias={materias} />
    </div>
  );
}
