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

export type Aviso = {
  id: string; titulo: string; inicio: string; ate: string; resumo: string; por_que_importa?: string;
  acao: { rotulo: string; url: string }; acoes_secundarias: { rotulo: string; url: string }[];
  fontes: { rotulo: string; url: string }[]; processos_relacionados: number[];
};

export type EventoCronologia = {
  data: string; fonte: "portal" | "documento"; tipo: "andamento" | "assercao" | "decisao"; processo: string; incidente: number; texto: string;
  contexto: "caso" | "referencia"; categoria?: string; andamento_id?: number; tipo_epistemico?: TipoEpistemico; atribuida_a?: string | null;
  trecho_fonte?: string; literal?: string; documento_id?: number; titulo_documento?: string | null; pagina?: number; assercao_id?: number;
  resultado?: string; quem_pediu?: string | null; quem_decidiu?: string; decisao_id?: number;
};
export type CronologiaDados = { inicio_do_caso: string; total: number; por_fonte: { portal: number; documento: number }; eventos: EventoCronologia[] };

export type Materia = {
  casa: "senado" | "camara"; codigo: string; sigla: string | null; numero: number | null; ano: number | null; comissao: string | null; identificacao: string | null;
  ementa: string; autor: string | null; data: string | null; url: string; url_api: string | null; consultas: string[]; primeiro_visto_em: string; ultimo_visto_em: string;
};

export type FonteExterna = {
  id: string; poder?: string; observacao?: string; orgao: string; rotulo: string; url: string; tipo: string; capturar: boolean; por_que: string;
  ultima: { id: number; fetched_at: string; http_status: number | null; sha256: string | null; bytes: number | null; content_type: string | null } | null;
  historico: { id: number; fetched_at: string; http_status: number | null; sha256: string | null }[]; mudou: boolean; versoes_distintas: number;
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

// ---------------------------------------------------------------- fluxos financeiros (fluxos.json)
export type FluxoFonte = {
  id: number; tipo: string; identificador: string; orgao: string; destinatario: string | null; emitido_em: string | null; incidente: number;
  processo: string | null; curadoria_path: string; curadoria_sha256: string; carregado_em: string;
  documento: { id: number; titulo: string | null; paginas: number | null; sha256: string | null };
};
export type FluxoAtor = {
  id: number; chave: string; nome: string; tipo: "pessoa_fisica" | "pessoa_juridica" | "desconhecido"; documento_mascarado: string | null;
  atividade: string | null; entidade_id: number | null; papeis: string[];
  totais: { entradas_centavos: number; saidas_centavos: number; n_transacoes: number };
};
export type FluxoBem = { id: number; tipo: "veiculo" | "imovel"; descricao: string; valor_centavos: number | null; valor_referencia_centavos: number | null; data_negocio: string | null };
export type FluxoComunicacao = {
  id: number; fonte_id: number; secao: "suspeita" | "automatica" | "especie" | "relatorio"; numero: string; titular_ator_id: number | null; segmento: string | null;
  comunicante: string | null; local: string | null; periodo_inicio: string | null; periodo_fim: string | null; valor_centavos: number | null;
  creditos_centavos: number | null; debitos_centavos: number | null; informacoes: string | null; consideracoes: string | null;
  pagina_inicio: number; pagina_fim: number; documento_id: number | null;
  participacoes: { ator_id: number; papel: string }[]; bens: FluxoBem[]; ocorrencias: { norma: string; codigo: string | null; descricao: string | null }[];
};
export type FluxoTransacao = {
  id: number; comunicacao_id: number; origem_ator_id: number | null; destino_ator_id: number | null; valor_centavos: number; data: string | null;
  periodo_inicio: string | null; periodo_fim: string | null; tipo: string; natureza: "individual" | "agregado" | "resumo_tipo"; quantidade: number | null;
  bem_id: number | null; descricao: string | null; pagina: number; trecho_fonte: string; documento_id: number | null; secao: FluxoComunicacao["secao"];
  situacao: "efetuado" | "previsto" | "cobrado" | "nao_informado";
};
export type FluxoAresta = {
  origem: number; destino: number; dirigida: boolean; valor_centavos: number; n: number; transacoes: number[]; comunicacao_id?: number;
  naturezas: string[]; tipos: string[]; secoes: string[];
};
export type FluxosDados = {
  fontes: FluxoFonte[]; atores: FluxoAtor[]; comunicacoes: FluxoComunicacao[]; transacoes: FluxoTransacao[];
  grafo: { nos: { id: number; nome: string; tipo: FluxoAtor["tipo"]; totais: FluxoAtor["totais"]; entidade_id: number | null }[]; arestas: FluxoAresta[] };
  resumo: { atores: number; comunicacoes: number; transacoes: number; individuais: number; agregadas: number; por_secao: Record<string, number> };
};

/** 1920500000 → "R$ 19.205.000,00"; com `curto`, "R$ 19,2 mi". */
export function formatarReais(centavos: number | null | undefined, curto = false): string {
  if (centavos == null) return "—";
  const v = centavos / 100;
  if (curto) {
    if (Math.abs(v) >= 1e6) return `R$ ${(v / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mi`;
    if (Math.abs(v) >= 1e3) return `R$ ${(v / 1e3).toLocaleString("pt-BR", { maximumFractionDigits: 0 })} mil`;
  }
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

// ---------------------------------------------------------------- trajetos (trajetos.json): passos com prova
export type ProvaAssercao = { tipo: "assercao"; id: number; documento_id: number; documento_titulo: string | null; incidente: number; pagina: number; tipo_epistemico: TipoEpistemico; texto: string; trecho_fonte: string; atribuida_a: string | null };
export type ProvaComunicacao = { tipo: "comunicacao"; comunicacao_id: number; secao: string; numero: string; comunicante: string | null; local: string | null; periodo_inicio: string | null; periodo_fim: string | null; documento_id: number; pagina: number; valor_centavos: number; n_transacoes: number; transacoes: { id: number; valor_centavos: number; pagina: number; trecho_fonte: string; data: string | null; periodo_inicio: string | null; periodo_fim: string | null; tipo: string; natureza: string; quantidade: number | null }[] };
export type ProvaDocumento = { tipo: "documento"; documento_id: number; documento_titulo: string | null; incidente: number; pagina: number; trecho_fonte: string; atribuida_a: string | null };
export type Prova = ProvaAssercao | ProvaComunicacao | ProvaDocumento;
export type PassoTrajeto = { de: string; para: string; valor: string | null; quando: string | null; como: string; provas: Prova[] };
export type Trajeto = { id: string; titulo: string; pergunta: string; resumo: string; quem_afirma: string; passos: PassoTrajeto[]; contrapontos: { quem: string; o_que: string; provas: Prova[] }[]; lacunas: string | null };
export type Cruzamento = { id: string; titulo: string; explicacao: string; eventos: { data: string; lado: "autos" | "cartorios"; texto: string; prova: Prova }[] };
export type TrajetosDados = { trajetos: Trajeto[]; cruzamentos: Cruzamento[] };
