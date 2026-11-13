#!/usr/bin/env python3

import json
import os
from html import escape
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USERNAME = "sidshah13"
API_ROOT = "https://api.github.com"
REQUEST_TIMEOUT_SECONDS = 30
USER_AGENT = "sidshah13-profile-stats-generator/1.0"


def api_get(path: str, token: str | None = None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
    }
    if token:
        headers["Authorization"] = "Bearer " + token

    request = Request(f"{API_ROOT}{path}", headers=headers)
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_repositories(token: str | None = None) -> list[dict[str, Any]]:
    repositories: list[dict[str, Any]] = []
    page = 1
    while True:
        batch = api_get(f"/users/{USERNAME}/repos?per_page=100&page={page}", token)
        if not batch:
            break
        repositories.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repositories


def render_github_stats_svg(stats: dict[str, int]) -> str:
    lines = [
        ("Public Repositories", stats["public_repos"]),
        ("Followers", stats["followers"]),
        ("Following", stats["following"]),
        ("Total Stars", stats["stars"]),
    ]
    rows = []
    y = 84
    for label, value in lines:
        rows.append(
            f'<text x="36" y="{y}" fill="#C9D1D9" font-family="Segoe UI, Arial, sans-serif" '
            f'font-size="19">{escape(label)}: <tspan fill="#64D2FF">{value}</tspan></text>'
        )
        y += 44

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="700" height="260" viewBox="0 0 700 260">'
        '<rect width="700" height="260" rx="14" fill="#070B14" stroke="#24324A" />'
        '<text x="36" y="48" fill="#0A84FF" font-family="Segoe UI, Arial, sans-serif" '
        'font-size="26" font-weight="600">GitHub Profile Statistics</text>'
        f'{"".join(rows)}'
        "</svg>"
    )


def render_top_languages_svg(language_counts: list[tuple[str, int]]) -> str:
    rows = []
    top = language_counts[:8]
    max_count = max((count for _, count in top), default=1)
    y = 78
    for language, count in top:
        ratio = count / max_count
        bar_width = max(8, int(350 * ratio))
        rows.append(
            '<g>'
            f'<text x="36" y="{y}" fill="#C9D1D9" font-family="Segoe UI, Arial, sans-serif" '
            f'font-size="17">{escape(language)} <tspan fill="#8B949E">({count})</tspan></text>'
            f'<rect x="250" y="{y - 15}" width="370" height="14" rx="7" fill="#151B23" />'
            f'<rect x="250" y="{y - 15}" width="{bar_width}" height="14" rx="7" fill="#64D2FF" />'
            "</g>"
        )
        y += 34

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="700" height="360" viewBox="0 0 700 360">'
        '<rect width="700" height="360" rx="14" fill="#070B14" stroke="#24324A" />'
        '<text x="36" y="48" fill="#0A84FF" font-family="Segoe UI, Arial, sans-serif" '
        'font-size="26" font-weight="600">Top Languages by Repository Count</text>'
        f'{"".join(rows)}'
        "</svg>"
    )


def write_if_changed(path: Path, content: str) -> None:
    previous = path.read_text(encoding="utf-8") if path.exists() else None
    if previous == content:
        print(f"No changes for {path.as_posix()}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Updated {path.as_posix()}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    stats_path = root / "assets/github-stats.svg"
    languages_path = root / "assets/top-languages.svg"
    token = os.environ.get("GITHUB_TOKEN")

    try:
        user = api_get(f"/users/{USERNAME}", token)
        repos = [repo for repo in fetch_repositories(token) if not repo.get("fork")]
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        if stats_path.exists() and languages_path.exists():
            print(f"Warning: failed to refresh statistics ({exc!s}); keeping existing assets.")
            return
        raise RuntimeError("Failed to fetch repository statistics from GitHub API") from exc

    stats = {
        "public_repos": int(user.get("public_repos", 0)),
        "followers": int(user.get("followers", 0)),
        "following": int(user.get("following", 0)),
        "stars": sum(int(repo.get("stargazers_count", 0)) for repo in repos),
    }

    language_counts: dict[str, int] = {}
    for repo in repos:
        language = repo.get("language")
        if language:
            language_counts[language] = language_counts.get(language, 0) + 1

    sorted_languages = sorted(language_counts.items(), key=lambda item: (-item[1], item[0].lower()))

    write_if_changed(stats_path, render_github_stats_svg(stats))
    write_if_changed(languages_path, render_top_languages_svg(sorted_languages))


if __name__ == "__main__":
    main()
