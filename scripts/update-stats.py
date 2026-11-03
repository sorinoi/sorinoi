import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

USERNAME = os.getenv('PROFILE_USERNAME', 'sorinoi')
TOKEN = os.getenv('GH_TOKEN') or os.getenv('GITHUB_TOKEN')
SVG_PATH = Path('assets/tech-dashboard.svg')
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)

def api(path, params=None):
    url = 'https://api.github.com' + path
    if params:
        url += '?' + urllib.parse.urlencode(params)
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'sorin-profile-stats', 'X-GitHub-Api-Version': '2022-11-28'}
    if TOKEN:
        headers['Authorization'] = 'Bearer ' + TOKEN
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'GitHub API HTTP {exc.code} for {path}: {exc.read().decode("utf-8", "replace")[:350]}') from exc

def get_stats():
    repos = []
    page = 1
    while True:
        batch = api(f'/users/{USERNAME}/repos', {'type': 'owner', 'per_page': 100, 'page': page})
        repos.extend(r for r in batch if not r.get('fork', False) and r.get('owner', {}).get('login', '').lower() == USERNAME.lower())
        if len(batch) < 100:
            break
        page += 1
    # Count stars for owned, non-fork public repositories.
    stars = sum(r.get('stargazers_count', 0) for r in repos)
    # GitHub Search counts publicly indexed commits authored by the username.
    commits = api('/search/commits', {'q': f'author:{USERNAME}', 'per_page': 1})['total_count']
    # Public PRs authored by this account, including PRs to other people's repositories.
    prs = api('/search/issues', {'q': f'type:pr author:{USERNAME}', 'per_page': 1})['total_count']
    # Repository count excludes forks to match stars scope.
    return {'Total Stars:': stars, 'Total Commits:': commits, 'Total PRs:': prs, 'Repositories:': len(repos)}

def update_svg(stats):
    if not SVG_PATH.is_file():
        raise FileNotFoundError(f'Missing {SVG_PATH}. Run from repository root.')
    tree = ET.parse(SVG_PATH)
    root = tree.getroot()
    texts = list(root.iter(f'{{{NS}}}text'))
    for label, value in stats.items():
        matches = [i for i, node in enumerate(texts) if (node.text or '').strip() == label]
        if len(matches) != 1:
            raise ValueError(f'Expected exactly one SVG label {label!r}, found {len(matches)}')
        label_node = texts[matches[0]]
        y = label_node.get('y')
        candidates = [node for node in texts if node.get('x') == '1428' and node.get('y') == y]
        if len(candidates) != 1:
            raise ValueError(f'Expected one value field at x=1428 y={y} for {label}')
        candidates[0].text = f'{value:,}'
        candidates[0].set('fill', '#6cf5ff')
    tree.write(SVG_PATH, encoding='unicode', xml_declaration=False)

if __name__ == '__main__':
    stats = get_stats()
    print('Public GitHub stats:', stats)
    update_svg(stats)
    print(f'Updated {SVG_PATH}')
