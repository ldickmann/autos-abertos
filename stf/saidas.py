"""Saídas abertas para quem quer trabalhar com os dados fora do site: CSV (planilha) e feed Atom (acompanhar).

CSV com BOM e ponto e vírgula, que é o que o Excel em português abre sem configurar nada. Toda linha carrega a fonte
(documento, página, trecho literal), como no site. O feed lista a última publicação da base, os avisos e as rodadas
de vigilância do portal, para que qualquer pessoa receba as mudanças num leitor de feeds.
"""

from __future__ import annotations

import csv
import io
from xml.sax.saxutils import escape


def _csv(cabecalho: list[str], linhas: list[list]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    w.writerow(cabecalho)
    w.writerows(linhas)
    return "﻿" + buf.getvalue()


def csv_decisoes(itens: list[dict]) -> str:
    cab = ["id", "data", "processo", "incidente", "resultado", "pedido", "quem_pediu", "decisao", "quem_decidiu", "condicoes", "documento_id", "pagina", "trecho_fonte", "url_documento"]
    return _csv(cab, [[i["id"], i.get("data"), i.get("processo"), i["incidente"], i["resultado"], i["pedido"], i.get("quem_pediu"), i["decisao"], i["quem_decidiu"],
                       " | ".join(i.get("condicoes") or []), i["documento_id"], i["pagina"], i["trecho_fonte"], i.get("url_documento")] for i in itens])


def csv_assercoes(assercoes: list[dict]) -> str:
    cab = ["id", "tipo_epistemico", "atribuida_a", "texto", "entidades", "documento_id", "titulo_documento", "incidente", "pagina", "trecho_fonte", "data_andamento", "modelo", "prompt_version", "url_documento"]
    return _csv(cab, [[a["id"], a["tipo_epistemico"], a.get("atribuida_a"), a["texto"], " | ".join(e["nome"] for e in a.get("entidades", [])),
                       a["documento"]["id"], a["documento"].get("titulo"), a["documento"]["incidente"], a["pagina"], a["trecho_fonte"], a.get("data_andamento"),
                       a["modelo"], a["prompt_version"], a["documento"].get("url")] for a in assercoes])


def csv_cronologia(eventos: list[dict]) -> str:
    cab = ["data", "origem", "tipo", "processo", "incidente", "texto", "tipo_epistemico", "atribuida_a", "resultado", "documento_id", "pagina", "trecho_fonte", "contexto"]
    return _csv(cab, [[e["data"], e["fonte"], e["tipo"], e["processo"], e["incidente"], e["texto"], e.get("tipo_epistemico"), e.get("atribuida_a"), e.get("resultado"),
                       e.get("documento_id"), e.get("pagina"), e.get("trecho_fonte"), e["contexto"]] for e in eventos])


def feed_atom(site: str, *, avisos: list[dict], mudancas: list[dict], gerado_em: str) -> str:
    def entrada(id_: str, titulo: str, atualizado: str, link: str, resumo: str) -> str:
        return (f"  <entry>\n    <id>{escape(id_)}</id>\n    <title>{escape(titulo)}</title>\n    <updated>{escape(atualizado)}</updated>\n"
                f"    <link href=\"{escape(link, {'\"': '&quot;'})}\"/>\n    <summary>{escape(resumo)}</summary>\n  </entry>\n")
    entradas = [entrada(f"{site}/#base-{gerado_em}", f"Base atualizada em {gerado_em[:16].replace('T', ' ')} UTC", gerado_em, f"{site}/", "Nova publicação dos dados do site.")]
    for a in avisos:
        entradas.append(entrada(f"{site}/#aviso-{a['id']}", f"Aviso: {a['titulo']} ({a['inicio'][:16].replace('T', ' ')})", a["inicio"], a.get("acao", {}).get("url", f"{site}/"), a.get("resumo", "")))
    for r in mudancas:
        total = sum(sum(p["resumo"].values()) for p in r["processos"])
        titulo = f"Portal do STF recoletado em {r['em'][:16].replace('T', ' ')}: " + (f"{total} mudança(s)" if total else "nenhuma mudança")
        detalhes = "; ".join(f"{p['processo']}: {', '.join(f'{m['o_que']} {m['mudanca']}: {m['item']}' for m in p['mudancas'])}" for p in r["processos"] if p["mudancas"]) or "Sem mudanças."
        entradas.append(entrada(f"{site}/mudancas/#{r['em']}", titulo, r["em"], f"{site}/mudancas/", detalhes[:2000]))
    entradas_ordenadas = [entradas[0]] + sorted(entradas[1:], key=lambda e: e, reverse=True)
    return ("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<feed xmlns=\"http://www.w3.org/2005/Atom\">\n"
            f"  <title>Autos Abertos: avisos e mudanças</title>\n  <id>{escape(site)}/feed.xml</id>\n  <updated>{escape(gerado_em)}</updated>\n"
            f"  <link href=\"{escape(site)}/\"/>\n  <link rel=\"self\" href=\"{escape(site)}/feed.xml\"/>\n" + "".join(entradas_ordenadas) + "</feed>\n")
