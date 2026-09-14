import Link from "next/link";
import { PontosChave } from "@/components/PontosChave";
import { getIntegridade, getMeta } from "@/lib/data";
import { formatarDataHora } from "@/lib/tipos";

/* Como qualquer pessoa confere, sozinha, que o que está aqui é o que está no portal do STF. */
export default function PaginaVerificar() {
  const meta = getMeta();
  const integ = getIntegridade();
  const exemplo = integ.documentos.find((d) => d.codigo_autenticacao) ?? integ.documentos[0];
  return (
    <div className="space-y-8">
      <header className="max-w-3xl">
        <h1 className="text-2xl">Verificar</h1>
        <p className="leitura mt-1">
          Este site não pede confiança: cada documento e cada página do portal que ele usa tem uma impressão digital
          (um <em>hash</em> SHA-256) registrada no momento da cópia. Se um byte mudar, o hash muda. Aqui está como conferir,
          sozinho, com o que o STF publica.
        </p>
      </header>

      <PontosChave titulo="O que você encontra aqui" itens={[
        { texto: <><strong>{integ.documentos.length} documentos</strong> com hash SHA-256 registrado{exemplo?.codigo_autenticacao ? "; a maioria tem código de autenticação do próprio STF" : ""}.</> },
        { texto: <>Três jeitos de conferir, do mais simples ao mais completo: pelo código do STF (um minuto), comparando o arquivo com o que o portal entrega hoje, ou refazendo a base inteira.</> },
        { texto: <>Todos os dados podem ser baixados (CSV, JSON, feed) e o repositório guarda os originais versionados com carimbo de tempo.</> },
      ]} />

      <section className="folha border border-neutral-300 bg-white p-4">
        <h2 className="text-lg">1. Pelo código de autenticação do STF (o jeito mais simples)</h2>
        <p className="leitura mt-1 text-sm">
          Toda decisão assinada eletronicamente traz um código e uma senha impressos no rodapé. O portal do STF tem uma página
          oficial que, com esses dois valores, mostra o documento original. Na página de cada documento deste site, os dois aparecem
          em "Autenticação no STF".
        </p>
        {exemplo?.codigo_autenticacao && (
          <p className="mt-2 text-sm">
            Exemplo: <Link className="underline" href={`/documento/${exemplo.id}`}>{exemplo.titulo} {exemplo.id}</Link> ({exemplo.processo}) — código <code>{exemplo.codigo_autenticacao}</code>
            {exemplo.senha_autenticacao ? <>, senha <code>{exemplo.senha_autenticacao}</code></> : null}, em{" "}
            <a className="underline" href="http://www.stf.jus.br/portal/autenticacao/autenticarDocumento.asp" rel="noreferrer">autenticarDocumento.asp</a>.
          </p>
        )}
      </section>

      <section className="folha border border-neutral-300 bg-white p-4">
        <h2 className="text-lg">2. Comparando o arquivo com o que o portal entrega hoje</h2>
        <p className="leitura mt-1 text-sm">
          Cada página de documento mostra a URL de origem no portal e o SHA-256 da cópia. Baixe o arquivo pela URL e calcule o hash no seu computador:
        </p>
        <div className="mt-2 grid gap-2 text-xs md:grid-cols-3">
          <div><p className="font-semibold">Windows (PowerShell)</p><pre className="overflow-x-auto rounded bg-neutral-100 p-2"><code>Get-FileHash .\arquivo.pdf -Algorithm SHA256</code></pre></div>
          <div><p className="font-semibold">macOS</p><pre className="overflow-x-auto rounded bg-neutral-100 p-2"><code>shasum -a 256 arquivo.pdf</code></pre></div>
          <div><p className="font-semibold">Linux</p><pre className="overflow-x-auto rounded bg-neutral-100 p-2"><code>sha256sum arquivo.pdf</code></pre></div>
        </div>
        <p className="mt-2 text-sm text-neutral-700">
          Se o valor for igual ao do site, a cópia é idêntica ao que o portal entrega. Se for diferente, ou o portal mudou o arquivo
          depois da nossa cópia, ou a nossa cópia está errada; em qualquer caso, a diferença fica visível, e é isso que importa.
        </p>
      </section>

      <section className="folha border border-neutral-300 bg-white p-4">
        <h2 className="text-lg">3. Conferindo o conjunto inteiro</h2>
        <p className="leitura mt-1 text-sm">
          O arquivo <a className="underline" href="data/integridade.json">integridade.json</a> lista as {integ.totais.snapshots} páginas do portal e os {integ.totais.documentos} documentos
          copiados, cada um com URL de origem, data e hora da cópia e SHA-256, mais os {integ.totais.registros_de_coleta} registros de coleta.
          O hash do próprio manifesto, gerado em {formatarDataHora(integ.gerado_em)}, é:
        </p>
        <p className="mt-2 break-all font-mono text-xs">{integ.raiz_sha256}</p>
        <p className="mt-2 text-sm text-neutral-700">
          Ele está gravado em <code>INTEGRIDADE.sha256</code> no repositório, e o histórico do Git guarda cada versão anterior. Assim,
          uma alteração silenciosa no conjunto deixaria rastro em dois lugares independentes. O próximo passo previsto é ancorar esse
          hash em um carimbo de tempo público (OpenTimestamps), para provar também <em>quando</em> cada cópia existia.
        </p>
      </section>

      <section className="folha border border-neutral-300 bg-white p-4">
        <h2 className="text-lg">Baixar os dados e acompanhar</h2>
        <p className="leitura mt-1 text-sm">Para planilha (CSV, UTF-8, ponto e vírgula; cada linha traz documento, página e trecho literal):</p>
        <ul className="mt-2 flex flex-wrap gap-2 text-sm">
          <li><a className="toque rounded border border-neutral-400 px-3 py-1 underline hover:bg-neutral-100" href="data/decisoes.csv">decisoes.csv</a></li>
          <li><a className="toque rounded border border-neutral-400 px-3 py-1 underline hover:bg-neutral-100" href="data/assercoes.csv">assercoes.csv</a></li>
          <li><a className="toque rounded border border-neutral-400 px-3 py-1 underline hover:bg-neutral-100" href="data/cronologia.csv">cronologia.csv</a></li>
          <li><a className="toque rounded border border-neutral-400 px-3 py-1 underline hover:bg-neutral-100" href="https://github.com/ldickmann/autos-abertos/releases" rel="noreferrer">pacote completo (release)</a></li>
        </ul>
        <p className="mt-2 text-sm text-neutral-700">Para receber avisos e as rodadas de vigilância do portal num leitor de feeds: <a className="underline" href="feed.xml">feed.xml</a> (Atom).</p>
      </section>

      <section className="folha border border-neutral-300 bg-white p-4">
        <h2 className="text-lg">4. Refazendo tudo do zero</h2>
        <p className="leitura mt-1 text-sm">
          O código é aberto. Qualquer pessoa pode coletar de novo o mesmo processo no portal do STF, reconstruir a base e comparar os hashes com os
          publicados aqui. As instruções estão no <a className="underline" href="https://github.com/ldickmann/autos-abertos" rel="noreferrer">repositório</a>;
          a coleta respeita o portal (uma requisição por vez, a cada 3 segundos, com identificação e contato).
        </p>
        <p className="mt-2 text-xs text-neutral-600">Base gerada em {formatarDataHora(meta.gerado_em)}.</p>
      </section>
    </div>
  );
}
