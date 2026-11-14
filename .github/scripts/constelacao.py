"""Gera a constelação de contribuições do perfil em SVG.

Cada dia do último ano aparece como um commit comum até a bolinha passar por
cima, em zigue-zague como a cobrinha; aí ele vira um astro que cresce com as
contribuições (cometa, planeta, sol, estrela gigante ou buraco negro) e mostra
o número do dia.

Uso: GITHUB_TOKEN=... python constelacao.py <usuario> <arquivo-de-saida.svg>
"""
import json
import os
import random
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


def astro(tipo, x, y):
    """Desenha o astro do dia; devolve (svg, cor do número, raio do brilho)."""
    if tipo == "cometa":
        return (f'<path d="M {x - 4},{y - 7} L {x - 17},{y - 14} L {x - 7},{y - 2} Z" fill="{PERI}" opacity="0.7"/>'
                f'<circle cx="{x}" cy="{y}" r="9" fill="{DIM}"/>', WHITE, 12)
    if tipo == "planeta":
        return (f'<ellipse cx="{x}" cy="{y}" rx="16" ry="4.5" fill="none" stroke="{PALE}" stroke-width="1.8" '
                f'transform="rotate(-20 {x} {y})"/>'
                f'<circle cx="{x}" cy="{y}" r="10" fill="{PERI}"/>', INK, 14)
    if tipo == "sol":
        return raios(x, y, 8, 13, 10.5, 2, PALE, 14) + f'<circle cx="{x}" cy="{y}" r="8.5" fill="{PALE}"/>', INK, 14
    if tipo == "gigante":
        return (f'<circle cx="{x}" cy="{y}" r="17" fill="url(#halo)"/>'
                + raios(x, y, 12, 17.5, 13.5, 2.4, WHITE, 20)
                + f'<circle cx="{x}" cy="{y}" r="11" fill="{WHITE}"/>'
                f'<circle cx="{x}" cy="{y}" r="14" fill="none" stroke="{PERI}" stroke-width="1"/>', INK, 18)
    disco = (f'fill="none" stroke="url(#disco)" stroke-width="3" stroke-dasharray="9 3 3 3" '
             f'transform="rotate(-15 {x} {y})"')
    giro = '<animate attributeName="stroke-dashoffset" from="0" to="-72" dur="2.6s" repeatCount="indefinite"/>'
    return (f'<circle cx="{x}" cy="{y}" r="17" fill="url(#halo)" opacity="0.5"/>'
            f'<ellipse cx="{x}" cy="{y}" rx="19" ry="6" {disco}>{giro}</ellipse>'
            f'<circle cx="{x}" cy="{y}" r="10.5" fill="#05060f" stroke="{WHITE}" stroke-width="1.4"/>', WHITE, 19)


W_PITCH = 22      # distância entre os dias
LEFT = 72         # início da grade, depois dos rótulos dos dias
TOP = 120         # linha do domingo
K = 0.78          # escala dos astros dentro da grade
PASSO = 0.06      # segundos que a bolinha leva de um dia para o próximo
PAUSA = 4         # segundos com tudo revelado antes de recomeçar
NORMAL = {"cometa": "#2e3754", "planeta": "#4a5a86", "sol": "#7187bb", "gigante": "#a9bde6", "buraco": "#d6e0f5"}


def caminho(weeks):
    """Ordem em zigue-zague: desce numa semana, sobe na seguinte, como a cobrinha."""
    pontos = []
    for c, week in enumerate(weeks):
        dias = sorted(week["contributionDays"], key=lambda d: d["weekday"], reverse=c % 2 == 1)
        pontos += [(c, d) for d in dias]
    return pontos


def svg(cal, login):
    weeks = cal["weeks"][-53:]
    W = LEFT + (len(weeks) - 1) * W_PITCH + 56
    H = TOP + 6 * W_PITCH + 46
    pontos = caminho(weeks)
    varredura = len(pontos) * PASSO
    DUR = varredura + PAUSA + 1.2
    r1, r2 = (varredura + PAUSA) / DUR, (varredura + PAUSA + 0.8) / DUR
    rng = random.Random(login)

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

    dias, trilha = [], []
    for i, (c, day) in enumerate(pontos):
        x, y = LEFT + c * W_PITCH, TOP + day["weekday"] * W_PITCH
        trilha.append(f"{x} {y}")
        n = day["contributionCount"]
        if n == 0:
            dias.append(f'<circle cx="{x}" cy="{y}" r="1.7" fill="{DIM}" opacity="0.5"/>')
            continue
        tipo = faixa(n)[1]
        f = i * PASSO / DUR
        a = f + 0.002
        some = f'values="1;1;0;0;1;1" keyTimes="0;{f:.4f};{a:.4f};{r1:.4f};{r2:.4f};1"'
        surge = f'values="0;0;1;1;0;0" keyTimes="0;{f:.4f};{a:.4f};{r1:.4f};{r2:.4f};1"'
        brilho = f'values="0;0;1;0;0" keyTimes="0;{f:.4f};{a:.4f};{min(f + 1.2 / DUR, r1):.4f};1"'
        desenho, ink, raio = astro(tipo, 0, 0)
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
    <linearGradient id="disco" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{PERI}"/><stop offset="0.5" stop-color="{WHITE}"/><stop offset="1" stop-color="{PERI}"/></linearGradient>
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
