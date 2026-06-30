"""Koneksi & inisialisasi database SQLite."""
import os
import sqlite3
from flask import g

import config


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(config.DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Buat skema bila belum ada."""
    schema_path = os.path.join(config.BASE_DIR, "schema.sql")
    conn = sqlite3.connect(config.DB_PATH)
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def catat_audit(user_id, aksi, objek=None, objek_id=None, keterangan=None):
    db = get_db()
    db.execute(
        "INSERT INTO audit_log (user_id, aksi, objek, objek_id, keterangan) VALUES (?,?,?,?,?)",
        (user_id, aksi, objek, objek_id, keterangan),
    )
    db.commit()
