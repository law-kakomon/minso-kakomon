#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data/sources.json（PDF の在りか）+ tools/classify.py（単元分類）→ data/kakomon.json"""
import json, sys, urllib.parse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import classify as C

TERM_ORDER = {'前期': 0, '中期': 1, '後期': 2, '履修免除': 3, '転入学': 4,
              '本試験': 0, '追試験': 1,
              'A日程': 0, 'B日程': 1, 'C日程': 2, 'D日程': 3, '論述式': 0}
UNIV_ORDER = {'同志社': 0, '立命館': 1, '関学': 2, '慶應': 3, '中央': 4}

def main():
    src = json.load(open(ROOT / 'data' / 'sources.json', encoding='utf-8'))
    hosts = src.get('hosts', {})

    def embed_of(url):
        """このページ（https）の中に PDF を埋め込めるか。
        理由は 'xfo'（大学が X-Frame-Options 等で禁止）/ 'http'（PDF が http 配信）。"""
        if not url:
            return False, None
        if url.startswith('http://'):
            return False, 'http'
        h = urllib.parse.urlparse(url).netloc
        info = hosts.get(h)
        if info and not info.get('embeddable'):
            return False, info.get('reason') or 'xfo'
        return True, None

    items = []
    for s in src['items']:
        embed, why = {}, {}
        for k in ('mondai', 'kaisetsu', 'kaitou'):
            embed[k], why[k] = embed_of(s.get(k))
        cls = C.CLASS.get(s['id'])
        units, topics, arts, hanrei = cls if cls else ([], [], [], [])
        items.append({
            **s,
            'embed': embed, 'embedWhy': why,
            # 単元・論点を何から読み取ったか（解説が無い回は問題文から判定している）
            'basis': '解説' if (s.get('kaisetsu') or s.get('combined')) else '問題',
            'units': units, 'topics': topics, 'articles': arts, 'hanrei': hanrei,
            'classified': bool(units),
        })
    items.sort(key=lambda x: (-x['year'], UNIV_ORDER.get(x['univ'], 9), TERM_ORDER.get(x['term'], 9)))
    # 単元ごとの件数
    counts = {}
    for it in items:
        for u in it['units']:
            counts[u] = counts.get(u, 0) + 1
            top = u.split('/')[0]
            if top != u:          # 小分類を持たない大分類（例: 親族）は二重に数えない
                counts[top] = counts.get(top, 0) + 1
    taxonomy = []
    for top, subs in C.TAXONOMY:
        taxonomy.append({
            'name': top, 'count': counts.get(top, 0),
            'subs': [{'name': s, 'key': f'{top}/{s}', 'count': counts.get(f'{top}/{s}', 0)} for s in subs],
        })
    out = {
        'generated': True,
        'sources': src['fetched'],
        'taxonomy': taxonomy,
        'items': items,
    }
    json.dump(out, open(ROOT / 'data' / 'kakomon.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # index.html にも埋め込む（file:// で直接開いても動くようにするため）
    import re as _re
    html_path = ROOT / 'index.html'
    if html_path.exists():
        h = html_path.read_text(encoding='utf-8')
        payload = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
        payload = payload.replace('</', '<\\/')   # </script> で閉じないように
        h2, n = _re.subn(
            r'(<script id="kakomon-data" type="application/json">).*?(</script>)',
            lambda m: m.group(1) + payload + m.group(2), h, flags=_re.S)
        if n:
            html_path.write_text(h2, encoding='utf-8')
            print(f'index.html にデータを埋め込み（{len(payload):,} バイト）')
        else:
            print('警告: index.html の埋め込み先が見つかりません')
    nc = [i['id'] for i in items if not i['classified']]
    print(f"{len(items)} 件 → data/kakomon.json")
    print(f"単元分類済み {len(items)-len(nc)} 件 / 未分類 {len(nc)} 件: {nc}")
    miss = [i['id'] for i in items if not i.get('kaisetsu') and not i.get('combined')]
    print(f"解説・講評なし {len(miss)} 件: {miss}")
    import collections
    print('大学別:', dict(collections.Counter(i['univ'] for i in items)))
    noemb = [i['id'] for i in items if any(i[k] and not i['embed'][k] for k in ('mondai','kaisetsu','kaitou'))]
    print(f"埋め込めない PDF を含む項目: {len(noemb)} 件")

if __name__ == '__main__':
    main()
