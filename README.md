# Arsip Peraturan — KSPPS BMT Amal Muslim

Aplikasi pengelolaan arsip peraturan: dari sumber syariah (Al-Qur'an, As-Sunnah, fatwa DSN-MUI) & hukum positif negara (UU, PP, Permen) sampai aturan internal BMT (AD/ART, keputusan RAT, SK pengurus, dll), lengkap dengan **hierarki dua pilar**, **timeline interaktif**, **asisten AI (RAG)**, **flag indikatif konflik**, **pengingat masa berlaku izin (H-30)**, dan **dashboard kepatuhan**.

Stack: Flask + SQLite + Bootstrap 5 (server-rendered Jinja, vanilla JS). PRD: [`docs/PRD_ARSIP_PERATURAN.md`](docs/PRD_ARSIP_PERATURAN.md).

Repo: https://github.com/aguswib1308/SIS-ARSIP

## Menjalankan

```bash
cd arsip-peraturan
pip install -r requirements.txt      # minimal: Flask + requests
python seed.py                       # buat DB + isi pengguna & arsip awal regulasi
python app.py                        # http://127.0.0.1:5050
```

Login awal: `admin/admin123` · `pengurus/pengurus123` · `dps/dps123` (ganti di produksi).

Uji end-to-end (DB terpisah `test_smoke.db`):
```bash
python smoke_test.py
```

## Peran (RBAC)
- **admin** — kelola pengguna, audit, diagnostik, semua hak.
- **pengurus** — CRUD dokumen, relasi, jalankan analisis AI, kelola flag.
- **dps** — baca semua, tinjau & putuskan flag konflik.

## Fitur per modul
- **Dokumen** (`dokumen_list/detail/form`): CRUD + metadata standar JDIH/BPHN, upload file multi-versi, ekstraksi teks + OCR (opsional), soft-delete, status & relasi.
- **Hierarki** (`/hierarki`): bagan dua pilar (Syariah + Hukum Positif) → payung BMT → dua badan hukum (Baitul Tamwil/Koperasi & Baitul Maal/ULAZ MKU).
- **Timeline** (`/timeline`): visualisasi interaktif (vis-timeline) berdasarkan tahun penetapan, warna = status, klik = detail.
- **Asisten AI** (`/asisten`): tanya-jawab RAG atas arsip. Tanpa LLM aktif → tampilkan kutipan relevan.
- **Flag konflik** (`/flag`): indikasi potensi pertentangan (AI/manual) untuk ditinjau manusia; bukan putusan final.
- **Dashboard** (`/`): ringkasan kepatuhan + pengingat izin H-30.

## Konfigurasi AI (opsional, gagal anggun)
LLM via gateway kompatibel OpenAI (9router/OpenRouter). Set environment variable:
```bash
export ARSIP_LLM_BASE_URL="http://127.0.0.1:9100/v1"
export ARSIP_LLM_API_KEY="xxxx"
export ARSIP_LLM_MODEL="claude-opus-4-8"
export ARSIP_REMINDER_HARI=30
export ARSIP_SECRET_KEY="..."
```
Tanpa LLM: arsip, pencairan, hierarki, timeline, reminder tetap berjalan; jawaban RAG menampilkan kutipan & analisis konflik otomatis nonaktif (flag manual tetap bisa).

## OCR (opsional)
Untuk PDF hasil scan, pasang `pytesseract` + Tesseract OCR (bahasa `ind`), `pdf2image` + poppler, `Pillow`. Lihat status di **Admin → Diagnostik Sistem**. Tanpa ini, teks dapat diisi manual per dokumen.

## Deploy ke VPS
Pola sama seperti `bmt-maal` (gunicorn + systemd + nginx). Port: gunicorn `127.0.0.1:5050`, nginx IP `:8090` (agar tak bentrok dengan billing & maal di VPS yang sama).

```bash
# Di VPS, sebagai root:
git clone https://github.com/aguswib1308/SIS-ARSIP.git /var/www/sis-arsip
cd /var/www/sis-arsip
bash deploy/setup_vps.sh          # venv, /etc/sis-arsip.env, seed DB, service, nginx, ufw 8090
# Akses: http://IP_VPS:8090

# Update berikutnya:
cd /var/www/sis-arsip && bash deploy/update_vps.sh
```
Rahasia (SECRET_KEY, kredensial LLM) ada di `/etc/sis-arsip.env` (mode 0600, dibuat otomatis). Service: `systemctl {status,restart} sis-arsip`. Domain + HTTPS: arahkan DNS lalu `certbot --nginx`, dan aktifkan blok domain di `deploy/nginx-arsip.conf`.

## Catatan data regulasi
Nomor regulasi eksternal diisi dari sumber resmi (BPK/JDIH, OJK, DSN-MUI). Dokumen **internal BMT** berisi contoh realistis bertanda *perlu verifikasi* — sesuaikan dengan dokumen asli (nomor badan hukum, NIB, IUSP, dsb).
