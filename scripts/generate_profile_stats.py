#!/usr/bin/env python3
"""Generate static GitHub profile cards using the GitHub REST API."""
import json
import os
import urllib.request
import urllib.error
from collections import Counter
from html import escape
from pathlib import Path

OWNER = "sidshah13"
API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def api(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "sidshah13-profile-stats",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    request = urllib.request.Request(API + path, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def svg_shell(title, subtitle, body, height=230):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="495" height="{height}" viewBox="0 0 495 {height}" role="img" aria-label="{escape(title)}">
<rect x="1" y="1" width="493" height="{height-2}" rx="15" fill="#070B14" stroke="#24324A" stroke-width="2"/>
<text x="26" y="39" fill="#64D2FF" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="18" font-weight="700">{escape(title)}</text>
<text x="26" y="62" fill="#8B949E" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="11">{escape(subtitle)}</text>
{body}
</svg>'''


def text(x, y, value, size=14, color="#C9D1D9", weight="400"):
    return f'<text x="{x}" y="{y}" fill="{color}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="{size}" font-weight="{weight}">{escape(str(value))}</text>'


def main():
    user = api(f"/users/{OWNER}")
    repos = []
    page = 1
    while True:
        batch = api(f"/users/{OWNER}/repos?type=owner&visibility=public&per_page=100&page={page}&sort=updated")
        if not batch:
            break
        repos.extend(r for r in batch if not r.get("fork") and not r.get("archived"))
        if len(batch) < 100:
            break
        page += 1

    stars = sum(r.get("stargazers_count", 0) for r in repos)
    forks = sum(r.get("forks_count", 0) for r in repos)
    languages = Counter()
    for repo in repos:
        try:
            languages.update(api(f"/repos/{OWNER}/{repo['name']}/languages"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            continue

    metrics = [
        ("PUBLIC REPOSITORIES", len(repos)),
        ("TOTAL STARS", stars),
        ("TOTAL FORKS", forks),
        ("FOLLOWERS", user.get("followers", 0)),
    ]
    body = ""
    positions = [(26, 112), (265, 112), (26, 174), (265, 174)]
    for (label, value), (x, y) in zip(metrics, positions):
        body += text(x, y, label, 10, "#8B949E", "600")
        body += text(x, y + 25, f"{value:,}", 23, "#C9D1D9", "700")
    Path("assets/github-stats.svg").write_text(
        svg_shell("GitHub Statistics", "Public, non-fork repositories · refreshed daily", body, 220),
        encoding="utf-8",
    )

    total = sum(languages.values())
    sorted_languages = languages.most_common(6)
    body = ""
    y = 96
    palette = ["#64D2FF", "#0A84FF", "#5E5CE6", "#30A46C", "#F5A623", "#E879F9"]
    if total:
        for index, (name, amount) in enumerate(sorted_languages):
            pct = amount / total * 100
            body += text(26, y, name, 12, "#C9D1D9", "600")
            body += text(465, y, f"{pct:.1f}%", 12, "#C9D1D9", "600").replace('text x="465"', 'text x="465" text-anchor="end"')
            body += f'<rect x="26" y="{y+10}" width="443" height="7" rx="3.5" fill="#182235"/>'
            body += f'<rect x="26" y="{y+10}" width="{443*pct/100:.2f}" height="7" rx="3.5" fill="{palette[index]}"/>'
            y += 28
    else:
        body += text(26, 112, "Language data is not available yet.", 13)
    Path("assets/top-languages.svg").write_text(
        svg_shell("Most Used Languages", "Aggregated across public, non-fork repositories", body, 270),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
