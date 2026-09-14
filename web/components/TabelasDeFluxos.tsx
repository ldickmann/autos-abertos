"use client";

import Link from "next/link";
import { useMemo, useState, type ReactNode } from "react";
import { formatarData, formatarReais, type FluxoAtor, type FluxoComunicacao, type FluxosDados, type FluxoTransacao } from "@/lib/tipos";

/*
  Quatro tabelas sobre o mesmo dataset, todas ordenáveis por coluna e filtráveis por texto:
  pessoas e empresas (quem recebeu e quem pagou), fluxos (uma linha por transação), comunicações e bens.
  Cada linha de fluxo mostra a página do relatório e o trecho literal de onde saiu; cada pessoa se expande
  para mostrar todos os seus fluxos. "Situação nos autos" é o status literal do portal do STF quando a
  pessoa é parte em algum processo do caso — o site não chama ninguém de suspeito.
*/

export type SituacaoAutos = { status: string; processos: string[]; entidade_id: number };

const ROTULO_SECAO: Record<string, string> = { suspeita: "suspeita", automatica: "automática", especie: "em espécie" };
const ROTULO_TIPO: Record<string, string> = {
  transferencia: "transferência", pix: "PIX", ted: "TED/DOC", boleto: "boleto", cdb_rdb: "CDB/RDB", cartao: "cartão", cheque: "cheque", tributo: "tributo",
  escritura_compra: "compra de imóvel", escritura_doacao: "doação de imóvel", alienacao_fiduciaria: "alienação fiduciária", compra_veiculo: "compra de veículo",
  pagamento_titulo: "pagamento de título", outros: "outros",
};
const ROTULO_NATUREZA: Record<string, string> = { individual: "operação datada", agregado: "agregado", resumo_tipo: "resumo por tipo" };
const ROTULO_ATOR: Record<string, string> = { pessoa_fisica: "pessoa física", pessoa_juridica: "pessoa jurídica", desconhecido: "só nome" };

type Coluna<T> = { chave: string; rotulo: string; valor: (r: T) => string | number | null | undefined; celula?: (r: T) => ReactNode; numerica?: boolean; classe?: string };

function useOrdenacao<T>(linhas: T[], colunas: Coluna<T>[], inicial: string, desc = true) {
  const [ord, setOrd] = useState<{ chave: string; desc: boolean }>({ chave: inicial, desc });
  const ordenadas = useMemo(() => {
    const col = colunas.find((c) => c.chave === ord.chave) ?? colunas[0];
    const dir = ord.desc ? -1 : 1;
    return [...linhas].sort((a, b) => {
      const va = col.valor(a), vb = col.valor(b);
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      if (typeof va === "number" && typeof vb === "number") return (va - vb) * dir;
      return String(va).localeCompare(String(vb), "pt-BR") * dir;
    });
  }, [linhas, colunas, ord]);
  const alternar = (chave: string) => setOrd((o) => (o.chave === chave ? { chave, desc: !o.desc } : { chave, desc: colunas.find((c) => c.chave === chave)?.numerica ?? false }));
  return { ordenadas, ord, alternar };
}

