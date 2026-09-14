export type TipoEpistemico = "fato_processual" | "alegacao_parte" | "fundamento_decisorio";

export type Snapshot = { id: number; fetched_at: string; sha256: string; url: string; aba: string } | null;

export type AssercaoResumo = {
  id: number; pagina: number; tipo_epistemico: TipoEpistemico; texto: string; trecho_fonte: string; atribuida_a: string | null;
};

export type Documento = {
  id: number; rotulo: string; formato: string; url: string; baixado: boolean;
  paginas: number | null; tem_texto: boolean; codigo_autenticacao: string | null; assercoes?: AssercaoResumo[];
};

export type PeticaoLigada = { numero: string; recebido_por: string | null; data_peticionamento: string | null } | null;

export type Andamento = {
  id: number; data: string; tipo: string; descricao: string; e_decisao: boolean; e_pauta: boolean;
  documentos: Documento[]; snapshot: Snapshot; hash: string; categoria?: string; peticao?: PeticaoLigada;
};

export type EventoLinhaTempo = {
  andamento_id: number; incidente: number; processo: string; data: string; tipo: string; categoria: string; descricao: string;
  e_decisao: boolean; e_pauta: boolean; e_recurso: boolean;
  documentos: { id: number; rotulo: string; baixado: boolean; paginas: number | null }[];
  peticao: PeticaoLigada; assercoes: number; hash: string; snapshot: number;
};

export type LinhaTempo = { categorias: { id: string; rotulo: string }[]; eventos: EventoLinhaTempo[] };

export type ReferenciasDocumento = {
  processos: { classe: string; numero: number; pagina: number; ocorrencias: number; trecho: string; incidente: number | null }[];
  dispositivos: { dispositivo: string; artigo: string; diploma: string; pagina: number; ocorrencias: number; trecho: string }[];
  andamentos_citados: { andamento_id: number; tipo_citado: string; data_citada: string; incidente: number }[];
};

export type Decisao = {
  id: number; documento_id: number; incidente: number; titulo_documento: string | null; url_documento: string; codigo_autenticacao: string | null;
  andamento_id: number | null; data: string | null; data_no_documento: string | null; pagina: number; pedido: string; quem_pediu: string | null;
  resultado: string; decisao: string; quem_decidiu: string; trecho_fonte: string; condicoes: string[]; modelo: string; prompt_version: string;
};

export type Decisoes = { rotulos_resultado: Record<string, string>; itens: Decisao[] };

export type Verbete = { termo: string; formas: string[]; explicacao: string; mais?: string; fonte?: "portal" | "glossario"; contexto?: string };

export type Integridade = {
  gerado_em: string; como_conferir: string; raiz_sha256: string;
  totais: { registros_de_coleta: number; snapshots: number; documentos: number };
  registros_de_coleta: { id: string; arquivo: string; sha256: string; linhas: number }[];
  snapshots: { id: number; coleta_id: string; incidente: number; aba: string; url: string; fetched_at: string; http_status: number; sha256: string; bytes: number }[];
  documentos: { id: number; incidente: number; titulo: string | null; url: string; formato: string; sha256: string; paginas: number | null; baixado_em: string | null;
    codigo_autenticacao: string | null; senha_autenticacao: string | null; processo: string | null }[];
};

export type Mudanca = { o_que: string; mudanca: "sumiu" | "apareceu" | "mudou"; item: string };
export type RodadaMudancas = {
  em: string;
  processos: { incidente: number; processo: string; antes: string | null; depois: string; abas_identicas: string[]; mudancas: Mudanca[];
    resumo: { sumiu: number; apareceu: number; mudou: number } }[];
};

export type Referencias = {
  dispositivos: { dispositivo: string; artigo: string; diploma: string; ocorrencias: number;
    documentos: { documento_id: number; incidente: number; titulo: string | null; pagina: number; ocorrencias: number }[] }[];
  processos_citados: { classe: string; numero: number; incidente: number | null; n_docs: number; n_ocorrencias: number; citado_por: number[] }[];
};

export type Parte = {
  id: number; nome: string; papel_portal: string; papel: string; status_processual: string; oab: string[];
  bloco: number; e_placeholder: boolean; entidade_id: number | null; snapshot: Snapshot;
};

