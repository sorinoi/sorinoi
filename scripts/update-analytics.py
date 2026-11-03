#!/usr/bin/env python3
"""Refresh pixel-analytics.svg using public GitHub REST endpoints.
No dependencies; GitHub Actions supplies GITHUB_TOKEN. Does not modify existing stats workflow.
"""
import collections
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USERNAME = os.getenv('PROFILE_USERNAME', 'sorinoi')
TOKEN = os.getenv('GITHUB_TOKEN', '')
ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT / 'assets' / 'pixel-analytics.svg'


def request(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'sorin-pixel-profile', 'X-GitHub-Api-Version': '2022-11-28'}
    if TOKEN:
        headers['Authorization'] = f'Bearer {TOKEN}'
    req = urllib.request.Request('https://api.github.com' + path, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)


def all_public_repos():
    repos = []
    for page in range(1, 11):
        batch = request(f'/users/{urllib.parse.quote(USERNAME)}/repos?type=owner&per_page=100&page={page}')
        repos.extend(r for r in batch if not r.get('private'))
        if len(batch) < 100:
            break
    return repos


def main():
    from xml.sax.saxutils import escape
    now = dt.datetime.now(dt.timezone.utc)
    today = now.date()
    counts = [0] * 14
    # Events API only exposes a limited recent public event window (at most 300 events).
    for page in range(1, 4):
        events = request(f'/users/{urllib.parse.quote(USERNAME)}/events/public?per_page=100&page={page}')
        if not events:
            break
        for event in events:
            date = dt.datetime.fromisoformat(event['created_at'].replace('Z', '+00:00')).date()
            delta = (today - date).days
            if 0 <= delta < 14:
                counts[13 - delta] += 1
        if len(events) < 100:
            break

    repos = all_public_repos()
    totals = collections.Counter()
    for repo in repos:
        # Skip forks: language composition of code the user owns/hosts, not upstream mirrors.
        if repo.get('fork'):
            continue
        try:
            languages = request(f"/repos/{urllib.parse.quote(USERNAME)}/{urllib.parse.quote(repo['name'])}/languages")
            totals.update(languages)
        except urllib.error.HTTPError as exc:
            print(f"Warning: could not read languages for {repo['name']}: {exc}", file=sys.stderr)
    languages = totals.most_common(5)

    def txt(x, y, val, size=23, color='#e5e7ff', bold=False, anchor=None):
        return (f'<text x="{x}" y="{y}" font-family="monospace" font-size="{size}" '
                f'font-weight="{"bold" if bold else "normal"}" fill="{color}"'
                + (f' text-anchor="{anchor}"' if anchor else '') + f'>{escape(str(val))}</text>')

    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="1475" height="472" viewBox="0 0 1475 472">',
         '<defs><linearGradient id="panel"><stop stop-color="#13102d"/><stop offset="1" stop-color="#080d1b"/></linearGradient></defs>',
         '<rect width="1475" height="472" fill="#0b0921"/>',
         '<rect x="16" y="16" width="1443" height="440" fill="url(#panel)" stroke="#9d4eff" stroke-width="3"/>',
         '<rect x="23" y="23" width="1429" height="426" fill="none" stroke="#35255c" stroke-width="2"/>',
         '<path d="M16 39V16H39 M1436 16H1459V39 M16 433V456H39 M1436 456H1459V433" fill="none" stroke="#22d3ee" stroke-width="5"/>',
         txt(54, 68, '[ 07 ]  GITHUB ANALYTICS // ACTIVITY MONITOR', 30, '#67e8f9', True),
         txt(1410, 68, '● UPDATED ' + now.strftime('%Y-%m-%d UTC'), 18, '#a78bfa', anchor='end'),
         txt(58, 112, 'RECENT PUBLIC ACTIVITY  /  LAST 14 DAYS', 21, '#c084fc', True),
         txt(58, 143, 'Public events API (limited to recent available events)', 17, '#8e9cba')]
    for i, value in enumerate(counts):
        x = 65 + i * 67
        shade = ['#1d2441', '#19435a', '#167c83', '#23d9c2'][min(3, value // 2)]
        s.append(f'<rect x="{x}" y="175" width="49" height="49" fill="{shade}" stroke="#33405c" stroke-width="2"/>')
        s.append(txt(x + 24, 207, value, 19, '#f5f3ff', True, 'middle'))
    s += [txt(65, 255, 'OLDER', 16, '#8e9cba'), txt(990, 255, 'LATEST', 16, '#8e9cba'),
          txt(58, 312, 'TOP REPOSITORY LANGUAGES  /  PUBLIC NON-FORK REPOS', 22, '#c084fc', True)]
    colors = ['#22d3ee', '#a855f7', '#f472b6', '#34d399', '#fbbf24']
    total = sum(v for _, v in languages)
    if not total:
        s.append(txt(58, 363, 'No public repository language data available', 21, '#67e8f9'))
    else:
        x = 58
        for i, (name, value) in enumerate(languages):
            width = round(1330 * value / total)
            if width:
                s.append(f'<rect x="{x}" y="342" width="{width}" height="21" fill="{colors[i]}"/>')
                x += width
        for i, (name, value) in enumerate(languages):
            x = 58 + (i % 3) * 445
            y = 398 + (i // 3) * 30
            s.append(f'<rect x="{x}" y="{y-13}" width="12" height="12" fill="{colors[i]}"/>')
            s.append(txt(x + 21, y, f'{name}: {value * 100 / total:.1f}%', 17, '#dce4fa'))
    s.append('</svg>')
    SVG.write_text(''.join(s), encoding='utf-8')
    print(f'Updated {SVG.relative_to(ROOT)}: {sum(counts)} public events, {len(repos)} public repos, {len(languages)} languages')


if __name__ == '__main__':
    main()
