"""Dataset curado de fluxos (data/curadoria/fluxos/*.json): validação e carga nas tabelas fluxo_*.

Formato do dataset (valores em texto no formato brasileiro, como aparecem na peça; datas AAAA-MM-DD):
{
  "fonte": {"tipo": "rif", "identificador": "...", "orgao": "COAF", "destinatario": "PF/SP", "emitido_em": "...",
            "documento": {"endpoint": "docspublicos", "id_portal": "..."}, "incidente": N},
  "comunicacoes": [{"secao": "suspeita|automatica|especie", "numero": "1", "titular": "<CNPJ/CPF>", "segmento": "...",
      "comunicante": "...", "local": "...", "periodo_inicio": "...", "periodo_fim": "...", "valor": "1.234,56",
      "creditos": "...", "debitos": "...", "informacoes": "<literal>", "consideracoes": "<literal>",
      "pagina_inicio": N, "pagina_fim": N,
      "participacoes": [{"nome": "...", "documento": "<CNPJ/CPF>", "papel": "titular|remetente|...", "atividade": "..."}],
      "bens": [{"id": "b1", "tipo": "veiculo|imovel", "descricao": "...", "valor": "...", "valor_referencia": "...",
                "data_negocio": "...", "identificacao": {...}}],
      "transacoes": [{"origem": "<doc>|null", "destino": "<doc>|null", "valor": "...", "data": "...", "periodo_inicio": "...",
                      "periodo_fim": "...", "tipo": "pix|ted|...", "natureza": "individual|agregado|resumo_tipo",
                      "quantidade": N, "bem": "b1", "descricao": "...", "pagina": N, "trecho": "<literal na página>"}],
      "ocorrencias": [{"norma": "...", "codigo": "...", "descricao": "..."}]}]
}
Toda transação precisa de `trecho` presente na `pagina` (comparação sem espaços). CPF nunca entra inteiro no banco.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .fluxos import PAPEIS, RE_CPF, centavos, chave_ator, mascarar_documento, mascarar_texto

SECOES = {"suspeita", "automatica", "especie"}
TIPOS_TRANSACAO = {"transferencia", "pix", "ted", "boleto", "cdb_rdb", "cartao", "cheque", "tributo", "escritura_compra", "escritura_doacao",
                   "alienacao_fiduciaria", "compra_veiculo", "pagamento_titulo", "outros"}
NATUREZAS = {"individual", "agregado", "resumo_tipo"}
TIPOS_BEM = {"veiculo", "imovel"}
RE_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_VALOR_BR = re.compile(r"^[\d.]+,\d{2}$")


def _sem_espacos(s: str) -> str:
    return re.sub(r"\s+", "", s)


def trecho_na_pagina(trecho: str, texto_pagina: str) -> bool:
    """O trecho literal precisa estar na página; ignora só espaços e quebras de linha."""
    return bool(trecho) and _sem_espacos(trecho) in _sem_espacos(texto_pagina)


def validar_dataset(dados: dict, *, paginas: dict[int, str]) -> list[str]:
    """Lista de erros (vazia = válido). `paginas` = {n: texto} do documento-fonte."""
    erros: list[str] = []
    fonte = dados.get("fonte") or {}
    for campo in ("tipo", "identificador", "orgao", "documento", "incidente"):
        if not fonte.get(campo):
            erros.append(f"fonte.{campo} ausente")

    def valor(caminho, v, obrigatorio=True):
        if v is None or v == "":
            if obrigatorio:
                erros.append(f"{caminho}: valor ausente")
            return
        if not isinstance(v, str) or not RE_VALOR_BR.match(v):
            erros.append(f"{caminho}: valor deve ser texto no formato brasileiro com centavos (ex.: 1.234,56), veio {v!r}")

    def data(caminho, v):
        if v is not None and not RE_DATA.match(str(v)):
            erros.append(f"{caminho}: data deve ser AAAA-MM-DD, veio {v!r}")

    def doc(caminho, v, obrigatorio=True):
        if v is None:
            if obrigatorio:
                erros.append(f"{caminho}: documento (CPF/CNPJ) ausente")
            return
        try:
            chave_ator(v)
        except ValueError:
            erros.append(f"{caminho}: documento não reconhecido {v!r}")

    for i, c in enumerate(dados.get("comunicacoes") or []):
        cam = f"comunicacoes[{i}]"
        if c.get("secao") not in SECOES:
            erros.append(f"{cam}.secao inválida: {c.get('secao')!r}")
        if not c.get("numero"):
            erros.append(f"{cam}.numero ausente")
        doc(f"{cam}.titular", c.get("titular"), obrigatorio=False)
        for k in ("valor", "creditos", "debitos"):
            valor(f"{cam}.{k}", c.get(k), obrigatorio=False)
        for k in ("periodo_inicio", "periodo_fim"):
            data(f"{cam}.{k}", c.get(k))
        for k in ("pagina_inicio", "pagina_fim"):
            if not isinstance(c.get(k), int) or c[k] not in paginas:
                erros.append(f"{cam}.{k}: página inexistente {c.get(k)!r}")
        for j, p in enumerate(c.get("participacoes") or []):
            if p.get("papel") not in PAPEIS.values():
                erros.append(f"{cam}.participacoes[{j}].papel inválido: {p.get('papel')!r}")
            if not p.get("nome"):
                erros.append(f"{cam}.participacoes[{j}].nome ausente")
            doc(f"{cam}.participacoes[{j}].documento", p.get("documento"))
        ids_bens = set()
        for j, b in enumerate(c.get("bens") or []):
            cb = f"{cam}.bens[{j}]"
            if b.get("tipo") not in TIPOS_BEM:
                erros.append(f"{cb}.tipo inválido: {b.get('tipo')!r}")
            if not b.get("descricao"):
                erros.append(f"{cb}.descricao ausente")
            valor(f"{cb}.valor", b.get("valor"), obrigatorio=False)
            valor(f"{cb}.valor_referencia", b.get("valor_referencia"), obrigatorio=False)
            data(f"{cb}.data_negocio", b.get("data_negocio"))
            if b.get("id"):
                ids_bens.add(b["id"])
        for j, t in enumerate(c.get("transacoes") or []):
            ct = f"{cam}.transacoes[{j}]"
            if t.get("tipo") not in TIPOS_TRANSACAO:
                erros.append(f"{ct}.tipo inválido: {t.get('tipo')!r}")
            if t.get("natureza") not in NATUREZAS:
                erros.append(f"{ct}.natureza inválida: {t.get('natureza')!r}")
            valor(f"{ct}.valor", t.get("valor"))
            doc(f"{ct}.origem", t.get("origem"), obrigatorio=False)
            doc(f"{ct}.destino", t.get("destino"), obrigatorio=False)
            if t.get("origem") is None and t.get("destino") is None:
                erros.append(f"{ct}: origem e destino ausentes")
            for k in ("data", "periodo_inicio", "periodo_fim"):
                data(f"{ct}.{k}", t.get(k))
            if t.get("quantidade") is not None and (not isinstance(t["quantidade"], int) or t["quantidade"] < 1):
                erros.append(f"{ct}.quantidade inválida")
            if t.get("bem") and t["bem"] not in ids_bens:
                erros.append(f"{ct}.bem desconhecido: {t['bem']!r}")
            pg = t.get("pagina")
            if not isinstance(pg, int) or pg not in paginas:
                erros.append(f"{ct}.pagina inexistente {pg!r}")
            elif not trecho_na_pagina(t.get("trecho") or "", paginas[pg]):
                erros.append(f"{ct}.trecho não encontrado na página {pg}: {str(t.get('trecho'))[:60]!r}")
            if RE_CPF.search(t.get("trecho") or ""):
                erros.append(f"{ct}.trecho contém CPF; escolha um trecho sem dado pessoal")
        for j, o in enumerate(c.get("ocorrencias") or []):
            if not o.get("norma"):
                erros.append(f"{cam}.ocorrencias[{j}].norma ausente")
    return erros


# ---------------------------------------------------------------- carga

def _paginas_do_documento(con, documento_id: int) -> dict[int, str]:
    return {r[0]: r[1] for r in con.execute("SELECT pagina, texto FROM documento_pagina WHERE documento_id=?", (documento_id,))}


def _ator_id(con, cache: dict, documento: str | None, nome: str | None = None, atividade: str | None = None) -> int | None:
    """Cria ou reaproveita o ator; nunca grava o CPF inteiro. Liga à entidade do caso quando o nome bate."""
    if documento is None:
        return None
    chave, tipo = chave_ator(documento)
    if chave.startswith("nome:"):
        chave = mascarar_texto(chave)
    if chave in cache:
        aid = cache[chave]
        if nome or atividade:
            con.execute("UPDATE fluxo_ator SET nome=COALESCE(nome, ?), atividade=COALESCE(atividade, ?) WHERE id=?", (mascarar_texto(nome), atividade, aid))
        return aid
    from .entidades import chave_nome
    if documento.startswith("nome:") and not nome:
        nome = documento[5:].strip()
    ent = con.execute("SELECT id FROM entidade WHERE chave=?", (chave_nome(nome),)).fetchone() if nome else None
    con.execute(
        "INSERT INTO fluxo_ator (chave, nome, tipo, documento_mascarado, atividade, entidade_id) VALUES (?,?,?,?,?,?)",
        (chave, mascarar_texto(nome) or mascarar_documento(documento), tipo,
         mascarar_documento(documento), atividade, ent[0] if ent else None))
    aid = con.execute("SELECT id FROM fluxo_ator WHERE chave=?", (chave,)).fetchone()[0]
    cache[chave] = aid
    return aid


def _c(v):
    return centavos(v) if v else None


def ingerir_fluxos(con, arquivo) -> dict:
    """Valida o dataset curado e projeta nas tabelas fluxo_*. Recarga substitui as comunicações da mesma fonte;
    atores são compartilhados entre fontes e ficam."""
    arquivo = Path(arquivo)
    bruto = arquivo.read_bytes()
    dados = json.loads(bruto.decode("utf-8"))
    fonte = dados["fonte"]
    d = fonte["documento"]
    doc = con.execute("SELECT id FROM documento WHERE endpoint=? AND id_portal=?", (d["endpoint"], d["id_portal"])).fetchone()
    if not doc:
        raise ValueError(f"documento-fonte não está no banco: {d}")
    paginas = _paginas_do_documento(con, doc[0])
    erros = validar_dataset(dados, paginas=paginas)
    if erros:
        raise ValueError("dataset inválido:\n  " + "\n  ".join(erros))

    res = {"comunicacoes": 0, "transacoes": 0, "atores": 0, "bens": 0}
    with con:
        con.execute(
            "INSERT INTO fluxo_fonte (tipo, identificador, orgao, destinatario, emitido_em, documento_id, incidente, curadoria_path, "
            "curadoria_sha256, carregado_em) VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(tipo, identificador) DO UPDATE SET "
            "documento_id=excluded.documento_id, curadoria_path=excluded.curadoria_path, curadoria_sha256=excluded.curadoria_sha256, "
            "carregado_em=excluded.carregado_em",
            (fonte["tipo"], fonte["identificador"], fonte["orgao"], fonte.get("destinatario"), fonte.get("emitido_em"), doc[0],
             fonte["incidente"], str(arquivo).replace("\\", "/"), hashlib.sha256(bruto).hexdigest(), datetime.now(timezone.utc).isoformat()))
        fid = con.execute("SELECT id FROM fluxo_fonte WHERE tipo=? AND identificador=?", (fonte["tipo"], fonte["identificador"])).fetchone()[0]
        for t in ("fluxo_ocorrencia", "fluxo_transacao", "fluxo_bem", "fluxo_participacao"):
            con.execute(f"DELETE FROM {t} WHERE comunicacao_id IN (SELECT id FROM fluxo_comunicacao WHERE fonte_id=?)", (fid,))
        con.execute("DELETE FROM fluxo_comunicacao WHERE fonte_id=?", (fid,))

        cache: dict[str, int] = {r[0]: r[1] for r in con.execute("SELECT chave, id FROM fluxo_ator")}
        antes = len(cache)
        for c in dados["comunicacoes"]:
            for p in c.get("participacoes") or []:
                _ator_id(con, cache, p["documento"], p["nome"], p.get("atividade"))
            titular = _ator_id(con, cache, c.get("titular"))
            cur = con.execute(
                "INSERT INTO fluxo_comunicacao (fonte_id, secao, numero, titular_ator_id, segmento, comunicante, local, periodo_inicio, "
                "periodo_fim, valor_centavos, creditos_centavos, debitos_centavos, informacoes, consideracoes, pagina_inicio, pagina_fim) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (fid, c["secao"], c["numero"], titular, c.get("segmento"), c.get("comunicante"), c.get("local"), c.get("periodo_inicio"),
                 c.get("periodo_fim"), _c(c.get("valor")), _c(c.get("creditos")), _c(c.get("debitos")), mascarar_texto(c.get("informacoes")),
                 mascarar_texto(c.get("consideracoes")), c["pagina_inicio"], c["pagina_fim"]))
            cid = cur.lastrowid
            res["comunicacoes"] += 1
            for p in c.get("participacoes") or []:
                con.execute("INSERT OR IGNORE INTO fluxo_participacao (comunicacao_id, ator_id, papel) VALUES (?,?,?)",
                            (cid, _ator_id(con, cache, p["documento"]), p["papel"]))
            bens_ids: dict[str, int] = {}
            for b in c.get("bens") or []:
                cur = con.execute(
                    "INSERT INTO fluxo_bem (comunicacao_id, tipo, descricao, valor_centavos, valor_referencia_centavos, data_negocio, identificacao) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (cid, b["tipo"], mascarar_texto(b["descricao"]), _c(b.get("valor")), _c(b.get("valor_referencia")), b.get("data_negocio"),
                     json.dumps(b["identificacao"], ensure_ascii=False) if b.get("identificacao") else None))
                if b.get("id"):
                    bens_ids[b["id"]] = cur.lastrowid
                res["bens"] += 1
            for t in c.get("transacoes") or []:
                con.execute(
                    "INSERT INTO fluxo_transacao (comunicacao_id, origem_ator_id, destino_ator_id, valor_centavos, data, periodo_inicio, "
                    "periodo_fim, tipo, natureza, quantidade, bem_id, descricao, pagina, trecho_fonte) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (cid, _ator_id(con, cache, t.get("origem")), _ator_id(con, cache, t.get("destino")), centavos(t["valor"]), t.get("data"),
                     t.get("periodo_inicio"), t.get("periodo_fim"), t["tipo"], t["natureza"], t.get("quantidade"),
                     bens_ids.get(t["bem"]) if t.get("bem") else None, mascarar_texto(t.get("descricao")), t["pagina"], t["trecho"]))
                res["transacoes"] += 1
            for o in c.get("ocorrencias") or []:
                con.execute("INSERT INTO fluxo_ocorrencia (comunicacao_id, norma, codigo, descricao) VALUES (?,?,?,?)",
                            (cid, o["norma"], o.get("codigo"), o.get("descricao")))
        res["atores"] = len(cache) - antes
    return res
