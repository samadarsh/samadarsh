"""Render the profile README images (banner, project cards, activity strip) as
light and dark SVGs. Project languages and weekly commits come from the GitHub API."""

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

USER = os.environ.get("GITHUB_USER", "samadarsh")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_DIR = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")

NAME = "Adarsh"
TITLE = "AI Engineer"
TAGLINE = "LLMs, RAG and production ML, applied to finance."
PROJECTS = [
    ("RepoMind", "Map-reduce LLM pipeline that explains", "any GitHub repository."),
    ("fin-sight", "RAG over financial filings with", "page-level citations."),
    ("VoiceNote-AI", "Tamil speech-to-text with Whisper and", "a custom romanizer."),
]
DISPLAY_NAMES = {"fin-sight": "Fin-Sight", "VoiceNote-AI": "VoiceNote AI"}
LANGUAGE_COLORS = {"Python": "#3572A5", "TypeScript": "#3178C6", "JavaScript": "#F1E05A"}

THEMES = {
    "light": {
        "bg": "#ffffff", "hero_a": "#f6f8fa", "hero_b": "#eef3fa", "border": "#d0d7de",
        "fg": "#1f2328", "muted": "#59636e", "accent": "#0969da", "net": "#0969da", "net_op": ".22",
    },
    "dark": {
        "bg": "#0d1117", "hero_a": "#0f1624", "hero_b": "#0d1117", "border": "#30363d",
        "fg": "#e6edf3", "muted": "#9198a1", "accent": "#4493f8", "net": "#4493f8", "net_op": ".28",
    },
}
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"


def api(path, retries=8):
    """GET a REST endpoint. Stats endpoints answer 202 while GitHub computes them."""
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    for _ in range(retries):
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status != 202:
                return json.load(resp)
        time.sleep(3)
    return None


def svg(width, height, label, body, css=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label)}">'
        f"<style>text{{font-family:{SANS}}}.mono{{font-family:{MONO}}}{css}</style>{body}</svg>"
    )


def banner(c):
    w, h = 860, 200
    layers = [3, 5, 5, 2]
    points = [
        [(560 + li * 82, 100 + (i - (n - 1) / 2) * 30) for i in range(n)]
        for li, n in enumerate(layers)
    ]
    edges = "".join(
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'
        for a, b in zip(points, points[1:]) for x1, y1 in a for x2, y2 in b
    )
    nodes = "".join(
        f'<circle cx="{x}" cy="{y}" r="5" style="animation-delay:{li * 0.4 + i * 0.15:.2f}s"/>'
        for li, layer in enumerate(points) for i, (x, y) in enumerate(layer)
    )
    body = (
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{c["hero_a"]}"/><stop offset="1" stop-color="{c["hero_b"]}"/>'
        f'</linearGradient></defs>'
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="12" fill="url(#g)" stroke="{c["border"]}"/>'
        f'<g stroke="{c["net"]}" stroke-opacity="{c["net_op"]}">{edges}</g>'
        f'<g fill="{c["accent"]}" class="n">{nodes}</g>'
        f'<text x="40" y="86" font-size="44" font-weight="700" letter-spacing="-.5" fill="{c["fg"]}">{NAME}</text>'
        f'<text x="42" y="120" font-size="16" font-weight="600" class="mono" fill="{c["accent"]}">{TITLE}</text>'
        f'<text x="42" y="150" font-size="14" fill="{c["muted"]}">{escape(TAGLINE)}</text>'
    )
    css = (
        ".n circle{animation:p 3.2s ease-in-out infinite}"
        "@keyframes p{0%,100%{opacity:.35}50%{opacity:1}}"
        "@media (prefers-reduced-motion:reduce){.n circle{animation:none}}"
    )
    return svg(w, h, f"{NAME}, {TITLE}. {TAGLINE}", body, css)


