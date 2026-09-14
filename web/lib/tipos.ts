export type Snapshot = { id: number; fetched_at: string; sha256: string; url: string; aba: string } | null;

export type Documento = {
  id: number; rotulo: string; formato: string; url: string; baixado: boolean;
  paginas: number | null; tem_texto: boolean; codigo_autenticacao: string | null;
};

export type Andamento = {
  id: number; data: string; tipo: string; descricao: string; e_decisao: boolean; e_pauta: boolean;
  documentos: Documento[]; snapshot: Snapshot; hash: string;
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
};

export type ProcessoResumo = {
  classe: string; numero: number; incidente: number | null; coletado: boolean; publicidade?: string | null;
  relator?: string | null; assuntos?: string[]; data_protocolo?: string | null; status?: string;
  contagens?: Record<string, number>; coletado_em?: string | null;
};

export type TipoEpistemico = "fato_processual" | "alegacao_parte" | "fundamento_decisorio";

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
    sha256: string; paginas: number | null; tem_texto: boolean; precisa_ocr: boolean; codigo_autenticacao: string | null;
    senha_autenticacao: string | null; baixado_em: string | null; snapshot: Snapshot;
    andamentos: { id: number; data: string; tipo: string; incidente: number }[];
  };
  paginas: { n: number; texto: string }[];
  chunks: { ordem: number; pagina_inicio: number; pagina_fim: number; secao: string | null; texto: string }[];
  assercoes: Assercao[];
};

export type Entidade = {
  id: number; nome: string; tipo: string; chave: string; natureza_provavel: string | null; origem: string;
  status_padrao: string | null;
  mencoes: { incidente: number; papel_portal: string; papel: string; processo: string | null; status_processual: string }[];
  assercoes: number;
};

export type Meta = {
  gerado_em: string; semente: number; coletado_em: Record<string, string>;
  coletas: { id: string; incidente: number; ingerida_em: string }[];
  contagens: Record<string, number>; tipos_epistemicos: Record<TipoEpistemico, string>;
};

export type Grafo = {
  nodes: { id: string; tipo: "processo" | "entidade"; rotulo: string; dados: Record<string, unknown> }[];
  edges: { origem: string; destino: string; tipo: string; dados: Record<string, unknown> }[];
};

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
