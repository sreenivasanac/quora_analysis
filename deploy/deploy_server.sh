#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/home/sreenivasanac/projects/quora_analysis"
WEB_ROOT="/var/www/quora_analysis"
FRONTEND_DIR="${REPO_DIR}/visualization/visualization_frontend"
FRONTEND_BUILD_DIR="${FRONTEND_DIR}/dist"

echo "[deploy] repo: ${REPO_DIR}"
cd "${REPO_DIR}"

export PATH="$HOME/.local/bin:$PATH"

echo "[deploy] git fetch/pull"
git fetch --prune
git checkout main
git pull --ff-only

echo "[deploy] restart backend (systemd)"
sudo /usr/bin/systemctl restart quora-api

echo "[deploy] frontend build"
cd "${FRONTEND_DIR}"
npm ci
npm run build

echo "[deploy] publish frontend -> ${WEB_ROOT}"
sudo /bin/mkdir -p "${WEB_ROOT}"
sudo /bin/rm -rf "${WEB_ROOT}"/*
sudo /bin/cp -r "${FRONTEND_BUILD_DIR}"/* "${WEB_ROOT}/"
sudo /bin/chown -R www-data:www-data "${WEB_ROOT}"

echo "[deploy] validate+reload nginx"
sudo /usr/sbin/nginx -t
sudo /usr/bin/systemctl reload nginx

echo "[deploy] done"
