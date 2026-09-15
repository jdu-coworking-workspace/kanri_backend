#!/usr/bin/env bash
# Frontend artefaktini S3 dan olib, PM2 ni yangilaydi.
# Build bu skriptda EMAS — GitHub Actions da qilinadi.
#
#   /usr/local/bin/kanri-deploy-frontend.sh deploy/frontend-<sha>.tar.gz
#
# Bucket nomi /etc/kanri-deploy.env dan olinadi. S3 ga kirish instance role
# orqali, kalit saqlanmaydi.

set -euo pipefail

KEY="${1:?Ishlatilishi: kanri-deploy-frontend.sh deploy/frontend-<sha>.tar.gz}"
APP_DIR=/var/www/kanri/frontend
APP_USER=kanri

# SSM buyruqlarni root sifatida bajaradi. Qo'lda chaqirsangiz sudo bilan.
if [ "$(id -u)" -ne 0 ]; then
    echo "XATO: root kerak. sudo bilan ishga tushiring." >&2
    exit 1
fi

# shellcheck source=/dev/null
source /etc/kanri-deploy.env
: "${DEPLOY_BUCKET:?/etc/kanri-deploy.env da DEPLOY_BUCKET topilmadi}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "==> Yuklab olinmoqda: s3://$DEPLOY_BUCKET/$KEY"
aws s3 cp "s3://$DEPLOY_BUCKET/$KEY" "$TMP/frontend.tar.gz"

mkdir -p "$TMP/new"
tar -xzf "$TMP/frontend.tar.gz" -C "$TMP/new"

# Artefakt haqiqatan build qilinganini tekshiramiz.
if [ ! -f "$TMP/new/.next/BUILD_ID" ]; then
    echo "XATO: .next/BUILD_ID yo'q — artefakt buzuq." >&2
    exit 1
fi

mkdir -p "$APP_DIR"
chown "$APP_USER:$APP_USER" "$APP_DIR"

# TMP root ga tegishli, kanri o'qiy olishi kerak.
chmod -R a+rX "$TMP/new"

echo "==> Fayllar ko'chirilmoqda"
# node_modules saqlanadi, qolgani almashtiriladi.
sudo -u "$APP_USER" -H rsync -a --delete --exclude node_modules \
    "$TMP/new/" "$APP_DIR/"

echo "==> Production dependency lar"
# Build allaqachon bo'lgan, devDependencies kerak emas.
cd "$APP_DIR"
sudo -u "$APP_USER" -H npm ci --omit=dev

echo "==> PM2"
# -H shart: PM2 daemon HOME=/home/kanri bo'yicha topiladi.
if sudo -u "$APP_USER" -H pm2 describe kanri-frontend >/dev/null 2>&1; then
    sudo -u "$APP_USER" -H pm2 reload kanri-frontend --update-env
else
    sudo -u "$APP_USER" -H pm2 start ecosystem.config.js
fi
sudo -u "$APP_USER" -H pm2 save

echo "==> Tayyor: $KEY"
