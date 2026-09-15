"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/*
  Duas linhas: em cima, seis seções; embaixo, as páginas da seção ativa. Nenhuma rota some — só muda de lugar.
  Páginas de detalhe (processo, documento, entidade) acendem a seção mais próxima.
*/
type Secao = { id: string; rotulo: string; href: string; itens: { href: string; rotulo: string }[]; casa: (p: string) => boolean };

const SECOES: Secao[] = [
  { id: "inicio", rotulo: "Início", href: "/", itens: [], casa: (p) => p === "/" },
  {
    id: "pagamentos", rotulo: "Rede de pagamentos", href: "/rede-de-pagamentos",
    itens: [{ href: "/rede-de-pagamentos", rotulo: "Tabelas: quem pagou, quem recebeu" }, { href: "/rede-de-pagamentos/trajetos", rotulo: "Os caminhos do dinheiro" }],
    casa: (p) => p.startsWith("/rede-de-pagamentos"),
  },
  {
    id: "acontecimentos", rotulo: "Acontecimentos", href: "/cronologia",
    itens: [{ href: "/cronologia", rotulo: "Cronologia" }, { href: "/linha-do-tempo", rotulo: "Linha do tempo" }, { href: "/decisoes", rotulo: "Decisões" }, { href: "/mudancas", rotulo: "O que mudou" }],
    casa: (p) => ["/cronologia", "/linha-do-tempo", "/decisoes", "/mudancas"].some((h) => p === h || p.startsWith(h + "/")),
  },
  {
    id: "autos", rotulo: "Autos", href: "/busca",
    itens: [{ href: "/busca", rotulo: "Buscar nos autos" }, { href: "/assercoes", rotulo: "Asserções" }, { href: "/referencias", rotulo: "Referências" }],
    casa: (p) => ["/busca", "/assercoes", "/referencias", "/processo", "/documento"].some((h) => p === h || p.startsWith(h + "/")),
  },
  {
    id: "quem", rotulo: "Quem é quem", href: "/entidades",
    itens: [{ href: "/entidades", rotulo: "Pessoas e órgãos" }, { href: "/congresso", rotulo: "Congresso" }, { href: "/fontes-externas", rotulo: "Fontes oficiais" }],
    casa: (p) => ["/entidades", "/entidade", "/congresso", "/fontes-externas"].some((h) => p === h || p.startsWith(h + "/")),
  },
  {
    id: "ajuda", rotulo: "Ajuda", href: "/glossario",
    itens: [{ href: "/glossario", rotulo: "Glossário" }, { href: "/verificar", rotulo: "Verificar" }, { href: "/sobre", rotulo: "Método" }],
    casa: (p) => ["/glossario", "/verificar", "/sobre"].some((h) => p === h || p.startsWith(h + "/")),
  },
];

export function NavPrincipal() {
  const pathname = (usePathname() ?? "/").replace(/\/+$/, "") || "/";
  const ativa = SECOES.find((s) => s.casa(pathname)) ?? SECOES[0];
  return (
    <nav aria-label="Principal" className="space-y-1">
      <ul className="nav-trilho -mx-4 flex gap-0.5 overflow-x-auto px-4 lg:mx-0 lg:flex-wrap lg:overflow-visible lg:px-0">
        {SECOES.map((s) => (
          <li key={s.id} className="shrink-0">
            <Link href={s.href} aria-current={ativa.id === s.id ? "page" : undefined}
              className={`block whitespace-nowrap rounded px-2.5 py-1.5 text-sm font-medium hover:bg-neutral-100 ${s.id === "pagamentos" ? "font-semibold" : ""}`}>
              {s.rotulo}
            </Link>
          </li>
        ))}
      </ul>
      {ativa.itens.length > 0 && (
        <ul aria-label={`Páginas de ${ativa.rotulo}`} className="nav-trilho -mx-4 flex gap-0.5 overflow-x-auto border-t border-neutral-200 px-4 pt-1 lg:mx-0 lg:flex-wrap lg:overflow-visible lg:px-0">
          {ativa.itens.map((i) => (
            <li key={i.href} className="shrink-0">
              <Link href={i.href} aria-current={pathname === i.href || (pathname.startsWith(i.href + "/") && !ativa.itens.some((o) => o.href !== i.href && pathname.startsWith(o.href))) ? "page" : undefined}
                className="block whitespace-nowrap rounded px-2.5 py-1 text-sm text-neutral-700 hover:bg-neutral-100">
                {i.rotulo}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </nav>
  );
}
