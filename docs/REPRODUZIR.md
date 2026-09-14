# Como reproduzir a base do zero

Qualquer pessoa, com este repositório e acesso ao portal do STF, consegue refazer a base e comparar com o que está publicado. Os passos são determinísticos: a mesma coleta produz os mesmos hashes; as respostas do modelo estão versionadas, então a camada semântica também se reproduz sem chamar modelo nenhum.

## Requisitos

- Python 3.12 ou mais novo; `pip install -r requirements.txt`.
- Conexão residencial ou corporativa comum. O portal do STF bloqueia endereços de datacenter (nuvem, CI), então a coleta não roda no GitHub Actions; o site, sim.
- Node 20+ só para gerar o site (`web/`).

## 1. Coletar (fala com o portal)

```bash
python -m stf expandir 7514886 --profundidade 3
```

Coleta o processo principal (Pet 15556, incidente 7514886) e os relacionados declarados nos andamentos, uma requisição por vez, a cada 3 segundos, com identificação e contato no User-Agent. Cada resposta do portal vira um blob em `data/raw/blobs/<sha256>` e uma linha no registro `data/raw/coletas/<data>-<incidente>.jsonl`. Nada é sobrescrito.

```bash
python -m stf baixar-docs
python -m stf extrair-texto
```

Baixa os documentos (PDF/RTF) referenciados nos andamentos e extrai o texto por página.

## 2. Reconstruir a projeção (não fala com o portal)

```bash
python -m stf reconstruir
```

Apaga a base SQLite derivada e a refaz a partir dos registros e blobs: incidentes, partes, andamentos, petições, deslocamentos, documentos, referências, entidades. É idempotente.

## 3. Reingerir a camada semântica (não chama modelo)

```bash
python -m stf ingerir-extracao
python -m stf ingerir-decisoes
```

Lê as respostas versionadas em `data/extracao/respostas/` e `data/extracao/decisoes/respostas/`, valida cada item contra o texto da página (trecho literal, página existente) e persiste só o que passa. Os totais publicados: 2430 asserções e 251 itens de decisão. Se quiser refazer as respostas com um modelo, `python -m stf preparar-extracao` e `preparar-decisoes` geram as entradas; o prompt está em `stf/prompts/`.

## 4. Exportar e conferir

```bash
python -m stf exportar
python -m stf verificar
python -m pytest -q
```

`exportar` escreve os JSON do site em `web/public/data/`, o mapa em `docs/MAPA-DO-CASO.md` e o manifesto `web/public/data/integridade.json` com o `raiz_sha256` também gravado em `INTEGRIDADE.sha256`. `verificar` recalcula o sha256 de cada blob local e compara com o registrado. Os testes incluem o guarda-corpo de neutralidade (`tests/test_neutralidade.py`).

## 5. O que comparar com o publicado

- `INTEGRIDADE.sha256`: se a sua coleta for feita em outra data, o portal pode ter mudado (novos andamentos), e o hash raiz será outro. Compare então documento a documento: o sha256 de cada PDF deve coincidir se o portal ainda entrega o mesmo arquivo.
- `python -m stf vigiar`: recoleta e escreve em `CHANGELOG-PORTAL.md` o que sumiu, apareceu ou mudou desde a cópia anterior.
- `docs/MAPA-DO-CASO.md`: contagens por processo, para ver se sua base tem o mesmo tamanho.

## 6. Gerar o site

```bash
cd web && npm ci && npm run build
```

O resultado em `web/out/` é estático: pode ser servido de qualquer lugar (`python -m http.server -d web/out`), sem servidor de aplicação nem banco. Para hospedar uma réplica pública, basta publicar essa pasta.
