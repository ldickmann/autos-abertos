import Link from "next/link";
import { getFontesExternas } from "@/lib/data";
import { formatarDataHora } from "@/lib/tipos";

/* Fontes oficiais fora do portal do STF, com cópia (hash) e histórico, para o caso não depender de um único portal. */
export default function PaginaFontesExternas() {
  const fontes = getFontesExternas();
  const porOrgao = new Map<string, typeof fontes>();
  for (const f of fontes) porOrgao.set(f.orgao, [...(porOrgao.get(f.orgao) ?? []), f]);
  return (
    <div className="space-y-6">
      <header className="max-w-3xl">
        <h1 className="text-2xl">Fontes oficiais fora do STF</h1>
        <p className="leitura mt-1">
          O caso não vive só no portal do STF: o Banco Central decretou a liquidação, o Senado investiga em comissão, o próprio regulador publica atas.
          Esta página lista as fontes oficiais que importam, guarda uma cópia com impressão digital de cada uma e avisa se a página mudou ou sumiu
          entre uma cópia e outra. Páginas de terceiros aparecem só como referência, sem cópia.
        </p>
      </header>
      {[...porOrgao.entries()].map(([orgao, lista]) => (
        <section key={orgao} aria-labelledby={`o-${orgao.replace(/\W+/g, "-")}`}>
          <h2 id={`o-${orgao.replace(/\W+/g, "-")}`} className="text-lg">{orgao}</h2>
          <ul className="mt-2 space-y-2">
            {lista.map((f) => (
              <li key={f.id} className="folha border border-neutral-300 bg-white p-3 text-sm">
                <p className="font-semibold"><a className="underline" href={f.url} rel="noreferrer">{f.rotulo}</a> <span className="font-normal text-neutral-600">({f.tipo})</span></p>
                <p className="leitura mt-1">{f.por_que}</p>
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
