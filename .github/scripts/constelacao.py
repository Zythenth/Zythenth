"""Gera a constelação de contribuições do perfil em SVG.

Cada dia do último ano vira um astro que cresce com o número de contribuições
(cometa, planeta, sol, estrela gigante e buraco negro), com o número escrito dentro, e um cometa atravessa o céu acendendo os dias por onde passa.

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

W = 1000
PITCH = 32
LEFT = 84
DUR = 18  # segundos de uma volta completa do cometa


def calendario(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "constelacao"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise SystemExit(f"Erro da API do GitHub: {data['errors']}")
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


FAIXAS = [  # (mínimo de contribuições no dia, astro, nome na legenda)
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


def bloco(weeks, top, fase0, rng):
    """Desenha um semestre: rótulos de mês e dias, estrelas e o brilho quando o cometa passa."""
    x0, x1 = LEFT - 40, LEFT + 26 * PITCH + 40
    out = []
    meses = [date.fromisoformat(w["contributionDays"][-1]["date"]).month for w in weeks]
    for c, week in enumerate(weeks):
        x = LEFT + c * PITCH
        novo = c == 0 or meses[c] != meses[c - 1]
        espremido = c == 0 and len(meses) > 2 and meses[1] != meses[0]
        if novo and not espremido:
            out.append(f'<text x="{x - 10}" y="{top - 22}" fill="{PERI}" font-family="{SANS}" font-size="13">'
                       f'{MESES[meses[c] - 1]}</text>')
        f = fase0 + 0.46 * (x - x0) / (x1 - x0)
        for day in week["contributionDays"]:
            y = top + day["weekday"] * PITCH
            n = day["contributionCount"]
            if n == 0:
                out.append(f'<circle cx="{x}" cy="{y}" r="2" fill="{DIM}" opacity="0.55"/>')
                continue
            desenho, ink, brilho = astro(faixa(n)[1], x, y)
            a, b, e = max(f - 0.006, 0.001), f + 0.004, min(f + 0.07, 0.999)
            out.append(
                f'<circle cx="{x}" cy="{y}" r="{brilho + 3}" fill="none" stroke="{WHITE}" stroke-width="1.6" opacity="0">'
                f'<animate attributeName="opacity" values="0;0;0.95;0;0" keyTimes="0;{a:.4f};{b:.4f};{e:.4f};1" '
                f'dur="{DUR}s" repeatCount="indefinite"/></circle>'
                + desenho +
                f'<text x="{x}" y="{y + 4.2:.1f}" text-anchor="middle" fill="{ink}" font-family="{SANS}" '
                f'font-size="{11.5 if n < 100 else 9}" font-weight="700">{n}</text>')
    for i, nome in ((1, "seg"), (3, "qua"), (5, "sex")):
        out.append(f'<text x="{LEFT - 30}" y="{top + i * PITCH + 4.5}" text-anchor="end" fill="{PERI}" '
                   f'font-family="{SANS}" font-size="12">{nome}</text>')
    return "".join(out)


def cometa(top, fase0):
    """Cometa que cruza o semestre na altura da quarta-feira e some no fim."""
    y = top + 3 * PITCH
    x0, x1 = LEFT - 40, LEFT + 26 * PITCH + 40
    if fase0 == 0:
        mov, kt = f"0 0;{x1 - x0} 0;{x1 - x0} 0", "0;0.46;1"
        op, okt = "1;1;0;0", "0;0.45;0.47;1"
    else:
        mov, kt = f"0 0;0 0;{x1 - x0} 0;{x1 - x0} 0", "0;0.5;0.96;1"
        op, okt = "0;0;1;1;0;0", "0;0.49;0.5;0.95;0.97;1"
    return (f'<g opacity="0"><animate attributeName="opacity" values="{op}" keyTimes="{okt}" dur="{DUR}s" '
            f'repeatCount="indefinite"/><g><animateTransform attributeName="transform" type="translate" '
            f'values="{mov}" keyTimes="{kt}" dur="{DUR}s" repeatCount="indefinite"/>'
            f'<path d="M {x0},{y - 3.5} L {x0 - 90},{y - 1} L {x0 - 90},{y + 1} L {x0},{y + 3.5} Z" fill="url(#cauda)"/>'
            f'<circle cx="{x0}" cy="{y}" r="11" fill="url(#halo)"/>'
            f'<circle cx="{x0}" cy="{y}" r="4.5" fill="{WHITE}"/></g></g>')


def svg(cal, login):
    weeks = cal["weeks"][-53:]
    metade = len(weeks) - 27
    top1, top2 = 132, 132 + 7 * PITCH + 92
    H = top2 + 6 * PITCH + 92
    rng = random.Random(login)
    fundo = "".join(
        f'<circle cx="{rng.uniform(10, W - 10):.0f}" cy="{rng.uniform(10, H - 10):.0f}" '
        f'r="{rng.choice([0.6, 0.9, 1.2])}" fill="{WHITE}" opacity="{rng.uniform(0.12, 0.35):.2f}"/>'
        for _ in range(70))
    total = cal["totalContributions"]
    total_txt = f"{total:,}".replace(",", ".")
    legenda_y = H - 34
    legenda, lx = [], LEFT - 16
    for minimo, tipo, nome in reversed(FAIXAS):
        prox = next((m for m, _, _ in reversed(FAIXAS) if m > minimo), None)
        faixa_txt = f"{minimo}+" if prox is None else (f"{minimo}" if prox - 1 == minimo else f"{minimo}–{prox - 1}")
        desenho, _, _ = astro(tipo, lx, legenda_y)
        legenda.append(desenho + f'<text x="{lx + 22}" y="{legenda_y + 4.5}" fill="{PALE}" font-family="{SANS}" '
                       f'font-size="13">{nome} <tspan fill="{PERI}">{faixa_txt}</tspan></text>')
        lx += 46 + 7.4 * len(f"{nome} {faixa_txt}")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Constelação de contribuições de {login}: {total_txt} contribuições no último ano">
  <title>Constelação de contribuições de {login}</title>
  <defs>
    <clipPath id="card"><rect width="{W}" height="{H}" rx="18"/></clipPath>
    <linearGradient id="cauda" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="{PALE}" stop-opacity="0.9"/><stop offset="1" stop-color="{PERI}" stop-opacity="0"/></linearGradient>
    <linearGradient id="disco" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{PERI}"/><stop offset="0.5" stop-color="{WHITE}"/><stop offset="1" stop-color="{PERI}"/></linearGradient>
    <radialGradient id="halo"><stop offset="0" stop-color="{WHITE}" stop-opacity="0.7"/><stop offset="1" stop-color="{WHITE}" stop-opacity="0"/></radialGradient>
  </defs>
  <g clip-path="url(#card)">
    <rect width="{W}" height="{H}" fill="{BASE}"/>
    <rect y="{H - 64}" width="{W}" height="64" fill="{SHADE}"/>
    {fundo}
    <text x="{LEFT - 30}" y="62" fill="{WHITE}" font-family="{SERIF}" font-size="30">{total_txt} contribuições no último ano</text>
    <rect x="{LEFT - 30}" y="76" width="{W - 2 * (LEFT - 30)}" height="1.2" fill="{LINE}"/>
    {bloco(weeks[:27], top1, 0, rng)}
    {bloco(weeks[27:27 + metade], top2, 0.5, rng)}
    {cometa(top1, 0)}
    {cometa(top2, 0.5)}
    {"".join(legenda)}
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
