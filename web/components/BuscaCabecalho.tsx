"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";

/*
  Busca sempre à vista. É um formulário GET para /busca/?q=…, então funciona sem JavaScript; com ele, no celular o
  campo fica escondido atrás de um botão e abre já focado. Na própria página de busca o campo do cabeçalho some:
  o da página é o mesmo, maior.
*/
export function BuscaCabecalho() {
  const pathname = usePathname() ?? "/";
  const [aberto, setAberto] = useState(false);
  const campo = useRef<HTMLInputElement>(null);
  useEffect(() => { if (aberto) campo.current?.focus(); }, [aberto]);
  useEffect(() => { setAberto(false); }, [pathname]);
  if (pathname.replace(/\/+$/, "") === "/busca") return null;
  const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
  return (
    <>
      <button type="button" className="toque rounded border border-neutral-300 bg-white px-2.5 py-1.5 text-sm md:hidden" aria-expanded={aberto} aria-controls="busca-cabecalho" onClick={() => setAberto((v) => !v)}>
        <span aria-hidden="true">⌕</span> Buscar
      </button>
      <form id="busca-cabecalho" role="search" action={`${base}/busca/`} method="get"
        className={`${aberto ? "flex" : "hidden"} order-1 col-span-3 min-w-0 items-center gap-1 md:order-none md:col-span-1 md:flex md:justify-self-end`}>
        <label className="sr-only" htmlFor="q-cabecalho">Buscar nos autos</label>
        <input ref={campo} id="q-cabecalho" name="q" type="search" placeholder="Buscar nos autos: nome, empresa, tema…" autoComplete="off"
          className="w-full min-w-0 rounded border border-neutral-400 bg-neutral-50 px-3 py-1.5 text-sm md:w-64 lg:w-72" />
        <button type="submit" className="toque shrink-0 whitespace-nowrap rounded border border-neutral-400 px-2.5 py-1.5 text-sm hover:bg-neutral-100">Buscar</button>
      </form>
    </>
  );
}
