import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, Newsreader } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { NavPrincipal } from "@/components/NavPrincipal";
import { TemaToggle } from "@/components/TemaToggle";
import { Aviso } from "@/components/Aviso";
import { getAvisos, getMeta, formatarDataHora } from "@/lib/data";

const newsreader = Newsreader({ subsets: ["latin"], variable: "--font-newsreader", axes: ["opsz"], style: ["normal", "italic"] });
const plex = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-plex" });
const plexMono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400"], variable: "--font-plex-mono" });

export const metadata: Metadata = {
  title: "Autos Abertos",
  description: "Dados públicos de processos do Supremo Tribunal Federal, estruturados, buscáveis e com proveniência em cada item.",
};

// Aplica o tema antes da primeira pintura, para não piscar. Padrão: escuro.
const SCRIPT_TEMA = `(function(){var t='escuro';try{var s=localStorage.getItem('tema');if(s==='claro'||s==='escuro')t=s;}catch(e){}document.documentElement.dataset.tema=t;})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const meta = getMeta();
  const avisos = getAvisos();
  return (
    <html lang="pt-BR" data-tema="escuro" className={`${newsreader.variable} ${plex.variable} ${plexMono.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: SCRIPT_TEMA }} />
      </head>
      <body className="min-h-screen bg-neutral-50 text-neutral-900">
        <a href="#conteudo" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2">
          Pular para o conteúdo
        </a>
        <header className="border-b border-neutral-300 bg-white">
          {/* Até lg: título e tema na primeira linha, nav como trilho rolável na segunda. Desktop: tudo numa linha. */}
          <div className="mx-auto grid max-w-6xl grid-cols-[1fr_auto] items-center gap-x-3 gap-y-2 px-4 py-3 lg:grid-cols-[auto_1fr_auto]">
            <Link href="/" className="font-serif text-xl tracking-tight">
              Autos Abertos <span className="hidden font-sans text-sm text-neutral-700 sm:inline">processos públicos do STF</span>
            </Link>
            <div className="order-3 col-span-2 min-w-0 lg:order-2 lg:col-span-1 lg:justify-self-end"><NavPrincipal /></div>
            <div className="order-2 lg:order-3"><TemaToggle /></div>
          </div>
        </header>
        {avisos.map((a) => <Aviso key={a.id} aviso={a} compacto />)}
        <main id="conteudo" className="mx-auto max-w-6xl px-4 py-6">{children}</main>
        <footer className="mt-12 border-t border-neutral-300 bg-white">
          <div className="mx-auto max-w-6xl px-4 py-4 text-xs text-neutral-700">
            <p>
              Fonte: portal público do STF (portal.stf.jus.br) e sistemas.stf.jus.br. Base gerada em {formatarDataHora(meta.gerado_em)}.
              Cada item mostra a data em que foi coletado e aponta para o documento de origem. Este site não emite opinião nem conclusão
              sobre pessoas; registra o que consta nos autos públicos, com o status processual literal do portal.
            </p>
            <p className="mt-1">Código aberto: <a className="underline" href="https://github.com/ldickmann/autos-abertos">github.com/ldickmann/autos-abertos</a></p>
          </div>
        </footer>
      </body>
    </html>
  );
}
