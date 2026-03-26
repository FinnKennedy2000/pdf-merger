from pathlib import Path

MAX_OUTPUT_MB = 5
MAX_OUTPUT_BYTES = MAX_OUTPUT_MB * 1024 * 1024

SESSION_TTL = 3600  # 1 hour in seconds
CLEANUP_INTERVAL = 900  # 15 minutes

TEMP_DIR = Path("/tmp/sessions")

ALLOWED_EXTS = {".pdf", ".docx", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".zip"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200 MB per upload batch
