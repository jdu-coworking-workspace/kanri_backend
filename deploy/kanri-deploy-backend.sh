#!/usr/bin/env bash
# Backend artifactini S3 dan olib, migration va systemd restartni bajaradi.
#
#   /usr/local/bin/kanri-deploy-backend.sh deploy/backend-<sha>.tar.gz
#
# Bucket nomi /etc/kanri-deploy.env dan olinadi. S3 ga kirish instance role
# orqali amalga oshadi.

set -euo pipefail

KEY="${1:?Ishlatilishi: kanri-deploy-backend.sh deploy/backend-<sha>.tar.gz}"
APP_DIR=/var/www/kanri/backend
APP_USER=kanri
SERVICE=kanri-api

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
aws s3 cp "s3://$DEPLOY_BUCKET/$KEY" "$TMP/backend.tar.gz"

mkdir -p "$TMP/new"
tar -xzf "$TMP/backend.tar.gz" -C "$TMP/new"

for required in alembic.ini migrations requirements.txt src; do
    if [ ! -e "$TMP/new/$required" ]; then
        echo "XATO: artifact ichida $required topilmadi." >&2
        exit 1
    fi
done

mkdir -p "$APP_DIR"
chown "$APP_USER:$APP_USER" "$APP_DIR"
# rsync runs as the application user, so it must be able to traverse TMP.
chmod a+rx "$TMP"
chmod -R a+rX "$TMP/new"

echo "==> Fayllar ko'chirilmoqda"
# .env, venv va media production serverda saqlanadi.
sudo -u "$APP_USER" -H rsync -a --delete \
    --exclude .env \
    --exclude venv \
    --exclude media \
    "$TMP/new/" "$APP_DIR/"

echo "==> Python dependency lar"
sudo -u "$APP_USER" -H "$APP_DIR/venv/bin/pip" install \
    --disable-pip-version-check -r "$APP_DIR/requirements.txt"

echo "==> Database migration"
cd "$APP_DIR"
sudo -u "$APP_USER" -H "$APP_DIR/venv/bin/alembic" upgrade head

echo "==> Systemd restart"
systemctl daemon-reload
systemctl restart "$SERVICE"
systemctl is-active --quiet "$SERVICE"

echo "==> Health check"
for attempt in $(seq 1 15); do
    if curl --fail --silent --show-error --max-time 5 \
        http://127.0.0.1:8000/ >/dev/null; then
        break
    fi
    if [ "$attempt" -eq 15 ]; then
        echo "XATO: backend health check 15 urinishdan keyin ham muvaffaqiyatsiz." >&2
        exit 1
    fi
    sleep 1
done

echo "==> Tayyor: $KEY"
