"use client";

import { useState, type ReactNode } from "react";

/*
  Peças comuns a toda lista filtrável do site, para que o leitor encontre sempre a mesma coisa no mesmo lugar:
  um campo "procurar" que ignora acentos, a contagem "N de M" com o botão de limpar quando há filtro ativo,
  um estado vazio que diz o que fazer, e "mostrar mais" para listas longas.
*/

export const normalizar = (s: string | null | undefined): string => (s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/* Verdadeiro se todas as palavras da consulta aparecem no texto (sem acento, sem caixa). */
export function casa(consulta: string, ...campos: (string | null | undefined)[]): boolean {
  const termos = normalizar(consulta).split(/\s+/).filter(Boolean);
  if (!termos.length) return true;
  const alvo = normalizar(campos.join(" "));
  return termos.every((t) => alvo.includes(t));
}

export function CampoProcurar({ valor, onChange, rotulo = "Procurar nesta lista", placeholder, className = "" }: {
  valor: string; onChange: (v: string) => void; rotulo?: string; placeholder?: string; className?: string;
}) {
  return (
    <label className={`flex min-w-0 flex-col ${className}`}>
      <span className="font-medium">{rotulo}</span>
      <input type="search" className="mt-1 w-full min-w-0 rounded border border-neutral-400 bg-neutral-50 px-2 py-1" value={valor} onChange={(ev) => onChange(ev.target.value)} placeholder={placeholder} />
    </label>
  );
}

export function Contagem({ n, total, rotulo, ativo, onLimpar, className = "", children }: {
  n: number; total: number; rotulo: string; ativo: boolean; onLimpar: () => void; className?: string; children?: ReactNode;
}) {
  return (
    <p role="status" className={`flex flex-wrap items-center gap-x-3 gap-y-1 text-neutral-700 ${className}`}>
      <span>{n === total ? `${total} ${rotulo}` : `${n} de ${total} ${rotulo}`}{children}</span>
      {ativo && <button type="button" className="toque rounded border border-neutral-400 px-2 py-0.5 text-xs hover:bg-neutral-100" onClick={onLimpar}>limpar filtros</button>}
    </p>
  );
}

export function Vazio({ onLimpar, dica = "Nada com esses filtros." }: { onLimpar?: () => void; dica?: string }) {
  return (
    <p className="rounded border border-dashed border-neutral-400 p-4 text-sm text-neutral-700">
      {dica}{onLimpar && <> <button type="button" className="toque underline" onClick={onLimpar}>Limpar os filtros</button> ou tente outra palavra.</>}
    </p>
  );
}

/* Mostra `passo` itens de cada vez; o botão diz quantos faltam. Reinicia quando a lista muda de tamanho. */
export function usePaginar<T>(itens: T[], passo = 100): { visiveis: T[]; restantes: number; mais: () => void } {
  const [limite, setLimite] = useState(passo);
  const [tamanho, setTamanho] = useState(itens.length);
  if (tamanho !== itens.length) { setTamanho(itens.length); setLimite(passo); }
  return { visiveis: itens.slice(0, limite), restantes: Math.max(0, itens.length - limite), mais: () => setLimite((l) => l + passo) };
}

export function MostrarMais({ restantes, onMais, rotulo = "itens" }: { restantes: number; onMais: () => void; rotulo?: string }) {
  if (restantes <= 0) return null;
  return (
    <p className="text-sm">
      <button type="button" className="toque rounded border border-neutral-400 px-3 py-1 hover:bg-neutral-100" onClick={onMais}>Mostrar mais ({restantes} {rotulo} restantes)</button>
    </p>
  );
}
