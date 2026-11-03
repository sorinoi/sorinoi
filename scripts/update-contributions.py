
#!/usr/bin/env python3
"""SORIN.exe — GitHub Contribution Matrix Generator."""

import html
import json
import os
import urllib.request
from pathlib import Path

TOKEN = os.environ["CONTRIBUTIONS_TOKEN"]
USERNAME = os.environ.get("PROFILE_USERNAME", "sorinoi")

WIDTH = 1475
HEIGHT = 365
BACKGROUND = "#0b0921"
COLORS = [
    "#211936",
    "#433066",
    "#7540b3",
    "#b45af1",
    "#22d3ee",
]

LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

QUERY = """
query($login: String!) {
  user(login: $login) {
    login
    contributionsCollection {
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
            weekday
          }
        }
      }
    }
  }
}
"""


def fetch_calendar():
    payload = json.dumps({
        "query": QUERY,
        "variables": {"login": USERNAME},
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
            "User-Agent": "SORIN.exe-Contribution-Matrix",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)

    if result.get("errors"):
        raise RuntimeError("GitHub GraphQL returned errors")

    user = (result.get("data") or {}).get("user")
    if not user or user["login"].lower() != USERNAME.lower():
        raise RuntimeError("GitHub account verification failed")

    return user["contributionsCollection"]


def render_svg(collection):
    calendar = collection["contributionCalendar"]
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]
    restricted = collection["restrictedContributionsCount"]

    if not 52 <= len(weeks) <= 54:
        raise ValueError("Unexpected contribution calendar length")

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" '
        f'fill="{BACKGROUND}"/>',
        '<rect x="16" y="16" width="1443" height="333" '
        'rx="8" fill="#13102d"/>',
        '<text x="48" y="64" fill="#22d3ee" '
        'font-family="monospace" font-size="27" '
        'font-weight="bold">CONTRIBUTION MATRIX</text>',
        '<text x="1425" y="64" text-anchor="end" '
        'fill="#c084fc" font-family="monospace" '
        'font-size="18">LAST 12 MONTHS</text>',
        f'<text x="48" y="105" fill="#e9d5ff" '
        f'font-family="monospace" font-size="24">'
        f'{total:,} CONTRIBUTIONS</text>',
        '<text x="1425" y="105" text-anchor="end" '
        'fill="#a78bfa" font-family="monospace" '
        'font-size="16">PUBLIC + ELIGIBLE PRIVATE ACTIVITY</text>',
    ]

    cell = 15
    gap = 6
    start_x = 155
    start_y = 137

    for week_index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            level = LEVELS[day["contributionLevel"]]
            x = start_x + week_index * (cell + gap)
            y = start_y + day["weekday"] * (cell + gap)
            date = html.escape(day["date"])
            count = int(day["contributionCount"])

            parts.append(
                f'<rect x="{x}" y="{y}" '
                f'width="{cell}" height="{cell}" rx="2" '
                f'fill="{COLORS[level]}">'
                f'<title>{date}: {count} contributions</title>'
                '</rect>'
            )

    parts.extend([
        '<text x="48" y="309" fill="#a78bfa" '
        'font-family="monospace" font-size="16">'
        'LESS</text>',
    ])

    for i, color in enumerate(COLORS):
        parts.append(
            f'<rect x="{105 + i * 24}" y="295" '
            f'width="15" height="15" fill="{color}"/>'
        )

    parts.extend([
        '<text x="240" y="309" fill="#a78bfa" '
        'font-family="monospace" font-size="16">'
        'MORE</text>',
        '<text x="1425" y="309" text-anchor="end" '
        'fill="#94a3b8" font-family="monospace" '
        'font-size="15">SOURCE: GITHUB GRAPHQL API</text>',
        '</svg>',
    ])

    print(f"Total contributions: {total}")
    print(f"Restricted contributions: {restricted}")
    print(f"Calendar weeks: {len(weeks)}")

    return "\n".join(parts)


def main():
    collection = fetch_calendar()
    svg = render_svg(collection)

    output = Path("assets/contribution-matrix.svg")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")

    print(f"Generated: {output}")


if __name__ == "__main__":
    main()
