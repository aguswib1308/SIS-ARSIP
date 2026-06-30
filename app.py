"""Aplikasi Pengelolaan Arsip Peraturan KSPPS BMT Amal Muslim.
Flask + SQLite + Bootstrap 5, server-rendered. Bahasa Indonesia.
"""
import os
import functools
from datetime import datetime

from flask import (Flask, render_template, request, redirect, url_for, session,
                   flash, g, jsonify, send_from_directory, abort)
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

import config
import db as dbmod
import ingest
import ai as aimod
import hierarki
import kepatuhan

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
app.teardown_appcontext(dbmod.close_db)


# ------------------------- Auth & RBAC -------------------------
def login_required(f):
    @functools.wraps(f)
    def wrap(*a, **k):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.path))
        return f(*a, **k)
    return wrap


def role_required(*peran):
    def deco(f):
        @functools.wraps(f)
        def wrap(*a, **k):
            if not session.get("user_id"):
                return redirect(url_for("login", next=request.path))
            if session.get("peran") not in peran:
                abort(403)
            return f(*a, **k)
        return wrap
    return deco


@app.context_processor
def inject_global():
    n = 0
    if session.get("user_id"):
        try:
            n = dbmod.get_db().execute(
                "SELECT COUNT(*) c FROM notifikasi WHERE dibaca=0 AND (user_id IS NULL OR user_id=?)",
                (session["user_id"],)).fetchone()["c"]
        except Exception:
            n = 0
    return {"notif_count": n, "nama_user": session.get("nama"),
            "peran_user": session.get("peran"), "llm_aktif": config.llm_aktif()}


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = dbmod.get_db()
        u = db.execute("SELECT * FROM users WHERE username=? AND aktif=1", (username,)).fetchone()
        if u and check_password_hash(u["password_hash"], password):
            session.clear()
            session["user_id"] = u["id"]
            session["nama"] = u["nama"]
            session["peran"] = u["peran"]
            dbmod.catat_audit(u["id"], "login", "user", u["id"])
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Username atau kata sandi salah.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    if session.get("user_id"):
        dbmod.catat_audit(session["user_id"], "logout", "user", session["user_id"])
    session.clear()
    return redirect(url_for("login"))


# ------------------------- Dashboard -------------------------
@app.route("/")
@login_required
def dashboard():
    db = dbmod.get_db()
    kepatuhan.sinkron_pengingat(db)
    data = kepatuhan.ringkasan_dashboard(db)
    return render_template("dashboard.html", d=data)


# ------------------------- Dokumen (CRUD) -------------------------
@app.route("/dokumen")
@login_required
def dokumen_list():
    db = dbmod.get_db()
    q = request.args.get("q", "").strip()
    f_pilar = request.args.get("pilar", "")
    f_entitas = request.args.get("entitas", "")
    f_status = request.args.get("status", "")
    f_tahun = request.args.get("tahun", "")

    sql = ("SELECT d.id, d.judul, d.nomor, d.tahun, d.pilar, d.entitas, d.level_kode, "
           "d.status, d.perlu_verifikasi FROM dokumen d WHERE d.dihapus=0")
    par = []
    if q:
        sql += (" AND d.id IN (SELECT d2.id FROM dokumen d2 "
                "LEFT JOIN dokumen_teks t ON t.dokumen_id=d2.id "
                "WHERE d2.judul LIKE ? OR d2.nomor LIKE ? OR COALESCE(d2.tag,'') LIKE ? "
                "OR COALESCE(d2.abstraksi,'') LIKE ? OR COALESCE(t.teks,'') LIKE ?)")
        like = f"%{q}%"
        par += [like, like, like, like, like]
    if f_pilar:
        sql += " AND d.pilar=?"; par.append(f_pilar)
    if f_entitas:
        sql += " AND d.entitas=?"; par.append(f_entitas)
    if f_status:
        sql += " AND d.status=?"; par.append(f_status)
    if f_tahun:
        sql += " AND d.tahun=?"; par.append(f_tahun)
    sql += " ORDER BY d.pilar, d.tahun DESC, d.id DESC"
    rows = db.execute(sql, par).fetchall()
    return render_template("dokumen_list.html", rows=rows, q=q,
                           f_pilar=f_pilar, f_entitas=f_entitas, f_status=f_status, f_tahun=f_tahun,
                           level_nama=hierarki.LEVEL_NAMA)


