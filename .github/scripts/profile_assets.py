"""Render the profile README images (banner, link bar, terminal, activity strip)
as light and dark SVGs. Stats come from the GitHub REST API."""

import json
import os
import re
import sys
import textwrap
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
TAGLINE = "Building AI agents, LLM apps, RAG pipelines and production ML systems."
RAG_COMMAND = 'python rag.py "what does adarsh do?"'
RAG_ANSWER = [
    "Builds LLM apps and AI agents end to end:",
    "data ingestion, retrieval, prompting,",
    "APIs and deployment.",
]
STACK_COMMAND = "cat stack.txt"
STACK = ["Python", "PyTorch", "LangChain", "FastAPI", "Docker"]
# Ask-first profile. Suggested questions open prefilled "ask:" issues (see ask_agent.py).
ASK_HEADLINE = ("Don't read about my work.", "Ask it.")
ASK_PLACEHOLDER = "Ask anything about my work or projects"
ASK_SUGGESTIONS = [
    ("fin-sight", "How does Fin-Sight cite its sources?"),
    ("bitewise", "What is BiteWise built on?"),
    ("stack", "What stack does Adarsh use for agents?"),
]
MINI_LINKS = [("portfolio", "portfolio"), ("linkedin", "linkedin"), ("repos", "all repos")]
ANSWER_MARK, ANSWER_END = "<!-- ask-answer -->", "<!-- ask-answer-end -->"
# Link bar sections, left to right: (file slug, icon, label)
LINKS = [("portfolio", "globe", "Portfolio"), ("linkedin", "person", "LinkedIn"), ("email", "mail", "Email")]

