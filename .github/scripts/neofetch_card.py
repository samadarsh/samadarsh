"""Render a neofetch-style stats card (light and dark SVG) from live GitHub data."""

import json
import os
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

USER = os.environ.get("GITHUB_USER", "samadarsh")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_DIR = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")

# Notebook JSON inflates byte counts far beyond the code it holds.
IGNORED_LANGUAGES = {"Jupyter Notebook"}

ART = [
    r"    /\    ",
    r"   /  \   ",
    r"  / /\ \  ",
    r" / ____ \ ",
    r"/_/    \_\ ",
]

THEMES = {
    "light": {
        "bg": "#ffffff", "border": "#d0d7de", "bar": "#f6f8fa", "text": "#1f2328",
        "muted": "#656d76", "accent": "#0969da", "art": "#1a7f37",
    },
    "dark": {
        "bg": "#0d1117", "border": "#30363d", "bar": "#161b22", "text": "#e6edf3",
        "muted": "#8b949e", "accent": "#58a6ff", "art": "#3fb950",
    },
}
PALETTE = ["#f85149", "#d29922", "#3fb950", "#58a6ff", "#bc8cff", "#39c5cf", "#ff7b72", "#8b949e"]

FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
SIZE, LINE, CHAR = 14, 22, 8.4
WIDTH, PAD, BAR = 720, 24, 36


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def uptime(created, now):
    months = (now.year - created.year) * 12 + now.month - created.month - (now.day < created.day)
    years, months = divmod(max(months, 0), 12)
    parts = [plural(years, "year")] if years else []
    return ", ".join(parts + [plural(months, "month")])


def collect():
    now = datetime.now(timezone.utc)
    user = api(f"/users/{USER}")
    repos = [r for r in api(f"/users/{USER}/repos?type=owner&per_page=100") if not r["fork"]]

    languages = Counter()
    for repo in repos:
        if repo["size"]:
            languages.update(api(f"/repos/{repo['full_name']}/languages"))
    for name in IGNORED_LANGUAGES:
        languages.pop(name, None)
    total = sum(languages.values()) or 1
    shares = [(name, count * 100 / total) for name, count in languages.most_common()]
    top = [(name, share) for name, share in shares if share >= 1][:3]

    query = urllib.parse.quote(f"author:{USER} author-date:>={now.year}-01-01")
    commits = api(f"/search/commits?q={query}&per_page=1")["total_count"]

    created = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
    return [
        ("OS", "GenAI × Finance"),
        ("Host", f"github.com/{USER}"),
        ("Kernel", top[0][0] if top else "Python"),
        ("Uptime", uptime(created, now)),
        ("Packages", f"{plural(len(repos), 'repo')} (public)"),
        ("Commits", f"{commits} in {now.year}"),
        ("Languages", " · ".join(f"{name} {share:.0f}%" for name, share in top)),
    ]


def render(fields, theme):
    c = THEMES[theme]
    info_x = PAD + 13 * CHAR
    top = BAR + PAD + SIZE
    rows = 2 + len(fields)
    prompt_y = top + (rows + 1) * LINE + 4
    height = prompt_y + PAD
    label_width = max(len(label) for label, _ in fields) + 2

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{escape(USER)} GitHub stats">',
        "<style>",
        f"text{{font-family:{FONT};font-size:{SIZE}px;fill:{c['text']};white-space:pre}}",
        f".a{{fill:{c['accent']};font-weight:600}}.m{{fill:{c['muted']}}}.art{{fill:{c['art']};font-weight:700}}",
        ".l{animation:in .35s ease-out both}",
        "@keyframes in{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:none}}",
        ".cur{animation:blink 1s steps(1) infinite}@keyframes blink{50%{opacity:0}}",
        "@media (prefers-reduced-motion:reduce){.l,.cur{animation:none}}",
        "</style>",
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="10" '
        f'fill="{c["bg"]}" stroke="{c["border"]}"/>',
        f'<path d="M0.5 10.5a10 10 0 0 1 10-10h{WIDTH - 21}a10 10 0 0 1 10 10v{BAR - 10}h-{WIDTH - 1}z" '
        f'fill="{c["bar"]}" stroke="{c["border"]}"/>',
    ]
    for i, color in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        out.append(f'<circle cx="{PAD + i * 20}" cy="{BAR / 2}" r="6" fill="{color}"/>')
    out.append(f'<text x="{WIDTH / 2}" y="{BAR / 2 + 5}" text-anchor="middle" class="m">'
               f"{escape(USER)}@github: ~</text>")

    for i, line in enumerate(ART):
        out.append(f'<text x="{PAD}" y="{top + (i + 1) * LINE}" class="art">{escape(line)}</text>')

    header = f"{USER}@github"
    lines = [
        f'<tspan class="a">{escape(USER)}</tspan>@<tspan class="a">github</tspan>',
        f'<tspan class="m">{"-" * len(header)}</tspan>',
    ] + [
        f'<tspan class="a">{escape(label + ":"):<{label_width}}</tspan>{escape(value)}'
        for label, value in fields
    ]
    for i, line in enumerate(lines):
        out.append(f'<text x="{info_x}" y="{top + i * LINE}" class="l" '
                   f'style="animation-delay:{i * 0.12:.2f}s">{line}</text>')

    swatch_y = top + rows * LINE - SIZE + 4
    for i, color in enumerate(PALETTE):
        out.append(f'<rect x="{info_x + i * 26}" y="{swatch_y}" width="22" height="14" rx="2" '
                   f'fill="{color}" class="l" style="animation-delay:{rows * 0.12:.2f}s"/>')

    out.append(f'<text x="{PAD}" y="{prompt_y}"><tspan class="art">{escape(USER)}@github</tspan>'
               f'<tspan class="m">:~$ </tspan><tspan class="cur">█</tspan></text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    fields = collect()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        name = "neofetch.svg" if theme == "light" else "neofetch-dark.svg"
        (OUT_DIR / name).write_text(render(fields, theme))
    for label, value in fields:
        print(f"{label}: {value}")


if __name__ == "__main__":
    main()
