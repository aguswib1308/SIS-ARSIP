"""Ekstraksi teks dokumen + OCR. Semua dependensi opsional & gagal anggun.

Strategi:
  - PDF digital  -> pdfminer.six / PyMuPDF bila tersedia.
  - PDF hasil scan / gambar -> OCR (pytesseract) bila tersedia.
  - Bila tak ada pustaka atau gagal -> status 'tertunda'/'gagal', dokumen tetap tersimpan.
"""
import os


def _ekstrak_pdf(path):
    # Coba PyMuPDF dulu (cepat), lalu pdfminer.
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        teks = "\n".join(page.get_text() for page in doc)
        doc.close()
        if teks.strip():
            return teks, "pdf"
    except Exception:
        pass
    try:
        from pdfminer.high_level import extract_text
        teks = extract_text(path)
        if teks and teks.strip():
            return teks, "pdf"
    except Exception:
        pass
    return "", None


def _ocr(path):
    try:
        import pytesseract
        from PIL import Image
        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf":
            try:
                from pdf2image import convert_from_path
                halaman = convert_from_path(path)
                return "\n".join(pytesseract.image_to_string(img, lang="ind+eng") for img in halaman), "ocr"
            except Exception:
                return "", None
        else:
            img = Image.open(path)
            return pytesseract.image_to_string(img, lang="ind+eng"), "ocr"
    except Exception:
        return "", None


def ekstrak_teks(path):
    """Kembalikan (teks, metode, status). status: 'selesai'|'tertunda'|'gagal'."""
    if not os.path.exists(path):
        return "", "tertunda", "gagal"
    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        teks, metode = _ekstrak_pdf(path)
        if teks.strip():
            return teks, metode, "selesai"
        # fallback OCR untuk PDF hasil scan
        teks, metode = _ocr(path)
        if teks.strip():
            return teks, metode, "selesai"
        return "", "tertunda", "tertunda"

    if ext in (".png", ".jpg", ".jpeg", ".webp"):
        teks, metode = _ocr(path)
        if teks.strip():
            return teks, metode, "selesai"
        return "", "tertunda", "tertunda"

    if ext in (".doc", ".docx"):
        try:
            import docx  # python-docx
            d = docx.Document(path)
            teks = "\n".join(p.text for p in d.paragraphs)
            if teks.strip():
                return teks, "docx", "selesai"
        except Exception:
            pass
        return "", "tertunda", "tertunda"

    return "", "tertunda", "tertunda"


def ketersediaan():
    """Diagnostik: pustaka apa yang tersedia."""
    hasil = {}
    for nama, modul in (("PyMuPDF", "fitz"), ("pdfminer", "pdfminer"),
                        ("pytesseract", "pytesseract"), ("Pillow", "PIL"),
                        ("pdf2image", "pdf2image"), ("python-docx", "docx")):
        try:
            __import__(modul)
            hasil[nama] = True
        except Exception:
            hasil[nama] = False
    return hasil
