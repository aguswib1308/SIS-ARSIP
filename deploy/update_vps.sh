#!/bin/bash
# Update kode di VPS (jalankan sebagai root):
#   cd /var/www/sis-arsip && bash deploy/update_vps.sh
set -e
APP_DIR=/var/www/sis-arsip
cd $APP_DIR

echo "=== 1. Tarik kode terbaru dari GitHub ==="
git pull origin main

echo "=== 2. Update dependencies ==="
venv/bin/pip install -r requirements.txt -q
venv/bin/pip install gunicorn -q

echo "=== 3. Migrasi skema (aman, hanya buat tabel baru bila belum ada) ==="
sudo -u www-data venv/bin/python -c "import db; db.init_db()"

echo "=== 4. Perbaiki kepemilikan & restart ==="
chown -R www-data:www-data $APP_DIR
systemctl restart sis-arsip
nginx -t && systemctl reload nginx

echo "=== SELESAI ==="
systemctl status sis-arsip --no-pager | head -8
