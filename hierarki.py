"""Data hierarki dua pilar & penyusunan struktur bagan/timeline."""

# Master level (dipakai juga oleh seed untuk mengisi tabel hierarki_level).
LEVELS = [
    # (kode, nama, pilar, urutan)
    ("alquran",    "Al-Qur'an",                         "Syariah", 1),
    ("assunnah",   "As-Sunnah / Hadits",                "Syariah", 2),
    ("ijma",       "Ijma' & Qiyas",                     "Syariah", 3),
    ("fatwa_dsn",  "Fatwa DSN-MUI",                     "Syariah", 4),
    ("fatwa_dps",  "Keputusan/Fatwa DPS",               "Syariah", 5),

    ("uud",        "UUD 1945",                          "Hukum Positif", 1),
    ("tap_mpr",    "Ketetapan MPR",                     "Hukum Positif", 2),
    ("uu",         "UU / Perppu",                       "Hukum Positif", 3),
    ("pp",         "Peraturan Pemerintah",              "Hukum Positif", 4),
    ("perpres",    "Peraturan Presiden",                "Hukum Positif", 5),
    ("perda_prov", "Perda Provinsi",                    "Hukum Positif", 6),
    ("perda_kab",  "Perda Kabupaten",                   "Hukum Positif", 7),
    ("permen",     "Peraturan Menteri / Lembaga",       "Hukum Positif", 8),

    ("ad",         "Anggaran Dasar (AD)",               "Internal", 1),
    ("art",        "Anggaran Rumah Tangga (ART)",       "Internal", 2),
    ("legalitas",  "Legalitas & Perizinan",             "Internal", 3),
    ("keputusan_rat", "Keputusan Rapat Anggota",        "Internal", 4),
    ("peraturan_pengurus", "Peraturan Pengurus / Persus", "Internal", 5),
    ("sk_pengurus", "SK Pengurus",                      "Internal", 6),
    ("keputusan_dps", "Keputusan DPS",                  "Internal", 7),
    ("sop",        "SOP / Pedoman / Kebijakan",         "Internal", 8),
    ("surat_edaran", "Surat Edaran",                    "Internal", 9),
    ("kontrak_akad", "Kontrak / Akad Baku",             "Internal", 10),
]

LEVEL_NAMA = {k: n for (k, n, _p, _u) in LEVELS}
LEVEL_PILAR = {k: p for (k, _n, p, _u) in LEVELS}


def levels_per_pilar():
    out = {"Syariah": [], "Hukum Positif": [], "Internal": []}
    for kode, nama, pilar, urutan in sorted(LEVELS, key=lambda x: (x[2], x[3])):
        out[pilar].append({"kode": kode, "nama": nama, "urutan": urutan})
    return out


def bagan_data(db):
    """Struktur untuk halaman hierarki: per pilar -> per level -> daftar dokumen.
    Untuk Internal, dokumen dikelompokkan per entitas badan hukum."""
    dokumen = db.execute(
        "SELECT id, judul, nomor, tahun, status, pilar, level_kode, entitas "
        "FROM dokumen WHERE dihapus=0 ORDER BY tahun"
    ).fetchall()

    struktur = {p: {} for p in ("Syariah", "Hukum Positif", "Internal")}
    for kode, nama, pilar, urutan in LEVELS:
        struktur[pilar][kode] = {"nama": nama, "urutan": urutan, "dokumen": []}

    for d in dokumen:
        pilar = d["pilar"]
        kode = d["level_kode"]
        if pilar in struktur and kode in struktur[pilar]:
            struktur[pilar][kode]["dokumen"].append(dict(d))

    # urutkan level
    hasil = {}
    for pilar, levels in struktur.items():
        hasil[pilar] = sorted(levels.values(), key=lambda x: x["urutan"])
    return hasil


def timeline_items(db):
    """Item untuk vis-timeline. group berdasarkan pilar."""
    rows = db.execute(
        "SELECT id, judul, nomor, tahun, status, pilar, entitas, tgl_penetapan "
        "FROM dokumen WHERE dihapus=0 AND tahun IS NOT NULL ORDER BY tahun"
    ).fetchall()
    groups = [
        {"id": "Syariah", "content": "Pilar Syariah"},
        {"id": "Hukum Positif", "content": "Pilar Hukum Positif"},
        {"id": "Internal", "content": "Internal BMT"},
    ]
    items = []
    for r in rows:
        start = r["tgl_penetapan"] or f"{r['tahun']}-01-01"
        label = (r["nomor"] + " — " if r["nomor"] else "") + r["judul"]
        items.append({
            "id": r["id"],
            "group": r["pilar"],
            "content": (label[:60] + "…") if len(label) > 60 else label,
            "start": start,
            "title": f"{r['judul']} ({r['status']})",
            "className": "status-" + r["status"].lower().replace(" ", "-"),
        })
    # relasi sebagai garis penghubung waktu (vis-timeline tidak menggambar edge antar item,
    # jadi relasi ditampilkan di halaman detail; di sini cukup item).
    return {"groups": groups, "items": items}
