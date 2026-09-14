import { ListaMaterias } from "@/components/ListaMaterias";
import { getLegislativo } from "@/lib/data";

export default function PaginaCongresso() {
  const materias = getLegislativo();
  const senado = materias.filter((m) => m.casa === "senado").length;
  const camara = materias.filter((m) => m.casa === "camara").length;
  return (
    <div className="space-y-4">
      <header className="max-w-3xl">
        <h1 className="text-2xl">O caso no Congresso Nacional</h1>
        <p className="leitura mt-1">
          O que Senado e Câmara fizeram, em requerimentos e propostas oficiais, sobre o caso: convocações, pedidos de informação ao Banco Central,
          pedidos de CPI, propostas de fiscalização. São {materias.length} matérias ({senado} do Senado, {camara} da Câmara), obtidas pelas APIs oficiais de dados abertos
          das duas Casas com buscas por palavra-chave, cada uma com o link para a tramitação.
        </p>
        <p className="mt-1 text-sm text-neutral-700">
          As ementas são as do próprio Congresso; o site não as interpreta. A busca da Câmara por palavra-chave alcança menos matérias que a do Senado; as consultas são repetidas a cada rodada e as respostas ficam guardadas com hash.
        </p>
      </header>
      <ListaMaterias materias={materias} />
    </div>
  );
}
