"use client";

import { useSyncExternalStore } from "react";

/*
  Diz se a tela satisfaz uma media query. No servidor (e durante a hidratação) devolve `false`,
  então o HTML estático é o do celular: painéis fechados. No desktop eles abrem logo após hidratar,
  sem deslocar o conteúdo principal.
*/
export function useTelaLarga(query = "(min-width: 1024px)"): boolean {
  return useSyncExternalStore(
    (aoMudar) => {
      const mq = window.matchMedia(query);
      mq.addEventListener("change", aoMudar);
      return () => mq.removeEventListener("change", aoMudar);
    },
    () => window.matchMedia(query).matches,
    () => false,
  );
}
