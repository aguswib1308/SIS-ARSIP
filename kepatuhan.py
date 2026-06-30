"""Logika kepatuhan: pengingat masa berlaku (H-30) & data dashboard."""
from datetime import date, datetime

import config


def _parse_tgl(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s[:19], fmt).date()
        except Exception:
            continue
    return None


def izin_akan_kedaluwarsa(db, hari=None):
    """Dokumen berjenis izin/legalitas yang berakhir <= H-x dari hari ini (atau sudah lewat)."""
    hari = config.REMINDER_HARI if hari is None else hari
    hari_ini = date.today()
    rows = db.execute(
        "SELECT id, judul, nomor, tahun, tgl_berakhir, status, entitas "
        "FROM dokumen WHERE dihapus=0 AND tgl_berakhir IS NOT NULL AND tgl_berakhir != ''"
    ).fetchall()
    hasil = []
    for r in rows:
        tgl = _parse_tgl(r["tgl_berakhir"])
        if not tgl:
            continue
        selisih = (tgl - hari_ini).days
        if selisih <= hari:
            hasil.append({
                "id": r["id"], "judul": r["judul"], "nomor": r["nomor"], "tahun": r["tahun"],
                "tgl_berakhir": r["tgl_berakhir"], "entitas": r["entitas"], "status": r["status"],
                "sisa_hari": selisih,
                "kedaluwarsa": selisih < 0,
            })
    hasil.sort(key=lambda x: x["sisa_hari"])
    return hasil


def sinkron_pengingat(db):
    """Buat/segarkan baris pengingat untuk izin yang mendekati kedaluwarsa. Idempoten."""
    daftar = izin_akan_kedaluwarsa(db)
    dibuat = 0
    for it in daftar:
        ada = db.execute(
            "SELECT id FROM pengingat WHERE dokumen_id=? AND jenis='masa_berlaku' AND status='aktif'",
            (it["id"],),
        ).fetchone()
        if ada:
            continue
        pesan = (f"Izin/legalitas '{it['judul']}' "
                 + ("SUDAH kedaluwarsa" if it["kedaluwarsa"] else f"berakhir dalam {it['sisa_hari']} hari")
                 + f" (berakhir {it['tgl_berakhir']}).")
        db.execute(
            "INSERT INTO pengingat (dokumen_id, jenis, tgl_target, pesan) VALUES (?,?,?,?)",
            (it["id"], "masa_berlaku", it["tgl_berakhir"], pesan),
        )
        db.execute(
            "INSERT INTO notifikasi (user_id, judul, pesan, tautan) VALUES (NULL, ?, ?, ?)",
            ("Pengingat masa berlaku", pesan, f"/dokumen/{it['id']}"),
        )
        dibuat += 1
    db.commit()
    return dibuat


def ringkasan_dashboard(db):
    """Angka-angka untuk dashboard kepatuhan."""
    total = db.execute("SELECT COUNT(*) c FROM dokumen WHERE dihapus=0").fetchone()["c"]
    per_status = {r["status"]: r["c"] for r in db.execute(
        "SELECT status, COUNT(*) c FROM dokumen WHERE dihapus=0 GROUP BY status").fetchall()}
    per_pilar = {r["pilar"]: r["c"] for r in db.execute(
        "SELECT pilar, COUNT(*) c FROM dokumen WHERE dihapus=0 GROUP BY pilar").fetchall()}
    per_entitas = {r["entitas"]: r["c"] for r in db.execute(
        "SELECT entitas, COUNT(*) c FROM dokumen WHERE dihapus=0 GROUP BY entitas").fetchall()}
    flag_terbuka = db.execute(
        "SELECT COUNT(*) c FROM flag_konflik WHERE status IN ('Baru','Sedang ditinjau')").fetchone()["c"]
    izin = izin_akan_kedaluwarsa(db)
    terbaru = db.execute(
        "SELECT id, judul, nomor, tahun, status, dibuat_pada FROM dokumen "
        "WHERE dihapus=0 ORDER BY id DESC LIMIT 5").fetchall()
    return {
        "total": total,
        "per_status": per_status,
        "per_pilar": per_pilar,
        "per_entitas": per_entitas,
        "flag_terbuka": flag_terbuka,
        "izin": izin,
        "izin_jumlah": len(izin),
        "terbaru": terbaru,
        "reminder_hari": config.REMINDER_HARI,
    }
