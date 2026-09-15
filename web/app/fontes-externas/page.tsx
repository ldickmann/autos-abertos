import Link from "next/link";
import { PontosChave } from "@/components/PontosChave";
import { getFontesExternas } from "@/lib/data";
import { formatarDataHora } from "@/lib/tipos";

/* Fontes oficiais fora do portal do STF, com cópia (hash) e histórico, para o caso não depender de um único portal. */
export default function PaginaFontesExternas() {
  const fontes = getFontesExternas();
  const porOrgao = new Map<string, typeof fontes>();
  const ordem = ["Judiciário", "Executivo (Polícia Federal)", "Executivo (Ministério da Justiça)", "Executivo (autarquia)", "Legislativo", "Legislativo (DF)", "Controle externo (DF)", "Terceiros"];
  for (const f of [...fontes].sort((a, b) => ordem.indexOf(a.poder ?? "Outros") - ordem.indexOf(b.poder ?? "Outros"))) porOrgao.set(f.poder ?? "Outros", [...(porOrgao.get(f.poder ?? "Outros") ?? []), f]);
  const comCopia = fontes.filter((f) => f.ultima?.sha256).length;
  const mudaram = fontes.filter((f) => f.mudou).length;
  const orgaos = [...new Set(fontes.map((f) => f.orgao))];
  const ultimaCaptura = fontes.map((f) => f.ultima?.fetched_at).filter(Boolean).sort().at(-1);
  const pontos = [
    { texto: <><strong>{fontes.length} fontes oficiais</strong> de {orgaos.length} órgãos ({orgaos.slice(0, 7).join(", ")}{orgaos.length > 7 ? "…" : ""}), {comCopia} com cópia e impressão digital guardadas.</> },
    { texto: <>{mudaram === 0 ? "Nenhuma delas mudou entre uma cópia e outra até agora." : `${mudaram} mudaram de conteúdo entre uma cópia e outra — o histórico de cada uma está abaixo.`}{ultimaCaptura ? ` Última captura: ${formatarDataHora(ultimaCaptura)}.` : ""}</> },
    { texto: <>Por que importa: a liquidação do Master pelo Banco Central, as fases da operação da PF e os atos do Congresso são fatos oficiais fora dos autos do STF; aqui cada um tem endereço, data e cópia.</> },
  ];
  return (
    <div className="space-y-6">
      <header className="max-w-3xl">
        <h1 className="text-2xl">Fontes oficiais fora do STF</h1>
        <p className="leitura mt-1">
          O caso não vive só no portal do STF: a Polícia Federal publica cada fase da operação, o Banco Central decretou a liquidação e publica atas, o Congresso e a Câmara Legislativa do DF debatem, o Tribunal de Contas do DF recebe denúncias sobre o BRB.
          Aqui estão as fontes oficiais de cada Poder, agrupadas.
          Esta página lista as fontes oficiais que importam, guarda uma cópia com impressão digital de cada uma e avisa se a página mudou ou sumiu
          entre uma cópia e outra. Páginas de terceiros aparecem só como referência, sem cópia.
        </p>
      </header>
      <PontosChave itens={pontos} />
      {[...porOrgao.entries()].map(([orgao, lista]) => (
        <section key={orgao} aria-labelledby={`o-${orgao.replace(/\W+/g, "-")}`}>
          <h2 id={`o-${orgao.replace(/\W+/g, "-")}`} className="text-lg">{orgao}</h2>
          <ul className="mt-2 space-y-2">
            {lista.map((f) => (
              <li key={f.id} className="folha border border-neutral-300 bg-white p-3 text-sm">
                <p className="font-semibold"><a className="underline" href={f.url} rel="noreferrer">{f.rotulo}</a> <span className="font-normal text-neutral-600">({f.orgao}, {f.tipo})</span></p>
                <p className="leitura mt-1">{f.por_que}</p>
                {f.observacao && <p className="mt-1 text-xs text-amber-900"><span className="rounded-sm border border-amber-700 bg-amber-100 px-1">observação</span> {f.observacao}</p>}
                {f.capturar ? (
                  f.ultima ? (
                    f.ultima.sha256 ? (
                      <p className="mt-1 text-xs text-neutral-700">
                        Cópia de {formatarDataHora(f.ultima.fetched_at)}: {f.ultima.bytes?.toLocaleString("pt-BR")} bytes, sha256 <span className="font-mono">{f.ultima.sha256.slice(0, 16)}…</span>
                        {" · "}{f.historico.length} captura(s), {f.versoes_distintas} versão(ões) distinta(s){f.mudou ? " — a página mudou entre capturas" : ""}
                      </p>
                    ) : (
                      <p className="mt-1 text-xs text-neutral-700">Última tentativa em {formatarDataHora(f.ultima.fetched_at)} falhou (HTTP {f.ultima.http_status ?? "sem resposta"}); será repetida na próxima rodada.</p>
                    )
                  ) : <p className="mt-1 text-xs text-neutral-700">Ainda sem cópia.</p>
                ) : <p className="mt-1 text-xs text-neutral-700">Só referência: não é copiada.</p>}
              </li>
            ))}
          </ul>
        </section>
      ))}
      <p className="text-sm text-neutral-700">As cópias ficam em <code>data/raw/blobs/</code> e o registro em <code>data/raw/externas.jsonl</code>, ambos no repositório. Para conferir uma cópia, veja <Link className="underline" href="/verificar">Verificar</Link>.</p>
    </div>
  );
}