export type Voto = { ordem: number; ministro: string; data: string; tipo_voto: string; acompanhando: string | null; antecipado: string | null };

export type Sessao = {
  objeto: string; objeto_completo: string; tipo_objeto: string; lista: string; julgado: number | null; relator: string;
  tipo_lista: string; colegiado: string; data_inicio: string; data_fim: string; texto_decisao: string | null;
  resultado: string | null; votos: Voto[]; snapshot: Snapshot;
};

export type Cabecalho = {
  classe: string; numero: number; incidente: number; numero_unico: string | null; relator: string | null;
  relator_ultimo_incidente: string | null; ultimo_incidente: string | null; publicidade: string | null;
  natureza: string | null; reu_preso: number; tipo_tramitacao: string | null; data_protocolo: string | null;
  orgao_origem: string | null; origem: string | null; descricao_procedencia: string | null; assuntos: string[];
  numeros_origem: string[]; snapshot: Snapshot;
};

export type Processo = {
  cabecalho: Cabecalho; partes: Parte[]; andamentos: Andamento[];
  peticoes: { numero: string; data_peticionamento: string; recebido_em: string; recebido_por: string; snapshot: Snapshot }[];
  deslocamentos: { destino: string; enviado_por: string; data_envio: string; guia: string; recebido_em: string | null; snapshot: Snapshot }[];
  relacoes: { tipo: string; classe: string; numero: number; fonte_andamento_id: number; snapshot: Snapshot }[];
  sessoes: Sessao[]; explicacoes_portal: Record<string, string | null>;
  contagem_assercoes?: Record<TipoEpistemico, number>; decisoes?: Decisao[];
};

export type ProcessoResumo = {
  classe: string; numero: number; incidente: number | null; coletado: boolean; publicidade?: string | null;
  relator?: string | null; assuntos?: string[]; data_protocolo?: string | null; status?: string;
  contagens?: Record<string, number>; coletado_em?: string | null;
};

export type Assercao = {
  id: number; pagina: number; tipo_epistemico: TipoEpistemico; texto: string; trecho_fonte: string;
  atribuida_a: string | null; entidades: { entidade_id: number; nome: string; tipo: string }[];
  modelo: string; prompt_version: string;
  documento?: { id: number; incidente: number; titulo: string; url: string; codigo_autenticacao: string | null };
  data_andamento?: string | null;
};

export type DocumentoCompleto = {
  meta: {
    id: number; incidente: number; endpoint: string; id_portal: string; formato: string; url: string; titulo: string;
    funcao?: string; sha256: string; paginas: number | null; tem_texto: boolean; precisa_ocr: boolean; codigo_autenticacao: string | null;
    senha_autenticacao: string | null; baixado_em: string | null; snapshot: Snapshot;
    andamentos: { id: number; data: string; tipo: string; incidente: number }[];
  };
  paginas: { n: number; texto: string }[];
  chunks: { ordem: number; pagina_inicio: number; pagina_fim: number; secao: string | null; texto: string }[];
  assercoes: Assercao[];
  referencias?: ReferenciasDocumento;
};

export type Entidade = {
  id: number; nome: string; tipo: string; chave: string; natureza_provavel: string | null; origem: string; grupo?: string | null;
  status_padrao: string | null;
  mencoes: { incidente: number; papel_portal: string; papel: string; processo: string | null; status_processual: string }[];
  assercoes: number;
};

export type Meta = {
  gerado_em: string; semente: number; coletado_em: Record<string, string>;
  coletas: { id: string; incidente: number; ingerida_em: string }[];
  contagens: Record<string, number>; tipos_epistemicos: Record<TipoEpistemico, string>;
  funcoes_documento?: Record<string, string>;
};

export type NoGrafo = { id: string; tipo: "processo" | "entidade"; rotulo: string; dados: Record<string, unknown> };
export type ArestaGrafo = { origem: string; destino: string; tipo: string; dados: Record<string, unknown> };
export type Grafo = { nodes: NoGrafo[]; edges: ArestaGrafo[] };

export function formatarData(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

export function formatarDataHora(iso: string | null | undefined): string {
  if (!iso) return "—";
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return iso;
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(dt.getUTCDate())}/${p(dt.getUTCMonth() + 1)}/${dt.getUTCFullYear()} ${p(dt.getUTCHours())}:${p(dt.getUTCMinutes())} UTC`;
}
