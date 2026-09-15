"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import type { Assercao, ConversaItem, ConversasDocumento } from "@/lib/tipos";
import { BadgeEpistemico } from "@/components/Badges";

/*
  Reconstituição de conversa, na pele do WhatsApp, a partir do que a PF escreveu sobre o celular analisado.
  O que está aqui não é a captura de tela (que só existe no PDF): é a frase da PF, tal qual, e as citações que
  ela faz — o lado direito é o aparelho analisado, como o próprio dono veria. Cada balão vira pelo verso e
  mostra a página e a frase literal de onde saiu.

  Micro-interações (só com mouse fino e sem prefers-reduced-motion): o aparelho inclina para o ponteiro, como
  um telefone na mão; o balão levanta ao passar o mouse e desdobra o verso ao clicar; as mensagens "chegam" na
  primeira vez em que a tela entra na viewport.
*/

type Pagina = { n: number; texto: string };

const MIUDAS = new Set(["de", "da", "do", "dos", "das", "e"]);
function nomeExibido(nome: string, aparelho: string, lado: "enviada" | "recebida" | null): string {
  if (lado === "enviada") return aparelho;
  return nome.split(/\s+/).map((w, i) => (i > 0 && MIUDAS.has(w.toLowerCase()) ? w.toLowerCase() : w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())).join(" ");
}
function corDoNome(nome: string): number {
  let h = 0;
  for (const c of nome) h = (h * 31 + c.charCodeAt(0)) % 360;
  return h;
}
function dataCurta(iso: string): string {
  const [a, m, d] = iso.split("-");
  return `${d}/${m}/${a}`;
}

