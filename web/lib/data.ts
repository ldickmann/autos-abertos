import "server-only";
import fs from "node:fs";
import path from "node:path";
import type { Assercao, DocumentoCompleto, Entidade, Grafo, Meta, Processo, ProcessoResumo } from "@/lib/tipos";

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

export function listarIncidentesColetados(): number[] {
  return getProcessos().filter((p) => p.coletado && p.incidente).map((p) => p.incidente as number);
}

export function listarDocumentos(): number[] {
  const dir = path.join(DATA_DIR, "documento");
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((f) => f.endsWith(".json")).map((f) => Number(f.replace(".json", "")));
}
