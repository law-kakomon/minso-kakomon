#!/bin/bash
# 民事訴訟法過去問帳をデフォルトブラウザで開く（サーバー未起動なら起動する）
PORT=8130
DIR="$(cd "$(dirname "$0")" && pwd)"
if ! lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then
  nohup python3 -m http.server $PORT --directory "$DIR" >/dev/null 2>&1 &
  sleep 0.5
fi
open "http://localhost:$PORT"
