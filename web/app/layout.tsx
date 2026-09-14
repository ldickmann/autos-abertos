import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { getMeta, formatarDataHora } from "@/lib/data";

export const metadata: Metadata = {
  title: "Mapeador de processos do STF",
  description: "Dados públicos de processos do Supremo Tribunal Federal, estruturados, buscáveis e com proveniência em cada item.",
};

const NAV = [
  { href: "/", rotulo: "Início" },
  { href: "/busca", rotulo: "Busca" },
  { href: "/assercoes", rotulo: "Asserções" },
  { href: "/grafo", rotulo: "Grafo" },
  { href: "/entidades", rotulo: "Entidades" },
  { href: "/sobre", rotulo: "Método" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const meta = getMeta();
  return (
    <html lang="pt-BR">
      <body className="min-h-screen bg-neutral-50 text-neutral-900">
        <a href="#conteudo" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2 focus:outline focus:outline-2 focus:outline-blue-700">
          Pular para o conteúdo
        </a>
        <header className="border-b border-neutral-300 bg-white">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
            <Link href="/" className="text-lg font-bold tracking-tight">
              Mapeador de processos do STF
            </Link>
            <nav aria-label="Principal">
              <ul className="flex flex-wrap gap-1">
                {NAV.map((n) => (
                  <li key={n.href}>
                    <Link href={n.href} className="rounded px-3 py-1.5 text-sm font-medium hover:bg-neutral-100 focus:outline focus:outline-2 focus:outline-blue-700">
                      {n.rotulo}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          </div>
        </header>
        <main id="conteudo" className="mx-auto max-w-6xl px-4 py-6">{children}</main>
        <footer className="mt-12 border-t border-neutral-300 bg-white">
          <div className="mx-auto max-w-6xl px-4 py-4 text-xs text-neutral-700">
            <p>
              Fonte: portal público do STF (portal.stf.jus.br) e sistemas.stf.jus.br. Base gerada em {formatarDataHora(meta.gerado_em)}.
              Cada item mostra a data em que foi coletado e aponta para o documento de origem. Este site não emite opinião nem conclusão
              sobre pessoas; registra o que consta nos autos públicos, com o status processual literal do portal.
            </p>
            <p className="mt-1">Código aberto: <a className="underline" href="https://github.com/ldickmann/nao-definido">github.com/ldickmann/nao-definido</a></p>
          </div>
        </footer>
      </body>
    </html>
  );
}