function Tabela<T>({ linhas, colunas, chave, inicial, expandir, rotuloVazio, descInicial = true }: {
  linhas: T[]; colunas: Coluna<T>[]; chave: (r: T) => string | number; inicial: string; expandir?: (r: T) => ReactNode; rotuloVazio: string; descInicial?: boolean;
}) {
  const { ordenadas, ord, alternar } = useOrdenacao(linhas, colunas, inicial, descInicial);
  const [aberta, setAberta] = useState<string | number | null>(null);
  if (!linhas.length) return <p className="mt-2 text-sm text-neutral-700">{rotuloVazio}</p>;
  return (
    <div className="mt-2 overflow-x-auto">
      <table className="w-full min-w-[720px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-neutral-400 text-left">
            {expandir && <th scope="col" className="w-6" />}
            {colunas.map((c) => (
              <th key={c.chave} scope="col" className={`py-1.5 pr-3 ${c.numerica ? "text-right" : ""}`} aria-sort={ord.chave === c.chave ? (ord.desc ? "descending" : "ascending") : "none"}>
                <button type="button" className="toque font-semibold underline-offset-2 hover:underline" onClick={() => alternar(c.chave)}>
                  {c.rotulo}{ord.chave === c.chave ? (ord.desc ? " ↓" : " ↑") : ""}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ordenadas.map((r) => {
            const k = chave(r);
            const abertaEsta = expandir && aberta === k;
            return (
              <FragmentoLinha key={k}>
                <tr className={`border-b border-neutral-200 align-top ${abertaEsta ? "bg-neutral-100" : ""}`}>
                  {expandir && (
                    <td className="py-1.5 pr-1">
                      <button type="button" className="toque rounded px-1 text-neutral-700 hover:bg-neutral-100" aria-expanded={!!abertaEsta} aria-label={abertaEsta ? "Recolher" : "Expandir"} onClick={() => setAberta(abertaEsta ? null : k)}>{abertaEsta ? "▾" : "▸"}</button>
                    </td>
                  )}
                  {colunas.map((c) => (
                    <td key={c.chave} className={`py-1.5 pr-3 ${c.numerica ? "text-right tabular-nums" : ""} ${c.classe ?? ""}`}>{c.celula ? c.celula(r) : (c.valor(r) ?? "—")}</td>
                  ))}
                </tr>
                {abertaEsta && (
                  <tr className="border-b border-neutral-200 bg-neutral-100"><td /><td colSpan={colunas.length} className="px-2 py-2">{expandir!(r)}</td></tr>
                )}
              </FragmentoLinha>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function FragmentoLinha({ children }: { children: ReactNode }) { return <>{children}</>; }

function quando(t: FluxoTransacao): string {
  if (t.data) return formatarData(t.data);
  if (t.periodo_inicio && t.periodo_fim) return `${formatarData(t.periodo_inicio)} – ${formatarData(t.periodo_fim)}`;
  return "—";
}

function LinkPagina({ documentoId, pagina }: { documentoId: number | null; pagina: number }) {
  return documentoId ? <Link className="underline" href={`/documento/${documentoId}#p-${pagina}`}>p. {pagina}</Link> : <>p. {pagina}</>;
}

function ListaFluxos({ tx, atorPorId, comPorId, ponto }: { tx: FluxoTransacao[]; atorPorId: Map<number, FluxoAtor>; comPorId: Map<number, FluxoComunicacao>; ponto?: number }) {
  if (!tx.length) return <p className="text-xs text-neutral-700">Nenhum fluxo com origem ou destino identificado; aparece só como relacionado numa comunicação.</p>;
  return (
    <ul className="space-y-1.5 text-xs">
      {tx.map((t) => {
        const saida = ponto != null && t.origem_ator_id === ponto;
        const outroId = ponto != null ? (saida ? t.destino_ator_id : t.origem_ator_id) : null;
        return (
          <li key={t.id}>
            <span className="font-medium tabular-nums">{formatarReais(t.valor_centavos)}</span>
            {ponto != null && <span> {saida ? "→ pagou a" : "← recebeu de"} <strong>{outroId == null ? "não informado" : atorPorId.get(outroId)?.nome}</strong></span>}
            <span className="text-neutral-700"> · {ROTULO_TIPO[t.tipo] ?? t.tipo}{t.natureza === "agregado" ? `, ${t.quantidade ?? "?"} lançamentos` : t.natureza === "resumo_tipo" ? " (resumo por tipo)" : ""} · {quando(t)}{t.descricao ? ` · ${t.descricao}` : ""}</span>
            <span className="block text-neutral-600">{comPorId.get(t.comunicacao_id)?.comunicante ?? ""} · <LinkPagina documentoId={t.documento_id} pagina={t.pagina} /> · <q className="italic">{t.trecho_fonte}</q></span>
          </li>
        );
      })}
    </ul>
  );
}

// ---------------------------------------------------------------- pessoas e empresas

type LinhaAtor = FluxoAtor & { recebeu: number; pagou: number; n: number; fluxos: FluxoTransacao[]; deQuem: string[]; paraQuem: string[]; situacao: SituacaoAutos | null; comunicacoes: number };

export function TabelaAtores({ dados, situacoes, busca }: { dados: FluxosDados; situacoes: Record<number, SituacaoAutos>; busca: string }) {
  const atorPorId = useMemo(() => new Map(dados.atores.map((a) => [a.id, a])), [dados]);
  const comPorId = useMemo(() => new Map(dados.comunicacoes.map((c) => [c.id, c])), [dados]);
  const linhas = useMemo<LinhaAtor[]>(() => dados.atores.map((a) => {
    const fluxos = dados.transacoes.filter((t) => t.natureza !== "resumo_tipo" && (t.origem_ator_id === a.id || t.destino_ator_id === a.id)).sort((x, y) => y.valor_centavos - x.valor_centavos);
    const soma = (m: Map<number, number>, id: number | null, v: number) => { if (id != null && id !== a.id) m.set(id, (m.get(id) ?? 0) + v); };
    const de = new Map<number, number>(), para = new Map<number, number>();
    for (const t of fluxos) { if (t.destino_ator_id === a.id) soma(de, t.origem_ator_id, t.valor_centavos); if (t.origem_ator_id === a.id) soma(para, t.destino_ator_id, t.valor_centavos); }
    const top = (m: Map<number, number>) => [...m.entries()].sort((x, y) => y[1] - x[1]).slice(0, 3).map(([id, v]) => `${atorPorId.get(id)?.nome ?? id} (${formatarReais(v, true)})`);
    return {
      ...a, fluxos,
      recebeu: fluxos.filter((t) => t.destino_ator_id === a.id).reduce((s, t) => s + t.valor_centavos, 0),
      pagou: fluxos.filter((t) => t.origem_ator_id === a.id).reduce((s, t) => s + t.valor_centavos, 0),
      n: fluxos.length, deQuem: top(de), paraQuem: top(para), situacao: situacoes[a.id] ?? null,
      comunicacoes: dados.comunicacoes.filter((c) => c.participacoes.some((p) => p.ator_id === a.id)).length,
    };
  }), [dados, situacoes, atorPorId]);

  const [soRecebeu, setSoRecebeu] = useState(false);
  const [soPartes, setSoPartes] = useState(false);
  const [tipo, setTipo] = useState("todos");
  const filtradas = useMemo(() => {
    const q = busca.trim().toLowerCase();
    return linhas.filter((l) => (!q || l.nome.toLowerCase().includes(q) || (l.atividade ?? "").toLowerCase().includes(q) || (l.documento_mascarado ?? "").includes(q))
      && (!soRecebeu || l.recebeu > 0) && (!soPartes || !!l.situacao) && (tipo === "todos" || l.tipo === tipo));
  }, [linhas, busca, soRecebeu, soPartes, tipo]);

  const colunas: Coluna<LinhaAtor>[] = [
    { chave: "nome", rotulo: "Nome", valor: (r) => r.nome, celula: (r) => <><span className="font-medium">{r.nome}</span>{r.documento_mascarado && <span className="block text-xs text-neutral-600">{r.documento_mascarado}</span>}</> },
    { chave: "tipo", rotulo: "Tipo", valor: (r) => ROTULO_ATOR[r.tipo] },
    { chave: "atividade", rotulo: "Atividade informada", valor: (r) => r.atividade?.toLowerCase() ?? null, classe: "max-w-[220px] text-xs" },
    { chave: "papeis", rotulo: "Papel no relatório", valor: (r) => r.papeis.join(", "), classe: "text-xs" },
    { chave: "situacao", rotulo: "Situação nos autos", valor: (r) => r.situacao?.status ?? null, celula: (r) => r.situacao ? <Link className="underline" href={`/entidade/${r.situacao.entidade_id}`}>{r.situacao.status} <span className="text-xs text-neutral-600">({r.situacao.processos.join(", ")})</span></Link> : <span className="text-xs text-neutral-600">não é parte</span> },
    { chave: "recebeu", rotulo: "Recebeu", valor: (r) => r.recebeu, numerica: true, celula: (r) => r.recebeu ? formatarReais(r.recebeu) : "—" },
    { chave: "pagou", rotulo: "Pagou", valor: (r) => r.pagou, numerica: true, celula: (r) => r.pagou ? formatarReais(r.pagou) : "—" },
    { chave: "n", rotulo: "Fluxos", valor: (r) => r.n, numerica: true },
    { chave: "de", rotulo: "Recebeu de (principais)", valor: (r) => r.deQuem.join("; "), classe: "max-w-[240px] text-xs" },
    { chave: "para", rotulo: "Pagou a (principais)", valor: (r) => r.paraQuem.join("; "), classe: "max-w-[240px] text-xs" },
  ];

  return (
    <div>
      <form className="mt-2 flex flex-wrap items-end gap-3 text-sm" onSubmit={(ev) => ev.preventDefault()}>
        <label className="block"><span className="block text-xs font-medium">Tipo</span>
          <select className="mt-0.5 rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={tipo} onChange={(ev) => setTipo(ev.target.value)}>
            <option value="todos">todos</option><option value="pessoa_fisica">pessoas físicas</option><option value="pessoa_juridica">pessoas jurídicas</option>
          </select></label>
        <label className="flex items-center gap-2"><input type="checkbox" checked={soRecebeu} onChange={(ev) => setSoRecebeu(ev.target.checked)} /> só quem recebeu dinheiro</label>
        <label className="flex items-center gap-2"><input type="checkbox" checked={soPartes} onChange={(ev) => setSoPartes(ev.target.checked)} /> só quem é parte nos autos</label>
        <span role="status" className="text-xs text-neutral-600">{filtradas.length} de {linhas.length}</span>
      </form>
      <Tabela linhas={filtradas} colunas={colunas} chave={(r) => r.id} inicial="recebeu" rotuloVazio="Nenhuma pessoa ou empresa com esses filtros."
        expandir={(r) => (
          <div className="space-y-2">
            {r.entidade_id && <p className="text-xs"><Link className="underline" href={`/entidade/${r.entidade_id}`}>Página desta pessoa/empresa nos autos</Link> · aparece em {r.comunicacoes} comunicação(ões) do relatório</p>}
            <ListaFluxos tx={r.fluxos} atorPorId={atorPorId} comPorId={comPorId} ponto={r.id} />
          </div>
        )} />
    </div>
  );
}

// ---------------------------------------------------------------- fluxos

export function TabelaFluxos({ dados, busca }: { dados: FluxosDados; busca: string }) {
  const atorPorId = useMemo(() => new Map(dados.atores.map((a) => [a.id, a])), [dados]);
  const comPorId = useMemo(() => new Map(dados.comunicacoes.map((c) => [c.id, c])), [dados]);
  const [natureza, setNatureza] = useState("sem_resumo");
  const [tipo, setTipo] = useState("todos");
  const [ano, setAno] = useState("todos");
  const anos = useMemo(() => [...new Set(dados.transacoes.map((t) => (t.data ?? t.periodo_inicio ?? "").slice(0, 4)).filter(Boolean))].sort(), [dados]);
  const tipos = useMemo(() => [...new Set(dados.transacoes.map((t) => t.tipo))].sort(), [dados]);
  const nome = (id: number | null) => (id == null ? "" : atorPorId.get(id)?.nome ?? "");
  const filtradas = useMemo(() => {
    const q = busca.trim().toLowerCase();
    return dados.transacoes.filter((t) => (natureza === "todas" || (natureza === "sem_resumo" ? t.natureza !== "resumo_tipo" : t.natureza === natureza))
      && (tipo === "todos" || t.tipo === tipo)
      && (ano === "todos" || (t.data ?? t.periodo_inicio ?? "").startsWith(ano))
      && (!q || nome(t.origem_ator_id).toLowerCase().includes(q) || nome(t.destino_ator_id).toLowerCase().includes(q) || (t.descricao ?? "").toLowerCase().includes(q)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dados, busca, natureza, tipo, ano]);
  const total = filtradas.reduce((s, t) => s + t.valor_centavos, 0);

  const colunas: Coluna<FluxoTransacao>[] = [
    { chave: "origem", rotulo: "De", valor: (t) => nome(t.origem_ator_id) || null, celula: (t) => nome(t.origem_ator_id) || <span className="text-xs text-neutral-600">não informado</span> },
    { chave: "destino", rotulo: "Para", valor: (t) => nome(t.destino_ator_id) || null, celula: (t) => nome(t.destino_ator_id) || <span className="text-xs text-neutral-600">não informado</span> },
    { chave: "valor", rotulo: "Valor", valor: (t) => t.valor_centavos, numerica: true, celula: (t) => formatarReais(t.valor_centavos) },
    { chave: "quando", rotulo: "Quando", valor: (t) => t.data ?? t.periodo_inicio ?? null, celula: (t) => <span className="whitespace-nowrap">{quando(t)}</span> },
    { chave: "tipo", rotulo: "Tipo", valor: (t) => ROTULO_TIPO[t.tipo] ?? t.tipo },
    { chave: "natureza", rotulo: "Natureza", valor: (t) => ROTULO_NATUREZA[t.natureza], celula: (t) => <>{ROTULO_NATUREZA[t.natureza]}{t.quantidade ? <span className="text-xs text-neutral-600"> · {t.quantidade} lanç.</span> : null}</> },
    { chave: "secao", rotulo: "Comunicação", valor: (t) => `${ROTULO_SECAO[t.secao]} ${comPorId.get(t.comunicacao_id)?.numero}`, classe: "text-xs" },
    { chave: "fonte", rotulo: "Fonte", valor: (t) => t.pagina, numerica: true, celula: (t) => <details className="text-left"><summary className="cursor-pointer whitespace-nowrap"><LinkPagina documentoId={t.documento_id} pagina={t.pagina} /> ▸</summary><q className="block max-w-[320px] text-xs italic">{t.trecho_fonte}</q>{t.descricao && <span className="block max-w-[320px] text-xs text-neutral-700">{t.descricao}</span>}</details> },
  ];
  return (
    <div>
      <form className="mt-2 flex flex-wrap items-end gap-3 text-sm" onSubmit={(ev) => ev.preventDefault()}>
        <label className="block"><span className="block text-xs font-medium">Natureza</span>
          <select className="mt-0.5 rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={natureza} onChange={(ev) => setNatureza(ev.target.value)}>
            <option value="sem_resumo">datadas e agregados</option><option value="individual">só operações datadas</option><option value="agregado">só agregados</option><option value="resumo_tipo">só resumos por tipo</option><option value="todas">todas</option>
          </select></label>
        <label className="block"><span className="block text-xs font-medium">Tipo</span>
          <select className="mt-0.5 rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={tipo} onChange={(ev) => setTipo(ev.target.value)}>
            <option value="todos">todos</option>{tipos.map((t) => <option key={t} value={t}>{ROTULO_TIPO[t] ?? t}</option>)}
          </select></label>
        <label className="block"><span className="block text-xs font-medium">Ano</span>
          <select className="mt-0.5 rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={ano} onChange={(ev) => setAno(ev.target.value)}>
            <option value="todos">todos</option>{anos.map((a) => <option key={a} value={a}>{a}</option>)}
          </select></label>
        <span role="status" className="text-xs text-neutral-600">{filtradas.length} fluxos · {formatarReais(total)}</span>
      </form>
      <Tabela linhas={filtradas} colunas={colunas} chave={(t) => t.id} inicial="valor" rotuloVazio="Nenhum fluxo com esses filtros." />
    </div>
  );
}

// ---------------------------------------------------------------- comunicações

export function TabelaComunicacoes({ dados, busca }: { dados: FluxosDados; busca: string }) {
  const atorPorId = useMemo(() => new Map(dados.atores.map((a) => [a.id, a])), [dados]);
  const q = busca.trim().toLowerCase();
  const linhas = useMemo(() => dados.comunicacoes.filter((c) => !q || [c.titular_ator_id ? atorPorId.get(c.titular_ator_id)?.nome : "", c.comunicante, c.local, c.informacoes, c.numero, ...c.participacoes.map((p) => atorPorId.get(p.ator_id)?.nome ?? "")].some((x) => (x ?? "").toLowerCase().includes(q))), [dados, q, atorPorId]);
  const colunas: Coluna<FluxoComunicacao>[] = [
    { chave: "secao", rotulo: "Tipo", valor: (c) => `${ROTULO_SECAO[c.secao]} ${c.numero}` },
    { chave: "titular", rotulo: "Titular", valor: (c) => (c.titular_ator_id ? atorPorId.get(c.titular_ator_id)?.nome : null) ?? null, celula: (c) => <span className="font-medium">{c.titular_ator_id ? atorPorId.get(c.titular_ator_id)?.nome : "—"}</span> },
    { chave: "comunicante", rotulo: "Quem comunicou", valor: (c) => c.comunicante, celula: (c) => <>{c.comunicante}{c.local && <span className="block text-xs text-neutral-600">{c.local}</span>}</> },
    { chave: "periodo", rotulo: "Período", valor: (c) => c.periodo_inicio, celula: (c) => <span className="whitespace-nowrap">{c.periodo_inicio ? formatarData(c.periodo_inicio) : "—"}{c.periodo_fim && c.periodo_fim !== c.periodo_inicio ? ` – ${formatarData(c.periodo_fim)}` : ""}</span> },
    { chave: "valor", rotulo: "Valor", valor: (c) => c.valor_centavos, numerica: true, celula: (c) => formatarReais(c.valor_centavos) },
    { chave: "creditos", rotulo: "Entradas", valor: (c) => c.creditos_centavos, numerica: true, celula: (c) => formatarReais(c.creditos_centavos) },
    { chave: "debitos", rotulo: "Saídas", valor: (c) => c.debitos_centavos, numerica: true, celula: (c) => formatarReais(c.debitos_centavos) },
    { chave: "n", rotulo: "Relacionados", valor: (c) => c.participacoes.length, numerica: true },
    { chave: "pagina", rotulo: "Fonte", valor: (c) => c.pagina_inicio, numerica: true, celula: (c) => <LinkPagina documentoId={c.documento_id} pagina={c.pagina_inicio} /> },
  ];
  return (
    <Tabela linhas={linhas} colunas={colunas} chave={(c) => c.id} inicial="valor" rotuloVazio="Nenhuma comunicação com essa busca."
      expandir={(c) => (
        <div className="space-y-2 text-xs">
          <p><strong>Relacionados:</strong> {c.participacoes.map((p) => `${atorPorId.get(p.ator_id)?.nome ?? p.ator_id} (${p.papel})`).join("; ")}</p>
          {c.bens.map((b) => <p key={b.id}><strong>{b.tipo === "veiculo" ? "veículo" : "imóvel"}:</strong> {b.descricao}{b.valor_centavos ? ` · ${formatarReais(b.valor_centavos)}` : ""}{b.valor_referencia_centavos ? ` · referência ${formatarReais(b.valor_referencia_centavos)}` : ""}</p>)}
          {c.informacoes && <q className="block whitespace-pre-line border-l-2 border-neutral-300 pl-2 italic">{c.informacoes}</q>}
          {c.consideracoes && <q className="block whitespace-pre-line border-l-2 border-neutral-300 pl-2 italic">{c.consideracoes}</q>}
          {c.ocorrencias.length > 0 && <p className="text-neutral-700"><strong>Enquadramento invocado:</strong> {c.ocorrencias.map((o) => `${o.norma}${o.codigo ? `, ${o.codigo}` : ""}${o.descricao ? ` — ${o.descricao}` : ""}`).join("; ")}</p>}
        </div>
      )} />
  );
}

// ---------------------------------------------------------------- bens

type LinhaBem = FluxosDados["comunicacoes"][number]["bens"][number] & { comunicacao: FluxoComunicacao; titular: string };

export function TabelaBens({ dados, busca }: { dados: FluxosDados; busca: string }) {
  const atorPorId = useMemo(() => new Map(dados.atores.map((a) => [a.id, a])), [dados]);
  const q = busca.trim().toLowerCase();
  const linhas = useMemo<LinhaBem[]>(() => dados.comunicacoes.flatMap((c) => c.bens.map((b) => ({ ...b, comunicacao: c, titular: (c.titular_ator_id ? atorPorId.get(c.titular_ator_id)?.nome : null) ?? "—" })))
    .filter((b) => !q || b.descricao.toLowerCase().includes(q) || b.titular.toLowerCase().includes(q)), [dados, atorPorId, q]);
  const colunas: Coluna<LinhaBem>[] = [
    { chave: "tipo", rotulo: "Tipo", valor: (b) => (b.tipo === "veiculo" ? "veículo" : "imóvel") },
    { chave: "descricao", rotulo: "Descrição", valor: (b) => b.descricao, classe: "max-w-[420px]" },
    { chave: "titular", rotulo: "Titular da comunicação", valor: (b) => b.titular },
    { chave: "valor", rotulo: "Valor declarado", valor: (b) => b.valor_centavos, numerica: true, celula: (b) => formatarReais(b.valor_centavos) },
    { chave: "ref", rotulo: "Valor de referência", valor: (b) => b.valor_referencia_centavos, numerica: true, celula: (b) => formatarReais(b.valor_referencia_centavos) },
    { chave: "razao", rotulo: "Declarado ÷ referência", valor: (b) => (b.valor_centavos && b.valor_referencia_centavos ? b.valor_centavos / b.valor_referencia_centavos : null), numerica: true, celula: (b) => (b.valor_centavos && b.valor_referencia_centavos ? `${(b.valor_centavos / b.valor_referencia_centavos).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}×` : "—") },
    { chave: "data", rotulo: "Data do negócio", valor: (b) => b.data_negocio, celula: (b) => <span className="whitespace-nowrap">{b.data_negocio ? formatarData(b.data_negocio) : "—"}</span> },
    { chave: "fonte", rotulo: "Fonte", valor: (b) => b.comunicacao.pagina_inicio, numerica: true, celula: (b) => <LinkPagina documentoId={b.comunicacao.documento_id} pagina={b.comunicacao.pagina_inicio} /> },
  ];
  return <Tabela linhas={linhas} colunas={colunas} chave={(b) => b.id} inicial="valor" rotuloVazio="Nenhum bem com essa busca." />;
}

// ---------------------------------------------------------------- painel: uma busca, quatro abas

type Aba = "pessoas" | "fluxos" | "comunicacoes" | "bens";

export function PainelFluxos({ dados, situacoes }: { dados: FluxosDados; situacoes: Record<number, SituacaoAutos> }) {
  const [aba, setAba] = useState<Aba>("pessoas");
  const [busca, setBusca] = useState("");
  const nBens = dados.comunicacoes.reduce((s, c) => s + c.bens.length, 0);
  const abas: { id: Aba; rotulo: string; n: number; dica: string }[] = [
    { id: "pessoas", rotulo: "Pessoas e empresas", n: dados.atores.length, dica: "quem recebeu, quem pagou e a situação de cada um nos autos" },
    { id: "fluxos", rotulo: "Fluxos", n: dados.transacoes.filter((t) => t.natureza !== "resumo_tipo").length, dica: "uma linha por transação, com a página do relatório e o trecho literal" },
    { id: "comunicacoes", rotulo: "Comunicações", n: dados.comunicacoes.length, dica: "o que cada banco, cooperativa, cartório ou concessionária relatou ao COAF" },
    { id: "bens", rotulo: "Bens", n: nBens, dica: "imóveis e veículos, com valor declarado e valor de referência" },
  ];
  const placeholder: Record<Aba, string> = { pessoas: "nome, atividade, CNPJ…", fluxos: "quem paga, quem recebe, descrição…", comunicacoes: "titular, comunicante, relacionado…", bens: "descrição, titular…" };
  return (
    <section aria-labelledby="painel" className="folha border border-neutral-300 bg-white p-4">
      <h2 id="painel" className="sr-only">Dados</h2>
      <label className="block">
        <span className="block text-sm font-semibold">Buscar</span>
        <input type="search" className="mt-1 w-full rounded border border-neutral-400 bg-neutral-50 px-3 py-2 text-base" value={busca} onChange={(ev) => setBusca(ev.target.value)} placeholder={placeholder[aba]} aria-label="Buscar na aba ativa" />
      </label>
      <div role="tablist" aria-label="Tabelas" className="mt-3 flex flex-wrap gap-1 border-b border-neutral-300">
        {abas.map((a) => (
          <button key={a.id} role="tab" type="button" aria-selected={aba === a.id} id={`aba-${a.id}`} aria-controls={`painel-${a.id}`} title={a.dica}
            className={`toque -mb-px rounded-t border border-b-0 px-3 py-1.5 text-sm ${aba === a.id ? "border-neutral-400 bg-white font-semibold" : "border-transparent text-neutral-700 hover:bg-neutral-100"}`}
            onClick={() => setAba(a.id)}>
            {a.rotulo} <span className="text-xs text-neutral-600">({a.n})</span>
          </button>
        ))}
      </div>
      <p className="mt-2 text-xs text-neutral-600">{abas.find((a) => a.id === aba)?.dica}. Clique no título de uma coluna para ordenar; ▸ abre os detalhes da linha.</p>
      <div role="tabpanel" id={`painel-${aba}`} aria-labelledby={`aba-${aba}`}>
        {aba === "pessoas" && <TabelaAtores dados={dados} situacoes={situacoes} busca={busca} />}
        {aba === "fluxos" && <TabelaFluxos dados={dados} busca={busca} />}
        {aba === "comunicacoes" && <TabelaComunicacoes dados={dados} busca={busca} />}
        {aba === "bens" && <TabelaBens dados={dados} busca={busca} />}
      </div>
    </section>
  );
}