@app.route("/dokumen/baru", methods=["GET", "POST"])
@role_required("admin", "pengurus")
def dokumen_baru():
    db = dbmod.get_db()
    if request.method == "POST":
        dok_id = _simpan_dokumen(db, None)
        flash("Dokumen tersimpan.", "success")
        return redirect(url_for("dokumen_detail", dok_id=dok_id))
    return render_template("dokumen_form.html", dok=None, versi=[], relasi=[],
                           levels=hierarki.levels_per_pilar(), semua=_semua_dokumen_ringkas(db))


@app.route("/dokumen/<int:dok_id>")
@login_required
def dokumen_detail(dok_id):
    db = dbmod.get_db()
    dok = db.execute("SELECT * FROM dokumen WHERE id=? AND dihapus=0", (dok_id,)).fetchone()
    if not dok:
        abort(404)
    teks = db.execute("SELECT * FROM dokumen_teks WHERE dokumen_id=?", (dok_id,)).fetchone()
    versi = db.execute("SELECT * FROM dokumen_versi WHERE dokumen_id=? ORDER BY versi DESC", (dok_id,)).fetchall()
    relasi = db.execute(
        "SELECT r.id, r.tipe_relasi, r.catatan, d.id dok_id, d.judul, d.nomor "
        "FROM relasi_dokumen r JOIN dokumen d ON d.id=r.dokumen_b WHERE r.dokumen_a=?", (dok_id,)).fetchall()
    relasi_balik = db.execute(
        "SELECT r.id, r.tipe_relasi, d.id dok_id, d.judul, d.nomor "
        "FROM relasi_dokumen r JOIN dokumen d ON d.id=r.dokumen_a WHERE r.dokumen_b=?", (dok_id,)).fetchall()
    flags = db.execute("SELECT * FROM flag_konflik WHERE dokumen_id=? ORDER BY id DESC", (dok_id,)).fetchall()
    return render_template("dokumen_detail.html", dok=dok, teks=teks, versi=versi,
                           relasi=relasi, relasi_balik=relasi_balik, flags=flags,
                           level_nama=hierarki.LEVEL_NAMA, semua=_semua_dokumen_ringkas(db, kecuali=dok_id))


@app.route("/dokumen/<int:dok_id>/edit", methods=["GET", "POST"])
@role_required("admin", "pengurus")
def dokumen_edit(dok_id):
    db = dbmod.get_db()
    dok = db.execute("SELECT * FROM dokumen WHERE id=? AND dihapus=0", (dok_id,)).fetchone()
    if not dok:
        abort(404)
    if request.method == "POST":
        _simpan_dokumen(db, dok_id)
        flash("Perubahan tersimpan.", "success")
        return redirect(url_for("dokumen_detail", dok_id=dok_id))
    return render_template("dokumen_form.html", dok=dok, levels=hierarki.levels_per_pilar(),
                           semua=_semua_dokumen_ringkas(db, kecuali=dok_id))


@app.route("/dokumen/<int:dok_id>/hapus", methods=["POST"])
@role_required("admin", "pengurus")
def dokumen_hapus(dok_id):
    db = dbmod.get_db()
    db.execute("UPDATE dokumen SET dihapus=1, diubah_pada=? WHERE id=?",
               (datetime.now().isoformat(timespec="seconds"), dok_id))
    db.commit()
    dbmod.catat_audit(session["user_id"], "hapus_dokumen", "dokumen", dok_id)
    flash("Dokumen dipindahkan ke arsip terhapus (soft-delete).", "warning")
    return redirect(url_for("dokumen_list"))


def _simpan_dokumen(db, dok_id):
    f = request.form
    fields = dict(
        judul=f.get("judul", "").strip(),
        pilar=f.get("pilar", "Internal"),
        level_kode=f.get("level_kode", ""),
        entitas=f.get("entitas", "Umum"),
        otoritas=f.get("otoritas", "").strip(),
        bentuk=f.get("bentuk", "").strip(),
        bentuk_singkat=f.get("bentuk_singkat", "").strip(),
        nomor=f.get("nomor", "").strip(),
        tahun=_int_or_none(f.get("tahun")),
        tgl_penetapan=f.get("tgl_penetapan", "").strip(),
        tgl_mulai_berlaku=f.get("tgl_mulai_berlaku", "").strip(),
        tgl_berakhir=f.get("tgl_berakhir", "").strip(),
        bidang_hukum=f.get("bidang_hukum", "").strip(),
        tag=f.get("tag", "").strip(),
        status=f.get("status", "Berlaku"),
        sumber=f.get("sumber", "").strip(),
        abstraksi=f.get("abstraksi", "").strip(),
        perlu_verifikasi=1 if f.get("perlu_verifikasi") else 0,
    )
    if dok_id is None:
        cols = ",".join(fields.keys())
        ph = ",".join("?" for _ in fields)
        cur = db.execute(f"INSERT INTO dokumen ({cols}, dibuat_oleh) VALUES ({ph}, ?)",
                         list(fields.values()) + [session["user_id"]])
        dok_id = cur.lastrowid
        db.commit()
        dbmod.catat_audit(session["user_id"], "buat_dokumen", "dokumen", dok_id, fields["judul"])
    else:
        setc = ",".join(f"{k}=?" for k in fields)
        db.execute(f"UPDATE dokumen SET {setc}, diubah_pada=? WHERE id=?",
                   list(fields.values()) + [datetime.now().isoformat(timespec="seconds"), dok_id])
        db.commit()
        dbmod.catat_audit(session["user_id"], "ubah_dokumen", "dokumen", dok_id, fields["judul"])

    # Upload file (opsional) -> versi baru + ekstraksi teks
    file = request.files.get("file")
    if file and file.filename:
        _proses_unggah(db, dok_id, file)
    return dok_id


