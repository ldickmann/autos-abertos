"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import type { Aviso as TAviso } from "@/lib/tipos";

/* Aviso editorial de acontecimento público (sessão, julgamento). Mostra o estado em tempo real:
   "começa em…", "ao vivo agora" ou "encerrada". Some sozinho depois de `ate`. */
function estado(a: TAviso, agora: number): { rotulo: string; vivo: boolean; passado: boolean } {
  const inicio = new Date(a.inicio).getTime();
  const fim = new Date(a.ate).getTime();
  if (agora > fim) return { rotulo: "encerrada", vivo: false, passado: true };
  if (agora >= inicio) return { rotulo: "ao vivo agora", vivo: true, passado: false };
  const h = Math.floor((inicio - agora) / 3600000);
  const m = Math.floor(((inicio - agora) % 3600000) / 60000);
  const rotulo = h >= 48 ? `em ${Math.round(h / 24)} dias` : h >= 1 ? `começa em ${h} h ${String(m).padStart(2, "0")} min` : `começa em ${m} min`;
  return { rotulo, vivo: false, passado: false };
}

const fmt = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit", timeZone: "America/Sao_Paulo" });

export function Aviso({ aviso, compacto = false }: { aviso: TAviso; compacto?: boolean }) {
  const [agora, setAgora] = useState<number | null>(null);
  const pathname = usePathname();
  useEffect(() => {
    setAgora(Date.now());
    const t = setInterval(() => setAgora(Date.now()), 30000);
    return () => clearInterval(t);
  }, []);
  const e = agora === null ? { rotulo: "", vivo: false, passado: false } : estado(aviso, agora);
  if (e.passado) return null;
  if (compacto && pathname === "/") return null;   // na capa o cartão completo já está logo abaixo
  const quando = fmt.format(new Date(aviso.inicio)) + " (Brasília)";

  if (compacto) {
    return (
      <div className={`aviso-faixa ${e.vivo ? "aviso-vivo" : ""}`} role="region" aria-label="Aviso de sessão do STF">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2 text-sm">
          <span className="aviso-selo">{e.vivo ? "AO VIVO" : "atenção"}</span>
          <span className="font-semibold">{aviso.titulo}</span>
          <span className="text-neutral-700">{quando}{e.rotulo ? ` · ${e.rotulo}` : ""}</span>
          <a className="toque ml-auto rounded border border-amber-700 px-3 py-1 font-medium underline" href={aviso.acao.url} rel="noreferrer">{e.vivo ? "Assistir agora" : aviso.acao.rotulo}</a>
        </div>
      </div>
    );
  }

  return (
    <section aria-labelledby={`aviso-${aviso.id}`} className={`folha aviso-cartao border p-5 ${e.vivo ? "aviso-vivo" : ""}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="aviso-selo">{e.vivo ? "AO VIVO" : "atenção"}</span>
        <p className="text-sm text-neutral-700">{quando}{e.rotulo ? ` · ${e.rotulo}` : ""}</p>
      </div>
      <h2 id={`aviso-${aviso.id}`} className="mt-1 text-2xl">{aviso.titulo}</h2>
      <p className="leitura mt-2 max-w-3xl">{aviso.resumo}</p>
      {aviso.por_que_importa && <p className="mt-2 max-w-3xl text-sm text-neutral-700">{aviso.por_que_importa}</p>}
      <div className="mt-3 flex flex-wrap gap-2">
        <a className="botao-primario toque rounded px-4 py-2 font-semibold" href={aviso.acao.url} rel="noreferrer">{e.vivo ? "Assistir agora" : aviso.acao.rotulo}</a>
        {aviso.acoes_secundarias.map((x) => <a key={x.url} className="toque rounded border border-neutral-400 px-3 py-2 text-sm hover:bg-neutral-100" href={x.url} rel="noreferrer">{x.rotulo}</a>)}
      </div>
      <details className="mt-3 text-xs text-neutral-700">
        <summary className="cursor-pointer">Aviso editorial: de onde vem esta informação</summary>
        <ul className="mt-1 list-disc pl-5">
          {aviso.fontes.map((f) => <li key={f.url}><a className="underline" href={f.url} rel="noreferrer">{f.rotulo}</a></li>)}
        </ul>
        <p className="mt-1">Este aviso é agenda pública, escrito pela equipe do site a partir das fontes acima; não faz parte dos autos e não afirma nada sobre pessoas.</p>
      </details>
    </section>
  );
}
