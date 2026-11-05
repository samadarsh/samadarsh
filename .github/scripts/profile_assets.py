"""Render the profile README images as SVGs:

- sky.svg: the sky over Chennai at build time (sun or moon, stars, the Bay of Bengal).
  Sunrise and sunset are calculated for Chennai's coordinates, so no weather API is needed.
- print.svg / print-dark.svg: a daily generative print of concentric rings shaped by the
  user's weekly commits over the last 52 weeks, numbered by the day of the year.
- link-*.svg: small text links in the same style, light and dark.

Stats come from the GitHub REST API. Only the Python standard library is used.
"""

import base64
import json
import math
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
FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

NAME = "Adarsh"
SUBTITLE = "AI Engineer, building agents from Chennai"
ROLE = "AI Engineer"
CITY = "Chennai"
LAT, LON = 13.0827, 80.2707
IST = timezone(timedelta(hours=5, minutes=30))
# The name and subtitle block in the sky image: the sun and moon stay out of it.
TEXT_RIGHT, TEXT_BOTTOM = 400, 130
LINKS = [("portfolio", "portfolio"), ("linkedin", "linkedin"), ("email", "email")]

THEMES = {
    "light": {"paper": "#faf8f3", "border": "#d0d7de", "ink": "#1f2328", "muted": "#59636e", "accent": "#bc4c00"},
    "dark": {"paper": "#161b22", "border": "#30363d", "ink": "#e6edf3", "muted": "#9198a1", "accent": "#f0883e"},
}
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
SERIF = "'Instrument Serif', Georgia, 'Times New Roman', serif"
REDUCED = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"


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
        # failing the whole render.
        if err.code in (404, 409):
            return []
        raise


def svg(width, height, label, body, css=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label, {chr(34): "&quot;"})}">'
        f"<style>.mono{{font-family:{MONO}}}{css}</style>{body}</svg>"
    )


def font_face(family, file, style):
    """Embed a font as a data URI: images on GitHub can't load external fonts."""
    data = base64.b64encode((FONT_DIR / file).read_bytes()).decode()
    return f"@font-face{{font-family:'{family}';font-style:{style};src:url(data:font/woff;base64,{data}) format('woff')}}"


SERIF_FONTS = (font_face("Instrument Serif", "InstrumentSerif-Regular.woff", "normal")
               + font_face("Instrument Serif", "InstrumentSerif-Italic.woff", "italic"))


def rng(seed):
    """Small deterministic generator, so a given day or hour always draws the same picture."""
    state = seed & 0xFFFFFFFF

    def next_value():
        nonlocal state
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        return state / 4294967296

    return next_value


def sun_times(day):
    """Sunrise and sunset in IST hours for Chennai (NOAA approximation, good to a minute or two)."""
    n = day.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1)
    eq = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                   - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    dec = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
           + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    lat = math.radians(LAT)
    ha = math.degrees(math.acos(math.cos(math.radians(90.833)) / (math.cos(lat) * math.cos(dec))
                                - math.tan(lat) * math.tan(dec)))
    rise = (720 - 4 * (LON + ha) - eq + 330) / 60
    set_ = (720 - 4 * (LON - ha) - eq + 330) / 60
    return rise, set_


def clock(hours):
    total = round(hours * 60) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def mix(a, b, t):
    return [round(x + (y - x) * t) for x, y in zip(a, b)]


def hexc(c):
    return "#%02x%02x%02x" % tuple(c)


SKY = {
    "night": ([8, 12, 28], [24, 32, 60]),
    "dawn": ([44, 52, 98], [242, 150, 104]),
    "day": ([86, 150, 214], [196, 226, 245]),
    "dusk": ([52, 40, 92], [240, 120, 70]),
}


def sky_colors(hr, rise, set_):
    def blend(a, b, t):
        return mix(SKY[a][0], SKY[b][0], t), mix(SKY[a][1], SKY[b][1], t)

    if hr < rise - 0.9 or hr > set_ + 1.1:
        return SKY["night"]
    if hr < rise + 0.9:
        t = (hr - (rise - 0.9)) / 1.8
        return blend("night", "dawn", t * 2) if t < 0.5 else blend("dawn", "day", (t - 0.5) * 2)
    if hr > set_ - 0.9:
        t = (hr - (set_ - 0.9)) / 2
        return blend("day", "dusk", t * 2) if t < 0.5 else blend("dusk", "night", (t - 0.5) * 2)
    return SKY["day"]


