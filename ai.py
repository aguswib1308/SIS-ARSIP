"""Modul AI: Asisten Tanya-Jawab (RAG) + Pemeriksa Konflik (flag indikatif).

Prinsip:
  - Retrieval pakai pencocokan kata kunci atas teks dokumen (tanpa dependensi embedding berat)
    sehingga pencarian tetap jalan tanpa internet/LLM.
  - Generasi jawaban & analisis konflik memanggil LLM via gateway 9router/OpenRouter
    (kompatibel OpenAI) BILA dikonfigurasi. Bila tidak, gagal anggun: tampilkan kutipan
    relevan + catatan bahwa LLM belum aktif.
  - AI TIDAK PERNAH mengubah status/menghapus dokumen. Semua aksi konsekuensial oleh manusia.
"""
import re
import json

import config

STOPWORDS = set("""
yang dan di ke dari untuk pada dengan atau ini itu adalah dalam tidak akan oleh
sebagai juga agar bila atas para suatu kami kita mereka the of to a an and or in on
""".split())


def _tokenize(teks):
    return [t for t in re.findall(r"[a-z0-9]+", (teks or "").lower()) if t not in STOPWORDS and len(t) > 2]


def cari_relevan(db, query, limit=5, hanya_berlaku=False):
    """Retrieval sederhana: skor = jumlah kecocokan token query pada judul+teks+tag."""
    tokens = _tokenize(query)
    if not tokens:
        return []
    sql = """
        SELECT d.id, d.judul, d.nomor, d.tahun, d.status, d.pilar, d.entitas,
               d.abstraksi, COALESCE(t.teks,'') AS teks, COALESCE(d.tag,'') AS tag
        FROM dokumen d
        LEFT JOIN dokumen_teks t ON t.dokumen_id = d.id
        WHERE d.dihapus = 0
    """
    if hanya_berlaku:
        sql += " AND d.status = 'Berlaku'"
    rows = db.execute(sql).fetchall()
    hasil = []
    for r in rows:
        korpus = " ".join([r["judul"] or "", r["abstraksi"] or "", r["teks"] or "", r["tag"] or ""]).lower()
        skor = sum(korpus.count(tok) for tok in tokens)
        if skor > 0:
            cuplikan = _cuplikan(r["abstraksi"] or r["teks"] or "", tokens)
            hasil.append({
                "id": r["id"], "judul": r["judul"], "nomor": r["nomor"], "tahun": r["tahun"],
                "status": r["status"], "pilar": r["pilar"], "entitas": r["entitas"],
                "skor": skor, "cuplikan": cuplikan,
            })
    hasil.sort(key=lambda x: x["skor"], reverse=True)
    return hasil[:limit]


def _cuplikan(teks, tokens, lebar=240):
    teks = (teks or "").strip()
    if not teks:
        return ""
    low = teks.lower()
    pos = -1
    for tok in tokens:
        pos = low.find(tok)
        if pos >= 0:
            break
    if pos < 0:
        return teks[:lebar] + ("..." if len(teks) > lebar else "")
    awal = max(0, pos - 60)
    return ("..." if awal > 0 else "") + teks[awal:awal + lebar] + ("..." if awal + lebar < len(teks) else "")


def _panggil_llm(system, user):
    """Panggil LLM via gateway OpenAI-compatible. Kembalikan (teks, error)."""
    if not config.llm_aktif():
        return None, "LLM belum dikonfigurasi (ARSIP_LLM_BASE_URL / ARSIP_LLM_API_KEY kosong)."
    try:
        import requests
        url = config.LLM_BASE_URL.rstrip("/") + "/chat/completions"
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {config.LLM_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": config.LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
            },
            timeout=config.LLM_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"], None
    except Exception as e:  # gagal anggun
        return None, f"Gagal menghubungi LLM: {e}"


