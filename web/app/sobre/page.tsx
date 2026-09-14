import { LegendaEpistemica } from "@/components/Badges";
import { formatarDataHora, getMeta } from "@/lib/data";

export default function PaginaSobre() {
  const meta = getMeta();
  return (
    <div className="max-w-3xl space-y-6 text-sm leading-relaxed">
      <h1 className="text-2xl font-bold">Método</h1>
      <section>
        <h2 className="text-lg font-bold">O que este site é</h2>
        <p>
          Uma camada de acesso estruturado a processos públicos do Supremo Tribunal Federal. Os dados vêm do portal público de
          acompanhamento processual e do serviço de sessões virtuais do STF. Não há resumo, narrativa ou opinião: cada item é a
          transcrição de um campo, andamento ou documento, com a data em que foi coletado e o ponteiro para a origem.
        </p>
      </section>
      <section>
        <h2 className="text-lg font-bold">Proveniência</h2>
        <p>
          Toda resposta do portal é guardada íntegra, identificada pelo seu hash SHA-256 e pela hora da coleta. O banco que alimenta
          este site é uma projeção desses arquivos e pode ser reconstruído do zero. Cada andamento, parte, documento e asserção carrega
          o identificador do snapshot de onde saiu. Documentos em PDF trazem ainda o código de autenticação que o próprio STF imprime
          no rodapé, verificável no portal do tribunal.
        </p>
      </section>
      <section>
        <h2 className="text-lg font-bold">Tipos de asserção</h2>
        <p>
          A única etapa com modelo de linguagem é a extração de asserções dos documentos. O modelo propõe; um validador determinístico
          descarta qualquer asserção sem página e trecho literal verificáveis. O modelo é proibido de concluir sobre conduta, caráter,
          culpa ou intenção de qualquer pessoa, e o esquema de dados não tem campo para isso.
        </p>
        <LegendaEpistemica descricoes={meta.tipos_epistemicos} />
      </section>
      <section>
        <h2 className="text-lg font-bold">Pessoas</h2>
        <p>
          O sistema registra o status processual literal do portal (requerente, requerido, investigado, interessado, advogado, autoridade
          policial). Nunca deriva, sugere ou rotula culpa. Entidades citadas em documentos e que não constam como parte aparecem como
          "terceiro mencionado". A identidade de advogados usa o número de OAB; a das demais entidades usa o nome exato, o que pode
          agrupar homônimos; por isso cada menção mostra o processo e o papel.
        </p>
      </section>
      <section>
        <h2 className="text-lg font-bold">Coleta</h2>
        <p>
          Toda requisição ao portal se identifica com o nome do projeto e um e-mail de contato. Uma requisição por vez, intervalo mínimo
          de três segundos, recuo em caso de erro, teto por execução, nenhuma descoberta automática de processos: só os processos que
          os próprios autos declaram como relacionados. O arquivo robots.txt do portal desaconselha acesso automatizado a essa área; a
          exceção adotada e seus limites estão documentados no repositório.
        </p>
      </section>
      <section>
        <h2 className="text-lg font-bold">Limitações</h2>
        <ul className="list-disc pl-6">
          <li>Processos sigilosos mostram só o que o portal público devolve: cabeçalho e poucos andamentos genéricos.</li>
          <li>Os agravos regimentais existem como andamentos, mas o portal não os expõe como incidentes próprios até serem julgados.</li>
          <li>Documentos gerados enquanto o processo era sigiloso trazem "SOB SIGILO" no lugar dos nomes das partes; a fonte para partes é o cadastro do portal, não o cabeçalho do PDF.</li>
          <li>O texto dos documentos é extraído automaticamente do PDF e pode conter erros de leitura; em caso de dúvida, consulte o original.</li>
        </ul>
      </section>
      <p className="text-xs text-neutral-700">Base gerada em {formatarDataHora(meta.gerado_em)}. Código-fonte, relatórios de cada fase e política de coleta em github.com/ldickmann/nao-definido.</p>
    </div>
  );
}
