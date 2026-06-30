"""Seed data: pengguna, level hierarki, dan arsip awal regulasi relevan BMT.

Nomor regulasi diisi berdasarkan riset sumber resmi (BPK/JDIH, OJK, DSN-MUI).
Dokumen internal BMT bersifat CONTOH realistis (perlu disesuaikan data asli).
Jalankan: python seed.py  (tambah --reset untuk kosongkan dulu).
"""
import sys
import sqlite3
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

import config
import db as dbmod
from hierarki import LEVELS

HARI_INI = date(2026, 6, 30)  # sinkron dgn konteks proyek


def _conn():
    c = sqlite3.connect(config.DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


# (judul, pilar, level_kode, entitas, otoritas, bentuk, bentuk_singkat, nomor, tahun,
#  status, tag, abstraksi, perlu_verifikasi, tgl_penetapan, tgl_berakhir)
DOKUMEN = [
    # ---------- PILAR SYARIAH ----------
    ("Al-Qur'an (sumber utama muamalah)", "Syariah", "alquran", "Umum",
     "Wahyu", "Kitab Suci", "", "", None, "Berlaku", "muamalah, riba, jual beli",
     "Sumber hukum tertinggi muamalah syariah; mis. QS Al-Baqarah:275 menghalalkan jual beli & mengharamkan riba.", 0, None, None),
    ("As-Sunnah / Hadits Nabi tentang muamalah", "Syariah", "assunnah", "Umum",
     "Nabi Muhammad SAW", "Hadits", "", "", None, "Berlaku", "muamalah, akad, amanah",
     "Sumber kedua; dasar akad mudharabah, musyarakah, larangan gharar & riba.", 0, None, None),
    ("Fatwa DSN-MUI tentang Murabahah", "Syariah", "fatwa_dsn", "Baitul Tamwil",
     "DSN-MUI", "Fatwa", "Fatwa", "No. 04/DSN-MUI/IV/2000", 2000, "Berlaku", "akad, murabahah, pembiayaan",
     "Ketentuan akad murabahah (jual beli dengan margin) sebagai dasar produk pembiayaan jual beli BMT.", 0, "2000-04-01", None),
    ("Fatwa DSN-MUI tentang Pembiayaan Mudharabah (Qiradh)", "Syariah", "fatwa_dsn", "Baitul Tamwil",
     "DSN-MUI", "Fatwa", "Fatwa", "No. 07/DSN-MUI/IV/2000", 2000, "Berlaku", "akad, mudharabah, bagi hasil",
     "Ketentuan pembiayaan mudharabah (bagi hasil) antara shahibul maal dan mudharib.", 0, "2000-04-01", None),
    ("Fatwa DSN-MUI tentang Pembiayaan Musyarakah", "Syariah", "fatwa_dsn", "Baitul Tamwil",
     "DSN-MUI", "Fatwa", "Fatwa", "No. 08/DSN-MUI/IV/2000", 2000, "Berlaku", "akad, musyarakah",
     "Ketentuan akad musyarakah (kongsi modal usaha bersama).", 0, "2000-04-01", None),
    ("Fatwa DSN-MUI tentang Pembiayaan Ijarah", "Syariah", "fatwa_dsn", "Baitul Tamwil",
     "DSN-MUI", "Fatwa", "Fatwa", "No. 09/DSN-MUI/IV/2000", 2000, "Berlaku", "akad, ijarah, sewa",
     "Ketentuan akad ijarah (sewa-menyewa / sewa jasa).", 0, "2000-04-01", None),
    ("Fatwa DSN-MUI tentang Wakalah", "Syariah", "fatwa_dsn", "Umum",
     "DSN-MUI", "Fatwa", "Fatwa", "No. 10/DSN-MUI/IV/2000", 2000, "Berlaku", "akad, wakalah",
     "Ketentuan akad wakalah (pemberian kuasa).", 0, "2000-04-01", None),
    ("Fatwa DSN-MUI tentang Tabungan", "Syariah", "fatwa_dsn", "Baitul Tamwil",
     "DSN-MUI", "Fatwa", "Fatwa", "No. 02/DSN-MUI/IV/2000", 2000, "Berlaku", "simpanan, tabungan, wadiah, mudharabah",
     "Dasar produk simpanan/tabungan syariah (wadiah & mudharabah).", 0, "2000-04-01", None),
    ("Fatwa DSN-MUI tentang Al-Qardh", "Syariah", "fatwa_dsn", "Umum",
     "DSN-MUI", "Fatwa", "Fatwa", "No. 19/DSN-MUI/IV/2001", 2001, "Berlaku", "akad, qardh, pinjaman kebajikan",
     "Ketentuan pinjaman kebajikan (qardh) tanpa tambahan; dasar qardhul hasan dari dana Maal.", 0, "2001-04-18", None),
    ("Keputusan DPS tentang Kesesuaian Syariah Produk Pembiayaan BMT", "Syariah", "fatwa_dps", "Baitul Tamwil",
     "Dewan Pengawas Syariah BMT Amal Muslim", "Keputusan DPS", "Kep. DPS", "No. 01/DPS-AM/2024", 2024, "Berlaku",
     "syariah, produk, pengawasan", "Penegasan kesesuaian syariah produk pembiayaan & simpanan BMT mengacu fatwa DSN-MUI.", 1, "2024-02-01", None),

    # ---------- PILAR HUKUM POSITIF ----------
    ("UUD 1945 Pasal 33 (Perekonomian & Koperasi)", "Hukum Positif", "uud", "Umum",
     "MPR RI", "Undang-Undang Dasar", "UUD", "Pasal 33 UUD 1945", 1945, "Berlaku", "konstitusi, koperasi, ekonomi",
     "Dasar konstitusional koperasi sebagai sokoguru ekonomi kerakyatan.", 0, None, None),
    ("UU tentang Perkoperasian", "Hukum Positif", "uu", "Baitul Tamwil",
     "DPR RI & Pemerintah", "Undang-Undang", "UU", "No. 25 Tahun 1992", 1992, "Berlaku", "koperasi, badan hukum",
     "UU induk perkoperasian yang berlaku saat ini (UU 17/2012 dibatalkan MK).", 0, "1992-10-21", None),
    ("UU tentang Perkoperasian (dibatalkan MK)", "Hukum Positif", "uu", "Baitul Tamwil",
     "DPR RI & Pemerintah", "Undang-Undang", "UU", "No. 17 Tahun 2012", 2012, "Dicabut", "koperasi, dibatalkan",
     "Dibatalkan Mahkamah Konstitusi tahun 2014; disimpan sebagai konteks historis.", 0, "2012-10-30", None),
    ("UU tentang Lembaga Keuangan Mikro", "Hukum Positif", "uu", "Baitul Tamwil",
     "DPR RI & Pemerintah", "Undang-Undang", "UU", "No. 1 Tahun 2013", 2013, "Berlaku", "lkm, keuangan mikro, ojk",
     "Mengatur kelembagaan & pengawasan Lembaga Keuangan Mikro.", 0, "2013-01-08", None),
    ("UU tentang Pengembangan & Penguatan Sektor Keuangan (P2SK)", "Hukum Positif", "uu", "Baitul Tamwil",
     "DPR RI & Pemerintah", "Undang-Undang", "UU", "No. 4 Tahun 2023", 2023, "Berlaku", "p2sk, koperasi sektor jasa keuangan, ojk",
     "Mengubah lanskap pengawasan koperasi sektor jasa keuangan & keuangan syariah.", 0, "2023-01-12", None),
    ("UU tentang Pengelolaan Zakat", "Hukum Positif", "uu", "Baitul Maal",
     "DPR RI & Pemerintah", "Undang-Undang", "UU", "No. 23 Tahun 2011", 2011, "Berlaku", "zakat, ziswaf, baznas, laz",
     "Dasar pengelolaan zakat oleh BAZNAS & LAZ; rujukan utama Baitul Maal / ULAZ MKU.", 0, "2011-11-25", None),
    ("UU tentang Perbankan Syariah", "Hukum Positif", "uu", "Baitul Tamwil",
     "DPR RI & Pemerintah", "Undang-Undang", "UU", "No. 21 Tahun 2008", 2008, "Berlaku", "syariah, prinsip, rujukan",
     "Rujukan prinsip syariah perbankan (bukan pengikat langsung BMT).", 0, "2008-07-16", None),
    ("UU tentang Ketenagakerjaan", "Hukum Positif", "uu", "Umum",
     "DPR RI & Pemerintah", "Undang-Undang", "UU", "No. 13 Tahun 2003", 2003, "Diubah", "ketenagakerjaan, karyawan, pkwt",
     "UU induk ketenagakerjaan; sebagian diubah UU Cipta Kerja (UU 6/2023).", 0, "2003-03-25", None),
    ("UU tentang Cipta Kerja", "Hukum Positif", "uu", "Umum",
     "DPR RI & Pemerintah", "Undang-Undang", "UU", "No. 6 Tahun 2023", 2023, "Berlaku", "cipta kerja, ketenagakerjaan",
     "Penetapan Perppu 2/2022 menjadi UU; mengubah ketentuan ketenagakerjaan yang berlaku sekarang.", 0, "2023-03-31", None),
    ("UU tentang Pembentukan Peraturan Perundang-undangan", "Hukum Positif", "uu", "Umum",
     "DPR RI & Pemerintah", "Undang-Undang", "UU", "No. 12 Tahun 2011 jo. No. 13 Tahun 2022", 2011, "Berlaku", "tata urutan, legislasi",
     "Dasar tata urutan peraturan perundang-undangan (hierarki Pilar Hukum Positif).", 0, "2011-08-12", None),
    ("PP tentang Pelaksanaan Kegiatan Usaha Simpan Pinjam oleh Koperasi", "Hukum Positif", "pp", "Baitul Tamwil",
     "Pemerintah", "Peraturan Pemerintah", "PP", "No. 9 Tahun 1995", 1995, "Berlaku", "simpan pinjam, koperasi",
     "Mengatur pelaksanaan kegiatan usaha simpan pinjam oleh koperasi.", 0, "1995-09-18", None),
    ("PP tentang PKWT, Alih Daya, Waktu Kerja & PHK", "Hukum Positif", "pp", "Umum",
     "Pemerintah", "Peraturan Pemerintah", "PP", "No. 35 Tahun 2021", 2021, "Berlaku", "pkwt, outsourcing, phk, ketenagakerjaan",
     "Aturan pelaksana ketenagakerjaan turunan Cipta Kerja.", 0, "2021-02-02", None),
    ("PP tentang Pengupahan", "Hukum Positif", "pp", "Umum",
     "Pemerintah", "Peraturan Pemerintah", "PP", "No. 36 Tahun 2021", 2021, "Berlaku", "upah, umk, pengupahan",
     "Aturan pengupahan turunan Cipta Kerja (dasar penghitungan upah karyawan).", 0, "2021-02-02", None),
    ("Permenkop UKM tentang Pelaksanaan Kegiatan USPPS oleh Koperasi", "Hukum Positif", "permen", "Baitul Tamwil",
     "Menteri Koperasi & UKM", "Peraturan Menteri", "Permenkop", "No. 16/Per/M.KUKM/IX/2015", 2015, "Berlaku", "kspps, uspps, syariah",
     "Dasar operasional Usaha Simpan Pinjam & Pembiayaan Syariah (USPPS/KSPPS) oleh koperasi.", 1, "2015-09-25", None),
    ("Permenkop UKM tentang Pelaksanaan Kegiatan USP & Pembiayaan Syariah oleh Koperasi", "Hukum Positif", "permen", "Baitul Tamwil",
     "Menteri Koperasi & UKM", "Peraturan Menteri", "Permenkop", "No. 11/Per/M.KUKM/XII/2017", 2017, "Dicabut", "uspps, syariah",
     "Penyempurnaan pengaturan USPPS; berstatus tidak berlaku (digantikan pengaturan berikutnya).", 1, "2017-12-18", None),
    ("Permenkop UKM tentang Perizinan Usaha Simpan Pinjam Koperasi", "Hukum Positif", "permen", "Baitul Tamwil",
     "Menteri Koperasi & UKM", "Peraturan Menteri", "Permenkop", "No. 11 Tahun 2018", 2018, "Berlaku", "izin, simpan pinjam",
     "Mengatur perizinan usaha simpan pinjam koperasi.", 1, "2018-08-22", None),
    ("POJK tentang Perizinan Usaha & Kelembagaan LKM", "Hukum Positif", "permen", "Baitul Tamwil",
     "Otoritas Jasa Keuangan", "Peraturan OJK", "POJK", "No. 12/POJK.05/2014", 2014, "Berlaku", "lkm, izin, ojk",
     "Perizinan usaha & kelembagaan Lembaga Keuangan Mikro.", 1, "2014-08-21", None),
    ("POJK tentang Penyelenggaraan Usaha LKM", "Hukum Positif", "permen", "Baitul Tamwil",
     "Otoritas Jasa Keuangan", "Peraturan OJK", "POJK", "No. 13/POJK.05/2014", 2014, "Berlaku", "lkm, usaha, ojk, syariah",
     "Penyelenggaraan usaha LKM termasuk berdasarkan prinsip syariah.", 1, "2014-08-21", None),
    ("POJK tentang Pembinaan & Pengawasan LKM", "Hukum Positif", "permen", "Baitul Tamwil",
     "Otoritas Jasa Keuangan", "Peraturan OJK", "POJK", "No. 14/POJK.05/2014", 2014, "Berlaku", "lkm, pengawasan, ojk",
     "Pembinaan & pengawasan Lembaga Keuangan Mikro.", 1, "2014-08-21", None),

    # ---------- INTERNAL: BAITUL TAMWIL (KOPERASI) ----------
    ("Anggaran Dasar KSPPS BMT Amal Muslim", "Internal", "ad", "Baitul Tamwil",
     "Rapat Anggota", "Anggaran Dasar", "AD", "AD/BMT-AM", 2016, "Berlaku", "ad, badan hukum, koperasi",
     "Anggaran Dasar koperasi: nama, tempat kedudukan, maksud-tujuan, keanggotaan, permodalan, perangkat organisasi.", 1, "2016-01-01", None),
    ("Anggaran Rumah Tangga KSPPS BMT Amal Muslim", "Internal", "art", "Baitul Tamwil",
     "Rapat Anggota", "Anggaran Rumah Tangga", "ART", "ART/BMT-AM", 2016, "Berlaku", "art, tata laksana",
     "Penjabaran AD: tata laksana keanggotaan, rapat, kepengurusan, pembagian SHU.", 1, "2016-01-01", None),
    ("Pengesahan Badan Hukum Koperasi", "Internal", "legalitas", "Baitul Tamwil",
     "Kementerian Koperasi & UKM", "Akta/SK Badan Hukum", "Badan Hukum", "No. BH (perlu diisi)", 2016, "Berlaku", "legalitas, badan hukum",
     "Surat Pengesahan Akta Pendirian / Badan Hukum koperasi.", 1, "2016-01-15", None),
    ("Nomor Induk Berusaha (NIB) via OSS", "Internal", "legalitas", "Baitul Tamwil",
     "Lembaga OSS", "NIB", "NIB", "NIB (perlu diisi)", 2021, "Berlaku", "oss, nib, perizinan",
     "Nomor Induk Berusaha dari sistem OSS; perlu pemantauan masa berlaku/pembaruan data.", 1, "2021-03-01",
     (HARI_INI + timedelta(days=15)).isoformat()),  # contoh: jatuh tempo 15 hari -> uji reminder
    ("Izin Usaha Simpan Pinjam (IUSP)", "Internal", "legalitas", "Baitul Tamwil",
     "Kementerian Koperasi & UKM", "Izin Usaha", "IUSP", "IUSP (perlu diisi)", 2021, "Berlaku", "izin, simpan pinjam",
     "Izin operasional usaha simpan pinjam koperasi; perlu pemantauan perpanjangan.", 1, "2021-06-20",
     (HARI_INI - timedelta(days=10)).isoformat()),  # contoh: sudah lewat -> uji reminder
    ("Keputusan Rapat Anggota Tahunan (RAT) Tahun Buku 2025", "Internal", "keputusan_rat", "Baitul Tamwil",
     "Rapat Anggota", "Keputusan RAT", "Kep. RAT", "No. 01/RAT/2026", 2026, "Berlaku", "rat, shu, kebijakan",
     "Pengesahan laporan pengurus, pembagian SHU, rencana kerja & RAPB tahun berjalan. Kekuasaan tertinggi koperasi.", 1, "2026-02-15", None),
    ("Peraturan Pengurus tentang Kepegawaian & Disiplin Karyawan", "Internal", "peraturan_pengurus", "Umum",
     "Pengurus", "Peraturan Pengurus", "Perpeng", "No. 02/PP/2024", 2024, "Berlaku", "kepegawaian, disiplin, sdm",
     "Aturan internal kepegawaian: jam kerja, cuti, sanksi; harus selaras UU Ketenagakerjaan & turunannya.", 1, "2024-01-10", None),
    ("SK Pengurus tentang Pengangkatan Pengelola/Manajer", "Internal", "sk_pengurus", "Baitul Tamwil",
     "Pengurus", "Surat Keputusan", "SK", "No. 05/SK/2025", 2025, "Berlaku", "sk, pengelola, struktur",
     "Pengangkatan pengelola & struktur manajemen pelaksana.", 1, "2025-01-05", None),
    ("Keputusan DPS tentang Penerapan Akad pada Produk BMT", "Internal", "keputusan_dps", "Baitul Tamwil",
     "Dewan Pengawas Syariah", "Keputusan DPS", "Kep. DPS", "No. 02/DPS-AM/2024", 2024, "Berlaku", "dps, akad, kepatuhan syariah",
     "Penetapan penerapan akad murabahah, mudharabah, ijarah pada produk; mengacu fatwa DSN-MUI.", 1, "2024-03-01", None),
    ("SOP Pembiayaan Murabahah", "Internal", "sop", "Baitul Tamwil",
     "Pengelola", "Standar Operasional Prosedur", "SOP", "SOP-PMB-01", 2024, "Berlaku", "sop, murabahah, pembiayaan",
     "Prosedur pengajuan, analisis, akad, pencairan & penagihan pembiayaan murabahah.", 1, "2024-04-01", None),
    ("Pedoman APU-PPT (Anti Pencucian Uang & Pencegahan Pendanaan Terorisme)", "Internal", "sop", "Umum",
     "Pengelola", "Pedoman", "Pedoman", "PED-APUPPT-01", 2023, "Berlaku", "apu-ppt, kepatuhan, cdd",
     "Pedoman penerapan prinsip mengenali nasabah (CDD) & pelaporan transaksi mencurigakan.", 1, "2023-06-01", None),
    ("Surat Edaran Pengurus tentang Kebijakan Simpanan Anggota", "Internal", "surat_edaran", "Baitul Tamwil",
     "Pengurus", "Surat Edaran", "SE", "No. 01/SE/2026", 2026, "Berlaku", "se, simpanan, anggota",
     "Penyesuaian nisbah/ketentuan simpanan anggota tahun berjalan.", 1, "2026-01-20", None),

    # ---------- INTERNAL: BAITUL MAAL (LAZ MKU / ULAZ MKU AMAL MUSLIM) ----------
    ("SK Penunjukan ULAZ MKU Amal Muslim (cabang LAZ MKU)", "Internal", "legalitas", "Baitul Maal",
     "LAZ MKU Pusat Yogyakarta", "Surat Keputusan", "SK", "SK-ULAZ (perlu diisi)", 2020, "Berlaku", "ulaz, laz mku, penunjukan",
     "Penunjukan unit pengelola/cabang LAZ MKU di Wonogiri sebagai ULAZ MKU Amal Muslim.", 1, "2020-01-01", None),
    ("Pedoman Pengelolaan ZIS dari LAZ MKU Pusat", "Internal", "sop", "Baitul Maal",
     "LAZ MKU Pusat", "Pedoman", "Pedoman", "PED-ZIS-MKU", 2022, "Berlaku", "zis, ziswaf, pengelolaan, penyaluran",
     "Pedoman penghimpunan & penyaluran ZIS yang wajib diikuti cabang; selaras UU 23/2011.", 1, "2022-01-01", None),
    ("SK Pengelola Baitul Maal / Amil ULAZ", "Internal", "sk_pengurus", "Baitul Maal",
     "Pengurus / LAZ MKU", "Surat Keputusan", "SK", "No. 03/SK-Maal/2025", 2025, "Berlaku", "amil, maal, sdm",
     "Pengangkatan amil/pengelola dana sosial Baitul Maal.", 1, "2025-02-01", None),
]

# Relasi antar dokumen (judul_a, tipe, judul_b)
RELASI = [
    ("UU tentang Cipta Kerja", "mengubah", "UU tentang Ketenagakerjaan"),
    ("Permenkop UKM tentang Perizinan Usaha Simpan Pinjam Koperasi", "mendasari", "Izin Usaha Simpan Pinjam (IUSP)"),
    ("Anggaran Rumah Tangga KSPPS BMT Amal Muslim", "melaksanakan", "Anggaran Dasar KSPPS BMT Amal Muslim"),
    ("SK Pengurus tentang Pengangkatan Pengelola/Manajer", "melaksanakan", "Keputusan Rapat Anggota Tahunan (RAT) Tahun Buku 2025"),
    ("SOP Pembiayaan Murabahah", "melaksanakan", "Fatwa DSN-MUI tentang Murabahah"),
    ("Peraturan Pengurus tentang Kepegawaian & Disiplin Karyawan", "mendasari", "PP tentang PKWT, Alih Daya, Waktu Kerja & PHK"),
    ("Pedoman Pengelolaan ZIS dari LAZ MKU Pusat", "melaksanakan", "UU tentang Pengelolaan Zakat"),
]

# Contoh flag indikatif (judul_dok, judul_lawan, ringkasan, keyakinan)
FLAG_CONTOH = [
    ("SOP Pembiayaan Murabahah", "Fatwa DSN-MUI tentang Murabahah",
     "Potensi: klausul denda keterlambatan pada SOP perlu ditinjau agar tidak menjadi tambahan riba; "
     "selaraskan dengan ketentuan ta'zir/ta'widh dalam fatwa DSN-MUI terkait.", "sedang"),
]


def seed_all(reset=False):
    dbmod.init_db()
    conn = _conn()
    cur = conn.cursor()

    if reset:
        for t in ("flag_konflik", "relasi_dokumen", "dokumen_teks", "dokumen_versi",
                  "pengingat", "notifikasi", "dokumen", "audit_log", "hierarki_level"):
            cur.execute(f"DELETE FROM {t}")
        conn.commit()

    # Pengguna
    if not cur.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        for nama, uname, pw, peran in [
            ("Admin IT", "admin", "admin123", "admin"),
            ("Pengurus BMT", "pengurus", "pengurus123", "pengurus"),
            ("Pengawas Syariah (DPS)", "dps", "dps123", "dps"),
        ]:
            cur.execute("INSERT INTO users (nama, username, password_hash, peran) VALUES (?,?,?,?)",
                        (nama, uname, generate_password_hash(pw), peran))

    # Level hierarki
    cur.execute("DELETE FROM hierarki_level")
    for kode, nama, pilar, urutan in LEVELS:
        cur.execute("INSERT INTO hierarki_level (kode, nama, pilar, urutan) VALUES (?,?,?,?)",
                    (kode, nama, pilar, urutan))

    # Dokumen
    judul_ke_id = {}
    if not cur.execute("SELECT 1 FROM dokumen LIMIT 1").fetchone():
        for d in DOKUMEN:
            (judul, pilar, level, entitas, otoritas, bentuk, bsingkat, nomor, tahun,
             status, tag, abstraksi, pv) = d[:13]
            tgl_penetapan = d[13] if len(d) > 13 else None
            tgl_berakhir = d[14] if len(d) > 14 else None
            cur.execute(
                "INSERT INTO dokumen (judul, pilar, level_kode, entitas, otoritas, bentuk, bentuk_singkat, "
                "nomor, tahun, status, tag, abstraksi, perlu_verifikasi, tgl_penetapan, tgl_mulai_berlaku, "
                "tgl_berakhir, dibuat_oleh) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
                (judul, pilar, level, entitas, otoritas, bentuk, bsingkat, nomor, tahun,
                 status, tag, abstraksi, pv, tgl_penetapan, tgl_penetapan, tgl_berakhir))
            did = cur.lastrowid
            judul_ke_id[judul] = did
            # teks awal (pakai abstraksi sbg korpus pencarian/RAG)
            cur.execute("INSERT INTO dokumen_teks (dokumen_id, teks, metode, status_ekstraksi) VALUES (?,?, 'manual','selesai')",
                        (did, f"{judul}. {abstraksi} Tag: {tag}."))
        conn.commit()

        # Relasi
        for ja, tipe, jb in RELASI:
            if ja in judul_ke_id and jb in judul_ke_id:
                cur.execute("INSERT INTO relasi_dokumen (dokumen_a, tipe_relasi, dokumen_b) VALUES (?,?,?)",
                            (judul_ke_id[ja], tipe, judul_ke_id[jb]))

        # Flag contoh
        for jd, jl, ring, keyakinan in FLAG_CONTOH:
            if jd in judul_ke_id:
                cur.execute("INSERT INTO flag_konflik (dokumen_id, dokumen_lawan, ringkasan, keyakinan, sumber_flag, status) "
                            "VALUES (?,?,?,?, 'ai', 'Baru')",
                            (judul_ke_id[jd], judul_ke_id.get(jl), ring, keyakinan))

    conn.commit()
    n_dok = cur.execute("SELECT COUNT(*) c FROM dokumen").fetchone()["c"]
    n_user = cur.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    conn.close()
    print(f"Seed selesai: {n_user} pengguna, {n_dok} dokumen, {len(RELASI)} relasi, {len(FLAG_CONTOH)} flag contoh.")
    print("Login: admin/admin123 · pengurus/pengurus123 · dps/dps123")


if __name__ == "__main__":
    seed_all(reset="--reset" in sys.argv)
