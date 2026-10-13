#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""単元判定の下ごしらえ。

data/sources.json の PDF を取ってきてテキスト化し、対象科目の節だけ切り出して、
引用条文・判例・論点文を一覧にする。この出力を見ながら tools/classify.py を書く。

    python3 tools/digest.py            # 全件
    python3 tools/digest.py dos-2026-zenki kei-2025-honshi   # 指定した回だけ

PDF とテキストは .cache/ に置く（git 管理外）。リポジトリに PDF は入れない。
"""
import json, re, subprocess, sys, urllib.request, unicodedata as ud
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
CACHE = ROOT / '.cache'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'

import classify as C
SUBJECT = C.SUBJECT_NAME            # 例: 民事訴訟法


def fetch(url, path):
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        path.write_bytes(r.read())
    return path


def to_text(pdf, txt):
    txt.parent.mkdir(parents=True, exist_ok=True)
    if not txt.exists() or txt.stat().st_size == 0:
        subprocess.run(['pdftotext', '-enc', 'UTF-8', str(pdf), str(txt)],
                       check=False, capture_output=True)
    return txt.read_text(encoding='utf-8', errors='replace') if txt.exists() else ''


def norm(t):
    t = ud.normalize('NFKC', t.replace('⺠', '民'))
    t = re.sub(r'[ \t　]+', ' ', t)
    return re.sub(r'\n{3,}', '\n\n', t)


def jp_len(t):
    return len(re.findall(r'[ぁ-んァ-ヶ一-龥]', t))


SUBJECTS_ALL = ['憲法', '民法', '刑法', '商法', '民事訴訟法', '刑事訴訟法', '行政法', '小論文']


def section(t, univ):
    """合冊 PDF から対象科目の節だけ取り出す。単独 PDF はそのまま返す。"""
    others = [s for s in SUBJECTS_ALL if s != SUBJECT]
    # 慶應・中央の出題趣旨は【科目】、慶應の問題は 科目〔問題〕
    flat, idx = [], []
    for i, ch in enumerate(t):
        if not ch.isspace():
            flat.append(ch); idx.append(i)
    flat = ''.join(flat)
    ms = [m for m in re.finditer(r'(' + '|'.join(SUBJECTS_ALL) + r')〔問題〕', flat)]
    for j, m in enumerate(ms):
        if m.group(1) == SUBJECT:
            e = idx[ms[j + 1].start()] if j + 1 < len(ms) else len(t)
            return t[idx[m.start()]:e]
    m = re.search(r'【\s*' + SUBJECT + r'\s*】', t)
    if m:
        nxt = re.search(r'【\s*(' + '|'.join(others) + r')\s*】', t[m.end():])
        return t[m.start(): m.end() + (nxt.start() if nxt else len(t))]
    return t          # 単独 PDF（同志社など）


ART = {}


def articles(t):
    """条文番号を数える。字間アキ・行またぎで割れた数字をつないでから拾い、他法はマスクする。"""
    t = re.sub(r'(?<=[0-9])\s+(?=[0-9])', '', t)
    mark = '◆SUB◆'
    t2 = t.replace(SUBJECT, mark)
    other_laws = (r'民法|会社法|商法|憲法|刑法|刑事訴訟法|民事執行法|民事保全法|破産法|人事訴訟法|'
                  r'家事事件手続法|借地借家法|不動産登記法|国家賠償法|行政事件訴訟法|仲裁法|'
                  r'民訴規則|規則|民執|民保|民訴費用法|弁護士法|裁判所法|同法|本法|旧法')
    t2 = re.sub(r'(' + other_laws + r')\s*(?:第\s*)?\d{1,4}\s*条?(?:\s*の\s*\d{1,2})?', '〇', t2)
    t2 = t2.replace(mark, SUBJECT)
    out = {}
    for m in re.finditer(r'(?<![0-9])(\d{1,4})\s*条', t2):
        n = int(m.group(1))
        if 1 <= n <= 405:
            out[n] = out.get(n, 0) + 1
    return out


HANREI = re.compile(r'(最大判|最大決|最判|最決|大判|大連判|大決|高判|高決)\s*'
                    r'((?:明治|大正|昭和|平成|令和)?\s*(?:\d{1,2}|元)\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)')
CUE = re.compile(r'[^。\n]{6,170}?(?:問題となる|問題である|が問われ|を問うもの|を問う問題|問うている|'
                 r'出題意図|出題趣旨|検討を求め|論ずべき|論じる必要|理解を問う|ポイントとなる|'
                 r'が争点|答えさせる|求められる)[^。\n]{0,60}。')


def main():
    src = json.load(open(ROOT / 'data' / 'sources.json', encoding='utf-8'))
    want = set(sys.argv[1:])
    for it in src['items']:
        if want and it['id'] not in want:
            continue
        # 解説を優先し、それが画像 PDF なら問題文で代用する
        t, kind = '', None
        for k in ('kaisetsu', 'mondai'):
            if not it.get(k): continue
            try:
                pdf = fetch(it[k], CACHE / 'pdf' / f"{it['id']}_{k}.pdf")
            except Exception as e:
                print(f"===== {it['id']}  [{k} 取得失敗 {e}]"); continue
            cand = norm(to_text(pdf, CACHE / 'txt' / f"{it['id']}_{k}.txt"))
            if jp_len(cand) >= 100:
                t, kind = cand, k
                break
        if not kind:
            print(f"===== {it['id']}  [画像 PDF のみ・本文を取り出せない]")
            continue
        sec = section(t, it['univ'])
        arts = articles(sec)
        han, cues = [], []
        for m in HANREI.finditer(sec):
            h = re.sub(r'\s+', '', m.group(0))
            if h not in han: han.append(h)
        for m in CUE.finditer(sec):
            c = re.sub(r'\s+', '', m.group(0))
            if c not in cues: cues.append(c)
        units = {}
        for n, c in arts.items():
            u = C.unit_of(n)
            if u: units[u] = units.get(u, 0) + c
        print(f"===== {it['id']}  [{kind}] {jp_len(sec)}字  {it['univ']} {it['year']} {it['term']}")
        print(f"  冒頭: {re.sub(chr(10), '/', sec[:110])}")
        print(f"  単元候補: {sorted(units.items(), key=lambda x: -x[1])[:8]}")
        print(f"  条文: {[a for a, _ in sorted(arts.items(), key=lambda x: -x[1])][:16]}")
        if han: print(f"  判例: {han[:8]}")
        for c in cues[:6]: print(f"  ◆ {c[:150]}")
        print()


if __name__ == '__main__':
    main()
