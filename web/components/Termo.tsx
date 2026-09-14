"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import type { Verbete } from "@/lib/tipos";

/* Um termo do glossário: sublinhado pontilhado; ao clicar ou focar, abre uma nota curta ao lado.
   Funciona por toque (sem depender de hover) e fecha com Esc ou clique fora. */
export function Termo({ verbete, children }: { verbete: Verbete | null; children: React.ReactNode }) {
  const [aberto, setAberto] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  const id = useId();
  useEffect(() => {
    if (!aberto) return;
    const fora = (ev: MouseEvent) => { if (ref.current && !ref.current.contains(ev.target as Node)) setAberto(false); };
    const esc = (ev: KeyboardEvent) => { if (ev.key === "Escape") setAberto(false); };
    document.addEventListener("mousedown", fora); document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", fora); document.removeEventListener("keydown", esc); };
  }, [aberto]);
  if (!verbete) return <>{children}</>;
  return (
    <span ref={ref} className="relative inline-block">
      <button type="button" className="termo" aria-expanded={aberto} aria-controls={id} onClick={() => setAberto((a) => !a)} title="o que significa?">
        {children}
      </button>
      {aberto && (
        <span id={id} role="note" className="nota-termo folha">
          <span className="block font-semibold">{verbete.termo}</span>
          <span className="leitura block">{verbete.explicacao}</span>
          <span className="mt-1 block text-xs text-neutral-600">{verbete.fonte === "portal" ? "explicação literal do portal do STF" : <>glossário editorial — <Link className="underline" href="/glossario">ver todos os termos</Link></>}</span>
        </span>
      )}
    </span>
  );
}