def sky(now):
    """The sky over the Bay of Bengal at `now` (IST). The sun rises over the sea on the right
    (east), arcs over and sets on the left; at night a crescent moon makes the same trip."""
    w, h = 860, 300
    hz = round(h * 0.74)
    hr = now.hour + now.minute / 60
    rise, set_ = sun_times(now.date())
    top, bot = sky_colors(hr, rise, set_)
    night = hr < rise - 0.3 or hr > set_ + 0.5
    day = (hr - rise) / (set_ - rise)
    is_sun = -0.05 <= day <= 1.05
    rad = h * 0.07

    def place(p, peak):
        """Position along the arc for progress p (0 = east horizon, 1 = west). Over the name
        and subtitle on the left, the arc stays below the text so it never covers it."""
        x = w * (0.88 - 0.76 * p)
        elev = math.sin(math.pi * min(1, max(0, p))) * hz * peak
        clear = hz - (TEXT_BOTTOM + rad + 10)
        cap = clear + max(0.0, min(1.0, (x - TEXT_RIGHT) / 90)) * (hz - clear)
        return x, hz - min(elev, cap) + h * 0.02

    if is_sun:
        bx, by = place(day, 0.78)
    else:
        bx, by = place(((hr - set_ + 24) % 24) / (24 - (set_ - rise)), 0.7)
    light = not night and 0.08 < day < 0.92
    text = "#102030" if light else "#f7f2e8"

    parts = [
        "<defs>",
        f'<clipPath id="r"><rect width="{w}" height="{h}" rx="10"/></clipPath>',
        f'<linearGradient id="air" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{hexc(top)}"/>'
        f'<stop offset="1" stop-color="{hexc(bot)}"/></linearGradient>',
        f'<linearGradient id="sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{hexc(mix(bot, [10, 30, 50], .55))}"/>'
        f'<stop offset="1" stop-color="{hexc(mix(top, [5, 15, 30], .6))}"/></linearGradient>',
    ]
    low = max(0, 1 - abs(day) / 0.12) + max(0, 1 - abs(day - 1) / 0.12)
    glow = "#ffbe78" if low else "#fff0c8"
    parts.append(f'<radialGradient id="glow"><stop offset="0" stop-color="{glow}" stop-opacity=".85"/>'
                 f'<stop offset="1" stop-color="{glow}" stop-opacity="0"/></radialGradient>')
    parts.append(f'<mask id="moon"><circle cx="{bx:.1f}" cy="{by:.1f}" r="{rad * .8:.1f}" fill="#fff"/>'
                 f'<circle cx="{bx + rad * .35:.1f}" cy="{by - rad * .2:.1f}" r="{rad * .7:.1f}" fill="#000"/></mask>')
    parts.append("</defs>")
    parts.append('<g clip-path="url(#r)">')
    parts.append(f'<rect width="{w}" height="{hz}" fill="url(#air)"/>')

    if night:
        r = rng(42)
        stars = []
        for i in range(150):
            op, x, y, big = 0.3 + r() * 0.7, r() * w, r() * hz * 0.95, r() < 0.1
            s = 2 if big else 1
            cls = ' class="tw"' if i % 11 == 0 else ""
            delay = f' style="animation-delay:{(i % 7) * .6:.1f}s"' if cls else ""
            stars.append(f'<rect{cls}{delay} x="{x:.1f}" y="{y:.1f}" width="{s}" height="{s}" fill="#fff" opacity="{op:.2f}"/>')
        parts.append("".join(stars))

    if is_sun:
        parts.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="{rad * 5:.1f}" fill="url(#glow)"/>')
        parts.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="{rad:.1f}" fill="{"#ffb070" if low else "#fff4d6"}"/>')
    else:
        parts.append(f'<rect width="{w}" height="{h}" fill="#f2efe2" mask="url(#moon)"/>')

    parts.append(f'<rect y="{hz}" width="{w}" height="{h - hz}" fill="url(#sea)"/>')
    r2 = rng(7)
    waves = []
    for _ in range(60):
        x, y, ln = r2() * w, hz + 3 + r2() * (h - hz), 8 + r2() * 30
        waves.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{ln:.1f}" height="1" fill="#fff" opacity=".18"/>')
    parts.append("".join(waves))
    shine = "#ffdcaa" if is_sun else "#f0f0e6"
    shine_op = ".35" if is_sun else ".18"
    spread = max(0.2, 1 - abs(by - hz) / hz)
    glints = []
    for i in range(14):
        ww = (24 + i * 3) * spread
        glints.append(f'<rect class="gl" style="animation-delay:{i * .25:.2f}s" x="{bx - ww / 2:.1f}" '
                      f'y="{hz + 4 + i * (h - hz) / 15:.1f}" width="{ww:.1f}" height="1.5" fill="{shine}" opacity="{shine_op}"/>')
    parts.append("".join(glints))
    parts.append("</g>")

    parts.append(f'<text x="43" y="97" font-family="{SERIF}" font-size="64" fill="{text}" letter-spacing="-.5">{escape(NAME)}</text>')
    parts.append(f'<text x="44" y="126" font-family="{SERIF}" font-style="italic" font-size="19" fill="{text}" '
                 f'opacity=".88">{escape(SUBTITLE)}</text>')
    meta1 = f"{LAT:.2f}°N {LON:.2f}°E · sunrise {clock(rise)} · sunset {clock(set_)}"
    meta2 = f"drawn {clock(hr)} IST · redrawn hourly"
    parts.append(f'<g class="mono" font-size="11" fill="#f7f2e8" opacity=".82" text-anchor="end">'
                 f'<text x="830" y="262">{meta1}</text><text x="830" y="279">{meta2}</text></g>')

    css = (SERIF_FONTS
           + ".tw{animation:tw 4s ease-in-out infinite}@keyframes tw{50%{opacity:.15}}"
           + ".gl{animation:gl 3s ease-in-out infinite}@keyframes gl{50%{opacity:.08}}" + REDUCED)
    label = f"{NAME}, {SUBTITLE}. The sky over {CITY} at {clock(hr)} IST."
    return svg(w, h, label, "".join(parts), css)


