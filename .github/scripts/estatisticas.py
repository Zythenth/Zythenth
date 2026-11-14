"""Gera os cartões de estatísticas e de linguagens do perfil em SVG, no tema espacial.

Cada número ganha um ícone de astro, o nível aparece como um planeta com a órbita
preenchida conforme a classificação, e as linguagens viram pequenos planetas coloridos.

Uso: GITHUB_TOKEN=... python estatisticas.py <usuario> <pasta-de-saida>
"""
import json
import math
import os
import sys
import urllib.request
from datetime import datetime, timezone

QUERY_PERFIL = """
query($login: String!) {
  user(login: $login) {
    name
    createdAt
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) { totalCount }
    contributionsCollection { totalPullRequestReviewContributions }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, orderBy: {field: STARGAZERS, direction: DESC}) {
      nodes {
        isFork
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } }
      }
    }
  }
}
"""

QUERY_COMMITS = """
query($login: String!, $de: DateTime!, $ate: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $de, to: $ate) { totalCommitContributions }
  }
}
"""

BASE, LINE = "#08090d", "#262a40"
PERI, PALE, WHITE = "#8a9fc6", "#c3d0ea", "#f9f9fd"
SANS = "Segoe UI, Helvetica, Arial, sans-serif"
SERIF = "Georgia, 'Times New Roman', serif"


