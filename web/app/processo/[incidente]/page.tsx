import Link from "next/link";
import { BadgeEpistemico, Carimbo, Publicidade, StatusProcessual } from "@/components/Badges";
import { LinhaDoTempo } from "@/components/LinhaDoTempo";
import { ListaDecisoes } from "@/components/ListaDecisoes";
import { PontosChave } from "@/components/PontosChave";
import { Termo } from "@/components/Termo";
import { formatarData, getDecisoes, getGlossario, getMeta, getProcesso, listarIncidentesColetados, nomeProprio, verbeteDe, verbetesParaTipos } from "@/lib/data";

export function generateStaticParams() {
  return listarIncidentesColetados().map((i) => ({ incidente: String(i) }));
}

export default async function PaginaProcesso({ params }: { params: Promise<{ incidente: string }> }) {
  const { incidente } = await params;
  const p = getProcesso(incidente);
  const meta = getMeta();
  const cab = p.cabecalho;
  const eSemente = cab.incidente === meta.semente;
  const decisoes = getDecisoes();
  const verbetesTipos = verbetesParaTipos(new Set(p.andamentos.map((a) => a.tipo)), p.explicacoes_portal);
  const verbetesResultado = Object.fromEntries(Object.entries(decisoes.rotulos_resultado).map(([k, r]) => [k, verbeteDe(r.split(" (")[0]) ?? verbeteDe(k)]));

  // "Em resumo": o que este processo é, quem está nele, o que foi decidido e o que aconteceu por último
  const ordenados = [...p.andamentos].filter((a) => a.data).sort((a, b) => b.data.localeCompare(a.data));
  const ultimo = ordenados[0];
  const ultimaDecisao = ordenados.find((a) => a.e_decisao);
  const nDecisoes = p.andamentos.filter((a) => a.e_decisao).length;
  const porStatus = (s: string) => p.partes.filter((x) => !x.e_placeholder && x.status_processual === s).map((x) => x.nome);
  const investigados = porStatus("investigado"), requeridos = porStatus("requerido"), requerentes = porStatus("requerente");
  const nomes = (xs: string[], n = 4) => xs.slice(0, n).join(", ") + (xs.length > n ? ` e mais ${xs.length - n}` : "");
  const itensDec = p.decisoes ?? [];
  const contaRes = (k: string) => itensDec.filter((i) => i.resultado === k).length;
  const relacionados = p.relacoes.map((r) => `${r.classe} ${r.numero}`);
  const resumo = [
    { texto: <><strong>{cab.classe} {cab.numero}</strong>{cab.natureza ? `, ${cab.natureza.toLowerCase()}` : ""}, relator {cab.relator ?? "—"}, protocolado em {formatarData(cab.data_protocolo)}; {cab.publicidade === "Sigiloso" ? "tramita sob sigilo: o portal devolve só o cabeçalho" : "público"}. Assunto cadastrado: {cab.assuntos.join("; ") || "—"}.</> },
    ...(requerentes.length || investigados.length || requeridos.length ? [{ texto: <>{requerentes.length ? <>Pede: <strong>{nomes(requerentes, 2)}</strong>. </> : null}{investigados.length ? <>Investigados: <strong>{nomes(investigados)}</strong>. </> : null}{requeridos.length ? <>Requeridos: {nomes(requeridos)}. </> : null}<a className="underline" href="#partes">Todas as partes</a>, com o status literal do portal.</> }] : []),
    { texto: <><strong>{p.andamentos.length} andamentos</strong>, {nDecisoes} deles decisões{itensDec.length ? <>; em {itensDec.length} pedidos analisados, {contaRes("deferido")} aceitos, {contaRes("indeferido")} negados e {contaRes("referendado")} referendados</> : null}. {relacionados.length ? `Relacionado nos autos a ${nomes(relacionados, 5)}.` : ""}</> },
    ...(ultimaDecisao ? [{ texto: <>Última decisão: <strong>{formatarData(ultimaDecisao.data)}</strong> — {ultimaDecisao.tipo}{ultimaDecisao.descricao ? `: ${ultimaDecisao.descricao.replace(/\s+/g, " ").slice(0, 200)}${ultimaDecisao.descricao.length > 200 ? "…" : ""}` : ""}</>, fonte: ultimaDecisao.documentos[0] ? { href: `/documento/${ultimaDecisao.documentos[0].id}`, rotulo: "abrir a peça" } : { href: `#andamento-${ultimaDecisao.id}`, rotulo: "ver na linha do tempo" } }] : []),
    ...(ultimo && ultimo.id !== ultimaDecisao?.id ? [{ texto: <>Último andamento: <strong>{formatarData(ultimo.data)}</strong> — {ultimo.tipo}{ultimo.descricao ? `: ${ultimo.descricao.replace(/\s+/g, " ").slice(0, 160)}` : ""}.</>, fonte: { href: `#andamento-${ultimo.id}`, rotulo: "ver" } }] : []),
  ];

  return (
    <div className="space-y-8">
      <nav aria-label="Trilha" className="text-sm"><Link className="underline" href="/">Início</Link> / {cab.classe} {cab.numero}</nav>
      <header className="rounded-lg border border-neutral-300 bg-white p-5">
        <div className="flex flex-wrap items-baseline gap-3">
          <h1 className="text-2xl font-bold"><Termo verbete={verbeteDe(cab.classe)}>{cab.classe}</Termo> {cab.numero}</h1>
          <Termo verbete={verbeteDe(cab.publicidade)}><Publicidade valor={cab.publicidade} /></Termo>
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
        {p.contagem_assercoes && Object.values(p.contagem_assercoes).some((n) => n > 0) && (
          <p className="mt-3 flex flex-wrap items-center gap-2 text-sm">
            <span className="font-semibold">Afirmações extraídas dos documentos:</span>
            {(["fato_processual", "alegacao_parte", "fundamento_decisorio"] as const).map((t) => (
              <span key={t} className="flex items-center gap-1"><BadgeEpistemico tipo={t} /> {p.contagem_assercoes?.[t] ?? 0}</span>
            ))}
            <a className="underline" href="#lt">(ver na linha do tempo)</a>
          </p>
        )}
        <div className="mt-3 flex flex-wrap gap-4">
          <Carimbo snapshot={cab.snapshot} />
          <a className="text-sm underline" href={`https://portal.stf.jus.br/processos/detalhe.asp?incidente=${cab.incidente}`} rel="noreferrer">Ver no portal do STF</a>
        </div>
      </header>

      <PontosChave titulo="Em resumo" itens={resumo} nota="Síntese calculada dos registros do portal e das decisões extraídas; nada é interpretação." />

      {(p.decisoes?.length ?? 0) > 0 && (
        <section aria-labelledby="dec">
          <h2 id="dec" className="text-lg font-bold">O que foi decidido neste processo <span className="text-sm font-normal text-neutral-700">({p.decisoes!.length} itens, pedido por pedido)</span></h2>
          <p className="mt-1 text-sm text-neutral-700">O que se pediu, quem pediu e o que o julgador decidiu, com a página e o trecho literal de cada decisão. Clique num resultado para ver o que a palavra significa.</p>
          <div className="mt-2">
            <ListaDecisoes itens={p.decisoes!} rotulos={decisoes.rotulos_resultado} processos={[{ incidente: cab.incidente, rotulo: `${cab.classe} ${cab.numero}` }]} verbetes={verbetesResultado} glossario={getGlossario()} compacta incidenteFixo={cab.incidente} />
          </div>
        </section>
      )}

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
                <Termo verbete={verbeteDe(pt.status_processual)}><StatusProcessual status={pt.status_processual} literal={pt.papel_portal} /></Termo>
                {pt.entidade_id && !pt.e_placeholder ? (
                  <Link className="underline" href={`/entidade/${pt.entidade_id}`} title={`No portal: ${pt.nome}`}>{nomeProprio(pt.nome)}</Link>
                ) : (
                  <span title={`No portal: ${pt.nome}`}>{nomeProprio(pt.nome)}</span>
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
              <div className="overflow-x-auto"><table className="tabela-responsiva mt-2 w-full border-collapse">
                <caption className="sr-only">Votos por ministro, com o tipo de voto literal publicado pelo STF</caption>
                <thead><tr className="border-b border-neutral-300 text-left"><th scope="col" className="py-1 pr-3">Ministro</th><th scope="col" className="py-1 pr-3">Voto (literal)</th><th scope="col" className="py-1 pr-3">Data</th></tr></thead>
                <tbody>{s.votos.map((v) => (<tr key={v.ordem} className="border-b border-neutral-100"><td data-rotulo="Ministro" className="py-1 pr-3">{v.ministro}</td><td data-rotulo="Voto (literal)" className="py-1 pr-3">{v.tipo_voto}</td><td data-rotulo="Data" className="py-1 pr-3">{formatarData(v.data)}</td></tr>))}</tbody>
              </table></div>
              <Carimbo snapshot={s.snapshot} />
            </div>
          ))}
        </section>
      )}

      <section aria-labelledby="lt">
        <h2 id="lt" className="text-lg font-bold">Linha do tempo <span className="text-sm font-normal text-neutral-700">({p.andamentos.length} andamentos)</span></h2>
        <LinhaDoTempo andamentos={p.andamentos} verbetes={verbetesTipos} />
      </section>

      <details className="rounded border border-neutral-300 bg-white p-3 text-sm">
        <summary className="cursor-pointer font-semibold">Petições ({p.peticoes.length})</summary>
        <div className="overflow-x-auto"><table className="tabela-responsiva mt-2 w-full border-collapse"><thead><tr className="border-b text-left"><th scope="col" className="py-1 pr-3">Número</th><th scope="col" className="py-1 pr-3">Peticionada</th><th scope="col" className="py-1 pr-3">Recebida</th><th scope="col" className="py-1 pr-3">Por</th></tr></thead>
          <tbody>{p.peticoes.map((q) => (<tr key={q.numero} className="border-b border-neutral-100"><td data-rotulo="Número" className="py-1 pr-3">{q.numero}</td><td data-rotulo="Peticionada" className="py-1 pr-3">{formatarData(q.data_peticionamento)}</td><td data-rotulo="Recebida" className="py-1 pr-3">{q.recebido_em?.replace("T", " ") ?? "—"}</td><td data-rotulo="Por" className="py-1 pr-3">{q.recebido_por}</td></tr>))}</tbody></table></div>
      </details>
      <details className="rounded border border-neutral-300 bg-white p-3 text-sm">
        <summary className="cursor-pointer font-semibold">Deslocamentos ({p.deslocamentos.length})</summary>
        <div className="overflow-x-auto"><table className="tabela-responsiva mt-2 w-full border-collapse"><thead><tr className="border-b text-left"><th scope="col" className="py-1 pr-3">Data</th><th scope="col" className="py-1 pr-3">De</th><th scope="col" className="py-1 pr-3">Para</th><th scope="col" className="py-1 pr-3">Guia</th><th scope="col" className="py-1 pr-3">Recebido</th></tr></thead>
          <tbody>{p.deslocamentos.map((d, i) => (<tr key={i} className="border-b border-neutral-100"><td data-rotulo="Data" className="py-1 pr-3">{formatarData(d.data_envio)}</td><td data-rotulo="De" className="py-1 pr-3">{d.enviado_por}</td><td data-rotulo="Para" className="py-1 pr-3">{d.destino}</td><td data-rotulo="Guia" className="py-1 pr-3">{d.guia}</td><td data-rotulo="Recebido" className="py-1 pr-3">{formatarData(d.recebido_em)}</td></tr>))}</tbody></table></div>
      </details>
    </div>
  );
}