def _proses_unggah(db, dok_id, file):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in config.ALLOWED_EXT:
        flash(f"Jenis file {ext} tidak diizinkan.", "danger")
        return
    last = db.execute("SELECT COALESCE(MAX(versi),0) v FROM dokumen_versi WHERE dokumen_id=?", (dok_id,)).fetchone()["v"]
    versi = last + 1
    aman = secure_filename(file.filename) or f"dok{dok_id}{ext}"
    nama_simpan = f"dok{dok_id}_v{versi}_{aman}"
    path = os.path.join(config.UPLOAD_DIR, nama_simpan)
    file.save(path)
    db.execute("INSERT INTO dokumen_versi (dokumen_id, versi, nama_file, path_file, ukuran, diunggah_oleh) "
               "VALUES (?,?,?,?,?,?)",
               (dok_id, versi, file.filename, path, os.path.getsize(path), session["user_id"]))
    # Ekstraksi teks
    teks, metode, status = ingest.ekstrak_teks(path)
    ada = db.execute("SELECT id FROM dokumen_teks WHERE dokumen_id=?", (dok_id,)).fetchone()
    if ada:
        db.execute("UPDATE dokumen_teks SET teks=?, metode=?, status_ekstraksi=?, diperbarui_pada=? WHERE dokumen_id=?",
                   (teks, metode, status, datetime.now().isoformat(timespec="seconds"), dok_id))
    else:
        db.execute("INSERT INTO dokumen_teks (dokumen_id, teks, metode, status_ekstraksi) VALUES (?,?,?,?)",
                   (dok_id, teks, metode, status))
    db.commit()
    if status == "selesai":
        flash(f"File diunggah (versi {versi}) & teks terekstraksi ({metode}).", "success")
    else:
        flash(f"File diunggah (versi {versi}). Ekstraksi teks tertunda "
              f"(pustaka OCR/PDF belum tersedia di server) — dapat diisi manual.", "warning")


@app.route("/dokumen/<int:dok_id>/teks", methods=["POST"])
@role_required("admin", "pengurus")
def dokumen_teks_manual(dok_id):
    db = dbmod.get_db()
    teks = request.form.get("teks", "")
    ada = db.execute("SELECT id FROM dokumen_teks WHERE dokumen_id=?", (dok_id,)).fetchone()
    if ada:
        db.execute("UPDATE dokumen_teks SET teks=?, metode='manual', status_ekstraksi='selesai', diperbarui_pada=? WHERE dokumen_id=?",
                   (teks, datetime.now().isoformat(timespec="seconds"), dok_id))
    else:
        db.execute("INSERT INTO dokumen_teks (dokumen_id, teks, metode, status_ekstraksi) VALUES (?,?, 'manual','selesai')",
                   (dok_id, teks))
    db.commit()
    flash("Teks dokumen diperbarui.", "success")
    return redirect(url_for("dokumen_detail", dok_id=dok_id))


@app.route("/file/<int:versi_id>")
@login_required
def unduh_file(versi_id):
    db = dbmod.get_db()
    v = db.execute("SELECT * FROM dokumen_versi WHERE id=?", (versi_id,)).fetchone()
    if not v:
        abort(404)
    direktori = os.path.dirname(v["path_file"])
    return send_from_directory(direktori, os.path.basename(v["path_file"]),
                               as_attachment=False, download_name=v["nama_file"])


