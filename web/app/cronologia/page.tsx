import { Cronologia } from "@/components/Cronologia";
import { getCronologia, getDecisoes, getProcessos } from "@/lib/data";

export default function PaginaCronologia() {
  const c = getCronologia();
  const processos = getProcessos().filter((p) => p.coletado && p.incidente).map((p) => ({ incidente: p.incidente as number, rotulo: `${p.classe} ${p.numero}` }));
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
      <Cronologia dados={c} processos={processos} rotulosResultado={getDecisoes().rotulos_resultado} />
    </div>
  );
}