/* A frase da PF com as citações em itálico, para o leitor ver o que é fala e o que é paráfrase. */
function ComCitacoes({ texto }: { texto: string }) {
  const partes = texto.split(/([“"][^“”"]+[”"])/);
  return <>{partes.map((p, i) => (/^[“"]/.test(p) ? <q key={i} className="zap-cit">{p.slice(1, -1)}</q> : <span key={i}>{p}</span>))}</>;
}

function Balao({ nome, lado, texto, hora, verso, indice, fragmento }: {
  nome: string; lado: "enviada" | "recebida"; texto: string; hora?: string | null; verso: ReactNode; indice: number; fragmento?: boolean;
}) {
  const [aberto, setAberto] = useState(false);
  return (
    <div className={`zap-linha zap-${lado}`} style={{ "--i": Math.min(indice, 14) } as React.CSSProperties}>
      <div className={`zap-balao ${aberto ? "zap-aberto" : ""}`} style={lado === "recebida" ? ({ "--matiz": corDoNome(nome) } as React.CSSProperties) : undefined}>
        <button type="button" className="zap-frente" aria-expanded={aberto} onClick={() => setAberto((v) => !v)} title={aberto ? "Esconder a fonte" : "Ver a fonte (página e frase da PF)"}>
          <span className="zap-nome">{nome}</span>
          <span className="zap-texto">{fragmento ? <span className="zap-frag" aria-label="trecho citado pela PF">…</span> : null}{texto}</span>
          <span className="zap-hora">{hora ?? ""}</span>
        </button>
        <div className="zap-verso" hidden={!aberto}>{verso}</div>
      </div>
    </div>
  );
}

function Fonte({ pagina, trecho, extra }: { pagina: number; trecho: string; extra?: ReactNode }) {
  return (
    <p>
      <span className="carimbo zap-selo-pf">PF</span> IPJ-A, p. {pagina}{extra}: <q className="italic">{trecho}</q>{" "}
      <a className="underline" href={`#texto-p-${pagina}`}>texto da página</a>
    </p>
  );
}

function Itens({ itens, aparelho }: { itens: ConversaItem[]; aparelho: string }) {
  let indice = 0;
  let dataAtual: string | null = null;
  const saida: ReactNode[] = [];
  itens.forEach((it, k) => {
    if (it.tipo === "secao") {
      saida.push(<div key={k} className="zap-chip zap-chip-secao" role="heading" aria-level={4}>{it.texto}</div>);
      return;
    }
    if (it.tipo === "figura") {
      saida.push(
        <div key={k} className="zap-figura" style={{ "--i": Math.min(indice++, 14) } as React.CSSProperties}>
          <span className="zap-figura-rotulo">Figura {it.numero} · captura de tela no PDF, p. {it.pagina}</span>
          <span className="zap-figura-legenda"><ComCitacoes texto={it.legenda} /></span>
        </div>,
      );
      return;
    }
    if (it.tipo === "mensagem") {
      if (it.data && it.data !== dataAtual) { dataAtual = it.data; saida.push(<div key={`d${k}`} className="zap-chip zap-chip-data">{dataCurta(it.data)}</div>); }
      saida.push(
        <Balao key={k} nome={nomeExibido(it.de, aparelho, it.lado)} lado={it.lado} texto={it.texto} hora={it.hora} indice={indice++}
          verso={<Fonte pagina={it.pagina} trecho={it.trecho} extra={it.para ? <> — {it.verbo} a {nomeExibido(it.para, aparelho, null)}{it.fuso ? `, ${it.hora} (${it.fuso})` : ""}</> : null} />} />,
      );
      return;
    }
    // relato: a frase da PF; se ela tem um só falante, as citações viram balões dele logo abaixo
    saida.push(
      <div key={k} className="zap-relato" style={{ "--i": Math.min(indice++, 14) } as React.CSSProperties}>
        <span className="zap-relato-quem">PF relata</span> <ComCitacoes texto={it.texto} />
      </div>,
    );
    if (it.de && it.lado) {
      for (const [j, fala] of it.falas.entries()) {
        saida.push(
          <Balao key={`${k}-${j}`} nome={nomeExibido(it.de, aparelho, it.lado)} lado={it.lado} texto={fala} indice={indice++} fragmento
            verso={<Fonte pagina={it.pagina} trecho={it.trecho} extra={<> — trecho citado dentro da frase da PF</>} />} />,
        );
      }
    }
  });
  return <>{saida}</>;
}

function usarInclinacao(ref: React.RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const pode = window.matchMedia("(hover: hover) and (pointer: fine)").matches && !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!pode) return;
    let quadro = 0;
    const mover = (ev: PointerEvent) => {
      cancelAnimationFrame(quadro);
      quadro = requestAnimationFrame(() => {
        const r = el.getBoundingClientRect();
        const x = (ev.clientX - r.left) / r.width, y = (ev.clientY - r.top) / r.height;
        el.style.setProperty("--ry", `${((x - 0.5) * 5).toFixed(2)}deg`);
        el.style.setProperty("--rx", `${((0.5 - y) * 4).toFixed(2)}deg`);
        el.style.setProperty("--mx", `${(x * 100).toFixed(1)}%`);
        el.style.setProperty("--my", `${(y * 100).toFixed(1)}%`);
      });
    };
    const sair = () => { cancelAnimationFrame(quadro); el.style.setProperty("--rx", "0deg"); el.style.setProperty("--ry", "0deg"); };
    el.addEventListener("pointermove", mover);
    el.addEventListener("pointerleave", sair);
    return () => { el.removeEventListener("pointermove", mover); el.removeEventListener("pointerleave", sair); };
  }, [ref]);
}

function usarChegada(ref: React.RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = ref.current;
    if (!el || !("IntersectionObserver" in window)) { el?.classList.add("zap-visto"); return; }
    const obs = new IntersectionObserver((entradas) => {
      for (const e of entradas) if (e.isIntersecting) { el.classList.add("zap-visto"); obs.disconnect(); }
    }, { threshold: 0, rootMargin: "0px 0px 10% 0px" });  // qualquer pixel do cartão à vista: cartões longos nunca atingiriam 15 %
    obs.observe(el);
    return () => obs.disconnect();
  }, [ref]);
}

/* Um cartão por sequência de páginas consecutivas com conversa; `paginas` são as páginas dessa sequência. */
export function ConversaWhats({ aparelho, fonte, paginas, textos, assercoes }: {
  aparelho: string; fonte: string; paginas: ConversasDocumento["paginas"]; textos: Pagina[]; assercoes: Map<number, Assercao[]>;
}) {
  const ref = useRef<HTMLElement>(null);
  usarInclinacao(ref);
  usarChegada(ref);
  const ns = paginas.map((p) => p.n);
  const iniciais = aparelho.split(/\s+/).map((w) => w[0]).slice(0, 2).join("");
  const nFalas = paginas.reduce((s, p) => s + p.itens.reduce((t, i) => t + (i.tipo === "mensagem" ? 1 : i.tipo === "relato" ? i.falas.length : 0), 0), 0);
  return (
    <section ref={ref} className="zap" aria-label={`Conversas descritas pela PF, páginas ${ns[0]} a ${ns[ns.length - 1]}`}>
      <header className="zap-topo">
        <span className="zap-avatar" aria-hidden="true">{iniciais}</span>
        <span className="zap-topo-texto">
          <strong>Aparelho de {aparelho}</strong>
          <span>segundo a Polícia Federal · {ns.length === 1 ? `p. ${ns[0]}` : `p. ${ns[0]}–${ns[ns.length - 1]}`} · {nFalas} {nFalas === 1 ? "fala citada" : "falas citadas"}</span>
        </span>
        <span className="carimbo zap-selo">reconstituição</span>
      </header>
      <div className="zap-tela">
        <p className="zap-aviso">As capturas de tela ficaram no PDF. O que se lê aqui é a descrição da PF, frase por frase; à direita, o que saiu do aparelho analisado. Toque num balão para ver a página e a frase de onde ele veio.</p>
        {paginas.map((p) => (
          <div key={p.n} className="zap-pagina">
            <a className="zap-chip zap-chip-pagina" id={`p-${p.n}`} href={`#texto-p-${p.n}`} title="Texto literal desta página">p. {p.n}</a>
            <Itens itens={p.itens} aparelho={aparelho} />
          </div>
        ))}
      </div>
      <footer className="zap-rodape">
        <p>Fonte: {fonte}. A PF descreve as conversas em prosa e cola as capturas como figuras; o site reconstitui só o que a frase permite: balão quando há um falante inequívoco e citação literal, relato quando não há. Nada aqui é conclusão do site.</p>
        <details className="zap-literal">
          <summary className="cursor-pointer font-semibold">{ns.length === 1 ? `Texto literal da página ${ns[0]}` : `Texto literal das páginas ${ns[0]}–${ns[ns.length - 1]}`}</summary>
          {textos.map((p) => (
            <article key={p.n} id={`texto-p-${p.n}`} className="mt-3 scroll-mt-20 rounded border border-neutral-300 bg-white">
              <h4 className="border-b border-neutral-200 px-4 py-2 text-sm font-semibold">Página {p.n} <a className="ml-2 text-xs font-normal underline" href={`#p-${p.n}`}>↑ na conversa</a></h4>
              {(assercoes.get(p.n) ?? []).length > 0 && (
                <ul className="space-y-2 border-b border-neutral-200 bg-neutral-50 px-4 py-3 text-sm" aria-label={`Asserções da página ${p.n}`}>
                  {(assercoes.get(p.n) ?? []).map((a) => (
                    <li key={a.id} id={`assercao-${a.id}`} className="flex gap-2"><BadgeEpistemico tipo={a.tipo_epistemico} /><div><p>{a.texto}{a.atribuida_a ? <span className="text-neutral-700"> — atribuída a {a.atribuida_a}</span> : null}</p><p className="text-xs text-neutral-700">trecho-fonte: “{a.trecho_fonte}”</p></div></li>
                  ))}
                </ul>
              )}
              <pre className="overflow-x-auto whitespace-pre-wrap px-4 py-3 font-sans text-sm leading-relaxed">{p.texto}</pre>
            </article>
          ))}
        </details>
      </footer>
    </section>
  );
}