# ------------------------- Relasi -------------------------
@app.route("/dokumen/<int:dok_id>/relasi", methods=["POST"])
@role_required("admin", "pengurus")
def relasi_tambah(dok_id):
    db = dbmod.get_db()
    tipe = request.form.get("tipe_relasi")
    lawan = _int_or_none(request.form.get("dokumen_b"))
    catatan = request.form.get("catatan", "").strip()
    if lawan and tipe:
        db.execute("INSERT INTO relasi_dokumen (dokumen_a, tipe_relasi, dokumen_b, catatan) VALUES (?,?,?,?)",
                   (dok_id, tipe, lawan, catatan))
        db.commit()
        flash("Relasi ditambahkan.", "success")
    return redirect(url_for("dokumen_detail", dok_id=dok_id))


@app.route("/relasi/<int:rid>/hapus", methods=["POST"])
@role_required("admin", "pengurus")
def relasi_hapus(rid):
    db = dbmod.get_db()
    r = db.execute("SELECT dokumen_a FROM relasi_dokumen WHERE id=?", (rid,)).fetchone()
    db.execute("DELETE FROM relasi_dokumen WHERE id=?", (rid,))
    db.commit()
    return redirect(url_for("dokumen_detail", dok_id=r["dokumen_a"]) if r else url_for("dokumen_list"))


# ------------------------- Hierarki & Timeline -------------------------
@app.route("/hierarki")
@login_required
def hal_hierarki():
    db = dbmod.get_db()
    return render_template("hierarki.html", bagan=hierarki.bagan_data(db))


@app.route("/timeline")
@login_required
def hal_timeline():
    return render_template("timeline.html")


@app.route("/api/timeline")
@login_required
def api_timeline():
    db = dbmod.get_db()
    return jsonify(hierarki.timeline_items(db))


# ------------------------- Asisten AI -------------------------
@app.route("/asisten", methods=["GET", "POST"])
@login_required
def asisten():
    hasil = None
    pertanyaan = ""
    if request.method == "POST":
        pertanyaan = request.form.get("pertanyaan", "").strip()
        if pertanyaan:
            hasil = aimod.jawab(dbmod.get_db(), pertanyaan)
    return render_template("asisten.html", hasil=hasil, pertanyaan=pertanyaan)


# ------------------------- Flag Konflik -------------------------
@app.route("/flag")
@login_required
def flag_list():
    db = dbmod.get_db()
    status = request.args.get("status", "")
    sql = ("SELECT fk.*, d.judul dok_judul, d.nomor dok_nomor, dl.judul lawan_judul "
           "FROM flag_konflik fk JOIN dokumen d ON d.id=fk.dokumen_id "
           "LEFT JOIN dokumen dl ON dl.id=fk.dokumen_lawan")
    par = []
    if status:
        sql += " WHERE fk.status=?"; par.append(status)
    sql += " ORDER BY fk.id DESC"
    rows = db.execute(sql, par).fetchall()
    return render_template("flag_list.html", rows=rows, status=status)


@app.route("/dokumen/<int:dok_id>/periksa", methods=["POST"])
@role_required("admin", "pengurus")
def periksa_konflik(dok_id):
    db = dbmod.get_db()
    lawan = _int_or_none(request.form.get("dokumen_lawan"))
    if not lawan:
        flash("Pilih dokumen pembanding.", "danger")
        return redirect(url_for("dokumen_detail", dok_id=dok_id))
    hasil = aimod.periksa_konflik(db, dok_id, lawan)
    if not hasil.get("ok"):
        flash(hasil.get("error", "Analisis gagal."), "warning")
        return redirect(url_for("dokumen_detail", dok_id=dok_id))
    if hasil.get("ada_potensi"):
        db.execute("INSERT INTO flag_konflik (dokumen_id, dokumen_lawan, ringkasan, kutipan, keyakinan, sumber_flag) "
                   "VALUES (?,?,?,?,?, 'ai')",
                   (dok_id, lawan, hasil.get("ringkasan", ""), str(hasil.get("kutipan", "")),
                    hasil.get("keyakinan", "rendah")))
        db.execute("INSERT INTO notifikasi (user_id, judul, pesan, tautan) VALUES (NULL,?,?,?)",
                   ("Flag konflik baru (AI)", hasil.get("ringkasan", "")[:200], f"/dokumen/{dok_id}"))
        db.commit()
        flash("AI menandai POTENSI konflik (indikatif). Silakan ditinjau.", "warning")
    else:
        flash("AI tidak menemukan indikasi konflik.", "success")
    return redirect(url_for("dokumen_detail", dok_id=dok_id))


