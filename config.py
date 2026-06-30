"""Konfigurasi aplikasi arsip peraturan. Rahasia diambil dari environment variable."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "dokumen")
DB_PATH = os.path.join(DATA_DIR, "arsip.db")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# Secret key Flask: dari env, fallback file lokal (pola seperti billing).
def _secret_key():
    env = os.environ.get("ARSIP_SECRET_KEY")
    if env:
        return env
    path = os.path.join(DATA_DIR, ".secret_key")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    key = os.urandom(32).hex()
    with open(path, "w", encoding="utf-8") as f:
        f.write(key)
    return key

SECRET_KEY = _secret_key()

MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB per upload
ALLOWED_EXT = {".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".webp"}

# --- Konfigurasi LLM (9router / OpenRouter, kompatibel OpenAI Chat Completions) ---
# Bila kosong, fitur AI gagal anggun (arsip tetap jalan, analisis ditandai "tertunda").
LLM_BASE_URL = os.environ.get("ARSIP_LLM_BASE_URL", "")     # mis. http://127.0.0.1:9100/v1
LLM_API_KEY = os.environ.get("ARSIP_LLM_API_KEY", "")
LLM_MODEL = os.environ.get("ARSIP_LLM_MODEL", "claude-opus-4-8")
LLM_TIMEOUT = int(os.environ.get("ARSIP_LLM_TIMEOUT", "60"))

# Ambang pengingat masa berlaku izin (hari). Terkonfirmasi user: H-30.
REMINDER_HARI = int(os.environ.get("ARSIP_REMINDER_HARI", "30"))

def llm_aktif():
    return bool(LLM_BASE_URL and LLM_API_KEY)
