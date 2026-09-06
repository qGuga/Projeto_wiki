import json
import re
from pathlib import Path
from urllib.parse import quote
import requests

html_path = Path('deepseek_html_20260906_58d8d0.html')
data = json.loads(Path('banco_completo_dmw.json').read_text(encoding='utf-8'))
pages = sorted({x.get('origem_pagina') for x in data if x.get('attack')})
base = 'https://web.archive.org/web/20250907151731id_/https://digitalmastersworld.wiki.gg'
image_map = {}
for index, page in enumerate(pages, 1):
    try:
        url = f'{base}/wiki/{quote(page, safe="_()-")}'
        response = requests.get(url, timeout=12, headers={'User-Agent': 'DMW-Wiki-Rebuild/1.0'})
        if response.status_code != 200:
            continue
        matches = re.findall(r'(/images/thumb/[^"\'\\s>]+)', response.text)
        matches = [match.replace('&amp;', '&') for match in matches if re.search(r'\.(?:png|jpg|jpeg|gif)', match, re.I)]
        preferred = next((match for match in matches if page.replace('_', ' ').lower() in match.lower().replace('_', ' ')), None)
        if preferred or matches:
            image_map[page] = base + (preferred or matches[0])
    except requests.RequestException:
        continue
    if index % 50 == 0:
        print(f'{index}/{len(pages)} paginas; {len(image_map)} imagens')

html = html_path.read_text(encoding='utf-8')
marker = '        const wikiDatabase = '
start = html.index(marker)
image_marker = '        const wikiPages = {};'
insert_at = html.index(image_marker, start)
image_js = '        const archivedImages = ' + json.dumps(image_map, ensure_ascii=False, separators=(',', ':')) + ';\n'
html = html[:insert_at] + image_js + html[insert_at:]
html_path.write_text(html, encoding='utf-8')
print(f'IMAGENS={len(image_map)} PAGINAS={len(pages)}')
