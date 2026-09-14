"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", rotulo: "Início" },
  { href: "/linha-do-tempo", rotulo: "Linha do tempo" },
  { href: "/grafo", rotulo: "Grafo" },
  { href: "/busca", rotulo: "Busca" },
  { href: "/assercoes", rotulo: "Asserções" },
  { href: "/entidades", rotulo: "Entidades" },
  { href: "/referencias", rotulo: "Referências" },
  { href: "/sobre", rotulo: "Método" },
];

// Páginas de detalhe (processo, documento, entidade) marcam a seção mais próxima.
function atual(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/" || pathname.startsWith("/processo/") || pathname.startsWith("/documento/");
  if (href === "/entidades") return pathname.startsWith("/entidade");
  return pathname === href || pathname.startsWith(href + "/");
}

// Em telas estreitas vira um trilho horizontal de uma linha, rolável; no desktop, a fila de sempre.
export function NavPrincipal() {
  const pathname = usePathname() ?? "/";
  return (
    <nav aria-label="Principal" className="nav-trilho -mx-4 overflow-x-auto px-4 lg:mx-0 lg:overflow-visible lg:px-0">
      <ul className="flex w-max gap-0.5 lg:w-auto lg:flex-wrap">
        {NAV.map((n) => (
          <li key={n.href}>
            <Link
              href={n.href}
              aria-current={atual(pathname, n.href) ? "page" : undefined}
              className="block whitespace-nowrap rounded px-2.5 py-1.5 text-sm font-medium hover:bg-neutral-100"
            >
              {n.rotulo}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