@app.route("/dokumen/<int:dok_id>/flag-manual", methods=["POST"])
@login_required
def flag_manual(dok_id):
    db = dbmod.get_db()
    db.execute("INSERT INTO flag_konflik (dokumen_id, dokumen_lawan, ringkasan, keyakinan, sumber_flag) "
               "VALUES (?,?,?,?, 'manual')",
               (dok_id, _int_or_none(request.form.get("dokumen_lawan")),
                request.form.get("ringkasan", "").strip(), request.form.get("keyakinan", "sedang")))
    db.commit()
    flash("Flag manual dibuat.", "success")
    return redirect(url_for("dokumen_detail", dok_id=dok_id))


@app.route("/flag/<int:fid>/tinjau", methods=["POST"])
@login_required
def flag_tinjau(fid):
    db = dbmod.get_db()
    status = request.form.get("status")
    catatan = request.form.get("catatan", "").strip()
    if status in ("Baru", "Sedang ditinjau", "Valid", "Bukan konflik"):
        db.execute("UPDATE flag_konflik SET status=?, catatan_peninjau=?, peninjau_id=?, ditinjau_pada=? WHERE id=?",
                   (status, catatan, session["user_id"], datetime.now().isoformat(timespec="seconds"), fid))
        db.commit()
        dbmod.catat_audit(session["user_id"], "tinjau_flag", "flag_konflik", fid, status)
        flash("Keputusan peninjauan tersimpan.", "success")
    return redirect(request.referrer or url_for("flag_list"))


# ------------------------- Notifikasi -------------------------
@app.route("/notifikasi")
@login_required
def notifikasi():
    db = dbmod.get_db()
    rows = db.execute(
        "SELECT * FROM notifikasi WHERE user_id IS NULL OR user_id=? ORDER BY id DESC LIMIT 100",
        (session["user_id"],)).fetchall()
    db.execute("UPDATE notifikasi SET dibaca=1 WHERE dibaca=0 AND (user_id IS NULL OR user_id=?)",
               (session["user_id"],))
    db.commit()
    return render_template("notifikasi.html", rows=rows)


# ------------------------- Admin: pengguna & audit -------------------------
@app.route("/admin/pengguna")
@role_required("admin")
def admin_pengguna():
    db = dbmod.get_db()
    rows = db.execute("SELECT id, nama, username, peran, aktif, dibuat_pada FROM users ORDER BY id").fetchall()
    return render_template("admin_pengguna.html", rows=rows)


@app.route("/admin/pengguna/baru", methods=["POST"])
@role_required("admin")
def admin_pengguna_baru():
    from werkzeug.security import generate_password_hash
    db = dbmod.get_db()
    try:
        db.execute("INSERT INTO users (nama, username, password_hash, peran) VALUES (?,?,?,?)",
                   (request.form["nama"].strip(), request.form["username"].strip(),
                    generate_password_hash(request.form["password"]), request.form["peran"]))
        db.commit()
        flash("Pengguna ditambahkan.", "success")
    except Exception as e:
        flash(f"Gagal: {e}", "danger")
    return redirect(url_for("admin_pengguna"))


@app.route("/admin/audit")
@role_required("admin")
def admin_audit():
    db = dbmod.get_db()
    rows = db.execute(
        "SELECT a.*, u.nama FROM audit_log a LEFT JOIN users u ON u.id=a.user_id "
        "ORDER BY a.id DESC LIMIT 200").fetchall()
    return render_template("admin_audit.html", rows=rows)


@app.route("/admin/diagnostik")
@role_required("admin")
def admin_diagnostik():
    return render_template("admin_diagnostik.html", ingest_lib=ingest.ketersediaan(),
                           llm=config.llm_aktif(), model=config.LLM_MODEL,
                           reminder=config.REMINDER_HARI)


# ------------------------- Helpers -------------------------
def _int_or_none(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _semua_dokumen_ringkas(db, kecuali=None):
    rows = db.execute("SELECT id, judul, nomor, tahun FROM dokumen WHERE dihapus=0 ORDER BY judul").fetchall()
    return [dict(r) for r in rows if r["id"] != kecuali]


@app.errorhandler(403)
def err403(e):
    return render_template("error.html", kode=403, pesan="Anda tidak punya akses ke halaman ini."), 403


@app.errorhandler(404)
def err404(e):
    return render_template("error.html", kode=404, pesan="Halaman tidak ditemukan."), 404


if __name__ == "__main__":
    if not os.path.exists(config.DB_PATH):
        dbmod.init_db()
    app.run(host="0.0.0.0", port=5050, debug=True)
