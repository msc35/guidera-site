#!/usr/bin/env bash
# Notify IndexNow (Bing, Yandex, Seznam, Naver, ...) that URLs on guidera.live changed.
# Usage: scripts/indexnow.sh https://guidera.live/page1.html https://guidera.live/page2.html ...
# Protocol: https://www.indexnow.org/documentation
set -euo pipefail

HOST="guidera.live"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KEYFILE="$(ls "$ROOT"/*.txt | xargs -n1 basename | grep -E '^[0-9a-f]{32}\.txt$' | head -1)"
KEY="${KEYFILE%.txt}"

if [ -z "$KEY" ]; then echo "No IndexNow key file found at the site root." >&2; exit 1; fi
if [ "$#" -eq 0 ]; then echo "Usage: $0 URL [URL...]" >&2; exit 1; fi

URLS=$(printf '"%s",' "$@"); URLS="[${URLS%,}]"
BODY=$(printf '{"host":"%s","key":"%s","keyLocation":"https://%s/%s","urlList":%s}' "$HOST" "$KEY" "$HOST" "$KEYFILE" "$URLS")

CODE=$(curl -sS -o /dev/null -w '%{http_code}' -X POST "https://api.indexnow.org/indexnow" \
  -H 'Content-Type: application/json; charset=utf-8' --data "$BODY")
echo "IndexNow response: HTTP $CODE ($# URLs)"
case "$CODE" in
  200|202) exit 0 ;;
  *) echo "See https://www.indexnow.org/documentation for the meaning of this code." >&2; exit 1 ;;
esac
