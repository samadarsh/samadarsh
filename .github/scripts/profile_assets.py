"""Render the profile README images (banner, project cards, terminal, activity strip)
as light and dark SVGs. Stats come from the GitHub REST API."""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

USER = os.environ.get("GITHUB_USER", "samadarsh")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_DIR = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")

NAME = "Adarsh"
TITLE = "AI Engineer"
TAGLINE = "Building LLM apps, RAG pipelines and production ML systems."
PROJECTS = [
    ("RepoMind", "Map-reduce LLM pipeline that explains", "any GitHub repository."),
    ("fin-sight", "RAG over financial filings with", "page-level citations."),
    ("VoiceNote-AI", "Tamil speech-to-text with Whisper and", "a custom romanizer."),
]
RAG_COMMAND = 'python rag.py "what does adarsh do?"'
RAG_ANSWER = [
    "Builds LLM applications end to end:",
    "data ingestion, retrieval, prompting,",
    "APIs and deployment.",
]
DISPLAY_NAMES = {"fin-sight": "Fin-Sight", "VoiceNote-AI": "VoiceNote AI"}
LANGUAGE_COLORS = {"Python": "#3572A5", "TypeScript": "#3178C6", "JavaScript": "#F1E05A"}

THEMES = {
    "light": {
        "bg": "#ffffff", "hero_a": "#f6f8fa", "hero_b": "#fbf1e8", "border": "#d0d7de",
        "fg": "#1f2328", "muted": "#59636e", "accent": "#bc4c00", "net": "#bc4c00", "net_op": ".22",
    },
    "dark": {
        "bg": "#0d1117", "hero_a": "#1a1511", "hero_b": "#0d1117", "border": "#30363d",
        "fg": "#e6edf3", "muted": "#9198a1", "accent": "#f0883e", "net": "#f0883e", "net_op": ".28",
    },
}
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        if err.code == 409:  # empty repository
            return []
        raise


def svg(width, height, label, body, css=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label, {chr(34): "&quot;"})}">'
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


def terminal(c, repos):
    """A mini RAG session about the profile; the answer streams in word by word."""
    w = 860
    prompt_y = 146 + len(RAG_ANSWER) * 22 + 10
    h = prompt_y + 22
    words = [line.split() for line in RAG_ANSWER]
    start, per_word = 1.6, 0.07
    answer, n = [], 0
    for i, line in enumerate(words):
        spans = []
        for word in line:
            spans.append(f'<tspan class="t" style="animation-delay:{start + n * per_word:.2f}s">{escape(word)}</tspan>')
            n += 1
        prefix = f'<tspan fill="{c["accent"]}">→ </tspan>' if i == 0 else "  "
        answer.append(
            f'<text x="24" y="{146 + i * 22}" font-size="14" class="mono" fill="{c["fg"]}" xml:space="preserve">'
            f'{prefix}{" ".join(spans)}</text>'
        )
    steps = [
        ("[retrieve]", f"{repos} repos indexed · 3 chunks retrieved", 94, 0.5),
        ("[generate]", "streaming...", 118, 1.1),
    ]
    step_rows = "".join(
        f'<text x="24" y="{y}" font-size="14" class="mono l" style="animation-delay:{d}s" xml:space="preserve">'
        f'<tspan fill="{c["accent"]}">{tag}</tspan>  <tspan fill="{c["muted"]}">{escape(text)}</tspan></text>'
        for tag, text, y, d in steps
    )
    dots = "".join(
        f'<circle cx="{22 + i * 18}" cy="17" r="5.5" fill="{color}"/>'
        for i, color in enumerate(("#ff5f57", "#febc2e", "#28c840"))
    )
    end = start + n * per_word
    body = (
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="10" fill="{c["bg"]}" stroke="{c["border"]}"/>'
        f'<line x1="0" x2="{w}" y1="34" y2="34" stroke="{c["border"]}"/>{dots}'
        f'<text x="{w / 2}" y="22" font-size="12" class="mono" text-anchor="middle" fill="{c["muted"]}">{USER.lower()} — zsh</text>'
        f'<text x="24" y="66" font-size="14" class="mono"><tspan fill="{c["accent"]}">~ $ </tspan>'
        f'<tspan fill="{c["fg"]}">{escape(RAG_COMMAND)}</tspan></text>'
        f"{step_rows}{''.join(answer)}"
        f'<text x="24" y="{prompt_y}" font-size="14" class="mono l" style="animation-delay:{end + 0.3:.2f}s" fill="{c["accent"]}">'
        f'~ $ <tspan class="cur">█</tspan></text>'
    )
    css = (
        ".l{animation:in .4s ease-out both}@keyframes in{from{opacity:0}to{opacity:1}}"
        ".t{animation:tok .2s ease-out both}@keyframes tok{from{fill-opacity:0}to{fill-opacity:1}}"
        ".cur{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}"
        "@media (prefers-reduced-motion:reduce){.l,.t,.cur{animation:none}}"
    )
    label = f"$ {RAG_COMMAND} — retrieved from {repos} repos; answer: {' '.join(RAG_ANSWER)}"
    return svg(w, h, label, body, css)


def collect_stats():
    """Public, non-fork repo count, and the user's own commits per week on each
    default branch over the last 52 weeks (weeks start Sunday, UTC)."""
    now = datetime.now(timezone.utc)
    first = (now - timedelta(days=(now.weekday() + 1) % 7, weeks=51)).replace(hour=0, minute=0, second=0, microsecond=0)
    since = first.strftime("%Y-%m-%dT%H:%M:%SZ")
    weeks = [0] * 52

    repos = [r for r in api(f"/users/{USER}/repos?type=owner&per_page=100") or [] if not r["fork"]]
    for repo in repos:
        if not repo["size"]:
            continue
        for page in range(1, 11):
            commits = api(f"/repos/{repo['full_name']}/commits?author={USER}&since={since}&per_page=100&page={page}")
            for c in commits:
                date = datetime.fromisoformat(c["commit"]["author"]["date"].replace("Z", "+00:00"))
                index = (date - first).days // 7
                if 0 <= index < 52:
                    weeks[index] += 1
            if len(commits) < 100:
                break
    return {"weeks": weeks, "repos": len(repos)}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    languages = {name: (api(f"/repos/{USER}/{name}") or {}).get("language") or "Python" for name, *_ in PROJECTS}
    stats = collect_stats()

    for theme, c in THEMES.items():
        suffix = "" if theme == "light" else "-dark"
        (OUT_DIR / f"banner{suffix}.svg").write_text(banner(c))
        (OUT_DIR / f"terminal{suffix}.svg").write_text(terminal(c, stats["repos"]))
        (OUT_DIR / f"activity{suffix}.svg").write_text(activity(c, stats["weeks"]))
        for name, *lines in PROJECTS:
            label = DISPLAY_NAMES.get(name, name)
            (OUT_DIR / f"card-{name.lower()}{suffix}.svg").write_text(card(c, label, lines, languages[name]))
    print(f"{sum(stats['weeks'])} commits in the last 52 weeks; {stats}")


if __name__ == "__main__":
    main()
