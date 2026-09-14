"use client";

import { useEffect, useState } from "react";

type Tema = "escuro" | "claro";

export function TemaToggle() {
  const [tema, setTema] = useState<Tema>("escuro");
  useEffect(() => {
    const atual = document.documentElement.dataset.tema;
    if (atual === "claro" || atual === "escuro") setTema(atual);
  }, []);
  const alternar = () => {
    const novo: Tema = tema === "escuro" ? "claro" : "escuro";
    document.documentElement.dataset.tema = novo;
    try { localStorage.setItem("tema", novo); } catch { /* sem armazenamento: vale só nesta página */ }
    setTema(novo);
  };
  return (
    <button
      type="button"
      onClick={alternar}
      aria-pressed={tema === "claro"}
      aria-label={tema === "escuro" ? "Mudar para tema claro" : "Mudar para tema escuro"}
      title={tema === "escuro" ? "Tema claro" : "Tema escuro"}
      className="interruptor rounded-full border border-neutral-300 bg-white p-1 hover:border-neutral-400"
    >
      <span className="face relative block h-6 w-6">
        <span aria-hidden className="lado absolute inset-0 grid place-items-center text-sm">☾</span>
        <span aria-hidden className="lado verso absolute inset-0 grid place-items-center text-sm">☀</span>
      </span>
    </button>
  );
}
