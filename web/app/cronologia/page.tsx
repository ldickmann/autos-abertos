import { Cronologia } from "@/components/Cronologia";
import { PontosChave } from "@/components/PontosChave";
import { formatarData, getCronologia, getDecisoes, getProcessos } from "@/lib/data";

export default function PaginaCronologia() {
  const c = getCronologia();
  const processos = getProcessos().filter((p) => p.coletado && p.incidente).map((p) => ({ incidente: p.incidente as number, rotulo: `${p.classe} ${p.numero}` }));
  const recentes = c.eventos.filter((e) => e.data >= "2025-01-01").sort((a, b) => b.data.localeCompare(a.data));
  const ultimo = recentes[0];
  const alegacoes = c.eventos.filter((e) => e.tipo === "assercao" && e.tipo_epistemico === "alegacao_parte").length;
  const fundamentos = c.eventos.filter((e) => e.tipo === "assercao" && e.tipo_epistemico === "fundamento_decisorio").length;
  const primeiroDia = recentes.at(-1)?.data;
  const pontos = [
    { texto: <><strong>{recentes.length} acontecimentos datados</strong> {primeiroDia ? `de ${formatarData(primeiroDia)} ` : ""}a {ultimo ? formatarData(ultimo.data) : "—"}, em três origens: registros do portal, datas escritas nos documentos e decisões pedido → resultado.</> },
    ...(ultimo ? [{ texto: <>Mais recente: <strong>{formatarData(ultimo.data)}</strong> — {ultimo.texto.slice(0, 180)}{ultimo.texto.length > 180 ? "…" : ""}{ultimo.atribuida_a ? ` (${ultimo.atribuida_a})` : ""}.</>, fonte: ultimo.documento_id ? { href: `/documento/${ultimo.documento_id}#p-${ultimo.pagina}`, rotulo: `p. ${ultimo.pagina}` } : undefined }] : []),
    { texto: <>Das afirmações com data, {alegacoes} são alegações de partes (PF, Procuradoria, defesas) e {fundamentos} são fundamentos de ministros — a página separa uma coisa da outra.</> },
  ];
  return (
    <div className="space-y-4">
      <header className="max-w-3xl">
        <h1 className="text-2xl">Cronologia: o que aconteceu, quando e segundo quem</h1>
        <p className="leitura mt-1">
          Três origens num fio só, sem misturar: o que o portal do STF registrou ({c.por_fonte.portal} decisões, julgamentos, recursos e distribuições),
          o que os próprios documentos dizem que aconteceu e em que data ({c.eventos.filter((e) => e.tipo === "assercao").length} afirmações com data no trecho literal,
          cada uma marcada como fato, alegação ou fundamento e atribuída a quem a fez) e as decisões pedido → resultado ({c.eventos.filter((e) => e.tipo === "decisao").length}).
        </p>
        <p className="mt-1 text-sm text-neutral-700">
          A data de cada afirmação é a que está escrita no trecho citado (conferida por regra, sem modelo). Quando um trecho tem mais de uma data, ele fica fora daqui.
          Datas anteriores a 2025 são jurisprudência e leis citadas, e ficam ocultas por padrão.
        </p>
      </header>
      <PontosChave itens={pontos} nota="Filtre abaixo por origem, tipo, processo e período; a busca vale para o texto dos eventos." />
      <Cronologia dados={c} processos={processos} rotulosResultado={getDecisoes().rotulos_resultado} />
    </div>
  );
}
