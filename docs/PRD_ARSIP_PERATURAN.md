# PRD — Aplikasi Pengelolaan Arsip Peraturan KSPPS BMT Amal Muslim

**Versi:** 1.0
**Tanggal:** 30 Juni 2026
**Penyusun:** Tim IT BMT Amal Muslim
**Status:** Draft untuk persetujuan
**Bentuk:** **Aplikasi standalone baru** (Flask + SQLite + Bootstrap 5), deploy di VPS — bukan modul dari aplikasi yang sudah ada.

---

## 1. Ringkasan & Tujuan

### 1.1 Masalah
BMT Amal Muslim tunduk pada **banyak lapis aturan** — dari sumber syariah (Al-Qur'an, As-Sunnah, fatwa DSN-MUI), hukum positif negara (UU, PP, Permen), sampai aturan internal (AD/ART, keputusan RAT, SK pengurus). Saat ini:
- Dokumen-dokumen itu **tersebar** (lemari fisik, folder komputer, WhatsApp) tanpa satu arsip terpusat.
- Tidak ada **peta hierarki** yang jelas: aturan mana mendasari aturan mana, mana yang lebih tinggi.
- Sulit tahu **status** sebuah peraturan: masih berlaku, sudah dicabut, atau diubah.
- **Perizinan & legalitas** (NIB/OSS, izin usaha simpan pinjam, badan hukum) bisa **lewat masa berlaku** tanpa ada pengingat.
- Tidak ada alat yang membantu pengurus/DPS **mendeteksi potensi pertentangan** antara aturan internal dengan aturan yang lebih tinggi (syariah maupun negara).

### 1.2 Solusi
Sebuah **aplikasi arsip peraturan** terpusat yang:
1. **Menyimpan & mengelola dokumen** peraturan (PDF/Word/gambar) dengan metadata baku, **ekstraksi teks otomatis + OCR**, dan versioning.
2. Menempatkan tiap dokumen dalam **hierarki dua pilar** (Syariah & Hukum Positif) yang bermuara ke dua badan hukum internal BMT.
3. Menyediakan **dua mode visualisasi**: **bagan hierarki** (atas→bawah) dan **timeline interaktif** (berdasarkan waktu penetapan & perubahan).
4. Melacak **status** (berlaku/dicabut/diubah/diganti) dan **relasi antar dokumen** (mencabut, mengubah, mengganti, melaksanakan, mendasari).
5. Memiliki **Asisten AI** (LLM cloud + RAG) untuk tanya-jawab atas arsip, **abstraksi otomatis**, dan **flag indikatif potensi konflik** untuk ditinjau manusia (DPS/pengurus) — **bukan** putusan final.
6. Memberi **pengingat masa berlaku** perizinan/legalitas dan **dashboard kepatuhan**.

### 1.3 Keputusan Terkonfirmasi (user, 30 Jun 2026)
| # | Aspek | Keputusan |
|---|---|---|
| 1 | Bentuk | **Aplikasi standalone baru** (Flask + SQLite + Bootstrap), deploy VPS |
| 2 | Mesin AI | **LLM cloud** (Claude/OpenRouter via infrastruktur 9router/Hermes yang sudah ada) + RAG/embedding |
| 3 | Ambisi AI | **Asisten + flag indikatif** — AI memberi indikasi potensi konflik, manusia yang memutuskan. AI tidak mengklaim putusan final |
| 4 | Dokumen masuk | **Upload PDF/Word/gambar + OCR + ekstraksi teks full-text** untuk indeks & analisis |
| 5 | Pengguna | **Pengurus & Pengawas (DPS)** + **Admin IT** (RBAC sederhana) |
| 6 | Notifikasi | **Dalam aplikasi** (inbox/lonceng) — WA/email di luar MVP |
| 7 | Status & relasi | **Lengkap** — status + relasi antar dokumen |
| 8 | Struktur badan hukum | **Baitul Tamwil** = badan hukum Koperasi (KSPPS); **Baitul Maal** = badan hukum **LAZ MKU** (pusat Yogyakarta), operasional sebagai cabang **ULAZ MKU Amal Muslim** |
| 9 | Standar metadata | Mengacu **standar JDIH/BPHN** sejauh relevan |
| 10 | Visualisasi | **Bagan hierarki** + **timeline interaktif** |

### 1.4 Ukuran Sukses (KPI)
- Semua dokumen peraturan kunci (eksternal & internal) terarsip dengan metadata baku & teks terindeks.
- Posisi tiap dokumen dalam hierarki & statusnya tampil akurat di **bagan** dan **timeline**.
- Pencarian full-text & semantik menemukan dokumen relevan dengan cepat.
- AI menghasilkan **abstraksi** & **flag konflik indikatif** yang membantu (bukan menyesatkan) — selalu disertai kutipan sumber & disclaimer.
- **Tidak ada perizinan yang kedaluwarsa tanpa peringatan** — reminder masa berlaku berfungsi.

---

## 2. Konteks & Posisi dalam Ekosistem

BMT Amal Muslim sudah memiliki beberapa sistem (billing `bmt-tagih`, `bmt-maal`, agent laporan harian, absensi, dll). Aplikasi ini **berdiri sendiri** karena domainnya (hukum/regulasi/kepatuhan) berbeda dari aplikasi keuangan, dan penggunanya spesifik (pengurus & DPS). Namun tetap **reuse pola teknis yang sudah teruji**: Flask + SQLite (WAL), auth session, deploy VPS (systemd + nginx), dan **infrastruktur LLM 9router/Hermes** yang sudah dipakai untuk wa-bot.

> **Catatan AI/LLM:** Aplikasi memanggil LLM lewat gateway **9router/OpenRouter** (kompatibel OpenAI Chat Completions). Model default mengarah ke keluarga **Claude** (mis. `claude-opus-4-8` untuk analisis konflik mendalam, model lebih ringan untuk abstraksi/ekstraksi). API key & base URL **dari environment variable**, tidak pernah literal di kode. Bila gateway/LLM tidak tersedia, fitur AI **gagal anggun** (dokumen tetap tersimpan & dapat dicari; analisis ditandai "tertunda").

---

## 3. Model Konseptual: Hierarki Dua Pilar

Inti aplikasi adalah **hierarki dua pilar** yang sama-sama mengikat peraturan internal BMT. Banyak aturan internal harus tunduk pada **kedua** pilar sekaligus (mis. produk pembiayaan harus sah secara **fatwa DSN-MUI** *dan* patuh **UU/Permenkop**). Di titik temu inilah AI mencari potensi konflik lintas-pilar.

```
          PILAR SYARIAH (Muamalah)                 PILAR HUKUM POSITIF NKRI
   ┌───────────────────────────────┐      ┌──────────────────────────────────┐
   │ 1. AL-QUR'AN                  │      │ 1. UUD 1945 (Pasal 33 — Koperasi) │
   │ 2. AS-SUNNAH / HADITS         │      │ 2. TAP MPR                        │
   │ 3. IJMA' & QIYAS (ijtihad)    │      │ 3. UU / PERPPU                    │
   │ 4. FATWA DSN-MUI              │      │ 4. PERATURAN PEMERINTAH (PP)      │
   │    (murabahah, mudharabah,    │      │ 5. PERATURAN PRESIDEN (Perpres)   │
   │     musyarakah, ijarah, dst)  │      │ 6. PERDA PROVINSI (Jateng)        │
   │ 5. KEPUTUSAN/FATWA DPS        │      │ 7. PERDA KAB. WONOGIRI            │
   │    (internal)                 │      │ 8. PERATURAN MENTERI / LEMBAGA    │
   │                               │      │    (Permenkop-UKM, POJK,          │
   │                               │      │     Permenaker, Kemenag/BAZNAS)   │
   └───────────────────────────────┘      └──────────────────────────────────┘
                 │                                          │
                 └─────────────────────┬────────────────────┘
                                       ▼
                  ╔═══════════════════════════════════════╗
                  ║       "BMT AMAL MUSLIM" (payung)       ║
                  ╚═══════════════════════════════════════╝
                       │                            │
   ┌───────────────────┴────────────┐   ┌───────────┴──────────────────────────┐
   ▼                                ▼   ▼                                       ▼
┌──────────────────────────────────┐ ┌──────────────────────────────────────────┐
│  BAITUL TAMWIL (Divisi Bisnis)   │ │  BAITUL MAAL (Divisi Sosial / ZIS)         │
│  Badan Hukum: KOPERASI (KSPPS)   │ │  Badan Hukum: LAZ MKU (pusat Yogyakarta)   │
│                                  │ │  Operasional: cabang ULAZ MKU Amal Muslim  │
│  Dasar eksternal utama:          │ │  Dasar eksternal utama:                    │
│   • UU Perkoperasian, Permenkop  │ │   • UU 23/2011 Pengelolaan Zakat           │
│   • UU LKM, UU P2SK, POJK        │ │   • Regulasi Kemenag / BAZNAS              │
│  Dokumen internal:               │ │   • Regulasi & SOP dari LAZ MKU pusat      │
│   • AD & ART Koperasi            │ │  Dokumen internal:                         │
│   • Legalitas: Akta, Badan Hukum,│ │   • SK penunjukan/pengangkatan ULAZ        │
│     NIB/OSS, IUSP, NPWP          │ │   • Pedoman & SOP pengelolaan ZIS          │
│   • Keputusan RAT ★              │ │   • Regulasi turunan dari LAZ MKU pusat    │
│   • Peraturan Pengurus / Persus  │ │   • SK & Surat Edaran internal Maal        │
│   • SK Pengurus                  │ │   • Kontrak/akad penyaluran                │
│   • Keputusan DPS                │ │                                            │
│   • SOP/Pedoman (APU-PPT, dll)   │ │                                            │
│   • Kontrak baku akad, SE        │ │                                            │
└──────────────────────────────────┘ └──────────────────────────────────────────┘
   ★ Rapat Anggota = kekuasaan tertinggi internal koperasi

  Catatan: Regulasi KETENAGAKERJAAN (UU 13/2003 jo. UU 6/2023, PP 35/2021,
  PP 36/2021) berstatus "UMUM" — mengikat KEDUA divisi.
```

Setiap dokumen internal ditandai **entitas**-nya (**Baitul Tamwil** / **Baitul Maal** / **Umum**) agar AI memakai kerangka hukum yang tepat saat memeriksa konflik.

---

## 4. Daftar Awal Regulasi Eksternal (kerangka isi)

Daftar berikut adalah **kerangka kategori** untuk diisi & diverifikasi nomor/tahun terbarunya oleh user — karena pengisian dokumen aktual adalah pekerjaan inti aplikasi ini. Yang ditandai cukup mapan; yang lain **wajib diverifikasi** sebelum dianggap final.

### 4.1 Koperasi & Lembaga Keuangan Mikro
- UU No. **25 Tahun 1992** tentang Perkoperasian *(masih berlaku)*.
- UU No. **17 Tahun 2012** tentang Perkoperasian *(dibatalkan MK tahun 2014 — disimpan sebagai konteks historis)*.
- UU No. **1 Tahun 2013** tentang Lembaga Keuangan Mikro.
- UU No. **4 Tahun 2023** tentang Pengembangan dan Penguatan Sektor Keuangan (**P2SK**) — mengubah lanskap pengawasan koperasi sektor jasa keuangan.
- PP No. **9 Tahun 1995** tentang Pelaksanaan Kegiatan Usaha Simpan Pinjam oleh Koperasi.
- **Permenkop-UKM** terkait KSPPS/USPPS — *(perlu verifikasi nomor & tahun terkini)*.
- **POJK** untuk LKM / koperasi sektor jasa keuangan pasca UU P2SK — *(perlu verifikasi)*.

### 4.2 Syariah & ZISWAF
- UU No. **21 Tahun 2008** tentang Perbankan Syariah *(rujukan prinsip, bukan pengikat langsung)*.
- UU No. **23 Tahun 2011** tentang Pengelolaan Zakat — untuk Baitul Maal / ULAZ MKU.
- **Fatwa-fatwa DSN-MUI** atas akad (murabahah, mudharabah, musyarakah, ijarah, wakalah, qardh, dll) — *(daftar nomor fatwa diisi bertahap)*.
- Regulasi **Kemenag / BAZNAS** terkait LAZ — *(perlu verifikasi)*.

### 4.3 Ketenagakerjaan (yang dipakai sekarang)
- UU No. **13 Tahun 2003** tentang Ketenagakerjaan **jo. UU No. 6 Tahun 2023** (Cipta Kerja).
- PP No. **35 Tahun 2021** (PKWT, alih daya/outsourcing, PHK).
- PP No. **36 Tahun 2021** tentang Pengupahan.
- **Permenaker** & **UMK/UMP** Kab. Wonogiri / Prov. Jateng terkini — *(perlu verifikasi tiap tahun)*.

### 4.4 Pembentukan Peraturan (acuan tata urutan)
- UU No. **12 Tahun 2011** **jo. UU No. 13 Tahun 2022** tentang Pembentukan Peraturan Perundang-undangan — dasar tata urutan pada Pilar Hukum Positif.

> **Prinsip pengisian:** Aplikasi disiapkan **kosong terstruktur**; user/admin yang mengunggah dokumen aktual. Field bertanda "perlu verifikasi" tidak boleh diisi nomor karangan oleh sistem.

---

## 5. Pengguna & Hak Akses (RBAC)

| Peran | Hak |
|---|---|
| **Admin IT** | Kelola user, upload massal, konfigurasi AI/sistem, hard-delete, semua hak di bawah. |
| **Pengurus** | CRUD dokumen, ubah status & relasi, jalankan analisis AI, tinjau & tutup flag konflik, terima notifikasi. |
| **Pengawas / DPS** | Baca semua; **tinjau & beri keputusan** atas flag konflik (terutama syariah); beri catatan/disposisi; terima notifikasi. |

> RBAC sederhana berbasis session (pola repo). **Staf umum & manajemen tidak diberi akses pada MVP** (dapat ditambah kemudian).

---

## 6. Manajemen Dokumen (CRUD)

### 6.1 Skema Metadata (mengacu standar JDIH/BPHN sejauh relevan)
| Field | Keterangan |
|---|---|
| **Judul** | Judul resmi dokumen |
| **Pilar** | Syariah / Hukum Positif / Internal |
| **Level hierarki** | UUD, UU, PP, Perpres, Perda, Permen/Lembaga, Fatwa DSN, AD, ART, Keputusan RAT, Peraturan Pengurus, SK Pengurus, Keputusan DPS, SOP/Pedoman, Izin/Legalitas, Surat Edaran, Kontrak Akad |
| **Entitas** | Baitul Tamwil / Baitul Maal / Umum |
| **T.E.U. Badan / Otoritas penerbit** | DPR, Pemerintah, Kemenkop, OJK, DSN-MUI, Pengurus, RAT, DPS, LAZ MKU, dll |
| **Bentuk & Bentuk Singkat** | mis. "Undang-Undang" / "UU" |
| **Nomor & Tahun** | mis. "No. 25 Tahun 1992" |
| **Tempat & Tanggal Penetapan / Pengundangan** | |
| **Tanggal mulai berlaku / berakhir** | (penting utk izin & legalitas) |
| **Bidang/Subjek Hukum & Tag** | akad, simpanan, kepegawaian, ZIS, perizinan, APU-PPT, dll |
| **Status** | Draf / **Berlaku** / Diubah / Dicabut / Diganti / Kedaluwarsa |
| **Sumber** | tautan resmi / asal dokumen |
| **Abstraksi/Ringkasan** | dapat **diisi otomatis oleh AI**, lalu diverifikasi manusia |
| **File lampiran** | PDF/Word/gambar — **multi-versi** |
| **Teks hasil ekstraksi/OCR** | untuk indeks full-text & RAG (tidak ditampilkan sebagai field edit) |

### 6.2 Operasi
- **Create** — upload file → **pipeline ingest** (ekstraksi teks / OCR → chunking → embedding) jalan otomatis → **AI pra-isi** metadata (nomor, judul, tahun, abstraksi) → user **verifikasi & simpan**.
- **Read** — halaman detail: viewer PDF, teks hasil ekstraksi, posisi di hierarki, daftar relasi, status, riwayat versi, dan **flag konflik** bila ada.
- **Update** — edit metadata; **ubah status** (mis. "Berlaku" → "Dicabut"); **tambah versi file** baru (riwayat versi tetap tersimpan); tambah/ubah relasi.
- **Delete** — **soft-delete** (recycle, dapat dipulihkan); **hard-delete hanya Admin IT**. Untuk peraturan tak berlaku, **didorong pakai status "Dicabut/Diganti"** agar jejak hukum tetap ada.

### 6.3 Relasi antar dokumen
Tipe relasi: `mencabut`, `mengubah`, `mengganti`, `melaksanakan` (peraturan pelaksana), `mendasari` (dasar hukum/rujukan). Contoh: *"SK Pengurus No.X **melaksanakan** Keputusan RAT 2025"*; *"Permenkop baru **mencabut** Permenkop lama"*. Relasi inilah yang memberi makna pada timeline & analisis konflik.

### 6.4 Versioning & Audit
Tiap dokumen menyimpan **riwayat versi file** + **log audit** (siapa membuat/mengubah/mengubah status, kapan). Audit trail bersifat append-only.

---

## 7. Visualisasi

### 7.1 Bagan Hierarki (atas → bawah)
Render dua pilar bertemu di payung BMT lalu bercabang ke dua badan hukum (lihat Bagian 3). Tiap simpul = dokumen/kelompok dokumen; warna menunjukkan **status** (hijau=Berlaku, abu=Dicabut, kuning=Diubah). Klik simpul → buka detail dokumen. Dapat difilter per **pilar/entitas/jenis/status**.

### 7.2 Timeline Interaktif *(baru)*
Mode kedua: sumbu **waktu** (tahun penetapan). Tiap dokumen jadi titik/strip pada garis waktu; **relasi** (mengubah/mencabut/mengganti) digambar sebagai penghubung antar titik sehingga **riwayat hidup sebuah aturan** terlihat (mis. UU lama → diubah → dicabut → diganti). Fitur:
- **Zoom & geser** rentang waktu; kelompokkan per **pilar / entitas / jenis**.
- **Filter** status & kategori; sorot rantai relasi sebuah dokumen.
- Penanda **masa berlaku/kedaluwarsa** (izin) muncul di garis waktu.
- Klik titik → detail dokumen.
- Implementasi memakai pustaka timeline JS ringan (mis. vis-timeline atau setara), data dari endpoint `/api/timeline`.

> Kedua mode berbagi sumber data & filter yang sama; pengguna beralih lewat tab "Hierarki / Timeline".

---

## 8. Modul AI (Asisten + Flag Indikatif)

LLM cloud via 9router/OpenRouter + RAG atas teks dokumen. **Dua fungsi inti:**

### 8.1 Asisten Tanya-Jawab (RAG)
Pengguna bertanya bahasa alami ("apa dasar hukum akad murabahah kami?", "izin OSS kami kapan kedaluwarsa?"). Sistem mengambil potongan dokumen relevan (semantic search) → LLM menjawab **dengan kutipan & tautan ke dokumen sumber**. Tanpa sumber, jawaban ditandai "tidak ditemukan di arsip".

### 8.2 Pemeriksa Konflik → Flag Indikatif
Saat dokumen baru masuk atau diminta, AI membandingkan terhadap (a) dokumen lebih tinggi di hierarki kedua pilar, dan (b) dokumen sejenis yang berlaku. Bila terindikasi pertentangan, AI menerbitkan **"Flag Indikatif Konflik"** ke inbox, berisi:
- ringkasan dugaan pertentangan,
- **kutipan kedua sisi** + tautan dokumen,
- tingkat keyakinan, dan
- **disclaimer tegas: ini indikasi untuk ditinjau manusia (DPS/pengurus), bukan putusan final.**

Status flag: `Baru` → `Sedang ditinjau` → `Valid (perlu tindak lanjut)` / `Bukan konflik (ditutup)`. Keputusan & catatan peninjau tercatat.

> **Guardrail:** AI tidak pernah mengubah status dokumen atau menghapus apa pun secara otomatis. Semua aksi konsekuensial dilakukan manusia. Prompt menyertakan konteks pilar/entitas dokumen agar kerangka hukum benar.

---

## 9. Kepatuhan & Pengingat

### 9.1 Pengingat Masa Berlaku *(MVP)*
Dokumen berjenis izin/legalitas (NIB/OSS, IUSP, badan hukum, sertifikat) memiliki **tanggal berakhir**. Sistem memunculkan **pengingat in-app** pada ambang **H-30** (dapat dikonfigurasi) agar tidak ada izin kedaluwarsa tanpa peringatan.

### 9.2 Dashboard Kepatuhan *(MVP)*
Satu layar ringkasan untuk pengurus/DPS: jumlah dokumen per status, **izin yang akan kedaluwarsa**, **flag konflik terbuka**, dokumen terbaru, dan distribusi per pilar/entitas.

---

## 10. Pencarian
- **Full-text search** atas teks hasil ekstraksi/OCR + **filter** (tahun, jenis, pilar, entitas, status) — selaras standar JDIH.
- **Pencarian semantik** (embedding) untuk temuan berbasis makna, terintegrasi dengan Asisten RAG.

---

## 11. Arsitektur & Komponen

- **Web app:** Flask + SQLite (WAL, `row_factory=Row`) + Bootstrap 5, Jinja server-rendered, vanilla JS. Auth session-based, decorator `login_required`/`role_required`. API prefiks `/api/`.
- **Penyimpanan:** file fisik (folder `data/dokumen/`, terstruktur per entitas/tahun) + DB metadata. Indeks vektor (mis. SQLite + ekstensi vektor / file index) untuk embedding.
- **Pipeline ingest (worker):** ekstraksi teks PDF digital (mis. `pdfminer`/`PyMuPDF`) + **OCR** untuk hasil scan (mis. Tesseract / layanan OCR) → chunking → embedding → simpan.
- **Gateway LLM:** klien kompatibel OpenAI → 9router/OpenRouter (key & base URL dari env).
- **Modul:** `app.py` (rute & auth), `dokumen.py` (CRUD+versioning), `ingest.py` (ekstraksi/OCR/embedding), `ai.py` (RAG + pemeriksa konflik), `hierarki.py` (bagan), `timeline.py` (endpoint timeline), `kepatuhan.py` (reminder+dashboard), `models.py`/`db.py`.
- **Deploy:** VPS, systemd + nginx, pola seperti `bmt-maal/deploy/`. Secrets di `/etc/`-env (mode 0600).

### 11.1 Skema Data (ringkas)
- `dokumen` (metadata + status + entitas + pilar + level + tanggal berlaku/berakhir)
- `dokumen_versi` (file per versi + hash + waktu + pengunggah)
- `dokumen_teks` (teks hasil ekstraksi/OCR per dokumen/chunk)
- `embedding` (vektor per chunk)
- `relasi_dokumen` (dokumen_a, tipe_relasi, dokumen_b)
- `flag_konflik` (dokumen, ringkasan, kutipan, keyakinan, status, peninjau, catatan)
- `pengingat` (dokumen, jenis, tanggal_target, status)
- `notifikasi` (user, pesan, tautan, dibaca)
- `users`, `audit_log`

---

## 12. Lingkup MVP vs Fase Lanjutan

### 12.1 MVP (Fase 1)
- CRUD dokumen + metadata standar JDIH/BPHN + versioning + soft-delete + audit.
- Ingest: upload + ekstraksi teks + **OCR** + indeks.
- Hierarki dua pilar (bagan) **+ timeline interaktif**.
- Status & relasi antar dokumen lengkap.
- Pencarian full-text + semantik.
- Asisten AI RAG + **flag indikatif konflik** (inbox in-app).
- **Pengingat masa berlaku izin** + **dashboard kepatuhan**.
- RBAC (Admin IT, Pengurus, DPS) + notifikasi in-app.

### 12.2 Fase 2 (lanjutan)
- **Registrasi Kewajiban Kepatuhan** (*obligation register*): pecah peraturan jadi daftar kewajiban + penanggung jawab + status patuh/belum.
- **Pemantauan peraturan baru** (*horizon scanning*): antrean "regulasi baru/perubahan perlu ditinjau".
- **Workflow persetujuan/pengesahan** dokumen internal (Draf → ditinjau → disahkan).
- Notifikasi **WhatsApp/email** (reuse Fonnte/wa-bot).
- Akses **manajemen & staf** (baca), portal/mobile.

### 12.3 Di luar lingkup (YAGNI saat ini)
- AI yang memutus konflik secara final/otomatis tanpa manusia.
- E-sign, portal publik eksternal.

---

## 13. Keamanan & Tata Kelola
- Akses berbasis peran; semua aksi tercatat di audit log.
- File & DB hanya di server; backup berkala.
- Secrets via environment variable (tidak ada literal di kode/crontab).
- AI **read-only terhadap keputusan**: tidak ada aksi konsekuensial otomatis; manusia selalu menyetujui.
- Disclaimer hukum/syariah pada setiap output AI: **bukan nasihat hukum/fatwa final**.

---

## 14. Risiko & Mitigasi
| Risiko | Mitigasi |
|---|---|
| AI **salah menandai** konflik (false positive/negative) | Posisikan sebagai **indikatif**; wajib tinjauan manusia; tampilkan kutipan & keyakinan; mudah menutup flag |
| OCR buruk pada scan jelek | Tandai kualitas ekstraksi; izinkan koreksi/entri manual; abstraksi tetap diverifikasi manusia |
| Biaya/ketersediaan LLM | Hybrid: embedding & pencarian jalan tanpa LLM; analisis konflik on-demand; gagal anggun bila gateway mati |
| Nomor regulasi keliru | Field "perlu verifikasi"; sistem tak mengarang nomor; verifikasi manusia sebelum "Berlaku" |
| Data sensitif legal bocor | RBAC ketat, akses terbatas pengurus/DPS/admin, audit, backup terenkripsi |

---

## 15. Pertanyaan Terbuka (untuk pematangan berikutnya)
1. Pustaka OCR/ekstraksi & indeks vektor final (Tesseract vs layanan; SQLite-vss vs file index).
2. Pustaka timeline JS yang dipakai (vis-timeline / TimelineJS / kustom).
3. Daftar fatwa DSN-MUI & Permenkop/POJK terbaru yang akan diunggah pertama (perlu verifikasi user).
4. Ambang reminder masa berlaku default **H-30** (terkonfirmasi user, 30 Jun 2026); eskalasi tambahan menyusul bila perlu.

---

*Dokumen ini adalah spesifikasi desain (PRD) untuk persetujuan. Setelah disetujui, dilanjutkan ke rencana implementasi bertahap (Fase 1 lebih dulu).*
