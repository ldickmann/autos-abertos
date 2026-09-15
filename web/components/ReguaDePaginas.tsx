"use client";

import { useEffect, useState, type FormEvent } from "react";

/*
  Régua fixa para documentos longos: diz em que página o leitor está e salta para a que ele digitar.
  Segue os blocos com id "p-N" (cartões de página e fichas de página dentro das conversas). Só aparece em
  documentos com mais de oito páginas e só depois que o leitor passou do cabeçalho.
*/
export function ReguaDePaginas({ total }: { total: number }) {
  const [atual, setAtual] = useState<number | null>(null);
  const [visivel, setVisivel] = useState(false);
  const [alvo, setAlvo] = useState("");

  useEffect(() => {
    const blocos = [...document.querySelectorAll<HTMLElement>('[id^="p-"]')].filter((el) => /^p-\d+$/.test(el.id));
    if (!blocos.length) return;
    const topo = () => {
      // a página "atual" é a do último bloco que já passou pelo terço superior da tela
      const linha = window.innerHeight * 0.33;
      let n: number | null = null;
      for (const el of blocos) { if (el.getBoundingClientRect().top <= linha) n = Number(el.id.slice(2)); else break; }
      setAtual(n);
      setVisivel(window.scrollY > 600);
    };
    topo();
    let quadro = 0;
    const aoRolar = () => { cancelAnimationFrame(quadro); quadro = requestAnimationFrame(topo); };
    window.addEventListener("scroll", aoRolar, { passive: true });
    return () => { window.removeEventListener("scroll", aoRolar); cancelAnimationFrame(quadro); };
  }, []);

  const ir = (ev: FormEvent) => {
    ev.preventDefault();
    const n = Number(alvo);
    if (!Number.isInteger(n) || n < 1 || n > total) return;
    const el = document.getElementById(`p-${n}`);
    if (el) { el.scrollIntoView({ block: "start" }); window.history.replaceState(null, "", `#p-${n}`); }
  };

  if (total <= 8) return null;
  return (
    <form onSubmit={ir} className={`regua ${visivel ? "regua-visivel" : ""}`} aria-label="Navegar pelas páginas do documento">
      <span className="regua-atual" aria-live="polite">{atual ? `p. ${atual}` : "início"} <span className="text-neutral-600">de {total}</span></span>
      <label className="sr-only" htmlFor="regua-alvo">Ir para a página</label>
      <input id="regua-alvo" type="number" min={1} max={total} inputMode="numeric" placeholder="ir para" value={alvo} onChange={(ev) => setAlvo(ev.target.value)}
        className="regua-campo rounded border border-neutral-400 bg-neutral-50 px-2 py-1 text-sm" />
      <button type="submit" className="toque rounded border border-neutral-400 px-2 py-1 text-sm hover:bg-neutral-100">Ir</button>
      <a href="#conteudo" className="toque rounded px-2 py-1 text-sm underline" onClick={(ev) => { ev.preventDefault(); window.scrollTo({ top: 0 }); }}>topo</a>
    </form>
  );
}