def consulta(query, variaveis, token):
    body = json.dumps({"query": query, "variables": variaveis}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "estatisticas"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise SystemExit(f"Erro da API do GitHub: {data['errors']}")
    return data["data"]["user"]


def dados(login, token):
    perfil = consulta(QUERY_PERFIL, {"login": login}, token)
    agora = datetime.now(timezone.utc)
    commits = 0
    for ano in range(int(perfil["createdAt"][:4]), agora.year + 1):  # a API aceita no máximo um ano por consulta; conta só o que é público
        de = datetime(ano, 1, 1, tzinfo=timezone.utc)
        ate = min(datetime(ano + 1, 1, 1, tzinfo=timezone.utc), agora)
        c = consulta(QUERY_COMMITS, {"login": login, "de": de.isoformat(), "ate": ate.isoformat()}, token)
        commits += c["contributionsCollection"]["totalCommitContributions"]
    repos = perfil["repositories"]["nodes"]
    linguagens = {}
    for repo in repos:
        if repo["isFork"]:
            continue
        for edge in repo["languages"]["edges"]:
            nome = edge["node"]["name"]
            atual = linguagens.setdefault(nome, {"tamanho": 0, "cor": edge["node"]["color"] or PERI})
            atual["tamanho"] += edge["size"]
    return {
        "nome": perfil["name"] or login,
        "estrelas": sum(r["stargazerCount"] for r in repos),
        "commits": commits,
        "prs": perfil["pullRequests"]["totalCount"],
        "issues": perfil["issues"]["totalCount"],
        "contribuiu": perfil["repositoriesContributedTo"]["totalCount"],
        "revisoes": perfil["contributionsCollection"]["totalPullRequestReviewContributions"],
        "seguidores": perfil["followers"]["totalCount"],
        "linguagens": linguagens,
    }


def nivel(d):
    """Mesma classificação usada pelos cartões de estatísticas mais comuns do GitHub."""
    exp = lambda x: 1 - 2 ** -x
    lognormal = lambda x: x / (1 + x)
    pesos = [(2, exp(d["commits"] / 1000)), (3, exp(d["prs"] / 50)), (1, exp(d["issues"] / 25)),
             (1, exp(d["revisoes"] / 2)), (4, lognormal(d["estrelas"] / 50)), (1, lognormal(d["seguidores"] / 10))]
    rank = 1 - sum(p * v for p, v in pesos) / sum(p for p, _ in pesos)
    limites = [1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100]
    niveis = ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"]
    letra = next(n for lim, n in zip(limites, niveis) if rank * 100 <= lim)
    return letra, 100 - rank * 100


# ícones de astro, desenhados num quadrado de 18 px com centro na origem
ICONES = {
    "estrelas": ('<circle r="9" fill="url(#h-estrela)"/>'
                 '<path d="M 0,-8 Q 1.2,-1.2 8,0 Q 1.2,1.2 0,8 Q -1.2,1.2 -8,0 Q -1.2,-1.2 0,-8 Z" fill="#ffd36b"/>'
                 '<circle r="1.8" fill="#fff8de"/>'),
    "commits": ('<path d="M 2,-1.6 L -9,-7 L 1,2.4 Z" fill="url(#cauda)"/>'
                '<circle cx="2" cy="0" r="4.6" fill="url(#h-cometa)"/><circle cx="2" cy="0" r="2.4" fill="#f2fcff"/>'),
    "prs": ('<ellipse rx="9" ry="2.6" fill="none" stroke="#c9b6ff" stroke-width="1.3" transform="rotate(-20)"/>'
            '<circle r="5" fill="url(#g-roxo)"/>'),
    "issues": ('<circle r="6.5" fill="url(#g-marte)"/><circle cx="-1.8" cy="-1.4" r="1.4" fill="#9a3a1c" opacity="0.8"/>'
               '<circle cx="2" cy="2.2" r="1" fill="#9a3a1c" opacity="0.7"/>'),
    "contribuiu": ('<circle r="6.5" fill="url(#g-lua)" mask="url(#m-lua)"/>'
                   '<circle cx="7" cy="-6" r="1.1" fill="#fff6d8"/>'),
}

DEFS_ICONES = """
    <radialGradient id="h-estrela"><stop offset="0" stop-color="#ffd36b" stop-opacity="0.5"/><stop offset="1" stop-color="#ffd36b" stop-opacity="0"/></radialGradient>
    <radialGradient id="h-cometa"><stop offset="0" stop-color="#9fe6ff"/><stop offset="1" stop-color="#9fe6ff" stop-opacity="0"/></radialGradient>
    <linearGradient id="cauda" x1="1" y1="0.5" x2="0" y2="0"><stop offset="0" stop-color="#7fd8f0" stop-opacity="0.95"/><stop offset="1" stop-color="#7fd8f0" stop-opacity="0"/></linearGradient>
    <radialGradient id="g-roxo" cx="0.35" cy="0.3" r="0.75"><stop offset="0" stop-color="#e2d6ff"/><stop offset="1" stop-color="#7b5cd6"/></radialGradient>
    <radialGradient id="g-marte" cx="0.35" cy="0.3" r="0.75"><stop offset="0" stop-color="#f29a6e"/><stop offset="1" stop-color="#b8461f"/></radialGradient>
    <radialGradient id="g-lua" cx="0.3" cy="0.4" r="0.75"><stop offset="0" stop-color="#fff4cf"/><stop offset="1" stop-color="#e2ab45"/></radialGradient>
    <mask id="m-lua"><rect x="-8" y="-8" width="16" height="16" fill="#fff"/><circle cx="3.2" cy="-1.8" r="5.8" fill="#000"/></mask>"""

PLANETA_NIVEL = {  # cor do planeta do nível: (centro, borda, brilho)
    "S": ("#fff4c2", "#f0a92e", "#ffd36b"), "A": ("#d9f3ff", "#3d8fe0", "#7fc4ff"),
    "B": ("#d6fff0", "#2fae8c", "#6de0bf"), "C": ("#e8deff", "#7b5cd6", "#b49cff"),
}


def moldura(W, H, conteudo, titulo, defs=""):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{titulo}">
  <title>{titulo}</title>
  <defs><clipPath id="card"><rect width="{W}" height="{H}" rx="16"/></clipPath>{defs}
  </defs>
  <g clip-path="url(#card)">
    <rect width="{W}" height="{H}" fill="{BASE}"/>
    {conteudo}
  </g>
  <rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="15.5" fill="none" stroke="{LINE}" stroke-width="1.5"/>
</svg>
"""


def numero(n):
    return f"{n:,}".replace(",", ".")


def cartao_estatisticas(d):
    W, H = 500, 200
    letra, pct = nivel(d)
    linhas = [("estrelas", "Estrelas recebidas", d["estrelas"]), ("commits", "Commits", d["commits"]),
              ("prs", "Pull requests", d["prs"]), ("issues", "Issues", d["issues"]),
              ("contribuiu", "Contribuiu em (último ano)", d["contribuiu"])]
    corpo = []
    for i, (chave, rotulo, valor) in enumerate(linhas):
        y = 80 + i * 24
        atraso = 0.15 + i * 0.12
        corpo.append(
            f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{atraso:.2f}s" dur="0.5s" fill="freeze"/>'
            f'<g transform="translate(38 {y - 5})">{ICONES[chave]}</g>'
            f'<text x="60" y="{y}" fill="{PALE}" font-family="{SANS}" font-size="14" font-weight="600">{rotulo}</text>'
            f'<text x="282" y="{y}" fill="{WHITE}" font-family="{SANS}" font-size="14" font-weight="700" text-anchor="end">{numero(valor)}</text></g>')

    cx, cy, r = 400, 112, 44
    centro, borda, brilho = PLANETA_NIVEL[letra[0]]
    volta = 2 * math.pi * r
    cheio = volta * pct / 100
    planeta = f"""
    <circle cx="{cx}" cy="{cy}" r="{r + 14}" fill="url(#h-nivel)"/>
    <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{LINE}" stroke-width="5"/>
    <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#orbita)" stroke-width="5" stroke-linecap="round"
      stroke-dasharray="{cheio:.1f} {volta:.1f}" transform="rotate(-90 {cx} {cy})">
      <animate attributeName="stroke-dasharray" from="0 {volta:.1f}" to="{cheio:.1f} {volta:.1f}" dur="1.4s" fill="freeze"/>
    </circle>
    <g><animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="18s" repeatCount="indefinite"/>
      <circle cx="{cx + r}" cy="{cy}" r="4.2" fill="url(#g-lua-nivel)"/></g>
    <circle cx="{cx}" cy="{cy}" r="27" fill="url(#g-nivel)"/>
    <ellipse cx="{cx}" cy="{cy}" rx="27" ry="27" fill="url(#sombra)"/>
    <text x="{cx}" y="{cy + 9}" fill="#0b0c18" font-family="{SANS}" font-size="26" font-weight="800" text-anchor="middle">{letra}</text>"""
    defs = DEFS_ICONES + f"""
    <radialGradient id="h-nivel"><stop offset="0.55" stop-color="{brilho}" stop-opacity="0.22"/><stop offset="1" stop-color="{brilho}" stop-opacity="0"/></radialGradient>
    <radialGradient id="g-nivel" cx="0.35" cy="0.3" r="0.75"><stop offset="0" stop-color="{centro}"/><stop offset="1" stop-color="{borda}"/></radialGradient>
    <radialGradient id="sombra" cx="0.35" cy="0.3" r="0.75"><stop offset="0.6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.4"/></radialGradient>
    <radialGradient id="g-lua-nivel" cx="0.35" cy="0.3" r="0.75"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#9d97a8"/></radialGradient>
    <linearGradient id="orbita" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7fd8f0"/><stop offset="1" stop-color="#b49cff"/></linearGradient>"""
    titulo = "Estatísticas no GitHub"
    conteudo = (f'<text x="28" y="44" fill="{WHITE}" font-family="{SERIF}" font-size="22">{titulo}</text>'
                + "".join(corpo) + planeta)
    return moldura(W, H, conteudo, f"{titulo} de {d['nome']}: nível {letra}", defs)


def clarear(cor, minimo=0.32):
    """Clareia cores muito escuras (como as de Lua e PowerShell) para aparecerem no fundo preto."""
    r, g, b = (int(cor[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    if lum >= minimo:
        return cor
    t = min(1, (minimo - lum) / (1 - lum) * 1.6)
    return "#" + "".join(f"{round((c + (1 - c) * t) * 255):02x}" for c in (r, g, b))


def cartao_linguagens(d, quantidade=6):
    W, H = 360, 200
    total = sum(v["tamanho"] for v in d["linguagens"].values()) or 1
    top = sorted(d["linguagens"].items(), key=lambda kv: -kv[1]["tamanho"])[:quantidade]
    soma_top = sum(v["tamanho"] for _, v in top) or 1
    x0, largura = 28, W - 56
    barra, legenda, defs = [], [], []
    x = x0
    for i, (nome, info) in enumerate(top):
        cor = clarear(info["cor"])
        w = largura * info["tamanho"] / soma_top
        barra.append(f'<rect x="{x:.1f}" y="66" width="{max(w - 2, 1):.1f}" height="8" fill="{cor}"/>')
        x += w
        coluna, linha = divmod(i, 3)
        lx, ly = 40 + coluna * 160, 108 + linha * 28
        pct = f"{100 * info['tamanho'] / total:.2f}".replace(".", ",")
        defs.append(f'<radialGradient id="l{i}" cx="0.35" cy="0.3" r="0.75"><stop offset="0" stop-color="#ffffff" stop-opacity="0.85"/>'
                    f'<stop offset="0.45" stop-color="{cor}"/><stop offset="1" stop-color="{cor}"/></radialGradient>')
        legenda.append(
            f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{0.2 + i * 0.1:.1f}s" dur="0.5s" fill="freeze"/>'
            f'<circle cx="{lx}" cy="{ly - 4.5}" r="9" fill="{cor}" opacity="0.18"/>'
            f'<circle cx="{lx}" cy="{ly - 4.5}" r="5.5" fill="url(#l{i})"/>'
            f'<text x="{lx + 14}" y="{ly}" fill="{PALE}" font-family="{SANS}" font-size="13">{nome} '
            f'<tspan fill="{WHITE}" font-weight="600">{pct}%</tspan></text></g>')
    titulo = "Linguagens mais usadas"
    conteudo = (f'<text x="28" y="44" fill="{WHITE}" font-family="{SERIF}" font-size="22">{titulo}</text>'
                f'<g clip-path="url(#barra)"><g>{"".join(barra)}'
                f'<animateTransform attributeName="transform" type="scale" from="0 1" to="1 1" dur="1.2s" fill="freeze"/></g></g>'
                + "".join(legenda))
    extra = f'<clipPath id="barra"><rect x="{x0}" y="66" width="{largura}" height="8" rx="4"/></clipPath>' + "".join(defs)
    return moldura(W, H, conteudo, f"{titulo} por {d['nome']}", extra)


def main():
    login, saida = sys.argv[1], sys.argv[2]
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("Defina GITHUB_TOKEN para consultar as estatísticas.")
    d = dados(login, token)
    os.makedirs(saida, exist_ok=True)
    for nome, conteudo in (("estatisticas.svg", cartao_estatisticas(d)), ("linguagens.svg", cartao_linguagens(d))):
        caminho = os.path.join(saida, nome)
        with open(caminho, "w", encoding="utf-8") as fh:
            fh.write(conteudo)
        print(f"{caminho}: {len(conteudo)} bytes")


if __name__ == "__main__":
    main()
