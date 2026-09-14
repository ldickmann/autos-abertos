import Link from "next/link";
import { Carimbo, Publicidade, StatusProcessual } from "@/components/Badges";
import { LinhaDoTempo } from "@/components/LinhaDoTempo";
import { formatarData, getMeta, getProcesso, listarIncidentesColetados } from "@/lib/data";

export function generateStaticParams() {
  return listarIncidentesColetados().map((i) => ({ incidente: String(i) }));
}

export default async function PaginaProcesso({ params }: { params: Promise<{ incidente: string }> }) {
  const { incidente } = await params;
  const p = getProcesso(incidente);
  const meta = getMeta();
  const cab = p.cabecalho;
  const eSemente = cab.incidente === meta.semente;

  return (
    <div className="space-y-8">
      <nav aria-label="Trilha" className="text-sm"><Link className="underline" href="/">Início</Link> / {cab.classe} {cab.numero}</nav>
      <header className="rounded-lg border border-neutral-300 bg-white p-5">
        <div className="flex flex-wrap items-baseline gap-3">
          <h1 className="text-2xl font-bold">{cab.classe} {cab.numero}</h1>
          <Publicidade valor={cab.publicidade} />
          {eSemente && <span className="rounded bg-neutral-800 px-2 py-0.5 text-xs font-semibold text-white">processo principal deste mapa</span>}
        </div>
        <dl className="mt-3 grid gap-x-8 gap-y-1 text-sm sm:grid-cols-2">
          <div><dt className="inline font-semibold">Incidente: </dt><dd className="inline">{cab.incidente}</dd></div>
          <div><dt className="inline font-semibold">Número único: </dt><dd className="inline">{cab.numero_unico ?? "—"}</dd></div>
          <div><dt className="inline font-semibold">Relator: </dt><dd className="inline">{cab.relator ?? "—"}</dd></div>
          <div><dt className="inline font-semibold">Relator do último incidente: </dt><dd className="inline">{cab.relator_ultimo_incidente ?? "—"} {cab.ultimo_incidente ? `(${cab.ultimo_incidente})` : ""}</dd></div>
          <div><dt className="inline font-semibold">Protocolo: </dt><dd className="inline">{formatarData(cab.data_protocolo)}</dd></div>
          <div><dt className="inline font-semibold">Origem: </dt><dd className="inline">{cab.orgao_origem ?? "—"} · {cab.descricao_procedencia ?? cab.origem ?? "—"}</dd></div>
          <div className="sm:col-span-2"><dt className="inline font-semibold">Assunto: </dt><dd className="inline">{cab.assuntos.join("; ") || "—"}</dd></div>
          <div className="sm:col-span-2"><dt className="inline font-semibold">Números de origem: </dt><dd className="inline break-all">{cab.numeros_origem.join(", ") || "—"}</dd></div>
        </dl>
        <div className="mt-3 flex flex-wrap gap-4">
          <Carimbo snapshot={cab.snapshot} />
          <a className="text-sm underline" href={`https://portal.stf.jus.br/processos/detalhe.asp?incidente=${cab.incidente}`} rel="noreferrer">Ver no portal do STF</a>
        </div>
      </header>

      {p.relacoes.length > 0 && (
        <section aria-labelledby="rel">
          <h2 id="rel" className="text-lg font-bold">Relações declaradas nos andamentos</h2>
          <ul className="mt-2 list-disc pl-6 text-sm">
            {p.relacoes.map((r, i) => (
              <li key={i}>
                <span className="font-medium">{r.classe} {r.numero}</span> — {r.tipo.replace(/_/g, " ")}{" "}
                <a className="underline" href={`#andamento-${r.fonte_andamento_id}`}>(ver andamento-fonte)</a>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="partes">
        <h2 id="partes" className="text-lg font-bold">Partes <span className="text-sm font-normal text-neutral-700">({p.partes.length}, com o status processual literal do portal)</span></h2>
        {p.partes.length === 0 ? (
          <p className="mt-2 text-sm text-neutral-700">O portal não lista partes para este processo (publicidade: {cab.publicidade ?? "—"}).</p>
        ) : (
          <ul className="mt-2 grid gap-1 text-sm sm:grid-cols-2">
            {p.partes.map((pt) => (
              <li key={pt.id} className={`flex flex-wrap items-center gap-2 rounded px-2 py-1 ${pt.papel === "advogado" ? "pl-6 text-neutral-800" : "bg-white"}`}>
                <StatusProcessual status={pt.status_processual} literal={pt.papel_portal} />
                {pt.entidade_id && !pt.e_placeholder ? (
                  <Link className="underline" href={`/entidade/${pt.entidade_id}`}>{pt.nome}</Link>
                ) : (
                  <span>{pt.nome}</span>
                )}
                {pt.oab.length > 0 && <span className="text-xs text-neutral-600">OAB {pt.oab.join(", ")}</span>}
              </li>
            ))}
          </ul>
        )}
      </section>

      {p.sessoes.length > 0 && (
        <section aria-labelledby="sessoes">
          <h2 id="sessoes" className="text-lg font-bold">Sessões virtuais</h2>
          {p.sessoes.map((s, i) => (
            <div key={i} className="mt-2 rounded border border-neutral-300 bg-white p-3 text-sm">
              <p><span className="font-semibold">{s.objeto_completo}</span> · lista {s.lista} · {s.colegiado} · {formatarData(s.data_inicio)} a {formatarData(s.data_fim)} · relator {s.relator}</p>
              <p className="text-neutral-700">{s.tipo_lista}{s.resultado ? ` · resultado: ${s.resultado}` : ""}{s.julgado === 0 ? " · julgado: não (registro do portal)" : ""}</p>
              {s.texto_decisao && <p className="mt-1">{s.texto_decisao}</p>}
              <table className="mt-2 w-full border-collapse">
                <caption className="sr-only">Votos por ministro, com o tipo de voto literal publicado pelo STF</caption>
                <thead><tr className="border-b border-neutral-300 text-left"><th scope="col" className="py-1 pr-3">Ministro</th><th scope="col" className="py-1 pr-3">Voto (literal)</th><th scope="col" className="py-1 pr-3">Data</th></tr></thead>
                <tbody>{s.votos.map((v) => (<tr key={v.ordem} className="border-b border-neutral-100"><td className="py-1 pr-3">{v.ministro}</td><td className="py-1 pr-3">{v.tipo_voto}</td><td className="py-1 pr-3">{formatarData(v.data)}</td></tr>))}</tbody>
              </table>
              <Carimbo snapshot={s.snapshot} />
            </div>
          ))}
        </section>
      )}

      <section aria-labelledby="lt">
        <h2 id="lt" className="text-lg font-bold">Linha do tempo <span className="text-sm font-normal text-neutral-700">({p.andamentos.length} andamentos)</span></h2>
        <LinhaDoTempo andamentos={p.andamentos} explicacoes={p.explicacoes_portal} />
      </section>

      <details className="rounded border border-neutral-300 bg-white p-3 text-sm">
        <summary className="cursor-pointer font-semibold">Petições ({p.peticoes.length})</summary>
        <table className="mt-2 w-full border-collapse"><thead><tr className="border-b text-left"><th scope="col" className="py-1 pr-3">Número</th><th scope="col" className="py-1 pr-3">Peticionada</th><th scope="col" className="py-1 pr-3">Recebida</th><th scope="col" className="py-1 pr-3">Por</th></tr></thead>
          <tbody>{p.peticoes.map((q) => (<tr key={q.numero} className="border-b border-neutral-100"><td className="py-1 pr-3">{q.numero}</td><td className="py-1 pr-3">{formatarData(q.data_peticionamento)}</td><td className="py-1 pr-3">{q.recebido_em?.replace("T", " ") ?? "—"}</td><td className="py-1 pr-3">{q.recebido_por}</td></tr>))}</tbody></table>
      </details>
      <details className="rounded border border-neutral-300 bg-white p-3 text-sm">
        <summary className="cursor-pointer font-semibold">Deslocamentos ({p.deslocamentos.length})</summary>
        <table className="mt-2 w-full border-collapse"><thead><tr className="border-b text-left"><th scope="col" className="py-1 pr-3">Data</th><th scope="col" className="py-1 pr-3">De</th><th scope="col" className="py-1 pr-3">Para</th><th scope="col" className="py-1 pr-3">Guia</th><th scope="col" className="py-1 pr-3">Recebido</th></tr></thead>
          <tbody>{p.deslocamentos.map((d, i) => (<tr key={i} className="border-b border-neutral-100"><td className="py-1 pr-3">{formatarData(d.data_envio)}</td><td className="py-1 pr-3">{d.enviado_por}</td><td className="py-1 pr-3">{d.destino}</td><td className="py-1 pr-3">{d.guia}</td><td className="py-1 pr-3">{formatarData(d.recebido_em)}</td></tr>))}</tbody></table>
      </details>
    </div>
  );
}
