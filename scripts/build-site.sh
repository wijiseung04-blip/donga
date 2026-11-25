#!/usr/bin/env bash
# Vercel 빌드 스크립트: DORA 대시보드를 정적 사이트(_site)로 만든다.
# Vercel이 넣어 주는 VERCEL_ENV, VERCEL_GIT_COMMIT_SHA, VERCEL_GIT_COMMIT_REF와
# 프로젝트 설정의 SITE_ENV_LABEL을 사용한다.
set -euo pipefail

OUT=_site
SRC=docs/images/docs
TARGET_ENV="${VERCEL_ENV:-local}"
COMMIT="${VERCEL_GIT_COMMIT_SHA:-unknown}"
BRANCH="${VERCEL_GIT_COMMIT_REF:-unknown}"
LABEL="${SITE_ENV_LABEL:-donga DORA 대시보드}"

rm -rf "$OUT"
mkdir -p "$OUT"
cp "$SRC/dashboard.html" "$OUT/index.html"
cp "$SRC/dora-metrics.json" "$OUT/"

cat > "$OUT/build-info.json" <<JSON
{"label": "${LABEL}", "environment": "${TARGET_ENV}", "branch": "${BRANCH}", "commit": "${COMMIT}", "builtAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
JSON

# 프로덕션이 아닌 배포(PR 프리뷰 등)에는 페이지 상단에 배포 정보를 표시한다
if [ "$TARGET_ENV" != "production" ]; then
  banner="<div style=\"background:#fff3cd;color:#664d03;padding:8px 16px;font:14px sans-serif;text-align:center\">🔍 ${LABEL} · ${TARGET_ENV} 미리보기 · 브랜치 ${BRANCH} · 커밋 ${COMMIT:0:7}</div>"
  awk -v banner="$banner" '{ print } /<body[^>]*>/ && !done { print banner; done = 1 }' \
    "$OUT/index.html" > "$OUT/index.tmp" && mv "$OUT/index.tmp" "$OUT/index.html"
fi

echo "사이트 생성 완료: $OUT (environment=${TARGET_ENV}, commit=${COMMIT})"
ls -la "$OUT"
