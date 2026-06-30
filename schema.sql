-- Skema database Aplikasi Pengelolaan Arsip Peraturan KSPPS BMT Amal Muslim
-- SQLite. Semua teks Bahasa Indonesia.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- Pengguna & hak akses (RBAC: admin, pengurus, dps)
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nama          TEXT NOT NULL,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    peran         TEXT NOT NULL CHECK (peran IN ('admin', 'pengurus', 'dps')),
    aktif         INTEGER NOT NULL DEFAULT 1,
    dibuat_pada   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Dokumen peraturan (inti arsip)
CREATE TABLE IF NOT EXISTS dokumen (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    judul              TEXT NOT NULL,
    pilar              TEXT NOT NULL CHECK (pilar IN ('Syariah', 'Hukum Positif', 'Internal')),
    level_kode         TEXT NOT NULL,        -- mengacu hierarki_level.kode
    entitas            TEXT NOT NULL CHECK (entitas IN ('Baitul Tamwil', 'Baitul Maal', 'Umum')),
    otoritas           TEXT,                 -- T.E.U. Badan / penerbit
    bentuk             TEXT,                 -- mis. "Undang-Undang"
    bentuk_singkat     TEXT,                 -- mis. "UU"
    nomor              TEXT,
    tahun              INTEGER,
    tgl_penetapan      TEXT,                 -- ISO date
    tgl_mulai_berlaku  TEXT,
    tgl_berakhir       TEXT,                 -- untuk izin/legalitas (reminder H-30)
    bidang_hukum       TEXT,
    tag                TEXT,                 -- dipisah koma
    status             TEXT NOT NULL DEFAULT 'Berlaku'
                       CHECK (status IN ('Draf','Berlaku','Diubah','Dicabut','Diganti','Kedaluwarsa')),
    sumber             TEXT,
    abstraksi          TEXT,
    abstraksi_oleh_ai  INTEGER NOT NULL DEFAULT 0,
    perlu_verifikasi   INTEGER NOT NULL DEFAULT 0,
    dihapus            INTEGER NOT NULL DEFAULT 0,   -- soft delete
    dibuat_oleh        INTEGER REFERENCES users(id),
    dibuat_pada        TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    diubah_pada        TEXT
);

-- Versi file lampiran (versioning)
CREATE TABLE IF NOT EXISTS dokumen_versi (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    dokumen_id    INTEGER NOT NULL REFERENCES dokumen(id) ON DELETE CASCADE,
    versi         INTEGER NOT NULL,
    nama_file     TEXT NOT NULL,
    path_file     TEXT NOT NULL,
    ukuran        INTEGER,
    diunggah_oleh INTEGER REFERENCES users(id),
    diunggah_pada TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Teks hasil ekstraksi / OCR (untuk pencarian & RAG)
CREATE TABLE IF NOT EXISTS dokumen_teks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    dokumen_id      INTEGER NOT NULL REFERENCES dokumen(id) ON DELETE CASCADE,
    teks            TEXT,
    metode          TEXT,        -- 'pdf', 'ocr', 'manual', 'tertunda'
    status_ekstraksi TEXT NOT NULL DEFAULT 'tertunda',  -- 'selesai','tertunda','gagal'
    diperbarui_pada TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Relasi antar dokumen
CREATE TABLE IF NOT EXISTS relasi_dokumen (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    dokumen_a     INTEGER NOT NULL REFERENCES dokumen(id) ON DELETE CASCADE,
    tipe_relasi   TEXT NOT NULL CHECK (tipe_relasi IN ('mencabut','mengubah','mengganti','melaksanakan','mendasari')),
    dokumen_b     INTEGER NOT NULL REFERENCES dokumen(id) ON DELETE CASCADE,
    catatan       TEXT,
    dibuat_pada   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Flag indikatif potensi konflik (AI + manual)
CREATE TABLE IF NOT EXISTS flag_konflik (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    dokumen_id    INTEGER NOT NULL REFERENCES dokumen(id) ON DELETE CASCADE,
    dokumen_lawan INTEGER REFERENCES dokumen(id) ON DELETE SET NULL,
    ringkasan     TEXT NOT NULL,
    kutipan       TEXT,
    keyakinan     TEXT,         -- 'rendah','sedang','tinggi'
    sumber_flag   TEXT NOT NULL DEFAULT 'ai',   -- 'ai' atau 'manual'
    status        TEXT NOT NULL DEFAULT 'Baru'
                  CHECK (status IN ('Baru','Sedang ditinjau','Valid','Bukan konflik')),
    peninjau_id   INTEGER REFERENCES users(id),
    catatan_peninjau TEXT,
    dibuat_pada   TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    ditinjau_pada TEXT
);

-- Pengingat (reminder masa berlaku izin, dll)
CREATE TABLE IF NOT EXISTS pengingat (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    dokumen_id    INTEGER NOT NULL REFERENCES dokumen(id) ON DELETE CASCADE,
    jenis         TEXT NOT NULL DEFAULT 'masa_berlaku',
    tgl_target    TEXT NOT NULL,
    pesan         TEXT,
    status        TEXT NOT NULL DEFAULT 'aktif',   -- 'aktif','selesai'
    dibuat_pada   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Notifikasi in-app
CREATE TABLE IF NOT EXISTS notifikasi (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER REFERENCES users(id),   -- NULL = untuk semua pengurus/dps
    judul         TEXT NOT NULL,
    pesan         TEXT,
    tautan        TEXT,
    dibaca        INTEGER NOT NULL DEFAULT 0,
    dibuat_pada   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Log audit (append-only)
CREATE TABLE IF NOT EXISTS audit_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER REFERENCES users(id),
    aksi          TEXT NOT NULL,
    objek         TEXT,
    objek_id      INTEGER,
    keterangan    TEXT,
    waktu         TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Master level hierarki (urutan tata-urut di tiap pilar)
CREATE TABLE IF NOT EXISTS hierarki_level (
    kode      TEXT PRIMARY KEY,
    nama      TEXT NOT NULL,
    pilar     TEXT NOT NULL,
    urutan    INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dokumen_status   ON dokumen(status);
CREATE INDEX IF NOT EXISTS idx_dokumen_pilar    ON dokumen(pilar);
CREATE INDEX IF NOT EXISTS idx_dokumen_entitas  ON dokumen(entitas);
CREATE INDEX IF NOT EXISTS idx_dokumen_level    ON dokumen(level_kode);
CREATE INDEX IF NOT EXISTS idx_teks_dokumen     ON dokumen_teks(dokumen_id);
CREATE INDEX IF NOT EXISTS idx_flag_status      ON flag_konflik(status);
