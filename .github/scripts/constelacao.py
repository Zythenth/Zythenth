"""Gera a constelação de contribuições do perfil em SVG.

Cada dia do último ano aparece como um commit comum até a bolinha passar por
cima, num trajeto livre como o da cobrinha; aí ele vira um astro que cresce com as
contribuições (cometa, planeta, sol, estrela gigante ou buraco negro) e mostra
o número do dia.

Uso: GITHUB_TOKEN=... python constelacao.py <usuario> <arquivo-de-saida.svg>
"""
import json
import os
import random
import zlib
import sys
import urllib.request
from datetime import date

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
    }
  }
}
"""

BASE, SHADE, LINE = "#08090d", "#0d0e14", "#262a40"
DIM, PERI, PALE, WHITE, INK = "#5a6686", "#8a9fc6", "#c3d0ea", "#f9f9fd", "#1f2240"
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
SANS = "Segoe UI, Helvetica, Arial, sans-serif"
SERIF = "Georgia, 'Times New Roman', serif"



def calendario(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "constelacao"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise SystemExit(f"Erro da API do GitHub: {data['errors']}")
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


FAIXAS = [  # (mínimo de contribuições no dia, astro, nome)
    (20, "buraco", "buraco negro"),
    (10, "gigante", "estrela gigante"),
    (6, "sol", "sol"),
    (3, "planeta", "planeta"),
    (1, "cometa", "cometa"),
]


def faixa(n):
    return next(f for f in FAIXAS if n >= f[0])


def raios(x, y, n, longo, curto, base, cor, giro):
    pontas = []
    for i in range(n):
        L = longo if i % 2 == 0 else curto
        pontas.append(f'<path d="M {x - base},{y} L {x},{y - L} L {x + base},{y} Z" fill="{cor}" '
                      f'transform="rotate({360 * i / n:.1f} {x} {y})"/>')
    return (f'<g>{"".join(pontas)}<animateTransform attributeName="transform" type="rotate" '
            f'from="0 {x} {y}" to="360 {x} {y}" dur="{giro}s" repeatCount="indefinite"/></g>')


# Cada astro tem variantes inspiradas em corpos reais; o dia escolhe uma de forma fixa pela data.
VARIANTES = {
    "cometa": ["cometa"],
    "planeta": ["terra", "marte", "saturno", "netuno", "jupiter"],
    "sol": ["sol"],
    "gigante": ["betelgeuse", "rigel", "aldebaran"],
    "buraco": ["buraco"],
}
HALOS = {  # cor do brilho de cada astro
    "cometa": "#7fd8f0", "sol": "#ffc94a", "betelgeuse": "#ff5a2e", "rigel": "#7aa6ff",
    "aldebaran": "#ff9a3c", "buraco": "#ff8a3d",
}
NUCLEOS = {  # (centro, borda) dos núcleos luminosos
    "cometa": ("#f2fcff", "#7fd8f0"), "sol": ("#fff6c2", "#ffbf2e"), "betelgeuse": ("#ffd9b0", "#ff5a2e"),
    "rigel": ("#ffffff", "#7aa6ff"), "aldebaran": ("#ffe6b8", "#ff9a3c"),
}


def defs_astros():
    """Gradientes e recortes usados pelos astros coloridos."""
    partes = [f'<radialGradient id="halo-{k}"><stop offset="0" stop-color="{c}" stop-opacity="0.75"/>'
              f'<stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>' for k, c in HALOS.items()]
    partes += [f'<radialGradient id="nucleo-{k}" cx="0.4" cy="0.38" r="0.65"><stop offset="0" stop-color="{a}"/>'
               f'<stop offset="1" stop-color="{b}"/></radialGradient>' for k, (a, b) in NUCLEOS.items()]
    partes += [
        '<linearGradient id="cauda" x1="1" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#9fe6ff" stop-opacity="0.9"/>'
        '<stop offset="1" stop-color="#9fe6ff" stop-opacity="0"/></linearGradient>',
        '<linearGradient id="disco" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ff6a2a"/>'
        '<stop offset="0.5" stop-color="#fff0c8"/><stop offset="1" stop-color="#ff6a2a"/></linearGradient>',
        '<radialGradient id="sombra" cx="0.35" cy="0.3" r="0.75"><stop offset="0.55" stop-color="#000" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#000" stop-opacity="0.45"/></radialGradient>',
        '<clipPath id="disco-planeta"><circle r="10"/></clipPath>',
    ]
    return "".join(partes)


def planeta(var):
    """Planetas desenhados na origem, com recorte circular e sombra."""
    if var == "terra":
        miolo = ('<circle r="10" fill="#2f74c8"/>'
                 '<path d="M -9,-3 C -6,-8 -1,-7 0,-3 C 1,1 -4,2 -3,6 C -6,7 -9,3 -9,-3 Z" fill="#4fae62"/>'
                 '<path d="M 3,-9 C 7,-8 9,-4 7,-1 C 5,1 3,-2 2,-5 Z M 4,4 C 7,3 9,6 6,9 C 4,9 3,6 4,4 Z" fill="#5fbf6e"/>'
                 '<path d="M -8,-6 C -3,-9 3,-9 7,-7" fill="none" stroke="#fff" stroke-width="1.4" opacity="0.7"/>', "#ffffff")
    elif var == "marte":
        miolo = ('<circle r="10" fill="#c8552e"/>'
                 '<path d="M -10,2 C -5,0 -2,5 3,3 C 6,2 8,5 10,4 L 10,10 L -10,10 Z" fill="#9a3a1c"/>'
                 '<circle cx="-3" cy="-3" r="2.2" fill="#a8411f"/><ellipse cx="0" cy="-9.4" rx="4.5" ry="1.8" fill="#f4ece6"/>', "#ffffff")
    elif var == "saturno":
        miolo = ('<circle r="10" fill="#e6c983"/><rect x="-10" y="-4" width="20" height="2.5" fill="#cfa862"/>'
                 '<rect x="-10" y="2" width="20" height="2" fill="#d6b46f"/>', "#3a2a0c")
    elif var == "netuno":
        miolo = ('<circle r="10" fill="#3b63dc"/><rect x="-10" y="-2" width="20" height="3" fill="#5f86f0"/>'
                 '<ellipse cx="4" cy="4" rx="3" ry="1.6" fill="#24409e"/>', "#ffffff")
    else:  # júpiter
        miolo = ('<circle r="10" fill="#e2b48a"/><rect x="-10" y="-6" width="20" height="2.4" fill="#b9784c"/>'
                 '<rect x="-10" y="0" width="20" height="3" fill="#c98d5f"/><rect x="-10" y="5.5" width="20" height="1.8" fill="#b9784c"/>'
                 '<ellipse cx="4" cy="3.6" rx="2.6" ry="1.5" fill="#a5532e"/>', "#2e1a0c")
    corpo, ink = miolo
    anel = ''
    if var == "saturno":
        anel = '<ellipse rx="17" ry="4.8" fill="none" stroke="#e8d39c" stroke-width="2.2" transform="rotate(-20)"/>'
    return (anel + f'<g clip-path="url(#disco-planeta)">{corpo}<circle r="10" fill="url(#sombra)"/></g>'), ink


def astro(var):
    """Desenha o astro do dia na origem; devolve (svg, cor do número, raio do brilho)."""
    if var == "cometa":
        return ('<path d="M -3,-8 L -19,-17 L -8,-2 Z" fill="url(#cauda)"/>'
                '<circle r="12" fill="url(#halo-cometa)"/><circle r="9" fill="url(#nucleo-cometa)"/>', "#0b2a3a", 12)
    if var in ("terra", "marte", "saturno", "netuno", "jupiter"):
        corpo, ink = planeta(var)
        return corpo, ink, 14
    if var == "sol":
        return ('<circle r="15" fill="url(#halo-sol)"/>' + raios(0, 0, 8, 13, 10.5, 2, "#ffb52e", 14)
                + '<circle r="8.5" fill="url(#nucleo-sol)"/>', "#4a2600", 14)
    if var in ("betelgeuse", "rigel", "aldebaran"):
        cor = HALOS[var]
        return (f'<circle r="19" fill="url(#halo-{var})"/>' + raios(0, 0, 12, 17.5, 13.5, 2.4, cor, 20)
                + f'<circle r="11" fill="url(#nucleo-{var})"/>'
                f'<circle r="14" fill="none" stroke="{cor}" stroke-width="1" opacity="0.7"/>', "#1a0f08", 18)
    disco = ('fill="none" stroke="url(#disco)" stroke-width="3" stroke-dasharray="9 3 3 3" transform="rotate(-15)"')
    giro = '<animate attributeName="stroke-dashoffset" from="0" to="-72" dur="2.6s" repeatCount="indefinite"/>'
    return ('<circle r="18" fill="url(#halo-buraco)" opacity="0.6"/>'
            f'<ellipse rx="19" ry="6" {disco}>{giro}</ellipse>'
            '<circle r="10.5" fill="#05060f" stroke="#ffd9a0" stroke-width="1.4"/>', WHITE, 19)


W_PITCH = 22      # distância entre os dias
LEFT = 72         # início da grade, depois dos rótulos dos dias
TOP = 120         # linha do domingo
K = 0.78          # escala dos astros dentro da grade
PASSO_MAX = 0.06  # segundos que a bolinha leva, no máximo, de uma casa para a vizinha
VARREDURA_MAX = 32  # duração máxima do passeio, em segundos
PAUSA = 4         # segundos com tudo revelado antes de recomeçar
NORMAL = {"cometa": "#2e3754", "planeta": "#4a5a86", "sol": "#7187bb", "gigante": "#a9bde6", "buraco": "#d6e0f5"}


ORDEM = ["cometa", "planeta", "sol", "gigante", "buraco"]


def caminho(weeks, rng):
    """Trajeto livre como o da cobrinha: revela primeiro os dias mais fracos e depois os
    mais fortes, sempre indo ao mais próximo da vez e contornando os dias de nível acima,
    que ainda não podem ser revelados.

    Devolve as casas visitadas e, para cada dia com contribuições, o passo em que ele foi revelado.
    """
    nivel = {(c, d["weekday"]): ORDEM.index(faixa(d["contributionCount"])[1])
             for c, w in enumerate(weeks) for d in w["contributionDays"] if d["contributionCount"]}
    colunas = len(weeks)
    pos, passos, revela = (-1, 3), [(-1, 3)], {}

    def rota(teto):
        """Busca em largura até o dia mais próximo do nível `teto`, com desempates aleatórios."""
        antes, fila = {pos: None}, [pos]
        for atual in fila:
            if nivel.get(atual) == teto:
                trecho = []
                while atual != pos:
                    trecho.append(atual)
                    atual = antes[atual]
                return trecho[::-1]
            vizinhos = [(atual[0] + dc, atual[1] + dr) for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            rng.shuffle(vizinhos)
            for q in vizinhos:
                if q not in antes and -1 <= q[0] <= colunas and -1 <= q[1] <= 7 and nivel.get(q, -1) <= teto:
                    antes[q] = atual
                    fila.append(q)
        return None

    for teto in range(len(ORDEM)):
        while teto in nivel.values():
            trecho = rota(teto)
            if trecho is None:  # cercado por dias mais fortes: atravessa por cima
                guardado, nivel = nivel, {q: teto for q in nivel}
                trecho = rota(teto)
                nivel = guardado
            for q in trecho:
                passos.append(q)
                if q in nivel:
                    del nivel[q]
                    revela[q] = len(passos) - 1
            pos = passos[-1]
    passos += [(c, pos[1]) for c in range(pos[0] + 1, colunas + 2)]  # sai pela direita
    return passos, revela


def svg(cal, login):
    weeks = cal["weeks"][-53:]
    W = LEFT + (len(weeks) - 1) * W_PITCH + 56
    H = TOP + 6 * W_PITCH + 46
    rng = random.Random(login)
    passos, revela = caminho(weeks, rng)
    PASSO = min(PASSO_MAX, VARREDURA_MAX / len(passos))
    varredura = len(passos) * PASSO
    DUR = varredura + PAUSA + 1.2
    r1, r2 = (varredura + PAUSA) / DUR, (varredura + PAUSA + 0.8) / DUR

    fundo = "".join(
        f'<circle cx="{rng.uniform(10, W - 10):.0f}" cy="{rng.uniform(10, H - 10):.0f}" '
        f'r="{rng.choice([0.6, 0.9, 1.2])}" fill="{WHITE}" opacity="{rng.uniform(0.12, 0.35):.2f}"/>'
        for _ in range(60))

    rotulos = []
    meses = [date.fromisoformat(w["contributionDays"][-1]["date"]).month for w in weeks]
    for c in range(len(weeks)):
        if (c == 0 and meses[1] == meses[0]) or (c > 0 and meses[c] != meses[c - 1]):
            rotulos.append(f'<text x="{LEFT + c * W_PITCH - 8}" y="{TOP - 24}" fill="{PERI}" '
                           f'font-family="{SANS}" font-size="13">{MESES[meses[c] - 1]}</text>')
    for i, nome in ((1, "seg"), (3, "qua"), (5, "sex")):
        rotulos.append(f'<text x="{LEFT - 22}" y="{TOP + i * W_PITCH + 4.5}" text-anchor="end" fill="{PERI}" '
                       f'font-family="{SANS}" font-size="12">{nome}</text>')

    trilha = [f"{LEFT + c * W_PITCH} {TOP + r * W_PITCH}" for c, r in passos]
    dias = []
    for c, week in enumerate(weeks):
        for day in week["contributionDays"]:
            x, y = LEFT + c * W_PITCH, TOP + day["weekday"] * W_PITCH
            n = day["contributionCount"]
            if n == 0:
                dias.append(f'<circle cx="{x}" cy="{y}" r="1.7" fill="{DIM}" opacity="0.5"/>')
                continue
            tipo = faixa(n)[1]
            f = revela[(c, day["weekday"])] * PASSO / DUR
            a = f + 0.002
            some = f'values="1;1;0;0;1;1" keyTimes="0;{f:.4f};{a:.4f};{r1:.4f};{r2:.4f};1"'
            surge = f'values="0;0;1;1;0;0" keyTimes="0;{f:.4f};{a:.4f};{r1:.4f};{r2:.4f};1"'
            brilho = f'values="0;0;1;0;0" keyTimes="0;{f:.4f};{a:.4f};{min(f + 1.2 / DUR, r1):.4f};1"'
            opcoes = VARIANTES[tipo]
            desenho, ink, raio = astro(opcoes[zlib.crc32(day["date"].encode()) % len(opcoes)])
            dias.append(
                f'<rect x="{x - 6}" y="{y - 6}" width="12" height="12" rx="3" fill="{NORMAL[tipo]}">'
                f'<animate attributeName="opacity" {some} dur="{DUR:.2f}s" repeatCount="indefinite"/></rect>'
                f'<circle cx="{x}" cy="{y}" r="{(raio + 3) * K:.1f}" fill="none" stroke="{WHITE}" stroke-width="1.4" opacity="0">'
                f'<animate attributeName="opacity" {brilho} dur="{DUR:.2f}s" repeatCount="indefinite"/></circle>'
                f'<g opacity="0"><animate attributeName="opacity" {surge} dur="{DUR:.2f}s" repeatCount="indefinite"/>'
                f'<g transform="translate({x} {y}) scale({K})">{desenho}'
                f'<text x="0" y="5" text-anchor="middle" fill="{ink}" font-family="{SANS}" '
                f'font-size="{14.5 if n < 100 else 11}" font-weight="700">{n}</text></g></g>')

    # bolinha que percorre a grade, com um rastro de pontos que vai sumindo
    ultimo = trilha[-1]
    valores = ";".join(trilha + [ultimo])
    tempos = ";".join(f"{i * PASSO / DUR:.5f}" for i in range(len(trilha))) + ";1"
    vis = f'values="0;1;1;0;0" keyTimes="0;0.003;{varredura / DUR:.4f};{(varredura + 0.6) / DUR:.4f};1"'
    bolinha = []
    for k, (raio, op) in enumerate(((5, 1), (3.6, 0.7), (2.8, 0.5), (2.1, 0.32), (1.5, 0.18))):
        corpo = (f'<circle r="12" fill="url(#halo)"/><circle r="{raio}" fill="{WHITE}"/>' if k == 0
                 else f'<circle r="{raio}" fill="{PALE}" opacity="{op}"/>')
        atraso = f'begin="{k * PASSO * 1.1:.2f}s"'
        bolinha.insert(0,
            f'<g opacity="0"><animate attributeName="opacity" {vis} dur="{DUR:.2f}s" {atraso} repeatCount="indefinite"/>'
            f'<g transform="translate({trilha[0]})"><animateTransform attributeName="transform" type="translate" '
            f'values="{valores}" keyTimes="{tempos}" dur="{DUR:.2f}s" {atraso} repeatCount="indefinite"/>{corpo}</g></g>')

    total = cal["totalContributions"]
    total_txt = f"{total:,}".replace(",", ".")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Constelação de contribuições de {login}: {total_txt} contribuições no último ano">
  <title>Constelação de contribuições de {login}</title>
  <defs>
    <clipPath id="card"><rect width="{W}" height="{H}" rx="18"/></clipPath>
    {defs_astros()}
    <radialGradient id="halo"><stop offset="0" stop-color="{WHITE}" stop-opacity="0.7"/><stop offset="1" stop-color="{WHITE}" stop-opacity="0"/></radialGradient>
  </defs>
  <g clip-path="url(#card)">
    <rect width="{W}" height="{H}" fill="{BASE}"/>
    {fundo}
    <text x="{LEFT - 22}" y="54" fill="{WHITE}" font-family="{SERIF}" font-size="28">{total_txt} contribuições no último ano</text>
    {"".join(rotulos)}
    {"".join(dias)}
    {"".join(bolinha)}
  </g>
  <rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="17.5" fill="none" stroke="{LINE}" stroke-width="1.5"/>
</svg>
"""


def main():
    login, saida = sys.argv[1], sys.argv[2]
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("Defina GITHUB_TOKEN para consultar o calendário de contribuições.")
    conteudo = svg(calendario(login, token), login)
    os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
    with open(saida, "w", encoding="utf-8") as fh:
        fh.write(conteudo)
    print(f"{saida}: {len(conteudo)} bytes")


if __name__ == "__main__":
    main()
