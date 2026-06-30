#!/bin/bash
# Setup pertama kali di VPS (jalankan sebagai root):
#   git clone https://github.com/aguswib1308/SIS-ARSIP.git /var/www/sis-arsip
#   cd /var/www/sis-arsip && bash deploy/setup_vps.sh
set -e
APP_DIR=/var/www/sis-arsip
ENV_FILE=/etc/sis-arsip.env

echo "=== 1. Dependencies sistem ==="
apt-get update -qq
apt-get install -y python3-pip python3-venv
# Opsional OCR (hapus komentar bila perlu OCR PDF hasil scan):
# apt-get install -y tesseract-ocr tesseract-ocr-ind poppler-utils

echo "=== 2. Folder log ==="
mkdir -p /var/log/sis-arsip
chown www-data:www-data /var/log/sis-arsip

echo "=== 3. File environment (rahasia) ==="
if [ ! -f "$ENV_FILE" ]; then
  SECRET=$(python3 -c 'import os;print(os.urandom(32).hex())')
  cat > "$ENV_FILE" <<EOF
ARSIP_SECRET_KEY=$SECRET
ARSIP_REMINDER_HARI=30
# Isi bila ingin AI aktif (gateway 9router/OpenRouter, kompatibel OpenAI):
# ARSIP_LLM_BASE_URL=http://127.0.0.1:9100/v1
# ARSIP_LLM_API_KEY=
# ARSIP_LLM_MODEL=claude-opus-4-8
EOF
  chmod 600 "$ENV_FILE"
  echo "  dibuat $ENV_FILE (mode 600)"
else
  echo "  $ENV_FILE sudah ada, dilewati"
fi

echo "=== 4. Virtualenv & requirements ==="
cd $APP_DIR
python3 -m venv venv
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt -q
venv/bin/pip install gunicorn -q

echo "=== 5. Data dir + inisialisasi DB & seed (pertama kali) ==="
mkdir -p data
chown -R www-data:www-data $APP_DIR
sudo -u www-data venv/bin/python seed.py

echo "=== 6. Systemd service ==="
cp deploy/sis-arsip.service /etc/systemd/system/sis-arsip.service
systemctl daemon-reload
systemctl enable sis-arsip
systemctl restart sis-arsip

echo "=== 7. Nginx ==="
cp deploy/nginx-arsip.conf /etc/nginx/sites-available/sis-arsip
ln -sf /etc/nginx/sites-available/sis-arsip /etc/nginx/sites-enabled/sis-arsip
nginx -t && systemctl reload nginx

echo "=== 8. Firewall (UFW) port 8090 ==="
ufw allow 8090/tcp 2>/dev/null || true

IP=$(hostname -I | awk '{print $1}')
echo ""
echo "======================================"
echo " SELESAI!"
echo " Akses : http://$IP:8090"
echo " Login : admin/admin123 - pengurus/pengurus123 - dps/dps123"
echo " GANTI password default & isi $ENV_FILE untuk AI."
echo "======================================"
systemctl status sis-arsip --no-pager | head -8
