#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""各法科大学院の公開ページから、対象科目の過去問 PDF の在りかを取得して data/sources.json に書き出す。

新年度が公開されたらこれを実行すると差分が表示される（新規項目は tools/classify.py に単元を追記する）。
PDF 自体はダウンロード・再配布しない。記録するのは大学公式ページ上の URL だけ。

科目を変えるときは下の SUBJECT だけ差し替える（民法版・会社法版と共用の作り）。
"""
import json, re, html, sys, os, urllib.request, urllib.parse, unicodedata as ud
from pathlib import Path

# ---------------------------------------------------------------- 科目の設定
SUBJECT = {
    'name': '民事訴訟法',
    'short': '民訴',
    # 同志社・中央は表の科目セルの文字列で拾う
    'cell': '民事訴訟法',
    # 立命館はファイル名の科目キー（民法=minpo, 商法=shoho, …）。無い科目は None
    # 立命館は2018・2019年度だけ「訴訟法オプション試験」（民訴・刑訴の合冊）を出している
    'ritsumei_key': 'option',
    # 関学はリンク文字「<科目>問題・解説（2026A日程）」の <科目>。無い科目は None
    'kwansei_label': None,
    # 慶應は合冊 PDF のリンク文字に含まれる科目名
    'keio_keyword': '民事訴訟法',
}

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'sources.json'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
PAGES = {
 '同志社': 'https://law-school.doshisha.ac.jp/entrance_ex/question/',
 '立命館': 'https://www.ritsumei.ac.jp/lawschool/admission/past.html/',
 '慶應':   'https://www.ls.keio.ac.jp/nyushi/examination.html',
 '関学':   'https://www.kwansei.ac.jp/lawschool/admissions/kakomon/',
 '中央':   'https://www.chuo-u.ac.jp/academics/pro_graduateschool/law/orientation/selection/past/',
}


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8', 'replace')


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s or ''))).strip()


def doshisha(h):
    h = re.sub(r'<!--.*?-->', '', h, flags=re.S)
    rows = []
    pat = re.compile(r'<h([2-5])[^>]*>(.*?)</h\1>|<tr[^>]*>(.*?)</tr>', re.S)
    head = sub = ''
    for m in pat.finditer(h):
        if m.group(1):
            if int(m.group(1)) == 5: sub = clean(m.group(2))
            else: head, sub = clean(m.group(2)), ''
            continue
        row = m.group(3)
        cells = [clean(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.S)]
        if SUBJECT['cell'] not in cells: continue
        links = re.findall(r'href="([^"]+\.pdf)"', row)
        ym = re.search(r'(\d{4})年度', head)
        if not ym or not links: continue
        rows.append({'year': int(ym.group(1)), 'sub': sub, 'links': links})
    seen = {}
    items = []
    for r in rows:
        y, fn = r['year'], r['links'][0].split('/')[-1]
        if '履修免除' in r['sub']:
            term, tid = '履修免除', 'menjo'
        elif '転入' in r['sub'] or 'tennyu' in fn:
            term, tid = '転入学', 'tennyu'
        elif 'zenki' in fn:
            term, tid = '前期', 'zenki'
        elif 'koki' in fn:
            term, tid = '後期', 'koki'
        else:
            term, tid = ('後期', 'koki') if seen.get(y) else ('前期', 'zenki')
        seen[y] = seen.get(y, 0) + 1
        # リンクは「順番」ではなく URL で種類を決める。
        # 解説の欄が空の年度があり、順番で割り当てると解答用紙を解説として拾ってしまう。
        kinds = {}
        for u in r['links']:
            f = u.rsplit('/', 1)[-1].lower()
            if '/questions/' in u or 'mondai' in f:
                kinds.setdefault('mondai', u)
            elif '/kaisetsu/' in u or 'kaisetsu' in f or f.startswith('kai'):
                kinds.setdefault('kaisetsu', u)
            elif '/kaitou/' in u or 'kaitou' in f or 'yoshi' in f or re.search(r't\d*\.pdf$', f):
                kinds.setdefault('kaitou', u)
        items.append({
            'id': f'dos-{y}-{tid}', 'univ': '同志社', 'year': y, 'term': term,
            'course': r['sub'] or '法学既修者',
            'mondai': kinds.get('mondai'), 'kaisetsu': kinds.get('kaisetsu'),
            'kaitou': kinds.get('kaitou'), 'kaisetsuLabel': '解説',
        })
    return items


def ritsumei(h):
    if not SUBJECT['ritsumei_key']:
        return []
    B = 'https://www.ritsumei.ac.jp'
    TERM = {'z': ('前期', 'zenki'), 'c': ('中期', 'chuki'), 'k': ('後期', 'koki')}
    key = SUBJECT['ritsumei_key']
    pat = rf'href="(/lawschool/assets/file/admission/past-(\d\d)([zck])_{key}\.pdf)"'
    found = sorted(set(re.findall(pat, h)))
    comment = {}
    for u, y, t in re.findall(r'href="(/lawschool/assets/file/admission/past-comment(\d{4})-([zck])\d?\.pdf)"', h):
        comment.setdefault((int(y), t), B + u)
    items = []
    for u, yy, t in found:
        y = 2000 + int(yy); term, tid = TERM[t]
        items.append({
            'id': f'rit-{y}-{tid}', 'univ': '立命館', 'year': y, 'term': term,
            'course': '法学既修者（B方式）',
            'mondai': B + u, 'kaisetsu': comment.get((y, t)), 'kaitou': None,
            'kaisetsuLabel': '入試講評',
            'kaisetsuNote': f"全科目まとめの講評。「訴訟法オプション試験（{SUBJECT['name']}）」の節を参照",
            'mondaiNote': '訴訟法オプション試験（民事訴訟法・刑事訴訟法の合冊）。'
                          f"{SUBJECT['name']}の問題を参照",
        })
    return items


def kwansei(h):
    if not SUBJECT['kwansei_label']:
        return []
    B = 'https://www.kwansei.ac.jp'
    h = re.sub(r'<!--.*?-->', '', h, flags=re.S)
    label = SUBJECT['kwansei_label']
    items, seen = [], set()
    for m in re.finditer(r'<a\s+[^>]*href="([^"]+\.pdf)"[^>]*>(.*?)</a>', h, re.S):
        href, txt = m.group(1), clean(m.group(2))
        t = ud.normalize('NFKC', txt)
        mm = re.search(rf'{label}問題・解説\s*\(\s*(\d{{4}})\s*([A-D])日程\s*\)', t)
        if not mm: continue
        year, term = int(mm.group(1)), mm.group(2)
        if (year, term) in seen: continue
        seen.add((year, term))
        items.append({
            'id': f'kgu-{year}-{term.lower()}', 'univ': '関学', 'year': year,
            'term': f'{term}日程', 'course': '一般入試（法学既修者）',
            'mondai': href if href.startswith('http') else B + href,
            'kaisetsu': None, 'kaitou': None, 'kaisetsuLabel': '解説', 'combined': True,
            'mondaiNote': '問題と解説（解答例・出題の意図・講評）が1つにまとまったもの',
        })
    items.sort(key=lambda x: (-x['year'], x['term']))
    return items


def keio(h):
    h = re.sub(r'<!--.*?-->', '', h, flags=re.S)
    i = h.find('過去の入試問題')
    body = h[i:] if i >= 0 else h
    toks = re.findall(r'<h([1-5])[^>]*>(.*?)</h\1>|<a\s+[^>]*href="(https://www\.keio\.ac\.jp/files/[^"]+)"[^>]*>(.*?)</a>', body, re.S)
    year = course = None; extra = '本試験'
    kw = SUBJECT['keio_keyword']
    others = {'憲法', '民法', '刑法', '商法', '民事訴訟法', '刑事訴訟法'} - {kw}
    buck = {}
    for lvl, hd, href, txt in toks:
        if hd:
            t = clean(hd)
            m = re.search(r'(\d{4})年度入試問題', t)
            if m:
                year = int(m.group(1)); course = None
                extra = '追試験' if '追試験' in t else '本試験'
            elif 'コース' in t:
                course = t
            continue
        # 2016年度以前は「論述式I/II」「マーク式」形式で科目の所在を特定できないため対象外
        if not (course and '既修' in course and year and year >= 2017): continue
        k = clean(txt)
        key = (year, extra)
        b = buck.setdefault(key, {'mondai': None, 'mondaiLabel': None, 'kaisetsu': None, 'generic': None})
        if '出題趣旨' in k:
            b['kaisetsu'] = href
        elif kw in k and not b['mondai']:
            b['mondai'] = href
            m = re.search(r'[（(]([^（）()]*' + kw + r'[^（）()]*)[）)]', k)
            b['mondaiLabel'] = m.group(1) if m else k
        elif not re.search('|'.join(sorted(others)), k) \
                and not re.search(r'小論文|論述式|マーク式|簡易記述式', k) and not b['generic']:
            b['generic'] = href
    items = []
    for (y, extra), b in sorted(buck.items(), reverse=True):
        if not b['mondai'] and b['generic']:
            b['mondai'] = b['generic']; b['mondaiLabel'] = '科目名の記載なし'
        if not b['mondai']: continue
        tid = 'tsuishi' if extra == '追試験' else 'honshi'
        items.append({
            'id': f'kei-{y}-{tid}', 'univ': '慶應', 'year': y, 'term': extra,
            'course': '法学既修者コース',
            'mondai': b['mondai'], 'kaisetsu': b['kaisetsu'], 'kaitou': None,
            'kaisetsuLabel': '出題趣旨',
            'kaisetsuNote': f"全科目まとめの出題趣旨。{SUBJECT['name']}の節を参照",
            'mondaiNote': f'合冊の試験問題（{b["mondaiLabel"]}）。{SUBJECT["name"]}の問題を参照' if b['mondaiLabel'] else None,
        })
    return items


def chuo(h):
    B = 'https://www.chuo-u.ac.jp'
    h = re.sub(r'<!--.*?-->', '', h, flags=re.S)
    m = re.search(r'<table[^>]*法学既修者[^>]*>(.*?)</table>', h, re.S) or re.search(r'<table[^>]*>(.*?)</table>', h, re.S)
    table = m.group(1) if m else h
    years, urls = [], []
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', table, re.S):
        cells = [clean(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.S)]
        ys = [int(x) for c in cells for x in re.findall(r'(\d{4})年度', c)]
        if ys and not years: years = ys
        if any(c == SUBJECT['cell'] for c in cells) and not urls:
            urls = re.findall(r'href="([^"]+\.pdf)"', row)
    shushi = {}
    for mm in re.finditer(r'<a\s+[^>]*href="([^"]+\.pdf)"[^>]*>(.*?)</a>', h, re.S):
        t = clean(mm.group(2))
        ym = re.search(r'(\d{4})年度.*法学既修者.*出題の意図', t)
        if ym: shushi[int(ym.group(1))] = B + mm.group(1)
    items = []
    for y, u in zip(years, urls):
        items.append({
            'id': f'chu-{y}-ronjutsu', 'univ': '中央', 'year': y, 'term': '論述式',
            'course': '法学既修者コース',
            'mondai': B + u, 'kaisetsu': shushi.get(y), 'kaitou': None,
            'kaisetsuLabel': '出題の意図',
            'kaisetsuNote': f"全科目まとめの「出題の意図及び評価の視点」。{SUBJECT['name']}の節を参照",
        })
    items.sort(key=lambda x: -x['year'])
    return items


def host_embed_check(items):
    """各ホストが PDF の iframe 埋め込みを許すかを実際のヘッダーで調べる。"""
    sample = {}
    for it in items:
        for k in ('mondai', 'kaisetsu', 'kaitou'):
            u = it.get(k)
            if u:
                sample.setdefault(urllib.parse.urlparse(u).netloc, u)
    out = {}
    for host, u in sorted(sample.items()):
        if u.startswith('http://'):
            out[host] = {'embeddable': False, 'reason': 'http'}
        else:
            try:
                req = urllib.request.Request(u, method='HEAD', headers={'User-Agent': UA})
                with urllib.request.urlopen(req, timeout=30) as r:
                    xfo = (r.headers.get('X-Frame-Options') or '').strip()
                    csp = (r.headers.get('Content-Security-Policy') or '')
                blocked = bool(xfo) or 'frame-ancestors' in csp.lower()
                out[host] = {'embeddable': not blocked, 'reason': 'xfo' if blocked else None}
            except Exception:
                out[host] = {'embeddable': False, 'reason': 'unreachable'}
        print(f"  {host}: {'埋め込み可' if out[host]['embeddable'] else '埋め込み不可（' + str(out[host]['reason']) + '）'}")
    return out


def main():
    items = []
    items += doshisha(get(PAGES['同志社']))
    items += ritsumei(get(PAGES['立命館']))
    items += kwansei(get(PAGES['関学']))
    items += keio(get(PAGES['慶應']))
    items += chuo(get(PAGES['中央']))
    old = {}
    if OUT.exists():
        old = {x['id']: x for x in json.load(open(OUT, encoding='utf-8'))['items']}
    new_ids = [x['id'] for x in items if x['id'] not in old]
    gone = [k for k in old if k not in {x['id'] for x in items}]
    print('ホストの埋め込み可否を確認中…')
    hosts = host_embed_check(items)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump({'subject': SUBJECT['name'], 'fetched': PAGES, 'hosts': hosts, 'items': items},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"{len(items)} 件を data/sources.json に保存")
    if new_ids: print('新規:', new_ids)
    if gone: print('消えた項目:', gone)
    if not new_ids and not gone and old: print('前回と同じ内容')


if __name__ == '__main__':
    main()
