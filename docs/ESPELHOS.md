# Espelhos e cópias fora do GitHub

O objetivo é que a base sobreviva à queda ou remoção de qualquer provedor isolado. Cada cópia abaixo é verificável pelos mesmos hashes (`INTEGRIDADE.sha256`, `integridade.json`).

## O que já existe

| cópia | onde | como conferir |
|---|---|---|
| Repositório Git (código + originais + registros) | https://github.com/ldickmann/autos-abertos | `git clone` → `python -m stf verificar` |
| Release versionada com o pacote completo (.zip + .sha256 + prova .ots) | https://github.com/ldickmann/autos-abertos/releases | `sha256sum` do zip = valor no `.sha256` |
| Site estático publicado | https://ldickmann.github.io/autos-abertos/ | qualquer pessoa pode servir `web/out/` em outro lugar |
| Carimbo de tempo (OpenTimestamps) | `docs/carimbos/*.ots` | `python scripts/carimbar.py --verify` (offline, contra a Bitcoin) |
| Wayback Machine (Internet Archive) | `docs/wayback.json` registra cada tentativa | `python scripts/arquivar.py --checar` |

## Como fazer mais cópias

1. **Clonar em outra máquina ou outro serviço Git** (GitLab, Codeberg, um servidor próprio): `git clone --mirror https://github.com/ldickmann/autos-abertos` e `git push --mirror <destino>`. O histórico inteiro vai junto, inclusive os originais.
2. **Wayback Machine**: `python scripts/arquivar.py` pede a cópia das páginas públicas; o serviço às vezes responde 429/500 e basta repetir mais tarde. Não precisa de conta.
3. **Item no archive.org** (depósito do pacote completo, com metadados e busca): precisa de uma conta gratuita.
   ```bash
   pip install internetarchive
   ia configure                       # e-mail e senha da conta
   ia upload autos-abertos-dados-2026-09-14 autos-abertos-dados-2026-09-14.zip autos-abertos-dados-2026-09-14.zip.sha256 INTEGRIDADE.sha256 \
     --metadata="title:Autos Abertos — dados públicos do STF (Pet 15556 e relacionados), 2026-09-14" \
     --metadata="mediatype:data" --metadata="language:por" \
     --metadata="description:Cópia verificável dos autos públicos: originais do portal do STF nomeados por sha256, base SQLite, JSON do site, manifesto de integridade e carimbo de tempo. Código e método: https://github.com/ldickmann/autos-abertos" \
     --metadata="subject:STF; Supremo Tribunal Federal; dados abertos; processo judicial; Brasil"
   ```
   O arquivo `.zip` está na release. Depois do upload, anote a URL do item aqui.
4. **IPFS** (opcional): `ipfs add -r web/out` publica o site inteiro sob um CID (hash do conteúdo); qualquer gateway serve a mesma cópia. Anote o CID aqui se fizer.

## Regra

Toda cópia nova deve ser registrada nesta página com a data e o hash raiz (`INTEGRIDADE.sha256`) do momento, para que se saiba exatamente qual versão cada espelho guarda.
