"use client";

import { useEffect, useState } from "react";

/* Botão "topo" que aparece depois de uma tela e meia de rolagem, em toda página. Nos documentos longos a régua
   de páginas já tem o seu, então aqui ele se cala. */
export function VoltarAoTopo() {
  const [visivel, setVisivel] = useState(false);
  const [temRegua, setTemRegua] = useState(false);
  useEffect(() => {
    setTemRegua(!!document.querySelector(".regua"));
    const ver = () => setVisivel(window.scrollY > window.innerHeight * 1.5);
    ver();
    window.addEventListener("scroll", ver, { passive: true });
    return () => window.removeEventListener("scroll", ver);
  }, []);
  if (temRegua) return null;
  return (
    <a href="#conteudo" className={`topo ${visivel ? "topo-visivel" : ""}`} aria-label="Voltar ao topo da página"
      onClick={(ev) => { ev.preventDefault(); window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" }); }}>
      ↑ topo
    </a>
  );
}
