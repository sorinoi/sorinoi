#!/usr/bin/env python3
"""Non-destructive, idempotent SORIN.exe seam styling for existing SVGs.
Run after any generator that rewrites an SVG. Does not alter statistics or labels.
"""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
S = lambda tag: f'{{{NS}}}{tag}'
FILES = [
    'tech-dashboard.svg',
    'pixel-analytics.svg',
    'featured-quests.svg',
    'contribution-matrix.svg',
]

def polish(path: Path):
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag != S('svg') or root.get('viewBox', '').split()[:3] != ['0', '0', '1475']:
        raise ValueError(f'Unexpected SVG format: {path}')
    height = int(float(root.get('viewBox').split()[3]))
    # Remove our prior overlay so repeated runs never accumulate lines.
    for node in list(root):
        if node.get('id') == 'sorin-seam-polish':
            root.remove(node)
    # Keep original artwork intact. Harmonize only the full-canvas background.
    bg = next((node for node in root if node.tag == S('rect') and
               node.get('width') == '1475' and node.get('height') == str(height)
               and node.get('x', '0') == '0' and node.get('y', '0') == '0'), None)
    if bg is None:
        raise ValueError(f'Cannot locate background rect: {path}')
    bg.set('fill', '#0b0921')
    # Analytics and Quests currently have their own outer framed boxes.
    # Remove only frame strokes (not the panel fill, cards or text).
    if path.name in ('pixel-analytics.svg', 'featured-quests.svg'):
        for node in root:
            if node.tag == S('rect') and node.get('x') in ('16', '23') and node.get('width') in ('1443', '1429'):
                node.attrib.pop('stroke', None)
                node.attrib.pop('stroke-width', None)
            if node.tag == S('path') and node.get('d', '').startswith('M16 39V16H39'):
                node.set('stroke', 'none')
    overlay = ET.SubElement(root, S('g'), {'id': 'sorin-seam-polish', 'fill': 'none'})
    # Continuous outer neon rails; leave 0..16px canvas padding in all panels.
    ET.SubElement(overlay, S('path'), {
        'd': f'M16 0 V{height} M1459 0 V{height}',
        'stroke': '#8b5cf6', 'stroke-width': '3', 'opacity': '0.9'})
    ET.SubElement(overlay, S('path'), {
        'd': f'M23 0 V{height} M1452 0 V{height}',
        'stroke': '#35255c', 'stroke-width': '2'})
    # Deliberate horizontal module separator at bottom, not an enclosing box.
    ET.SubElement(overlay, S('path'), {
        'd': f'M16 {height-2} H1459',
        'stroke': '#22d3ee', 'stroke-width': '2', 'opacity': '0.65'})
    tree.write(path, encoding='unicode', xml_declaration=False)
    print(f'Polished {path} (preserved data and text)')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('names', nargs='*', choices=FILES, metavar='SVG_NAME',
                        help='SVG filenames; default: all three')
    args = parser.parse_args()
    for name in args.names or FILES:
        polish(Path('assets') / name)
