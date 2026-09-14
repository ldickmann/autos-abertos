import "server-only";
import fs from "node:fs";
import path from "node:path";
import type { Assercao, Decisoes, DocumentoCompleto, Entidade, Grafo, LinhaTempo, Meta, Processo, ProcessoResumo, Referencias, Verbete } from "@/lib/tipos";

export * from "@/lib/tipos";

const DATA_DIR = path.join(process.cwd(), "public", "data");

function ler<T>(rel: string): T {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, rel), "utf-8")) as T;
}

export const getMeta = () => ler<Meta>("meta.json");
export const getProcessos = () => ler<ProcessoResumo[]>("processos.json");
export const getProcesso = (incidente: number | string) => ler<Processo>(`processo/${incidente}.json`);
export const getDocumento = (id: number | string) => ler<DocumentoCompleto>(`documento/${id}.json`);
export const getEntidades = () => ler<Entidade[]>("entidades.json");
export const getAssercoes = () => ler<Assercao[]>("assercoes.json");
export const getGrafo = () => ler<Grafo>("grafo.json");
export const getLinhaTempo = () => ler<LinhaTempo>("linha_tempo.json");
export const getReferencias = () => ler<Referencias>("referencias.json");
export const getDecisoes = () => ler<Decisoes>("decisoes.json");
export const getGlossario = () => ler<Verbete[]>("glossario.json");

let _indiceGlossario: Map<string, Verbete> | null = null;
/** Verbete cujo termo ou alguma das formas coincide com o texto (sem acentos, sem caixa); null se não houver. */
export function verbeteDe(texto: string | null | undefined): Verbete | null {
  if (!texto) return null;
  if (!_indiceGlossario) {
    _indiceGlossario = new Map();
    for (const v of getGlossario()) for (const f of [v.termo, ...v.formas]) _indiceGlossario.set(normalizarTermo(f), v);
  }
  return _indiceGlossario.get(normalizarTermo(texto)) ?? null;
}
function normalizarTermo(s: string): string {
  return s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/\s+/g, " ").trim();
}

export function listarIncidentesColetados(): number[] {
  return getProcessos().filter((p) => p.coletado && p.incidente).map((p) => p.incidente as number);
}

export function listarDocumentos(): number[] {
  const dir = path.join(DATA_DIR, "documento");
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((f) => f.endsWith(".json")).map((f) => Number(f.replace(".json", "")));
}
