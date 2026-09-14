"""Sessão virtual: JSON público de sistemas.stf.jus.br, o mesmo que a aba do portal carrega.

- `votacao?oi=<incidente>`: objetos incidente do processo que passaram por sessão virtual
  (tipo PR = processo, IJ = incidente de julgamento, RC = recurso), com `principal` e `pai`.
- `votacao?sessaoVirtual=<objeto>`: listas de julgamento daquele objeto, com sessão, relator,
  votos por ministro (tipo de voto literal) e links para voto/relatório em PDF.

Tudo é literal do JSON. Nenhuma interpretação de resultado: o "placar" da interface é a
lista de votos com o `tipoVoto.descricao` que o STF publicou.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime

URL_OI = "https://sistemas.stf.jus.br/repgeral/votacao?oi={incidente}"
URL_SESSAO = "https://sistemas.stf.jus.br/repgeral/votacao?sessaoVirtual={objeto}"


@dataclass
class ObjetoIncidente:
    id: int
    principal: int | None
    pai: int | None
    tipo: str | None
    tipo_descricao: str | None
    identificacao: str | None
    identificacao_completa: str | None
    cadeia: str | None


@dataclass
class DocumentoSessao:
    rotulo: str          # Voto | Relatório | Voto Vogal | ...
    id_portal: str
    url: str
    ministro: str | None


@dataclass
class Voto:
    ordem: int | None
    ministro: str | None
    data: str | None
    tipo_voto: str | None
    acompanhando: str | None
    antecipado: str | None


@dataclass
class ListaJulgamento:
    objeto_incidente_id: int
    lista_id: int | None
    nome_lista: str | None
    julgado: bool | None
    relator: str | None
    tipo_lista: str | None
    colegiado: str | None
    sessao_numero: int | None
    sessao_ano: int | None
    data_inicio: str | None
    data_fim: str | None
    tipo_sessao: str | None
    texto_decisao: str | None
    resultado: str | None
    votos: list[Voto] = field(default_factory=list)
    documentos: list[DocumentoSessao] = field(default_factory=list)


def _int(x) -> int | None:
    try:
        return int(x) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _data(x) -> str | None:
    if not x:
        return None
    try:
        return datetime.strptime(x, "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def _desc(x) -> str | None:
    if isinstance(x, dict):
        return x.get("descricao") or None
    return x or None


def parse_objetos_incidente(raw: bytes) -> list[ObjetoIncidente]:
    data = json.loads(raw.decode("utf-8")) if raw.strip() else []
    out = []
    for it in data:
        oi = it.get("objetoIncidente", {}) if isinstance(it, dict) else {}
        if not oi:
            continue
        out.append(ObjetoIncidente(
            id=int(oi["id"]), principal=_int(oi.get("principal")), pai=_int(oi.get("pai")),
            tipo=(oi.get("tipoObjetoIncidente") or {}).get("codigo"),
            tipo_descricao=(oi.get("tipoObjetoIncidente") or {}).get("descricao"),
            identificacao=oi.get("identificacao"), identificacao_completa=oi.get("identificacaoCompleta"),
            cadeia=oi.get("cadeia") or None,
        ))
    return out


def _doc(rotulo_padrao: str, d: dict | str | None, ministro: str | None) -> DocumentoSessao | None:
    if not isinstance(d, dict) or not d.get("link"):
        return None
    return DocumentoSessao(rotulo=d.get("descricao") or rotulo_padrao, id_portal=str(d.get("codigo")),
                           url=d["link"], ministro=ministro)


def parse_sessao_virtual(raw: bytes) -> list[ListaJulgamento]:
    data = json.loads(raw.decode("utf-8")) if raw.strip() else []
    out: list[ListaJulgamento] = []
    for it in data:
        oi = it.get("objetoIncidente", {})
        for l in it.get("listasJulgamento", []) or []:
            s = l.get("sessao") or {}
            relator = _desc(l.get("ministroRelator"))
            lista = ListaJulgamento(
                objeto_incidente_id=int(oi["id"]), lista_id=_int(l.get("id")), nome_lista=l.get("nomeLista"),
                julgado=l.get("julgado"), relator=relator, tipo_lista=_desc(l.get("tipoListaJulgamento")),
                colegiado=_desc(s.get("colegiado")), sessao_numero=_int(s.get("numero")), sessao_ano=_int(s.get("ano")),
                data_inicio=_data(s.get("dataInicio") or s.get("dataPrevistaInicio")),
                data_fim=_data(s.get("dataFim") or s.get("dataPrevistaFim")),
                tipo_sessao=_desc(s.get("tipoSessao")), texto_decisao=l.get("textoDecisao") or None,
                resultado=_desc(l.get("tipoResultadoJulgamento")),
            )
            for rotulo, chave in (("Voto", "votoRelator"), ("Relatório", "relatorioRelator")):
                d = _doc(rotulo, l.get(chave), relator)
                if d:
                    lista.documentos.append(d)
            for v in l.get("votos", []) or []:
                ministro = _desc(v.get("ministro"))
                lista.votos.append(Voto(
                    ordem=_int(v.get("numeroOrdemVotoSessao")), ministro=ministro, data=_data(v.get("dataVoto")),
                    tipo_voto=_desc(v.get("tipoVoto")), acompanhando=v.get("acompanhandoMinistro") or None,
                    antecipado=v.get("votoAntecipado") or None,
                ))
                for t in v.get("textos", []) or []:
                    d = _doc("Voto", t, ministro)
                    if d:
                        lista.documentos.append(d)
            out.append(lista)
    return out


def url_oi(incidente: int) -> str:
    return URL_OI.format(incidente=incidente)


def url_sessao(objeto: int) -> str:
    return URL_SESSAO.format(objeto=objeto)
