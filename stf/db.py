"""Schema SQLite. Projeção derivada dos blobs; reconstruível com `stf reconstruir`.

Convenções:
- toda linha de fato carrega `snapshot_first_seen` e `snapshot_last_seen`
  (proveniência: qual snapshot a mostrou pela primeira/última vez);
- linhas nunca são apagadas; um item que sumiu do portal fica com `last_seen`
  parado no último snapshot em que apareceu;
- `hash_natural` é a chave de deduplicação entre coletas (ver stf/hashing.py).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS coleta (
    id            TEXT PRIMARY KEY,
    incidente     INTEGER NOT NULL,
    registro_path TEXT NOT NULL,
    ingerida_em   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshot (
    id           INTEGER PRIMARY KEY,
    coleta_id    TEXT NOT NULL REFERENCES coleta(id),
    incidente    INTEGER NOT NULL,
    aba          TEXT NOT NULL,
    url          TEXT NOT NULL,
    fetched_at   TEXT NOT NULL,
    http_status  INTEGER NOT NULL,
    sha256       TEXT NOT NULL,
    bytes        INTEGER NOT NULL,
    raw_path     TEXT NOT NULL,
    content_type TEXT,
    UNIQUE (coleta_id, aba, url, fetched_at)
);
CREATE INDEX IF NOT EXISTS ix_snapshot_inc_aba ON snapshot(incidente, aba, fetched_at);

CREATE TABLE IF NOT EXISTS incidente (
    numero                   INTEGER PRIMARY KEY,
    classe                   TEXT,
    numero_processo          INTEGER,
    numero_unico             TEXT,
    relator                  TEXT,
    relator_ultimo_incidente TEXT,
    ultimo_incidente         TEXT,
    publicidade              TEXT,
    natureza                 TEXT,
    reu_preso                INTEGER,
    tipo_tramitacao          TEXT,
    meio                     TEXT,
    assuntos                 TEXT,   -- JSON
    data_protocolo           TEXT,
    orgao_origem             TEXT,
    origem                   TEXT,
    numeros_origem           TEXT,   -- JSON
    descricao_procedencia    TEXT,
    primeiro_visto_em        TEXT NOT NULL,
    ultimo_visto_em          TEXT NOT NULL,
    snapshot_first_seen      INTEGER NOT NULL,
    snapshot_last_seen       INTEGER NOT NULL
);

-- histórico: uma linha por versão distinta do cabeçalho
CREATE TABLE IF NOT EXISTS incidente_versao (
    id          INTEGER PRIMARY KEY,
    incidente   INTEGER NOT NULL,
    snapshot_id INTEGER NOT NULL,
    hash        TEXT NOT NULL,
    campos      TEXT NOT NULL,   -- JSON
    UNIQUE (incidente, hash)
);

CREATE TABLE IF NOT EXISTS parte (
    id                  INTEGER PRIMARY KEY,
    incidente           INTEGER NOT NULL,
    hash_natural        TEXT NOT NULL UNIQUE,
    papel_portal        TEXT NOT NULL,
    papel               TEXT NOT NULL,
    nome                TEXT NOT NULL,
    oab                 TEXT NOT NULL,   -- JSON
    bloco               INTEGER NOT NULL,
    posicao             INTEGER NOT NULL,
    e_placeholder       INTEGER NOT NULL DEFAULT 0,
    snapshot_first_seen INTEGER NOT NULL,
    snapshot_last_seen  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS andamento (
    id                  INTEGER PRIMARY KEY,
    incidente           INTEGER NOT NULL,
    hash_natural        TEXT NOT NULL UNIQUE,
    data                TEXT NOT NULL,
    tipo                TEXT NOT NULL,
    descricao           TEXT NOT NULL,
    posicao             INTEGER NOT NULL,   -- última posição vista na lista servida
    aba_origem          TEXT NOT NULL DEFAULT 'andamentos',
    e_decisao           INTEGER NOT NULL DEFAULT 0,
    e_pauta             INTEGER NOT NULL DEFAULT 0,
    e_recurso           INTEGER NOT NULL DEFAULT 0,
    snapshot_first_seen INTEGER NOT NULL,
    snapshot_last_seen  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_andamento_inc_data ON andamento(incidente, data);

CREATE TABLE IF NOT EXISTS tipo_andamento (
    nome              TEXT PRIMARY KEY,
    explicacao_portal TEXT,
    primeiro_visto_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documento (
    id                  INTEGER PRIMARY KEY,
    incidente           INTEGER NOT NULL,
    endpoint            TEXT NOT NULL,
    id_portal           TEXT NOT NULL,
    formato             TEXT NOT NULL,
    url                 TEXT NOT NULL,
    titulo              TEXT,
    sha256              TEXT,
    paginas             INTEGER,
    tem_camada_texto    INTEGER,
    texto_path          TEXT,
    codigo_autenticacao TEXT,
    senha_autenticacao  TEXT,
    blob_path           TEXT,
    http_status         INTEGER,
    baixado_em          TEXT,
    snapshot_download   INTEGER,
    precisa_ocr         INTEGER,
    snapshot_first_seen INTEGER NOT NULL,
    UNIQUE (endpoint, id_portal)
);

CREATE TABLE IF NOT EXISTS documento_pagina (
    documento_id INTEGER NOT NULL REFERENCES documento(id),
    pagina       INTEGER NOT NULL,
    texto        TEXT NOT NULL,
    chars        INTEGER NOT NULL,
    PRIMARY KEY (documento_id, pagina)
);

CREATE TABLE IF NOT EXISTS documento_chunk (
    id            INTEGER PRIMARY KEY,
    documento_id  INTEGER NOT NULL REFERENCES documento(id),
    ordem         INTEGER NOT NULL,
    pagina_inicio INTEGER NOT NULL,
    pagina_fim    INTEGER NOT NULL,
    secao         TEXT,
    texto         TEXT NOT NULL,
    chars         INTEGER NOT NULL,
    UNIQUE (documento_id, ordem)
);

CREATE VIRTUAL TABLE IF NOT EXISTS documento_fts USING fts5(
    texto,
    content='documento_pagina', content_rowid='rowid',
    tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER IF NOT EXISTS documento_pagina_ai AFTER INSERT ON documento_pagina BEGIN
    INSERT INTO documento_fts(rowid, texto) VALUES (new.rowid, new.texto);
END;

CREATE TABLE IF NOT EXISTS andamento_documento (
    andamento_id INTEGER NOT NULL REFERENCES andamento(id),
    documento_id INTEGER NOT NULL REFERENCES documento(id),
    rotulo       TEXT,
    PRIMARY KEY (andamento_id, documento_id)
);

CREATE TABLE IF NOT EXISTS peticao (
    id                  INTEGER PRIMARY KEY,
    incidente           INTEGER NOT NULL,
    hash_natural        TEXT NOT NULL UNIQUE,
    numero              TEXT NOT NULL,
    data_peticionamento TEXT,
    recebido_em         TEXT,
    recebido_por        TEXT,
    posicao             INTEGER NOT NULL,
    snapshot_first_seen INTEGER NOT NULL,
    snapshot_last_seen  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS deslocamento (
    id                  INTEGER PRIMARY KEY,
    incidente           INTEGER NOT NULL,
    hash_natural        TEXT NOT NULL UNIQUE,
    destino             TEXT NOT NULL,
    enviado_por         TEXT,
    data_envio          TEXT,
    guia                TEXT,
    recebido_em         TEXT,
    posicao             INTEGER NOT NULL,
    snapshot_first_seen INTEGER NOT NULL,
    snapshot_last_seen  INTEGER NOT NULL
);

-- relações entre processos, extraídas deterministicamente do texto dos andamentos.
-- destino é (classe, número), não incidente: o portal não expõe o incidente. Fase 2 resolve.
CREATE TABLE IF NOT EXISTS processo_relacao (
    id                  INTEGER PRIMARY KEY,
    incidente_origem    INTEGER NOT NULL,
    classe_destino      TEXT NOT NULL,
    numero_destino      INTEGER NOT NULL,
    tipo                TEXT NOT NULL,   -- justifica_prevencao | relacionado | autuado_a_partir
    fonte_andamento_id  INTEGER REFERENCES andamento(id),
    snapshot_first_seen INTEGER NOT NULL,
    UNIQUE (incidente_origem, classe_destino, numero_destino, tipo)
);

-- processo (classe+número) → incidente principal, resolvido via listarProcessos.asp
CREATE TABLE IF NOT EXISTS processo (
    classe              TEXT NOT NULL,
    numero              INTEGER NOT NULL,
    incidente_principal INTEGER,
    status              TEXT NOT NULL,   -- resolvido | multiplos | nao_encontrado | erro | semente
    candidatos          TEXT,            -- JSON, quando multiplos
    url_final           TEXT,
    snapshot_id         INTEGER,         -- snapshot da resposta de resolução
    resolvido_em        TEXT,
    profundidade        INTEGER,         -- distância da semente em que foi descoberto
    PRIMARY KEY (classe, numero)
);

-- entidades canônicas, derivadas deterministicamente das partes (ver stf/entidades.py)
CREATE TABLE IF NOT EXISTS entidade (
    id                INTEGER PRIMARY KEY,
    tipo              TEXT NOT NULL,     -- parte | advogado
    chave             TEXT NOT NULL UNIQUE,   -- oab:<num/UF> | nome:<normalizado>
    nome              TEXT NOT NULL,     -- forma mais frequente vista
    natureza_provavel TEXT,              -- pessoa_juridica quando o nome tem sufixo societário explícito; senão NULL
    origem            TEXT NOT NULL DEFAULT 'partes',  -- partes | portal (relator/votos) | documento ("terceiro mencionado")
    grupo             TEXT               -- agrupamento curado de órgãos (stf/curadoria/grupos.json); NULL para o resto
);
CREATE TABLE IF NOT EXISTS entidade_mencao (
    entidade_id  INTEGER NOT NULL REFERENCES entidade(id),
    parte_id     INTEGER NOT NULL UNIQUE REFERENCES parte(id),
    incidente    INTEGER NOT NULL,
    papel_portal TEXT NOT NULL,
    papel        TEXT NOT NULL,
    bloco        INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_mencao_entidade ON entidade_mencao(entidade_id);

-- sessão virtual (JSON de sistemas.stf.jus.br): objetos incidente, listas de julgamento e votos
CREATE TABLE IF NOT EXISTS objeto_incidente (
    id                     INTEGER PRIMARY KEY,
    incidente_principal    INTEGER,
    pai                    INTEGER,
    tipo                   TEXT,     -- PR | IJ | RC | ...
    tipo_descricao         TEXT,
    identificacao          TEXT,
    identificacao_completa TEXT,
    cadeia                 TEXT,
    snapshot_first_seen    INTEGER NOT NULL,
    snapshot_last_seen     INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS lista_julgamento (
    id                  INTEGER PRIMARY KEY,
    objeto_incidente_id INTEGER NOT NULL,
    lista_id            INTEGER,
    nome_lista          TEXT,
    julgado             INTEGER,
    relator             TEXT,
    tipo_lista          TEXT,
    colegiado           TEXT,
    sessao_numero       INTEGER,
    sessao_ano          INTEGER,
    data_inicio         TEXT,
    data_fim            TEXT,
    tipo_sessao         TEXT,
    texto_decisao       TEXT,
    resultado           TEXT,
    hash                TEXT NOT NULL UNIQUE,
    snapshot_first_seen INTEGER NOT NULL,
    snapshot_last_seen  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS voto (
    id           INTEGER PRIMARY KEY,
    lista_id     INTEGER NOT NULL REFERENCES lista_julgamento(id),
    ordem        INTEGER,
    ministro     TEXT,
    data         TEXT,
    tipo_voto    TEXT,
    acompanhando TEXT,
    antecipado   TEXT,
    UNIQUE (lista_id, ordem, ministro)
);

-- Fase 4: camada semântica (único lugar com LLM)
CREATE TABLE IF NOT EXISTS extracao (
    id                    INTEGER PRIMARY KEY,
    documento_id          INTEGER NOT NULL REFERENCES documento(id),
    sha256_documento      TEXT NOT NULL,
    prompt_version        TEXT NOT NULL,
    modelo                TEXT NOT NULL,
    executada_em          TEXT NOT NULL,
    status                TEXT NOT NULL,   -- ok | rejeitada:<motivo> | erro:<tipo>
    input_tokens          INTEGER,
    output_tokens         INTEGER,
    cache_read_tokens     INTEGER,
    assercoes_validas     INTEGER,
    assercoes_descartadas INTEGER,
    resposta_path         TEXT,            -- resposta bruta do modelo (blob), para auditoria
    descartadas_json      TEXT,
    UNIQUE (documento_id, sha256_documento, prompt_version, modelo)
);

CREATE TABLE IF NOT EXISTS assercao (
    id              INTEGER PRIMARY KEY,
    documento_id    INTEGER NOT NULL REFERENCES documento(id),
    extracao_id     INTEGER NOT NULL REFERENCES extracao(id),
    pagina          INTEGER NOT NULL,
    tipo_epistemico TEXT NOT NULL CHECK (tipo_epistemico IN ('fato_processual','alegacao_parte','fundamento_decisorio')),
    texto           TEXT NOT NULL,
    trecho_fonte    TEXT NOT NULL,   -- citação literal presente na página (verificada)
    atribuida_a     TEXT,
    entidades_json  TEXT NOT NULL,
    modelo          TEXT NOT NULL,
    prompt_version  TEXT NOT NULL,
    criado_em       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_assercao_doc ON assercao(documento_id, pagina);

-- pedidos e resultados por decisão (stf/decisoes.py): extensão da Fase 4, mesmo regime de validação
CREATE TABLE IF NOT EXISTS decisao_item (
    id             INTEGER PRIMARY KEY,
    documento_id   INTEGER NOT NULL REFERENCES documento(id),
    extracao_id    INTEGER NOT NULL REFERENCES extracao(id),
    pagina         INTEGER NOT NULL,
    pedido         TEXT NOT NULL,
    quem_pediu     TEXT,
    resultado      TEXT NOT NULL CHECK (resultado IN ('deferido','indeferido','parcialmente_deferido','homologado','referendado',
                                                      'negado_seguimento','nao_conhecido','prejudicado','determinado_de_oficio','outro')),
    decisao        TEXT NOT NULL,
    quem_decidiu   TEXT NOT NULL,
    data           TEXT,
    trecho_fonte   TEXT NOT NULL,   -- citação literal presente na página (verificada)
    condicoes_json TEXT NOT NULL,
    modelo         TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    criado_em      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_decisao_item_doc ON decisao_item(documento_id, pagina);

-- datas citadas no trecho literal de cada asserção (stf/datas.py): projeção determinística
CREATE TABLE IF NOT EXISTS assercao_data (
    assercao_id INTEGER NOT NULL REFERENCES assercao(id),
    data        TEXT NOT NULL,     -- AAAA-MM-DD
    literal     TEXT NOT NULL,     -- como aparece no trecho ("18/11/2025", "1º de junho de 2026")
    n_datas     INTEGER NOT NULL,  -- quantas datas distintas o trecho tem; 1 = entra na cronologia
    PRIMARY KEY (assercao_id, data)
);
CREATE INDEX IF NOT EXISTS ix_assercao_data_data ON assercao_data(data);

CREATE TABLE IF NOT EXISTS assercao_entidade (
    assercao_id  INTEGER NOT NULL REFERENCES assercao(id),
    entidade_id  INTEGER NOT NULL REFERENCES entidade(id),
    nome_literal TEXT NOT NULL,
    tipo_citado  TEXT NOT NULL,
    PRIMARY KEY (assercao_id, entidade_id)
);

-- referências determinísticas (stf/referencias.py): texto de documentos e descrições de andamentos
CREATE TABLE IF NOT EXISTS documento_ref_processo (
    id           INTEGER PRIMARY KEY,
    documento_id INTEGER NOT NULL REFERENCES documento(id),
    pagina       INTEGER NOT NULL,
    classe       TEXT NOT NULL,
    numero       INTEGER NOT NULL,
    ocorrencias  INTEGER NOT NULL,
    trecho       TEXT NOT NULL,
    UNIQUE (documento_id, pagina, classe, numero)
);
CREATE INDEX IF NOT EXISTS ix_ref_processo ON documento_ref_processo(classe, numero);
CREATE TABLE IF NOT EXISTS documento_ref_dispositivo (
    id           INTEGER PRIMARY KEY,
    documento_id INTEGER NOT NULL REFERENCES documento(id),
    pagina       INTEGER NOT NULL,
    artigo       TEXT NOT NULL,
    diploma      TEXT NOT NULL,
    dispositivo  TEXT NOT NULL,   -- "art. 312 CPP"
    ocorrencias  INTEGER NOT NULL,
    trecho       TEXT NOT NULL,
    UNIQUE (documento_id, pagina, dispositivo)
);
CREATE INDEX IF NOT EXISTS ix_ref_dispositivo ON documento_ref_dispositivo(dispositivo);
CREATE TABLE IF NOT EXISTS andamento_peticao (
    andamento_id  INTEGER NOT NULL UNIQUE REFERENCES andamento(id),
    peticao_id    INTEGER NOT NULL REFERENCES peticao(id),
    numero_citado TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documento_ref_andamento (
    documento_id INTEGER NOT NULL REFERENCES documento(id),
    pagina       INTEGER NOT NULL,
    andamento_id INTEGER NOT NULL REFERENCES andamento(id),
    tipo_citado  TEXT NOT NULL,
    data_citada  TEXT NOT NULL,
    PRIMARY KEY (documento_id, andamento_id)
);
CREATE INDEX IF NOT EXISTS ix_parte_inc ON parte(incidente);
CREATE INDEX IF NOT EXISTS ix_documento_inc ON documento(incidente);
CREATE INDEX IF NOT EXISTS ix_pagina_doc ON documento_pagina(documento_id);
CREATE INDEX IF NOT EXISTS ix_assercao_entidade_ent ON assercao_entidade(entidade_id);
CREATE INDEX IF NOT EXISTS ix_andamento_tipo ON andamento(tipo);
CREATE INDEX IF NOT EXISTS ix_peticao_inc ON peticao(incidente, numero);
CREATE INDEX IF NOT EXISTS ix_andamento_documento_doc ON andamento_documento(documento_id);

-- fontes externas oficiais (stf/externas.py): capturas append-only de páginas do Banco Central, Senado etc.
CREATE TABLE IF NOT EXISTS fonte_externa_snapshot (
    id           INTEGER PRIMARY KEY,
    fonte_id     TEXT NOT NULL,
    url          TEXT NOT NULL,
    fetched_at   TEXT NOT NULL,
    http_status  INTEGER,
    sha256       TEXT,
    bytes        INTEGER,
    content_type TEXT,
    raw_path     TEXT
);
CREATE INDEX IF NOT EXISTS ix_fonte_externa_fonte ON fonte_externa_snapshot(fonte_id, id);

-- matérias do Congresso que mencionam o caso (stf/legislativo.py): projeção do registro data/raw/legislativo.jsonl + blobs
CREATE TABLE IF NOT EXISTS materia_legislativa (
    casa             TEXT NOT NULL,     -- senado | camara
    codigo           TEXT NOT NULL,     -- código da matéria na casa
    sigla            TEXT,
    numero           INTEGER,
    ano              INTEGER,
    comissao         TEXT,
    identificacao    TEXT,
    ementa           TEXT NOT NULL,
    autor            TEXT,
    data             TEXT,
    url              TEXT NOT NULL,     -- página pública de tramitação
    url_api          TEXT,
    consultas_json   TEXT NOT NULL,     -- quais consultas (casa:palavra) devolveram a matéria
    primeiro_visto_em TEXT NOT NULL,
    ultimo_visto_em  TEXT NOT NULL,
    PRIMARY KEY (casa, codigo)
);

CREATE VIRTUAL TABLE IF NOT EXISTS andamento_fts USING fts5(
    descricao, tipo,
    content='andamento', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER IF NOT EXISTS andamento_ai AFTER INSERT ON andamento BEGIN
    INSERT INTO andamento_fts(rowid, descricao, tipo) VALUES (new.id, new.descricao, new.tipo);
END;
"""

TABELAS_DERIVADAS = [
    "assercao_data", "decisao_item", "documento_ref_processo", "documento_ref_dispositivo", "andamento_peticao", "documento_ref_andamento",
    "assercao_entidade", "assercao", "extracao",
    "entidade_mencao", "entidade", "processo", "documento_fts", "documento_chunk", "documento_pagina",
    "voto", "lista_julgamento", "objeto_incidente",
    "andamento_documento", "processo_relacao", "andamento_fts", "andamento", "tipo_andamento",
    "documento", "parte", "peticao", "deslocamento", "incidente_versao", "incidente",
    "snapshot", "coleta",
]


def abrir(caminho: str | Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(caminho))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    if str(caminho) != ":memory:":
        con.execute("PRAGMA journal_mode = WAL")
    return con


def criar_schema(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def apagar_projecao(con: sqlite3.Connection) -> None:
    """Apaga só a projeção. Os blobs e registros de coleta ficam intactos."""
    for t in TABELAS_DERIVADAS:
        con.execute(f"DROP TABLE IF EXISTS {t}")
    con.commit()
