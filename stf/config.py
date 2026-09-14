"""Configuração fixa do projeto. Mudar aqui é mudar a política de coleta."""

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
BLOBS = DATA / "raw" / "blobs"
COLETAS = DATA / "raw" / "coletas"
BANCO = DATA / "stf.sqlite"
BUNDLE_TLS = RAIZ / "recon" / "certs" / "stf-chain.pem"

BASE = "https://portal.stf.jus.br"
BASE_PROCESSOS = f"{BASE}/processos/"
ROBOTS_URL = f"{BASE}/robots.txt"

VERSAO = "0.1"
CONTATO = "ldickmann12@gmail.com"
# O WAF do portal (AWS ALB) devolve 403 a qualquer UA sem prefixo "Mozilla/5.0".
# Este formato passa e se identifica com nome, versão e contato (Fase 0, seção 3).
USER_AGENT = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; stf-mapeador/{VERSAO}; +mailto:{CONTATO})"

INTERVALO_MINIMO_S = 3.0
TETO_REQUISICOES_POR_COLETA = 12   # 1 casca + 9 abas + margem para redirects; documentos têm teto próprio
BACKOFF_BASE_S = 5.0
BACKOFF_TENTATIVAS = 3
TIMEOUT_S = 60.0
TETO_REQUISICOES_POR_EXPANSAO = 150  # 7 resoluções + 7 vizinhos × 11 abas = 84 no caso-semente; margem para agravos
