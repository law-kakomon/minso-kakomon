# 民事訴訟法過去問帳

ロースクール既修者入試（民事訴訟法）の過去問を、**民訴の単元ごとに**引ける学習帳。

**https://law-kakomon.github.io/minso-kakomon/**

- **単元から引く** — 裁判所／当事者／訴えの提起／審理／証拠／訴訟の終了／複数請求・多数当事者／上訴・再審／特別手続
- **条文から引く** — 検索欄に `114` と入れると、114条が論じられている回が並ぶ
- **論点・判例で探す** — 「既判力」「最判平成3年12月17日」などで検索
- **問題と解説をその場で読む** — 同志社・立命館は PDF をページ内に表示。慶應・中央はサーバー側の設定で埋め込めないため新しいタブで開く
- **解いた回に印をつける** — チェックはこの端末のブラウザにだけ残る

収録は同志社・立命館・慶應・中央の4校、計 57 回（2005〜2027年度）。
立命館は2018・2019年度だけ「訴訟法オプション試験」として民訴を出題していた（6回）。
関学は既修者入試で民事訴訟法を課していないため、収録対象外。

**PDF は各大学の公式ページをそのまま開きます**（このリポジトリに複製は置いていません）。

## 使い方

上の URL をブラウザで開くだけ。スマホでは「ホーム画面に追加」するとアプリのように使える。

手元で動かすとき:

```bash
open 開く.command
```

## 更新

```bash
python3 tools/fetch_sources.py   # 新年度を検知
python3 tools/digest.py <新しいID>  # 解説を読んで単元判定の材料を出す
# tools/classify.py に単元・論点を追記
python3 tools/build_data.py
```

くわしくは [CLAUDE.md](CLAUDE.md)。

## 出典

- [同志社大学法科大学院 過去の入試・履修免除試験問題](https://law-school.doshisha.ac.jp/entrance_ex/question/)
- [慶應義塾大学法科大学院 過去の入試問題](https://www.ls.keio.ac.jp/nyushi/examination.html)
- [中央大学法科大学院 入学者選抜の過去問題等の情報公開](https://www.chuo-u.ac.jp/academics/pro_graduateschool/law/orientation/selection/past/)

単元・論点・条文の整理は、各大学が公開している解説・出題趣旨・出題の意図にもとづく。

## 姉妹サイト

- [民法過去問帳](https://law-kakomon.github.io/minpo-kakomon/)
