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
    snapshot_first_seen INTEGER NOT NULL,
    UNIQUE (endpoint, id_portal)
);

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
    natureza_provavel TEXT               -- pessoa_juridica quando o nome tem sufixo societário explícito; senão NULL
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
    "entidade_mencao", "entidade", "processo",
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