def smooth(weeks):
    out = []
    for i in range(len(weeks)):
        total = weight = 0
        for k in range(-3, 4):
            wt = 4 - abs(k)
            total += weeks[(i + k) % len(weeks)] * wt
            weight += wt
        out.append(total / weight)
    return out


def rings(weeks, cx, cy, radius, seed, layers=40, points=150):
    """One closed curve per layer. Each curve swells where the year was busiest (52 weeks
    around the circle, clockwise from the top) plus a small wobble from the day's seed."""
    sm = smooth(weeks)
    peak = max(sm) or 1
    r = rng(seed)
    phase = [r() * math.pi * 2 for _ in range(6)]
    freq = [f + int(r() * 3) for f in (2, 3, 5, 7, 9, 11)]
    curves = []
    for j in range(layers):
        t = j / (layers - 1)
        pts = []
        for n in range(points):
            a = n / points * math.pi * 2
            wi = a / (math.pi * 2) * 52
            i0 = int(wi) % 52
            f = wi - int(wi)
            v = (sm[i0] * (1 - f) + sm[(i0 + 1) % 52] * f) / peak
            wobble = sum(math.sin(a * freq[q] + phase[q] + t * (q + 1) * 1.3) / (q + 2) for q in range(6))
            rad = radius * (0.16 + 0.5 * t) + radius * 0.34 * v * t ** 1.4 + radius * 0.03 * wobble * t
            pts.append((cx + math.cos(a - math.pi / 2) * rad, cy + math.sin(a - math.pi / 2) * rad))
        d = "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z"
        curves.append((j, t, d))
    return curves


def daily_print(c, weeks, now):
    w, h = 860, 560
    doy = now.timetuple().tm_yday
    total = sum(weeks)
    paths = []
    for j, t, d in rings(weeks, w / 2, 248, 180, doy * 7919 + now.year):
        hot = j % 9 == 4
        color = c["accent"] if hot else c["ink"]
        op = 0.95 if hot else 0.5 * (0.4 + 0.6 * t)
        width = 1.3 if hot else 0.8
        paths.append(f'<path class="rg" style="animation-delay:{j * .03:.2f}s;--o:{op:.2f}" d="{d}" fill="none" '
                     f'stroke="{color}" stroke-width="{width}" stroke-linejoin="round" opacity="{op:.2f}"/>')
    date = f"{now.day} {now.strftime('%b').upper()} {now.year}"
    body = (
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="10" fill="{c["paper"]}" stroke="{c["border"]}"/>'
        + "".join(paths)
        + f'<text x="{w / 2}" y="486" text-anchor="middle" font-family="{SERIF}" font-style="italic" font-size="24" '
          f'fill="{c["ink"]}">{escape(NAME)}, a year in commits, No. {doy}</text>'
        + f'<text class="mono" x="{w / 2}" y="514" text-anchor="middle" font-size="11" letter-spacing=".5" fill="{c["muted"]}">'
          f'{escape(ROLE.upper())} · {escape(CITY.upper())} · {total} COMMITS OVER 52 WEEKS · DRAWN {date}</text>'
    )
    css = SERIF_FONTS + ".rg{animation:rg .9s ease-out both}@keyframes rg{from{opacity:0}to{opacity:var(--o)}}" + REDUCED
    label = f"{NAME}, a year in commits, No. {doy}: a print of concentric rings shaped by {total} commits over the last 52 weeks."
    return svg(w, h, label, body, css)


def text_link(c, label):
    width = round(len(label) * 7.8 + 4)
    body = (f'<text class="mono" x="2" y="15" font-size="13" fill="{c["ink"]}">{escape(label)}</text>'
            f'<rect x="2" y="20" width="{width - 4}" height="1" fill="{c["accent"]}"/>')
    return svg(width, 24, label, body)


def collect_stats():
    """The user's own commits per week on each default branch over the last 52 weeks
    (weeks start Sunday, UTC), across their public, non-fork repositories."""
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
            for item in commits:
                date = datetime.fromisoformat(item["commit"]["author"]["date"].replace("Z", "+00:00"))
                index = (date - first).days // 7
                if 0 <= index < 52:
                    weeks[index] += 1
            if len(commits) < 100:
                break
    return weeks


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(IST)
    weeks = collect_stats()

    (OUT_DIR / "sky.svg").write_text(sky(now))
    for theme, c in THEMES.items():
        suffix = "" if theme == "light" else "-dark"
        (OUT_DIR / f"print{suffix}.svg").write_text(daily_print(c, weeks, now))
        for slug, label in LINKS:
            (OUT_DIR / f"link-{slug}{suffix}.svg").write_text(text_link(c, label))
    print(f"{sum(weeks)} commits in the last 52 weeks; sky drawn at {now:%H:%M} IST")


if __name__ == "__main__":
    main()
