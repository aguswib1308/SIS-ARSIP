"""Uji end-to-end ringan: jalankan semua fitur utama via Flask test client.
Memakai database terpisah (test_smoke.db) agar tidak mengganggu data asli.
Jalankan: python smoke_test.py
"""
import os
import sys

import config

# Arahkan ke DB uji SEBELUM modul lain memakai config.DB_PATH.
config.DB_PATH = os.path.join(config.DATA_DIR, "test_smoke.db")
for ext in ("", "-wal", "-shm"):
    p = config.DB_PATH + ext
    if os.path.exists(p):
        os.remove(p)

import seed
import app as appmod

GAGAL = []


def cek(nama, kondisi, detail=""):
    status = "OK  " if kondisi else "GAGAL"
    print(f"[{status}] {nama}" + (f" — {detail}" if detail and not kondisi else ""))
    if not kondisi:
        GAGAL.append(nama)


def login(client, username, password):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=True)


def main():
    seed.seed_all(reset=True)
    appmod.app.config["TESTING"] = True
    c = appmod.app.test_client()

    # 1. Auth
    r = login(c, "pengurus", "pengurus123")
    cek("Login pengurus", r.status_code == 200 and "Dashboard" in r.get_data(as_text=True))
    r = c.get("/login")
    r2 = appmod.app.test_client().post("/login", data={"username": "pengurus", "password": "salah"}, follow_redirects=True)
    cek("Tolak sandi salah", "salah" in r2.get_data(as_text=True).lower())

    # 2. Dashboard + reminder izin (H-30)
    r = c.get("/")
    html = r.get_data(as_text=True)
    cek("Dashboard tampil", r.status_code == 200)
    cek("Reminder izin muncul (H-30)", "Kedaluwarsa" in html or "hari" in html, "izin mendekati/lewat tidak terdeteksi")

    # 3. Daftar dokumen + pencarian
    r = c.get("/dokumen")
    cek("Daftar dokumen", r.status_code == 200)
    r = c.get("/dokumen?q=murabahah")
    cek("Pencarian full-text 'murabahah'", "Murabahah" in r.get_data(as_text=True))
    r = c.get("/dokumen?pilar=Syariah")
    cek("Filter pilar Syariah", r.status_code == 200 and "Fatwa" in r.get_data(as_text=True))

    # 4. Detail dokumen
    r = c.get("/dokumen/1")
    cek("Detail dokumen", r.status_code == 200 and "Metadata" in r.get_data(as_text=True))

    # 5. Hierarki & timeline
    r = c.get("/hierarki")
    h = r.get_data(as_text=True)
    cek("Hierarki dua pilar", r.status_code == 200 and "Baitul Tamwil" in h and "Baitul Maal" in h)
    r = c.get("/timeline")
    cek("Halaman timeline", r.status_code == 200)
    r = c.get("/api/timeline")
    data = r.get_json()
    cek("API timeline JSON", r.status_code == 200 and len(data.get("items", [])) > 10,
        f"items={len(data.get('items', [])) if data else 0}")
    cek("Timeline 3 grup pilar", data and len(data.get("groups", [])) == 3)

    # 6. Asisten AI (RAG fallback tanpa LLM)
    r = c.post("/asisten", data={"pertanyaan": "apa dasar hukum akad murabahah"}, follow_redirects=True)
    a = r.get_data(as_text=True)
    cek("Asisten RAG menemukan dokumen relevan", "Murabahah" in a)

    # 7. Flag konflik (seed berisi 1 contoh) + tinjau
    r = c.get("/flag")
    cek("Daftar flag konflik", r.status_code == 200 and "indikatif" in r.get_data(as_text=True).lower())
    r = c.post("/flag/1/tinjau", data={"status": "Sedang ditinjau", "catatan": "uji"}, follow_redirects=True)
    cek("Tinjau flag (ubah status)", r.status_code == 200 and "Sedang ditinjau" in r.get_data(as_text=True))

    # 8. CRUD: buat dokumen baru
    r = c.post("/dokumen/baru", data={
        "judul": "SOP Uji Otomatis", "pilar": "Internal", "level_kode": "sop",
        "entitas": "Baitul Tamwil", "status": "Draf", "tahun": "2026", "tag": "uji",
    }, follow_redirects=True)
    cek("Buat dokumen baru", r.status_code == 200 and "SOP Uji Otomatis" in r.get_data(as_text=True))

    # 9. Relasi + flag manual pada dokumen baru
    baru = appmod.dbmod  # akses db via app context
    with appmod.app.test_request_context():
        db = baru.get_db()
        did = db.execute("SELECT id FROM dokumen WHERE judul='SOP Uji Otomatis'").fetchone()["id"]
    r = c.post(f"/dokumen/{did}/flag-manual", data={"ringkasan": "uji manual", "keyakinan": "rendah"}, follow_redirects=True)
    cek("Flag manual", r.status_code == 200)

    # 10. RBAC: DPS tidak boleh buat dokumen
    cdps = appmod.app.test_client()
    login(cdps, "dps", "dps123")
    r = cdps.get("/dokumen/baru")
    cek("RBAC: DPS ditolak buat dokumen (403)", r.status_code == 403)
    r = cdps.get("/flag")
    cek("RBAC: DPS boleh akses flag", r.status_code == 200)

    # 11. Admin-only
    cadm = appmod.app.test_client()
    login(cadm, "admin", "admin123")
    r = cadm.get("/admin/pengguna")
    cek("Admin: kelola pengguna", r.status_code == 200)
    r = cadm.get("/admin/diagnostik")
    cek("Admin: diagnostik", r.status_code == 200)
    r = c.get("/admin/pengguna")  # pengurus
    cek("RBAC: pengurus ditolak admin (403)", r.status_code == 403)

    print("\n" + ("=" * 40))
    if GAGAL:
        print(f"HASIL: {len(GAGAL)} GAGAL -> {GAGAL}")
        sys.exit(1)
    print("HASIL: SEMUA UJI LULUS [OK]")


if __name__ == "__main__":
    main()