THEMES = {
    "light": {
        "bg": "#ffffff", "hero_a": "#f6f8fa", "hero_b": "#fbf1e8", "border": "#d0d7de",
        "fg": "#1f2328", "muted": "#59636e", "accent": "#bc4c00", "net": "#bc4c00", "net_op": ".22",
        "surface": "#f6f8fa", "glow_op": ".22", "glow_op2": ".14",
    },
    "dark": {
        "bg": "#0d1117", "hero_a": "#1a1511", "hero_b": "#0d1117", "border": "#30363d",
        "fg": "#e6edf3", "muted": "#9198a1", "accent": "#f0883e", "net": "#f0883e", "net_op": ".28",
        "surface": "#151b23", "glow_op": ".36", "glow_op2": ".24",
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
        # 409: empty repository. 404: a repo renamed or made private; skip it rather than
        # failing the whole daily render.
        if err.code in (404, 409):
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


def ask_hero(c):
    """Name line, headline and a question box over a slowly drifting glow."""
    w, h = 860, 300
    box_w, box_x, box_y = 620, (860 - 620) / 2, 196
    glow = c["accent"]
    body = (
        '<defs><filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="46"/></filter>'
        f'<clipPath id="clip"><rect width="{w}" height="{h}" rx="14"/></clipPath></defs>'
        f'<g clip-path="url(#clip)"><rect width="{w}" height="{h}" fill="{c["bg"]}"/>'
        f'<ellipse class="g1" cx="300" cy="120" rx="230" ry="110" fill="{glow}" opacity="{c["glow_op"]}" filter="url(#blur)"/>'
        f'<ellipse class="g2" cx="600" cy="190" rx="200" ry="90" fill="{glow}" opacity="{c["glow_op2"]}" filter="url(#blur)"/></g>'
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="14" fill="none" stroke="{c["border"]}"/>'
        f'<text x="{w / 2}" y="58" font-size="15" text-anchor="middle" fill="{c["muted"]}">'
        f'<tspan font-weight="600" fill="{c["fg"]}">{escape(NAME)}</tspan> · {escape(TITLE)}</text>'
        f'<text x="{w / 2}" y="112" font-size="38" font-weight="700" letter-spacing="-.6" text-anchor="middle" fill="{c["fg"]}">'
        f'{escape(ASK_HEADLINE[0])}</text>'
        f'<text x="{w / 2}" y="158" font-size="38" font-weight="700" letter-spacing="-.6" text-anchor="middle" fill="{c["accent"]}">'
        f'{escape(ASK_HEADLINE[1])}</text>'
        f'<rect x="{box_x - 4}" y="{box_y - 4}" width="{box_w + 8}" height="60" rx="15" fill="{c["accent"]}" fill-opacity=".12"/>'
        f'<rect x="{box_x}" y="{box_y}" width="{box_w}" height="52" rx="12" fill="{c["bg"]}" stroke="{c["accent"]}"/>'
        f'<text x="{box_x + 18}" y="{box_y + 32}" font-size="15" class="mono" fill="{c["muted"]}">{escape(ASK_PLACEHOLDER)}'
        f'<tspan class="cur" fill="{c["accent"]}"> ▍</tspan></text>'
        f'<rect x="{box_x + box_w - 74}" y="{box_y + 12}" width="60" height="28" rx="8" fill="{c["accent"]}"/>'
        f'<text x="{box_x + box_w - 44}" y="{box_y + 31}" font-size="12" font-weight="600" text-anchor="middle" fill="{c["bg"]}">Ask ↗</text>'
    )
    css = (
        ".g1{animation:d1 16s ease-in-out infinite alternate}.g2{animation:d2 19s ease-in-out infinite alternate}"
        "@keyframes d1{to{transform:translate(110px,30px)}}@keyframes d2{to{transform:translate(-120px,-30px)}}"
        ".cur{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}"
        "@media (prefers-reduced-motion:reduce){.g1,.g2,.cur{animation:none}}"
    )
    return svg(w, h, f"{NAME}, {TITLE}. {ASK_HEADLINE[0]} {ASK_HEADLINE[1]} Ask a question about my work.", body, css)


def ask_chip(c, text):
    w, h = round(len(text) * 6.8 + 46), 34
    body = (
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{h / 2}" fill="{c["bg"]}" stroke="{c["border"]}"/>'
        f'<text x="16" y="22" font-size="13" fill="{c["fg"]}">{escape(text)}'
        f'<tspan dx="6" fill="{c["muted"]}">↗</tspan></text>'
    )
    return svg(w, h, f"Ask: {text}", body)


def answer_card(c, answer):
    """The latest answer you approved, or an invitation when there is none yet."""
    w = 640
    if answer:
        question = answer["question"] if len(answer["question"]) <= 80 else answer["question"][:77].rsplit(" ", 1)[0] + "…"
        lines = textwrap.wrap(answer["answer"], 78)[:3]
        if len(textwrap.wrap(answer["answer"], 78)) > 3:
            lines[-1] = lines[-1].rstrip(".,;") + "…"
        label = "LATEST ANSWER"
    else:
        question, lines, label = "No questions answered yet.", ["Ask the first one: my agent replies with sources in about a minute."], "ASK ME"
    h = 74 + len(lines) * 19
    rows = "".join(
        f'<text x="16" y="{68 + i * 19}" font-size="13" fill="{c["muted"]}">{escape(line)}</text>' for i, line in enumerate(lines)
    )
    body = (
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="10" fill="{c["surface"]}" stroke="{c["border"]}"/>'
        f'<text x="16" y="24" font-size="11" class="mono" letter-spacing="1" fill="{c["muted"]}">{label}</text>'
        f'<text x="16" y="46" font-size="14" font-weight="600" fill="{c["fg"]}">{escape(question)}</text>{rows}'
    )
    alt = f"Latest answer. Q: {question} A: {' '.join(lines)}" if answer else "No questions answered yet."
    return svg(w, h, alt, body)


def mini_link(c, label):
    w, h = round(len(label) * 7.0 + 30), 28
    body = (f'<text x="6" y="19" font-size="13"><tspan fill="{c["accent"]}">→ </tspan>'
            f'<tspan fill="{c["muted"]}">{escape(label)}</tspan></text>')
    return svg(w, h, label, body)


def latest_answer():
    """Question and answer text of the most recently approved "ask:" issue."""
    try:
        issues = api(f"/repos/{USER}/{USER}/issues?labels=approved&state=all&sort=updated&direction=desc&per_page=5") or []
    except Exception as err:  # never fail the whole build over the answer card
        print(f"warning: could not read approved answers: {err}")
        return None
    for issue in issues:
        for note in api(f"/repos/{USER}/{USER}/issues/{issue['number']}/comments?per_page=50") or []:
            body = note.get("body") or ""
            if note["user"].get("type") == "Bot" and ANSWER_MARK in body and ANSWER_END in body:
                text = body.split(ANSWER_MARK, 1)[1].split(ANSWER_END, 1)[0]
                text = re.sub(r"\s+", " ", re.sub(r"https?://\S+", "", text)).strip()
                question = re.sub(r"^\s*ask\s*:\s*", "", issue["title"], flags=re.I).strip()
                return {"question": question, "answer": text, "number": issue["number"]}
    return None


def icon(kind, x, y, color):
    """16px stroke icons for the link bar."""
    paths = {
        "globe": '<circle cx="8" cy="8" r="6.5"/><ellipse cx="8" cy="8" rx="2.8" ry="6.5"/><path d="M1.5 8h13"/>',
        "person": '<circle cx="8" cy="5.5" r="2.8"/><path d="M2.5 14.5c.6-3 2.8-4.6 5.5-4.6s4.9 1.6 5.5 4.6"/>',
        "mail": '<rect x="1.5" y="3" width="13" height="10" rx="2"/><path d="M2 4.5l6 4.5 6-4.5"/>',
    }
    return (
        f'<g transform="translate({x:.1f},{y})" fill="none" stroke="{color}" stroke-width="1.6" '
        f'stroke-linecap="round" stroke-linejoin="round">{paths[kind]}</g>'
    )


def link_segment(c, kind, label, position, count):
    """One section of the link bar. Sections sit side by side in the README, so only
    the outer ends are rounded, and every section but the last draws a divider."""
    w, h, r, q = 284, 46, 10, 9.5
    if position == 0:
        edge = f"M{w},.5 H{r} A{q},{q} 0 0 0 .5,{r} V{h - r} A{q},{q} 0 0 0 {r},{h - .5} H{w}"
        shape = edge + " Z"
    elif position == count - 1:
        edge = f"M0,.5 H{w - r} A{q},{q} 0 0 1 {w - .5},{r} V{h - r} A{q},{q} 0 0 1 {w - r},{h - .5} H0"
        shape = edge + " Z"
    else:
        edge = f"M0,.5 H{w} M0,{h - .5} H{w}"
        shape = f"M0,0 H{w} V{h} H0 Z"
    divider = "" if position == count - 1 else f'<line x1="{w - .5}" x2="{w - .5}" y1="10" y2="{h - 10}" stroke="{c["border"]}"/>'
    # The arrow rides on the label as a tspan, so its gap never depends on font
    # metrics; only the icon uses the estimated text width.
    text_w = len(label) * 7.6 + 18
    cx = w / 2 + 12
    body = (
        f'<path d="{shape}" fill="{c["bg"]}"/><path d="{edge}" fill="none" stroke="{c["border"]}"/>{divider}'
        + icon(kind, cx - text_w / 2 - 24, 15, c["accent"])
        + f'<text x="{cx:.1f}" y="28" font-size="14" font-weight="600" text-anchor="middle" fill="{c["fg"]}">'
        f'{escape(label)}<tspan dx="6" font-size="13" font-weight="400" fill="{c["muted"]}">↗</tspan></text>'
    )
    return svg(w, h, label, body)


def activity(c, weeks, first):
    """Weekly commit bars in a frame: rounded tops, month labels, the peak week
    labeled and a dashed weekly average. Bars grow in on load."""
    w, h = 860, 200
    x0, x1, top, bottom = 24, w - 24, 58, 156
    slot = (x1 - x0) / len(weeks)
    total, peak = sum(weeks), max(weeks)
    avg = total / len(weeks)
    y = lambda v: bottom - (bottom - top) * v / (peak or 1)

    marks = []
    for i, v in enumerate(weeks):
        x = x0 + i * slot + 1
        if not v:
            marks.append(f'<rect x="{x:.1f}" y="{bottom - 2}" width="{slot - 2:.1f}" height="2" rx="1" fill="{c["border"]}"/>')
            continue
        bh = max(4, bottom - y(v))
        marks.append(
            f'<path class="b" style="animation-delay:{i * 0.015:.2f}s" fill="{c["accent"]}" '
            f'd="M{x:.1f},{bottom} v{-(bh - 3):.1f} q0,-3 3,-3 h{slot - 8:.1f} q3,0 3,3 v{bh - 3:.1f}z"/>'
        )

    labels = []
    if peak:
        ay = y(avg)
        labels.append(f'<line x1="{x0}" x2="{x1}" y1="{ay:.1f}" y2="{ay:.1f}" stroke="{c["muted"]}" stroke-dasharray="3 4" stroke-opacity=".7"/>')
        labels.append(f'<text x="{x0}" y="{ay - 6:.1f}" font-size="11" class="mono" fill="{c["muted"]}">avg {avg:.1f}/wk</text>')
        i = weeks.index(peak)
        date = first + timedelta(weeks=i)
        end = date + timedelta(days=6)
        span = f"{date:%b} {date.day} – {end.day}" if end.month == date.month else f"{date:%b} {date.day} – {end:%b} {end.day}"
        px = min(max(x0 + i * slot + slot / 2, x0 + 70), x1 - 70)
        labels.append(
            f'<text x="{px:.1f}" y="{y(peak) - 8:.1f}" font-size="11" class="mono" text-anchor="middle" '
            f'fill="{c["fg"]}">{peak} · {span}</text>'
        )
    last_month = first.month
    for i in range(1, len(weeks)):
        date = first + timedelta(weeks=i)
        if date.month != last_month:
            labels.append(f'<text x="{x0 + i * slot:.1f}" y="{bottom + 22}" font-size="11" class="mono" fill="{c["muted"]}">{date:%b}</text>')
        last_month = date.month

    body = (
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="10" fill="{c["bg"]}" stroke="{c["border"]}"/>'
        f'<text x="{x0}" y="34" font-size="15" font-weight="600" fill="{c["fg"]}">{total} commits</text>'
        f'<text x="{x1}" y="34" font-size="12" class="mono" text-anchor="end" fill="{c["muted"]}">last 52 weeks</text>'
        + "".join(marks) + "".join(labels)
        + f'<line x1="{x0}" x2="{x1}" y1="{bottom + .5}" y2="{bottom + .5}" stroke="{c["border"]}"/>'
    )
    css = (
        ".b{transform-box:fill-box;transform-origin:bottom;animation:g .6s ease-out both}"
        "@keyframes g{from{transform:scaleY(0)}to{transform:scaleY(1)}}"
        "@media (prefers-reduced-motion:reduce){.b{animation:none}}"
    )
    return svg(w, h, f"{total} commits in the last 52 weeks, peak {peak} in one week", body, css)


def terminal(c, repos):
    """A mini RAG session about the profile; the answer streams in word by word."""
    w = 860
    stack_y = 146 + len(RAG_ANSWER) * 22 + 10
    prompt_y = stack_y + 54
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
    stack_rows = (
        f'<g class="l" style="animation-delay:{end + 0.4:.2f}s">'
        f'<text x="24" y="{stack_y}" font-size="14" class="mono"><tspan fill="{c["accent"]}">~ $ </tspan>'
        f'<tspan fill="{c["fg"]}">{escape(STACK_COMMAND)}</tspan></text>'
        f'<text x="24" y="{stack_y + 22}" font-size="14" class="mono" fill="{c["muted"]}">{escape(" · ".join(STACK))}</text></g>'
    )
    body = (
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="10" fill="{c["bg"]}" stroke="{c["border"]}"/>'
        f'<line x1="0" x2="{w}" y1="34" y2="34" stroke="{c["border"]}"/>{dots}'
        f'<text x="{w / 2}" y="22" font-size="12" class="mono" text-anchor="middle" fill="{c["muted"]}">{USER.lower()} — zsh</text>'
        f'<text x="24" y="66" font-size="14" class="mono"><tspan fill="{c["accent"]}">~ $ </tspan>'
        f'<tspan fill="{c["fg"]}">{escape(RAG_COMMAND)}</tspan></text>'
        f"{step_rows}{''.join(answer)}{stack_rows}"
        f'<text x="24" y="{prompt_y}" font-size="14" class="mono l" style="animation-delay:{end + 0.9:.2f}s" fill="{c["accent"]}">'
        f'~ $ <tspan class="cur">█</tspan></text>'
    )
    css = (
        ".l{animation:in .4s ease-out both}@keyframes in{from{opacity:0}to{opacity:1}}"
        ".t{animation:tok .2s ease-out both}@keyframes tok{from{fill-opacity:0}to{fill-opacity:1}}"
        ".cur{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}"
        "@media (prefers-reduced-motion:reduce){.l,.t,.cur{animation:none}}"
    )
    label = (f"$ {RAG_COMMAND} — retrieved from {repos} repos; answer: {' '.join(RAG_ANSWER)} "
             f"$ {STACK_COMMAND}: {', '.join(STACK)}")
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
    return {"weeks": weeks, "first": first, "repos": len(repos)}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stats = collect_stats()
    answer = latest_answer()

    for theme, c in THEMES.items():
        suffix = "" if theme == "light" else "-dark"
        (OUT_DIR / f"banner{suffix}.svg").write_text(banner(c))
        (OUT_DIR / f"ask-hero{suffix}.svg").write_text(ask_hero(c))
        for slug, text in ASK_SUGGESTIONS:
            (OUT_DIR / f"ask-chip-{slug}{suffix}.svg").write_text(ask_chip(c, text))
        (OUT_DIR / f"ask-answer{suffix}.svg").write_text(answer_card(c, answer))
        for slug, label in MINI_LINKS:
            (OUT_DIR / f"mini-{slug}{suffix}.svg").write_text(mini_link(c, label))
        for i, (slug, kind, label) in enumerate(LINKS):
            (OUT_DIR / f"link-{slug}{suffix}.svg").write_text(link_segment(c, kind, label, i, len(LINKS)))
        (OUT_DIR / f"terminal{suffix}.svg").write_text(terminal(c, stats["repos"]))
        (OUT_DIR / f"activity{suffix}.svg").write_text(activity(c, stats["weeks"], stats["first"]))
    print(f"{sum(stats['weeks'])} commits in the last 52 weeks; latest answer: {answer and answer['number']}")


if __name__ == "__main__":
    main()
