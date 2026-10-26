#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/home/dymes/dev/TBXR}"
EXPECTED_BRANCH="${EXPECTED_BRANCH:-chore/jd/qol-patch-10262026}"
FRONTEND_DIR="${REPO_DIR}/frontend"
PM2_FRONTEND_APP="${PM2_FRONTEND_APP:-tbxr-frontend}"
PM2_BACKEND_APP="${PM2_BACKEND_APP:-tbxr-backend}"

echo "[deploy] repo: ${REPO_DIR}"
cd "${REPO_DIR}"

if [[ ! -d .git ]]; then
  echo "[deploy] ERROR: ${REPO_DIR} is not a git repository"
  exit 1
fi

echo "[deploy] fetching latest refs"
git fetch --all --prune

CURRENT_BRANCH="$(git branch --show-current)"
if [[ "${CURRENT_BRANCH}" != "${EXPECTED_BRANCH}" ]]; then
  echo "[deploy] switching branch ${CURRENT_BRANCH} -> ${EXPECTED_BRANCH}"
  git checkout "${EXPECTED_BRANCH}"
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "[deploy] ERROR: working tree has local changes; aborting to avoid destructive pull"
  git status --short
  exit 1
fi

echo "[deploy] pulling latest ${EXPECTED_BRANCH}"
git pull --ff-only origin "${EXPECTED_BRANCH}"

echo "[deploy] branch: $(git branch --show-current)"
echo "[deploy] commit: $(git rev-parse --short HEAD)"
echo "[deploy] head:   $(git log -1 --oneline)"

if [[ -f "${FRONTEND_DIR}/dist/index.html" ]]; then
  echo "[deploy] frontend dist before: $(stat -c '%y %n' "${FRONTEND_DIR}/dist/index.html")"
else
  echo "[deploy] frontend dist before: missing"
fi

echo "[deploy] installing frontend dependencies"
cd "${FRONTEND_DIR}"
npm ci --no-audit --no-fund

echo "[deploy] building frontend"
npm run build

echo "[deploy] frontend dist after:  $(stat -c '%y %n' dist/index.html)"

echo "[deploy] restarting PM2 apps"
pm2 restart "${PM2_FRONTEND_APP}"
pm2 restart "${PM2_BACKEND_APP}"

echo "[deploy] PM2 status"
pm2 list
pm2 describe "${PM2_FRONTEND_APP}" | sed -n '1,30p'
pm2 describe "${PM2_BACKEND_APP}" | sed -n '1,30p'

echo "[deploy] done"