def card(c, name, lines, language):
    w, h = 280, 120
    color = LANGUAGE_COLORS.get(language, c["muted"])
    desc = "".join(
        f'<text x="16" y="{56 + i * 19}" font-size="13" fill="{c["muted"]}">{escape(line)}</text>'
        for i, line in enumerate(lines)
    )
    body = (
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="8" fill="{c["bg"]}" stroke="{c["border"]}"/>'
        f'<text x="16" y="30" font-size="14" font-weight="600" fill="{c["accent"]}">{escape(name)}</text>'
        f"{desc}"
        f'<circle cx="20.5" cy="98" r="4.5" fill="{color}"/>'
        f'<text x="31" y="102" font-size="12" fill="{c["muted"]}">{escape(language)}</text>'
    )
    return svg(w, h, f"{name}: {' '.join(lines)}", body)


def activity(c, weeks):
    w, h = 860, 96
    top, bottom, slot = 28, 88, w / len(weeks)
    peak = max(weeks) or 1
    bars = []
    for i, v in enumerate(weeks):
        bh = max(2, (bottom - top) * v / peak) if v else 2
        fill, opacity = (c["accent"], 0.35 + 0.65 * v / peak) if v else (c["border"], 1)
        bars.append(
            f'<rect x="{i * slot + 2:.1f}" y="{bottom - bh:.1f}" width="{slot - 4:.1f}" '
            f'height="{bh:.1f}" rx="2" fill="{fill}" fill-opacity="{opacity:.2f}"/>'
        )
    total = sum(weeks)
    body = (
        f'<text x="0" y="14" font-size="13" font-weight="600" fill="{c["fg"]}">{total} commits</text>'
        f'<text x="{w}" y="14" font-size="12" class="mono" text-anchor="end" fill="{c["muted"]}">last 52 weeks</text>'
        + "".join(bars)
        + f'<line x1="0" x2="{w}" y1="{bottom + 4}" y2="{bottom + 4}" stroke="{c["border"]}"/>'
    )
    return svg(w, h, f"{total} commits in the last 52 weeks", body)


def weekly_commits():
    """Commits by USER per week (weeks start Sunday, UTC) over the last 52 weeks."""
    now = datetime.now(timezone.utc)
    this_week = (now - timedelta(days=(now.weekday() + 1) % 7)).replace(hour=0, minute=0, second=0, microsecond=0)
    starts = [int((this_week - timedelta(weeks=51 - i)).timestamp()) for i in range(52)]
    index = {s: i for i, s in enumerate(starts)}
    weeks = [0] * 52

    repos = api(f"/users/{USER}/repos?type=owner&per_page=100") or []
    for repo in repos:
        if repo["fork"] or not repo["size"]:
            continue
        stats = api(f"/repos/{repo['full_name']}/stats/contributors")
        if stats is None:
            print(f"warning: stats not ready for {repo['full_name']}, skipped")
            continue
        for entry in stats or []:
            if (entry.get("author") or {}).get("login", "").lower() != USER.lower():
                continue
            for week in entry["weeks"]:
                if week["w"] in index:
                    weeks[index[week["w"]]] += week["c"]
    return weeks


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    languages = {name: (api(f"/repos/{USER}/{name}") or {}).get("language") or "Python" for name, *_ in PROJECTS}
    weeks = weekly_commits()

    for theme, c in THEMES.items():
        suffix = "" if theme == "light" else "-dark"
        (OUT_DIR / f"banner{suffix}.svg").write_text(banner(c))
        (OUT_DIR / f"activity{suffix}.svg").write_text(activity(c, weeks))
        for name, *lines in PROJECTS:
            label = DISPLAY_NAMES.get(name, name)
            (OUT_DIR / f"card-{name.lower()}{suffix}.svg").write_text(card(c, label, lines, languages[name]))
    print(f"{sum(weeks)} commits in the last 52 weeks; languages: {languages}")


if __name__ == "__main__":
    main()