SYS_ASISTEN = (
    "Anda asisten hukum/kepatuhan untuk KSPPS BMT Amal Muslim (koperasi syariah, Wonogiri). "
    "Jawab HANYA berdasarkan kutipan dokumen yang diberikan. Sertakan rujukan nomor/judul dokumen. "
    "Bila informasi tidak ada di kutipan, katakan tidak ditemukan di arsip. "
    "Akhiri dengan disclaimer: ini bukan nasihat hukum/fatwa final."
)


def jawab(db, pertanyaan):
    """RAG: ambil dokumen relevan, jawab via LLM bila aktif."""
    relevan = cari_relevan(db, pertanyaan, limit=5)
    if not relevan:
        return {"jawaban": None, "relevan": [], "llm": False,
                "catatan": "Tidak ditemukan dokumen relevan di arsip untuk pertanyaan ini."}
    konteks = "\n\n".join(
        f"[Dok {r['id']}] {r['judul']} (Nomor {r['nomor'] or '-'}, {r['tahun'] or '-'}, status {r['status']}):\n{r['cuplikan']}"
        for r in relevan
    )
    teks, err = _panggil_llm(SYS_ASISTEN, f"Pertanyaan: {pertanyaan}\n\nKutipan dokumen:\n{konteks}")
    if teks:
        return {"jawaban": teks, "relevan": relevan, "llm": True, "catatan": None}
    return {"jawaban": None, "relevan": relevan, "llm": False,
            "catatan": f"Menampilkan kutipan relevan. {err}"}


SYS_KONFLIK = (
    "Anda peninjau kepatuhan syariah & hukum untuk koperasi syariah. Bandingkan DUA dokumen. "
    "Tentukan apakah ada POTENSI pertentangan (mis. aturan internal bertentangan dengan aturan lebih tinggi "
    "atau dengan fatwa DSN-MUI). Jawab dalam JSON valid dengan kunci: "
    '"ada_potensi" (true/false), "ringkasan" (1-2 kalimat), "kutipan" (bagian relevan kedua sisi), '
    '"keyakinan" ("rendah"|"sedang"|"tinggi"). Ini hanya INDIKASI untuk ditinjau manusia, bukan putusan final.'
)


def _teks_dok(db, dok_id, maks=4000):
    r = db.execute("SELECT teks FROM dokumen_teks WHERE dokumen_id=?", (dok_id,)).fetchone()
    t = (r["teks"] if r else "") or ""
    return t[:maks]


def periksa_konflik(db, dok_id, lawan_id):
    """Analisis potensi konflik dua dokumen via LLM. Kembalikan dict hasil (tidak menyimpan)."""
    a = db.execute("SELECT * FROM dokumen WHERE id=?", (dok_id,)).fetchone()
    b = db.execute("SELECT * FROM dokumen WHERE id=?", (lawan_id,)).fetchone()
    if not a or not b:
        return {"ok": False, "error": "Dokumen tidak ditemukan."}
    if not config.llm_aktif():
        return {"ok": False, "error": "LLM belum dikonfigurasi; analisis konflik otomatis tidak tersedia. "
                                      "Anda tetap dapat membuat flag manual."}
    prompt = (
        f"DOKUMEN A: {a['judul']} (Nomor {a['nomor']}, {a['tahun']}, pilar {a['pilar']}, "
        f"level {a['level_kode']}, entitas {a['entitas']}).\nIsi:\n{_teks_dok(db, dok_id)}\n\n"
        f"DOKUMEN B: {b['judul']} (Nomor {b['nomor']}, {b['tahun']}, pilar {b['pilar']}, "
        f"level {b['level_kode']}, entitas {b['entitas']}).\nIsi:\n{_teks_dok(db, lawan_id)}"
    )
    teks, err = _panggil_llm(SYS_KONFLIK, prompt)
    if not teks:
        return {"ok": False, "error": err}
    parsed = _parse_json(teks)
    if not parsed:
        return {"ok": True, "ada_potensi": True, "ringkasan": teks[:500],
                "kutipan": "", "keyakinan": "rendah", "mentah": teks}
    parsed["ok"] = True
    return parsed


def _parse_json(teks):
    m = re.search(r"\{.*\}", teks, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None
