"""Rewrite the "Recent activity" block in README.md with the latest commits
across the owner's public repositories."""

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

USER = os.environ.get("GITHUB_USER", "samadarsh")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = Path(__file__).resolve().parents[2] / "README.md"
START = "<!-- recent-activity:start -->"
END = "<!-- recent-activity:end -->"
MAX_ITEMS = 5
MAX_REPOS = 8
PER_REPO = 2

# Default messages from GitHub's web editor ("Update README.md", "Delete x.py")
# and README-only edits say little about the work, so they are skipped.
NOISE = re.compile(r"^(Update|Create|Delete|Add files via upload)\b(\s+\S+)?$|readme", re.I)


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def recent_repos():
    repos = api(f"/users/{USER}/repos?type=owner&sort=pushed&per_page=30")
    return [
        r for r in repos
        if not r["fork"] and not r["archived"] and r["name"].lower() != USER.lower()
    ][:MAX_REPOS]


def repo_commits(repo):
    try:
        return api(f"/repos/{repo['full_name']}/commits?author={USER}&per_page=20")
    except urllib.error.HTTPError as err:
        if err.code == 409:  # empty repository
            return []
        raise


def recent_commits(repos):
    commits = []
    for repo in repos:
        kept = 0
        for c in repo_commits(repo):
            message = c["commit"]["message"].splitlines()[0].strip()
            if len(c["parents"]) > 1 or NOISE.search(message):
                continue
            if kept == PER_REPO:
                break
            kept += 1
            commits.append({
                "repo": repo["name"],
                "repo_url": repo["html_url"],
                "sha": c["sha"][:7],
                "url": c["html_url"],
                "message": message.rstrip("."),
                "date": datetime.fromisoformat(c["commit"]["author"]["date"].replace("Z", "+00:00")),
            })
    commits.sort(key=lambda c: c["date"], reverse=True)
    return commits[:MAX_ITEMS]


def escape(text):
    return re.sub(r"([\\`*_\[\]<>])", r"\\\1", text)


def render(commits):
    lines = [
        f"- [`{c['sha']}`]({c['url']}) {escape(c['message'])} · "
        f"[{c['repo']}]({c['repo_url']}) · {c['date']:%b} {c['date'].day}, {c['date'].year}"
        for c in commits
    ]
    return "\n".join(lines) or "_No recent activity._"


def main():
    readme = README.read_text()
    block = f"{START}\n{render(recent_commits(recent_repos()))}\n{END}"
    updated = re.sub(f"{re.escape(START)}.*?{re.escape(END)}", lambda _: block, readme, flags=re.S)
    if updated != readme:
        README.write_text(updated)
        print("README updated")
    else:
        print("No changes")


if __name__ == "__main__":
    main()
