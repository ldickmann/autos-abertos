// Corrige um defeito do `next build` (output: "export") no Windows: os payloads de segmento
// deveriam virar arquivos planos `__next.<a>.<b>.txt`, mas o exportador só troca "/" por "."
// e o caminho no Windows usa "\", então saem diretórios `__next.<a>/<b>.txt`. O cliente pede o
// nome plano e recebe 404 no prefetch. Este script achata os diretórios para o nome esperado.
import fs from "node:fs";
import path from "node:path";

const out = path.join(process.cwd(), "out");
let corrigidos = 0;

function achatar(dir) {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) {
      if (ent.name.startsWith("__next.")) {
        for (const arquivo of listar(p)) {
          const rel = path.relative(p, arquivo).split(path.sep).join(".");
          const destino = path.join(dir, `${ent.name}.${rel}`);
          fs.renameSync(arquivo, destino);
          corrigidos++;
        }
        fs.rmSync(p, { recursive: true, force: true });
      } else {
        achatar(p);
      }
    }
  }
}

function listar(dir) {
  const acc = [];
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) acc.push(...listar(p));
    else acc.push(p);
  }
  return acc;
}

if (fs.existsSync(out)) {
  achatar(out);
  console.log(`flatten-segments: ${corrigidos} arquivo(s) de segmento renomeado(s)`);
}
